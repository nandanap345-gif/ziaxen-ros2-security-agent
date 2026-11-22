"""Adapt external sensor CSV recordings to the frozen noise-model input schema."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


_ALIASES: dict[str, tuple[str, ...]] = {
    "imu.linear_acceleration.x": ("acc_x", "accel_x", "acceleration_x", "linear_acceleration_x"),
    "imu.linear_acceleration.y": ("acc_y", "accel_y", "acceleration_y", "linear_acceleration_y"),
    "imu.linear_acceleration.z": ("acc_z", "accel_z", "acceleration_z", "linear_acceleration_z"),
    "imu.angular_velocity.x": ("gyro_x", "gyroscope_x", "angular_velocity_x"),
    "imu.angular_velocity.y": ("gyro_y", "gyroscope_y", "angular_velocity_y"),
    "imu.angular_velocity.z": ("gyro_z", "gyroscope_z", "angular_velocity_z"),
    "imu.orientation.x": ("imu_orientation_x", "orientation_x", "quat_x"),
    "imu.orientation.y": ("imu_orientation_y", "orientation_y", "quat_y"),
    "imu.orientation.z": ("imu_orientation_z", "orientation_z", "quat_z"),
    "imu.orientation.w": ("imu_orientation_w", "orientation_w", "quat_w"),
    "odom.pose.pose.position.x": ("position_x", "pos_x", "odom_x", "x_position"),
    "odom.pose.pose.position.y": ("position_y", "pos_y", "odom_y", "y_position"),
    "odom.pose.pose.position.z": ("position_z", "pos_z", "odom_z", "z_position"),
    "odom.twist.twist.linear.x": ("velocity_x", "vel_x", "speed_x", "linear_velocity_x"),
    "odom.twist.twist.linear.y": ("velocity_y", "vel_y", "speed_y", "linear_velocity_y"),
    "odom.twist.twist.linear.z": ("velocity_z", "vel_z", "linear_velocity_z"),
    "odom.twist.twist.angular.x": ("odom_angular_velocity_x", "angular_rate_x"),
    "odom.twist.twist.angular.y": ("odom_angular_velocity_y", "angular_rate_y"),
    "odom.twist.twist.angular.z": ("odom_angular_velocity_z", "angular_rate_z"),
    "odom.pose.pose.orientation.x": ("odom_orientation_x", "odom_quat_x"),
    "odom.pose.pose.orientation.y": ("odom_orientation_y", "odom_quat_y"),
    "odom.pose.pose.orientation.z": ("odom_orientation_z", "odom_quat_z"),
    "odom.pose.pose.orientation.w": ("odom_orientation_w", "odom_quat_w"),
    "contact.data": ("contact", "contact_data"),
}
_TIME_ALIASES = ("sim_time_s", "time_s", "timestamp_s", "time", "timestamp", "sim_time_ns", "time_ns", "timestamp_ns")
_UNIT_FACTORS = {
    "acceleration": {"m/s^2": 1.0, "m/s2": 1.0, "g": 9.80665},
    "angular_velocity": {"rad/s": 1.0, "deg/s": np.pi / 180.0},
    "position": {"m": 1.0, "cm": 0.01, "mm": 0.001},
    "velocity": {"m/s": 1.0, "cm/s": 0.01, "km/h": 1.0 / 3.6},
}
_DEFAULT_UNITS = {
    "acceleration": "m/s^2",
    "angular_velocity": "rad/s",
    "position": "m",
    "velocity": "m/s",
}


@dataclass
class ExternalAdaptation:
    """Resampled sensor values plus provenance and model-applicability status."""

    frame: pd.DataFrame
    mapping: dict[str, Any]
    applicable: bool


def _normalized_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def _time_seconds(frame: pd.DataFrame, column: str) -> pd.Series:
    values = frame[column]
    normalized = _normalized_name(column)
    if normalized.endswith("ns"):
        numeric = pd.to_numeric(values, errors="coerce") / 1e9
    elif normalized.endswith("ms"):
        numeric = pd.to_numeric(values, errors="coerce") / 1e3
    else:
        numeric = pd.to_numeric(values, errors="coerce")
    if numeric.notna().all():
        return numeric.astype(float)
    parsed = pd.to_datetime(values, errors="coerce", utc=True)
    if parsed.isna().any():
        raise ValueError(f"External time column {column!r} contains invalid values.")
    return (parsed - parsed.iloc[0]).dt.total_seconds().astype(float)


def _unit_category(column: str) -> str | None:
    if "linear_acceleration" in column:
        return "acceleration"
    if "angular_velocity" in column or ".angular." in column:
        return "angular_velocity"
    if ".position." in column:
        return "position"
    if ".linear." in column:
        return "velocity"
    return None


def _training_median(bundle: dict[str, Any], column: str) -> float:
    value = bundle.get("normal_reference", {}).get("median", {}).get(f"raw::{column}")
    if value is None or not np.isfinite(float(value)):
        raise ValueError(f"The frozen model has no finite training median for {column!r}.")
    return float(value)


def adapt_external_frame(
    source: pd.DataFrame,
    model_bundle: dict[str, Any],
    *,
    time_column: str | None = None,
    units: dict[str, str] | None = None,
    column_map: dict[str, str] | None = None,
) -> ExternalAdaptation:
    """Map and resample a sensor table to the noise model's 50 Hz raw schema.

    ``units`` overrides the SI defaults for acceleration, angular velocity,
    position, and velocity. Coordinates are mapped by axis only; no frame
    rotation or vehicle-specific calibration is inferred.
    """
    if source.empty:
        raise ValueError("External sensor CSV is empty.")
    raw_columns = model_bundle.get("raw_sensor_columns")
    if not isinstance(raw_columns, list) or not raw_columns:
        raise ValueError("The frozen noise model has no raw sensor schema.")

    if time_column is None:
        normalized_times = {_normalized_name(name): name for name in source.columns}
        time_column = next(
            (normalized_times[_normalized_name(alias)] for alias in _TIME_ALIASES
             if _normalized_name(alias) in normalized_times),
            None,
        )
    if time_column is None or time_column not in source:
        raise ValueError("External CSV must include a recognizable timestamp column.")

    times = _time_seconds(source, time_column)
    if times.isna().any():
        raise ValueError(f"External time column {time_column!r} contains invalid values.")
    order = np.argsort(times.to_numpy(), kind="stable")
    ordered = source.iloc[order].reset_index(drop=True)
    times = times.iloc[order].reset_index(drop=True)
    if len(times) < 2 or float(times.iloc[-1]) <= float(times.iloc[0]):
        raise ValueError("External timestamps must span at least two distinct times.")

    unit_settings = dict(_DEFAULT_UNITS)
    unit_settings.update(units or {})
    unknown_units = set(unit_settings).difference(_UNIT_FACTORS)
    if unknown_units:
        raise ValueError(f"Unsupported unit categories: {sorted(unknown_units)}")
    for category, unit in unit_settings.items():
        if unit not in _UNIT_FACTORS[category]:
            raise ValueError(f"Unsupported {category} unit: {unit!r}.")

    normalized_columns: dict[str, list[str]] = {}
    for name in ordered.columns:
        normalized_columns.setdefault(_normalized_name(str(name)), []).append(str(name))

    explicit_map = column_map or {}
    invalid_targets = set(explicit_map).difference(raw_columns)
    if invalid_targets:
        raise ValueError(f"Explicit map contains unknown model columns: {sorted(invalid_targets)}")

    mapped: dict[str, pd.Series] = {}
    mapped_records: list[dict[str, Any]] = []
    derived_records: list[dict[str, Any]] = []
    for target in raw_columns:
        candidate_names = [target, *_ALIASES.get(target, ())]
        requested = explicit_map.get(target)
        if requested is not None:
            if requested not in ordered:
                raise ValueError(f"Mapped source column {requested!r} is not in the CSV.")
            matches = [requested]
        else:
            matches = [
                candidate
                for alias in candidate_names
                for candidate in normalized_columns.get(_normalized_name(alias), [])
            ]
            matches = list(dict.fromkeys(matches))
        if len(matches) > 1:
            raise ValueError(
                f"Multiple source columns match model input {target!r}: {matches}. "
                "Provide an explicit column_map."
            )
        if not matches:
            continue
        source_column = matches[0]
        values = pd.to_numeric(ordered[source_column], errors="coerce")
        category = _unit_category(target)
        unit = unit_settings.get(category, "dimensionless") if category else "dimensionless"
        factor = _UNIT_FACTORS[category][unit] if category else 1.0
        mapped[target] = values.astype(float) * factor
        mapped_records.append(
            {
                "source_column": source_column,
                "model_column": target,
                "unit_category": category,
                "source_unit": unit,
                "conversion_factor_to_training_units": float(factor),
            }
        )

    for axis in "xyz":
        position = f"odom.pose.pose.position.{axis}"
        velocity = f"odom.twist.twist.linear.{axis}"
        if velocity not in mapped and position in mapped:
            mapped[velocity] = mapped[position].diff().div(times.diff()).replace(
                [np.inf, -np.inf], np.nan
            )
            derived_records.append(
                {
                    "model_column": velocity,
                    "method": f"causal first difference of {position} over source timestamps",
                    "unit": unit_settings["velocity"],
                }
            )

    start_time = float(times.iloc[0])
    elapsed = times - start_time
    sample_index = pd.to_timedelta(elapsed, unit="s")
    source_values = pd.DataFrame(
        {name: values.to_numpy(dtype=float) for name, values in mapped.items()},
        index=sample_index,
    )
    source_values = source_values.groupby(level=0).mean().sort_index()
    resampled = source_values.resample("20ms").mean().interpolate(
        method="time", limit_direction="both"
    )
    if resampled.empty:
        raise ValueError("External data did not produce any 50 Hz samples.")

    missing_columns = [
        column
        for column in raw_columns
        if column not in resampled or resampled[column].notna().sum() == 0
    ]
    absent_columns = set(raw_columns).difference(resampled.columns)
    missing_records = []
    for column in raw_columns:
        median = _training_median(model_bundle, column)
        if column in resampled:
            missing_count = int(resampled[column].isna().sum())
            resampled[column] = resampled[column].fillna(median)
        else:
            missing_count = len(resampled)
            resampled[column] = median
        if column in missing_columns or missing_count:
            missing_records.append(
                {
                    "model_column": column,
                    "training_median": median,
                    "rows_filled": missing_count,
                    "column_absent": column in absent_columns,
                }
            )
    resampled = resampled.reindex(columns=raw_columns)
    output_time = np.arange(len(resampled), dtype=float) / 50.0
    resampled.insert(0, "sim_time_s", output_time)
    resampled.insert(0, "sim_time_ns", np.rint(output_time * 1e9).astype(np.int64))

    mapped_count = len(raw_columns) - len(missing_columns)
    missing_count = len(raw_columns) - mapped_count
    missing_fraction = missing_count / len(raw_columns)
    applicable = missing_fraction <= 0.5
    mapping = {
        "source_timestamp_column": time_column,
        "source_start_time": start_time,
        "target_rate_hz": 50,
        "mapped_columns": mapped_records,
        "derived_columns": derived_records,
        "missing_columns_filled_with_training_median": missing_records,
        "coverage": {
            "model_raw_columns": len(raw_columns),
            "mapped_or_derived_columns": mapped_count,
            "missing_column_count": missing_count,
            "missing_fraction": missing_fraction,
            "applicable": applicable,
        },
        "unit_assumptions": unit_settings,
        "coordinate_frame_transform": "none; axis labels are mapped as supplied",
    }
    return ExternalAdaptation(frame=resampled, mapping=mapping, applicable=applicable)


def adapt_external_csv(
    input_path: str | Path,
    model_bundle: dict[str, Any],
    *,
    time_column: str | None = None,
    units: dict[str, str] | None = None,
    column_map: dict[str, str] | None = None,
    mapping_path: str | Path | None = None,
) -> ExternalAdaptation:
    """Read an external CSV and adapt it to the frozen noise model.

    When ``mapping_path`` is supplied, write the mapping even if the data is
    not applicable, so the reason for skipping metrics is preserved.
    """
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"External CSV was not found: {path}")
    try:
        source = pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise ValueError(f"Could not read external CSV {path}: {error}") from error
    result = adapt_external_frame(
        source,
        model_bundle,
        time_column=time_column,
        units=units,
        column_map=column_map,
    )
    if mapping_path is not None:
        destination = Path(mapping_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(result.mapping, indent=2) + "\n", encoding="utf-8"
        )
    return result
