import json

import numpy as np
import pandas as pd

from ziaxen_agent.external_adapter import adapt_external_csv, adapt_external_frame


def _bundle():
    columns = [
        "imu.linear_acceleration.x",
        "imu.angular_velocity.x",
        "odom.pose.pose.position.x",
        "odom.twist.twist.linear.x",
        "imu.orientation.x",
        "odom.age_s",
        "contact.data",
        "odom.pose.pose.position.y",
        "odom.pose.pose.position.z",
    ]
    return {
        "raw_sensor_columns": columns,
        "normal_reference": {
            "median": {f"raw::{column}": 10.0 for column in columns}
        },
    }


def test_external_adapter_resamples_converts_units_and_marks_sparse_mapping():
    source = pd.DataFrame(
        {
            "time_s": [0.0, 0.05, 0.10],
            "acc_x": [1.0, 2.0, 3.0],
            "gyro_x": [180.0, 90.0, 0.0],
            "position_x": [0.0, 0.05, 0.10],
            "odom_age_s": [np.nan, np.nan, np.nan],
        }
    )

    result = adapt_external_frame(
        source,
        _bundle(),
        units={
            "acceleration": "g",
            "angular_velocity": "deg/s",
            "position": "m",
            "velocity": "m/s",
        },
    )

    assert len(result.frame) == 6
    assert result.frame["sim_time_s"].iloc[-1] == 0.1
    assert result.frame["imu.linear_acceleration.x"].iloc[0] == 9.80665
    assert result.frame["imu.angular_velocity.x"].iloc[0] == np.pi
    assert result.frame["odom.twist.twist.linear.x"].iloc[-1] == 1.0
    assert result.frame["imu.orientation.x"].eq(10.0).all()
    assert result.mapping["coverage"]["missing_fraction"] > 0.5
    missing_age = next(
        item
        for item in result.mapping["missing_columns_filled_with_training_median"]
        if item["model_column"] == "odom.age_s"
    )
    assert missing_age["rows_filled"] == len(result.frame)
    assert not missing_age["column_absent"]
    assert result.frame["odom.age_s"].eq(10.0).all()
    assert not result.applicable


def test_external_csv_writes_mapping_for_not_applicable_dataset(tmp_path):
    source_path = tmp_path / "recording.csv"
    mapping_path = tmp_path / "reports" / "recording_mapping.json"
    pd.DataFrame(
        {"time_s": [0.0, 0.05], "acc_x": [0.0, 0.1]}
    ).to_csv(source_path, index=False)

    result = adapt_external_csv(source_path, _bundle(), mapping_path=mapping_path)

    assert not result.applicable
    assert json.loads(mapping_path.read_text(encoding="utf-8")) == result.mapping
