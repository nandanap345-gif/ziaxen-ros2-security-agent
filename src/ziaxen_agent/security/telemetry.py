"""Validation and causal feature preparation for recorded telemetry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..data import event_labels
from .alerts import Finding


TIME_COLUMNS = {"sim_time_ns", "sim_time_s"}
LABEL_COLUMNS = {"is_attack", "attack_type", "attack_target", "attack_id"}
EXPECTED_EMPTY_COLUMNS = {"new_nodes", "contact_mon.stamp_lag_mean_s"}


def load_telemetry(path: str | Path) -> pd.DataFrame:
    telemetry_path = Path(path)
    if not telemetry_path.is_file():
        raise FileNotFoundError(f"Telemetry file was not found: {telemetry_path}")
    try:
        frame = pd.read_csv(telemetry_path)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise ValueError(f"Could not read telemetry file {telemetry_path}: {error}") from error
    if frame.empty:
        raise ValueError(f"Telemetry file is empty: {telemetry_path}")
    return frame


def event_labels_for_telemetry(
    telemetry: pd.DataFrame, events: pd.DataFrame
) -> np.ndarray:
    """Reuse the project's event-derived start-inclusive/stop-exclusive labels."""
    return event_labels(telemetry, events)


def telemetry_health_findings(
    frame: pd.DataFrame,
    run_id: str,
    *,
    timestamp_ns: int | None = None,
    stale_tick_multiple: int = 3,
    tick_seconds: float = 0.5,
    collector_drop_column: str = "collector_queue_drops",
) -> list[Finding]:
    findings: list[Finding] = []
    if "sim_time_ns" not in frame:
        return [
            Finding(
                rule_id="missing_timestamp",
                timestamp_sim_ns=timestamp_ns or 0,
                run_id=run_id,
                source="health",
                severity="high",
                evidence={"missing_column": "sim_time_ns"},
                what_this_does_not_prove="A missing timestamp prevents reliable ordering and latency analysis.",
                recommended_next_step="Verify the telemetry export schema and regenerate the recording if possible.",
            )
        ]
    times = pd.to_numeric(frame["sim_time_ns"], errors="coerce")
    valid_times = times.dropna()
    now = int(timestamp_ns if timestamp_ns is not None else valid_times.iloc[-1]) if len(valid_times) else 0
    for column in frame.columns:
        if frame[column].isna().all() and column not in EXPECTED_EMPTY_COLUMNS:
            findings.append(
                Finding(
                    rule_id="all_nan_column",
                    timestamp_sim_ns=now,
                    run_id=run_id,
                    source="health",
                    severity="info",
                    evidence={"column": str(column), "row_count": len(frame)},
                    what_this_does_not_prove="An empty telemetry field may be unsupported by this source, not an attack.",
                    recommended_next_step="Check whether this field is expected for the current topic and collector.",
                )
            )
    if times.isna().any():
        findings.append(
            Finding(
                rule_id="invalid_timestamp",
                timestamp_sim_ns=now,
                run_id=run_id,
                source="health",
                severity="high",
                evidence={"invalid_timestamp_rows": int(times.isna().sum())},
                what_this_does_not_prove="Invalid timestamps do not identify the cause of the data-quality problem.",
                recommended_next_step="Check the collector clock and the telemetry export.",
            )
        )
        return findings

    steps = np.diff(times.to_numpy(dtype=np.float64)) / 1e9
    duplicate_count = int((steps == 0).sum())
    out_of_order_count = int((steps < 0).sum())
    if duplicate_count:
        findings.append(
            Finding(
                rule_id="duplicate_ticks",
                timestamp_sim_ns=now,
                run_id=run_id,
                source="health",
                severity="medium",
                evidence={"duplicate_tick_count": duplicate_count, "timestamp_column": "sim_time_ns"},
                what_this_does_not_prove="Duplicate ticks may result from collection or export behaviour.",
                recommended_next_step="Check source tick generation and deduplication before interpreting rates.",
            )
        )
    if out_of_order_count:
        findings.append(
            Finding(
                rule_id="out_of_order_ticks",
                timestamp_sim_ns=now,
                run_id=run_id,
                source="health",
                severity="high",
                evidence={"out_of_order_tick_count": out_of_order_count, "timestamp_column": "sim_time_ns"},
                what_this_does_not_prove="Out-of-order rows do not establish replay or malicious activity.",
                recommended_next_step="Verify ordering at the collector and preserve original timestamps.",
            )
        )
    stale_limit = stale_tick_multiple * tick_seconds
    stale_steps = np.flatnonzero(steps > stale_limit)
    for position in stale_steps:
        findings.append(
            Finding(
                rule_id="stale_telemetry",
                timestamp_sim_ns=int(times.iloc[position + 1]),
                run_id=run_id,
                source="health",
                severity="medium",
                evidence={
                    "gap_s": float(steps[position]),
                    "threshold_s": stale_limit,
                    "from_sim_time_ns": int(times.iloc[position]),
                    "to_sim_time_ns": int(times.iloc[position + 1]),
                },
                what_this_does_not_prove="A telemetry gap can result from collection loss or simulation scheduling.",
                recommended_next_step="Check collector health and compare with independent system logs.",
            )
        )
    if collector_drop_column in frame:
        drops = pd.to_numeric(frame[collector_drop_column], errors="coerce")
        observed = drops.dropna()
        if not observed.empty and float(observed.max()) > 0:
            findings.append(
                Finding(
                    rule_id="collector_drops",
                    timestamp_sim_ns=now,
                    run_id=run_id,
                    source="health",
                    severity="medium",
                    evidence={
                        "column": collector_drop_column,
                        "maximum_cumulative_drops": float(observed.max()),
                    },
                    what_this_does_not_prove="Collector drops indicate observability loss, not an attack by themselves.",
                    recommended_next_step="Resolve telemetry collection loss before relying on negative findings.",
                )
            )
    return findings


def telemetry_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Create numeric, label-free, causal features from a telemetry table."""
    numeric: dict[str, pd.Series] = {}
    for column in frame.columns:
        if column in TIME_COLUMNS or column in LABEL_COLUMNS:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        if values.notna().any():
            numeric[str(column)] = values.astype(float)

    features = pd.DataFrame(numeric, index=frame.index)
    if "new_nodes" in frame:
        nodes = frame["new_nodes"].fillna("").astype(str).str.strip()
        features["derived::new_node_count"] = nodes.map(
            lambda value: len([item for item in value.split(";") if item.strip()])
        ).astype(float)
        features["derived::has_new_nodes"] = nodes.ne("").astype(float)
    if "node_list_hash" in frame:
        hashes = frame["node_list_hash"].fillna("").astype(str)
        features["derived::node_hash_changed"] = hashes.ne(hashes.shift(1)).astype(float)

    if "sim_time_s" in frame:
        times = pd.to_numeric(frame["sim_time_s"], errors="coerce")
    elif "sim_time_ns" in frame:
        times = pd.to_numeric(frame["sim_time_ns"], errors="coerce") / 1e9
    else:
        raise ValueError("Telemetry must contain sim_time_s or sim_time_ns.")
    delta = times.diff()
    valid_delta = delta.where(delta.gt(0) & delta.le(2.0))
    for column, values in numeric.items():
        features[f"derived::rate::{column}"] = values.diff().div(valid_delta)
        features[f"derived::rolling_std::{column}"] = values.rolling(
            window=5, min_periods=2
        ).std()
    return features.replace([np.inf, -np.inf], np.nan)
