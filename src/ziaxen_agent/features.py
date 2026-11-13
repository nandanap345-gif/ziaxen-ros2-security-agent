"""Causal temporal feature engineering for aligned IMU and odometry signals."""

from __future__ import annotations

import numpy as np
import pandas as pd


TIME_COLUMNS = {"sim_time_ns", "sim_time_s", "t_rel_s"}
LABEL_COLUMNS = {"is_attack", "is_attack_event", "attack_type", "attack_target", "attack_id"}
ROLLING_WINDOW_ROWS = 25  # 0.5 seconds at the dataset's documented 50 Hz.


def sensor_columns(frame: pd.DataFrame) -> list[str]:
    """Return numeric sensor columns while excluding timestamps, labels, and metadata."""
    columns: list[str] = []
    for name in frame.columns:
        if name in TIME_COLUMNS or name in LABEL_COLUMNS:
            continue
        if not str(name).startswith(("imu.", "odom.", "contact.")):
            continue
        values = pd.to_numeric(frame[name], errors="coerce")
        if values.notna().any():
            columns.append(str(name))
    return columns


def engineer_features(
    frame: pd.DataFrame,
    expected_raw_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Create raw, per-second change, and trailing variability features.

    Rolling windows only use current and past rows, so they are suitable for
    recorded-stream inference without looking ahead.
    """
    available = sensor_columns(frame)
    raw_columns = expected_raw_columns if expected_raw_columns is not None else available
    if not raw_columns:
        raise ValueError(
            "No numeric IMU, odometry, or contact columns were found in the input."
        )

    features: dict[str, pd.Series] = {}
    numeric: dict[str, pd.Series] = {}
    for column in raw_columns:
        if column in frame:
            numeric[column] = pd.to_numeric(frame[column], errors="coerce")
        else:
            numeric[column] = pd.Series(np.nan, index=frame.index, dtype=float)
        features[f"raw::{column}"] = numeric[column]

    if "sim_time_s" in frame:
        times = pd.to_numeric(frame["sim_time_s"], errors="coerce")
    elif "sim_time_ns" in frame:
        times = pd.to_numeric(frame["sim_time_ns"], errors="coerce") / 1e9
    else:
        raise ValueError("Input must contain sim_time_s or sim_time_ns.")
    delta_time = times.diff()
    valid_delta = delta_time.where(delta_time.gt(0) & delta_time.le(0.2))

    for column, values in numeric.items():
        name = column.replace("::", "_")
        changes_per_second = values.diff().div(valid_delta)
        features[f"rate::{name}"] = changes_per_second
        features[f"rolling_std::{name}"] = values.rolling(
            ROLLING_WINDOW_ROWS, min_periods=5
        ).std()
    result = pd.DataFrame(features, index=frame.index)
    result = result.replace([np.inf, -np.inf], np.nan)
    return result
