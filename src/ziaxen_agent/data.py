"""Dataset discovery, loading, and event-based label validation."""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPECTED_ALIGNED_HZ = 50.0
EXPECTED_TELEMETRY_HZ = 2.0


@dataclass
class RunData:
    """All data and provenance for one dataset run."""

    run_id: str
    relative_path: str
    metadata: dict[str, Any]
    aligned: pd.DataFrame
    telemetry: pd.DataFrame
    events: pd.DataFrame


def _plain(value: Any) -> Any:
    """Convert pandas/numpy values to JSON-friendly Python values."""
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def event_labels(aligned: pd.DataFrame, events: pd.DataFrame) -> np.ndarray:
    """Build row labels from event start/stop timestamps, never from CSV labels."""
    if "sim_time_ns" not in aligned:
        raise ValueError("aligned.csv.gz must contain sim_time_ns.")
    times = pd.to_numeric(aligned["sim_time_ns"], errors="coerce")
    if times.isna().any():
        raise ValueError("aligned.csv.gz contains missing or invalid sim_time_ns values.")
    labels = np.zeros(len(aligned), dtype=np.int8)
    if events.empty:
        return labels

    required = {"sim_time_ns", "event", "attack_id", "attack_type"}
    missing = required.difference(events.columns)
    if missing:
        raise ValueError(f"events.csv is missing required columns: {sorted(missing)}")

    event_frame = events.copy()
    event_frame["event"] = event_frame["event"].astype(str).str.lower()
    for attack_id, group in event_frame.groupby("attack_id", dropna=False):
        starts = group.loc[group["event"].eq("start"), "sim_time_ns"]
        stops = group.loc[group["event"].eq("stop"), "sim_time_ns"]
        if len(starts) != 1 or len(stops) != 1:
            raise ValueError(
                f"Attack {attack_id!r} must have exactly one start and one stop event."
            )
        start_ns = int(pd.to_numeric(starts.iloc[0], errors="raise"))
        stop_ns = int(pd.to_numeric(stops.iloc[0], errors="raise"))
        if stop_ns <= start_ns:
            raise ValueError(f"Attack {attack_id!r} has a non-positive event duration.")
        active = (times >= start_ns) & (times < stop_ns)
        labels[active.to_numpy()] = 1
    return labels


def _validate_event_labels(aligned: pd.DataFrame, labels: np.ndarray, run_id: str) -> None:
    """Compare stored label columns with the authoritative event-derived labels."""
    if "is_attack" not in aligned:
        return
    stored = pd.to_numeric(aligned["is_attack"], errors="coerce")
    if stored.isna().any():
        raise ValueError(f"{run_id}: is_attack contains missing or invalid values.")
    mismatch = int((stored.to_numpy(dtype=np.int8) != labels).sum())
    if mismatch:
        raise ValueError(
            f"{run_id}: events.csv and aligned.csv.gz disagree on {mismatch} row labels."
        )


def load_runs(
    data_root: str | Path,
    seeds: set[int] | None = None,
    expected_counts: bool = False,
) -> list[RunData]:
    """Load normal runs and the 27 noise runs indexed by dataset_index.csv."""
    root = Path(data_root).expanduser().resolve()
    index_path = root / "dataset_index.csv"
    if not index_path.is_file():
        raise FileNotFoundError(
            f"dataset_index.csv was not found under {root}. "
            "Point --data-root to the AI_team_data directory."
        )
    index = pd.read_csv(index_path)
    required_index = {"relative_path", "type", "attack_name", "npc", "seed", "level"}
    missing_index = required_index.difference(index.columns)
    if missing_index:
        raise ValueError(f"dataset_index.csv is missing columns: {sorted(missing_index)}")

    selected = index.loc[
        index["type"].eq("normal") | index["attack_name"].eq("noise")
    ].copy()
    if seeds is not None:
        selected = selected.loc[pd.to_numeric(selected["seed"]).isin(seeds)]
    if expected_counts:
        checked_seeds = seeds if seeds is not None else {1, 2, 3}
        normal_count = int(selected["type"].eq("normal").sum())
        noise_count = int(selected["attack_name"].eq("noise").sum())
        expected_normal_count = 3 * len(checked_seeds)
        expected_noise_count = 9 * len(checked_seeds)
        if (normal_count, noise_count) != (
            expected_normal_count,
            expected_noise_count,
        ):
            raise ValueError(
                f"Expected {expected_normal_count} normal and "
                f"{expected_noise_count} noise runs, found "
                f"{normal_count} normal and {noise_count} noise runs."
            )
        noise_rows = selected.loc[selected["attack_name"].eq("noise")]
        observed = {
            (int(row.level), int(row.npc), int(row.seed))
            for row in noise_rows.itertuples(index=False)
        }
        expected = set(
            product((1, 2, 3), (10, 20, 30), checked_seeds)
        )
        if observed != expected:
            missing = sorted(expected - observed)
            extra = sorted(observed - expected)
            raise ValueError(
                f"Noise scenario coverage is incomplete; missing={missing}, extra={extra}."
            )
        normal_rows = selected.loc[selected["type"].eq("normal")]
        observed_normal = {
            (int(row.npc), int(row.seed))
            for row in normal_rows.itertuples(index=False)
        }
        expected_normal = set(product((10, 20, 30), checked_seeds))
        if observed_normal != expected_normal:
            missing = sorted(expected_normal - observed_normal)
            extra = sorted(observed_normal - expected_normal)
            raise ValueError(
                f"Normal scenario coverage is incomplete; missing={missing}, extra={extra}."
            )
        if "status" in index and not index.loc[selected.index, "status"].eq("completed").all():
            raise ValueError("Selected normal/noise index rows must all be completed.")

    runs: list[RunData] = []
    missing_files: list[str] = []
    for _, row in selected.iterrows():
        relative_path = str(row["relative_path"])
        run_path = (root / relative_path).resolve()
        if root not in run_path.parents:
            raise ValueError(f"Unsafe dataset_index.csv path: {relative_path}")
        file_paths = {
            "aligned": run_path / "aligned.csv.gz",
            "telemetry": run_path / "telemetry.csv.gz",
            "events": run_path / "events.csv",
            "manifest": run_path / "manifest.json",
        }
        for key, path in file_paths.items():
            if not path.is_file():
                missing_files.append(f"{relative_path}/{path.name}")
        if any(not path.is_file() for path in file_paths.values()):
            continue

        aligned = pd.read_csv(file_paths["aligned"])
        telemetry = pd.read_csv(file_paths["telemetry"])
        events = pd.read_csv(file_paths["events"])
        manifest = json.loads(file_paths["manifest"].read_text(encoding="utf-8"))
        labels = event_labels(aligned, events)
        run_id = str(manifest.get("scenario") or Path(relative_path).name)
        _validate_event_labels(aligned, labels, run_id)
        telemetry_labels = event_labels(telemetry, events)
        _validate_event_labels(telemetry, telemetry_labels, f"{run_id} telemetry")
        aligned["is_attack_event"] = labels

        indexed_type = str(row["type"])
        indexed_attack = str(row["attack_name"])
        event_types = set(events["attack_type"].dropna().astype(str)) if not events.empty else set()
        if indexed_type == "normal" and labels.any():
            raise ValueError(f"{run_id}: normal run has attack events.")
        if indexed_attack == "noise" and event_types and event_types != {"noise"}:
            raise ValueError(
                f"{run_id}: dataset index says noise but events contain {sorted(event_types)}."
            )

        metadata = {key: _plain(value) for key, value in row.to_dict().items()}
        metadata["manifest"] = manifest
        metadata["event_types"] = sorted(event_types)
        runs.append(
            RunData(
                run_id=run_id,
                relative_path=relative_path,
                metadata=metadata,
                aligned=aligned,
                telemetry=telemetry,
                events=events,
            )
        )

    if missing_files:
        preview = "\n".join(f"  - {item}" for item in missing_files[:20])
        more = f"\n  ... and {len(missing_files) - 20} more" if len(missing_files) > 20 else ""
        raise FileNotFoundError(f"Dataset files are missing:\n{preview}{more}")
    if not runs:
        raise ValueError("No normal or noise runs were found for the requested seed split.")
    return runs


def _median_rate(frame: pd.DataFrame) -> float | None:
    """Estimate sampling rate from strictly increasing sim_time_s values."""
    if "sim_time_s" not in frame or len(frame) < 2:
        return None
    times = pd.to_numeric(frame["sim_time_s"], errors="coerce").dropna().to_numpy()
    steps = np.diff(times)
    positive = steps[steps > 0]
    if len(positive) == 0:
        return None
    return float(1.0 / np.median(positive))


def inspect_runs(runs: list[RunData]) -> dict[str, Any]:
    """Summarize schemas, missingness, sample rates, event timing, and run metadata."""
    if not runs:
        raise ValueError("Cannot inspect an empty run list.")
    aligned_columns = list(runs[0].aligned.columns)
    telemetry_columns = list(runs[0].telemetry.columns)
    mismatched_aligned = {
        run.run_id: sorted(set(aligned_columns).symmetric_difference(run.aligned.columns))
        for run in runs
        if set(aligned_columns) != set(run.aligned.columns)
    }
    mismatched_telemetry = {
        run.run_id: sorted(set(telemetry_columns).symmetric_difference(run.telemetry.columns))
        for run in runs
        if set(telemetry_columns) != set(run.telemetry.columns)
    }
    aligned_missing = pd.concat(
        [run.aligned.isna().sum() for run in runs], axis=1
    ).sum(axis=1)
    telemetry_missing = pd.concat(
        [run.telemetry.isna().sum() for run in runs], axis=1
    ).sum(axis=1)
    aligned_rows = sum(len(run.aligned) for run in runs)
    telemetry_rows = sum(len(run.telemetry) for run in runs)
    start_stop: list[dict[str, Any]] = []
    attack_configurations: list[dict[str, Any]] = []
    for run in runs:
        run_start_ns = int(pd.to_numeric(run.aligned["sim_time_ns"]).iloc[0])
        attacks = (
            run.metadata.get("manifest", {})
            .get("scenario_config", {})
            .get("attacks", [])
        )
        if attacks:
            attack_configurations.append(
                {
                    "run_id": run.run_id,
                    "attack_configuration": attacks,
                    "ego_driven_by": run.metadata.get("manifest", {}).get(
                        "ego_driven_by"
                    ),
                }
            )
        for _, event in run.events.iterrows():
            start_stop.append(
                {
                    "run_id": run.run_id,
                    "event": str(event.get("event")),
                    "attack_type": str(event.get("attack_type")),
                    "sim_time_s": float(event["sim_time_ns"]) / 1e9,
                    "run_elapsed_s": (
                        float(event["sim_time_ns"]) - run_start_ns
                    )
                    / 1e9,
                    "attack_target": str(event.get("attack_target")),
                }
            )
    rates = [
        {"run_id": run.run_id, "aligned_hz": _median_rate(run.aligned),
         "telemetry_hz": _median_rate(run.telemetry)}
        for run in runs
    ]
    for entry in rates:
        if entry["aligned_hz"] is not None and not np.isclose(
            entry["aligned_hz"], EXPECTED_ALIGNED_HZ, rtol=0.1
        ):
            warnings.warn(
                f"{entry['run_id']}: expected about 50 Hz aligned data; "
                f"measured {entry['aligned_hz']:.2f} Hz.",
                stacklevel=2,
            )
        if entry["telemetry_hz"] is not None and not np.isclose(
            entry["telemetry_hz"], EXPECTED_TELEMETRY_HZ, rtol=0.1
        ):
            warnings.warn(
                f"{entry['run_id']}: expected about 2 Hz telemetry; "
                f"measured {entry['telemetry_hz']:.2f} Hz.",
                stacklevel=2,
            )
    labels = np.concatenate(
        [run.aligned["is_attack_event"].to_numpy(dtype=np.int8) for run in runs]
    )
    label_counts = {
        "normal": int((labels == 0).sum()),
        "attack": int((labels == 1).sum()),
    }
    return {
        "runs_loaded": len(runs),
        "normal_runs": sum(run.metadata["type"] == "normal" for run in runs),
        "noise_runs": sum(run.metadata["attack_name"] == "noise" for run in runs),
        "aligned_rows_total": aligned_rows,
        "telemetry_rows_total": telemetry_rows,
        "event_derived_label_counts": label_counts,
        "aligned_shape_first_run": list(runs[0].aligned.shape),
        "telemetry_shape_first_run": list(runs[0].telemetry.shape),
        "aligned_columns": aligned_columns,
        "telemetry_columns": telemetry_columns,
        "aligned_missing_count_by_column": {
            str(name): int(count) for name, count in aligned_missing.items() if count
        },
        "aligned_missing_percent_by_column": {
            str(name): round(float(count) * 100.0 / aligned_rows, 5)
            for name, count in aligned_missing.items()
            if count
        },
        "telemetry_missing_count_by_column": {
            str(name): int(count) for name, count in telemetry_missing.items() if count
        },
        "telemetry_missing_percent_by_column": {
            str(name): round(float(count) * 100.0 / telemetry_rows, 5)
            for name, count in telemetry_missing.items()
            if count
        },
        "aligned_schema_differences": mismatched_aligned,
        "telemetry_schema_differences": mismatched_telemetry,
        "sample_rates_hz": rates,
        "events": start_stop,
        "attack_configurations": attack_configurations,
    }
