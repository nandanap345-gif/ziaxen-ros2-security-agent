"""Saved-model sensor-noise agent for recorded or incoming data frames."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .features import engineer_features, sensor_columns
from .models import anomaly_scores, explain_row


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


class SensorNoiseAgent:
    """Score each timestamp and return anomaly status plus feature context."""

    def __init__(self, bundle: dict[str, Any], threshold: float | None = None):
        if bundle.get("task") != "normal_vs_sensor_noise":
            raise ValueError("The saved model is not a normal-vs-sensor-noise model.")
        self.bundle = bundle
        self.model_name = str(bundle["selected_model"])
        self.model = bundle["models"][self.model_name]
        self.threshold = float(
            bundle["thresholds"][self.model_name] if threshold is None else threshold
        )

    @classmethod
    def load(cls, model_path: str | Path, threshold: float | None = None):
        path = Path(model_path)
        if not path.is_file():
            raise FileNotFoundError(f"Saved model was not found: {path}")
        return cls(joblib.load(path), threshold=threshold)

    def predict(self, frame: pd.DataFrame) -> list[dict[str, Any]]:
        """Return one alert/result record per input row."""
        if frame.empty:
            return []
        time_column = "sim_time_s" if "sim_time_s" in frame else "sim_time_ns"
        if time_column not in frame:
            raise ValueError("Incoming data must contain sim_time_s or sim_time_ns.")
        times = pd.to_numeric(frame[time_column], errors="coerce")
        if times.isna().any():
            raise ValueError(f"Incoming data has invalid values in {time_column}.")
        if not times.is_monotonic_increasing:
            raise ValueError("Incoming timestamps must be in non-decreasing order.")
        available_sensor_columns = sensor_columns(frame)
        if not available_sensor_columns:
            raise ValueError(
                "Incoming data must include at least one numeric IMU, odometry, "
                "or contact field."
            )
        missing_sensor_columns = sorted(
            set(self.bundle["raw_sensor_columns"]) - set(available_sensor_columns)
        )
        unexpected_sensor_columns = sorted(
            set(available_sensor_columns) - set(self.bundle["raw_sensor_columns"])
        )
        engineered = engineer_features(
            frame, expected_raw_columns=self.bundle["raw_sensor_columns"]
        ).reindex(columns=self.bundle["feature_columns"])
        scores = anomaly_scores(self.model, self.model_name, engineered)
        results: list[dict[str, Any]] = []
        metadata_columns = [
            column
            for column in frame.columns
            if column not in self.bundle["raw_sensor_columns"]
        ]
        for index, (_, row) in enumerate(frame.iterrows()):
            score = float(scores[index])
            anomaly = score >= self.threshold
            result = {
                "timestamp": _json_value(row[time_column]),
                "timestamp_unit": "seconds" if time_column == "sim_time_s" else "nanoseconds",
                "anomaly_status": "anomaly" if anomaly else "normal",
                "anomaly": bool(anomaly),
                "anomaly_score": score,
                "threshold": self.threshold,
                "model": self.model_name,
                "responsible_features": (
                    explain_row(engineered.iloc[index], self.bundle["normal_reference"])
                    if anomaly
                    else []
                ),
                "input_metadata": {
                    str(column): _json_value(row[column]) for column in metadata_columns
                },
                "input_warnings": {
                    "missing_sensor_columns": missing_sensor_columns,
                    "ignored_unexpected_sensor_columns": unexpected_sensor_columns,
                },
            }
            results.append(result)
        return results

    def predict_file(self, input_path: str | Path) -> list[dict[str, Any]]:
        """Load a CSV/CSV.GZ recording and return its row-wise alerts."""
        path = Path(input_path)
        if not path.is_file():
            raise FileNotFoundError(f"Input recording was not found: {path}")
        return self.predict(pd.read_csv(path))
