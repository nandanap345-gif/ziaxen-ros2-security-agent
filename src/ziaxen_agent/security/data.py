"""Run-grouped loading for telemetry security experiments."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ..data import event_labels


@dataclass
class SecurityRun:
    run_id: str
    relative_path: str
    attack_name: str
    run_type: str
    npc: int
    seed: int
    level: int
    telemetry: pd.DataFrame
    labels: pd.Series
    events: pd.DataFrame
    manifest: dict[str, Any]


def load_security_runs(
    data_root: str | Path, *, seeds: set[int] | None = None
) -> list[SecurityRun]:
    """Load every indexed run or fail; use events.csv as the only label source."""
    root = Path(data_root).expanduser().resolve()
    index_path = root / "dataset_index.csv"
    if not index_path.is_file():
        raise FileNotFoundError(f"dataset_index.csv was not found under {root}.")
    index = pd.read_csv(index_path)
    required = {
        "relative_path",
        "type",
        "attack_name",
        "npc",
        "seed",
        "level",
        "status",
    }
    missing_columns = required.difference(index.columns)
    if missing_columns:
        raise ValueError(f"dataset_index.csv is missing columns: {sorted(missing_columns)}")
    if seeds is not None:
        index = index.loc[pd.to_numeric(index["seed"]).isin(seeds)]
    runs: list[SecurityRun] = []
    missing_files: list[str] = []
    for _, row in index.iterrows():
        relative = str(row["relative_path"])
        run_path = (root / relative).resolve()
        if root not in run_path.parents:
            raise ValueError(f"Unsafe dataset_index.csv path: {relative}")
        expected = {
            "telemetry": run_path / "telemetry.csv.gz",
            "events": run_path / "events.csv",
            "manifest": run_path / "manifest.json",
        }
        missing_files.extend(
            f"{relative}/{name}" for name, path in expected.items() if not path.is_file()
        )
        if any(not path.is_file() for path in expected.values()):
            continue
        try:
            telemetry = pd.read_csv(expected["telemetry"])
            events = pd.read_csv(expected["events"])
            manifest = json.loads(expected["manifest"].read_text(encoding="utf-8"))
            labels = event_labels(telemetry, events)
        except (OSError, ValueError, pd.errors.ParserError, json.JSONDecodeError) as error:
            raise ValueError(f"{relative}: failed to load telemetry/events/manifest: {error}") from error
        if len(telemetry) != len(labels):
            raise ValueError(f"{relative}: event labels do not match telemetry row count.")
        times = pd.to_numeric(telemetry.get("sim_time_ns"), errors="coerce")
        if times.isna().any():
            raise ValueError(f"{relative}: telemetry has invalid sim_time_ns values.")
        run_name = str(manifest.get("scenario") or Path(relative).name)
        runs.append(
            SecurityRun(
                run_id=run_name,
                relative_path=relative,
                attack_name=str(row["attack_name"]),
                run_type=str(row["type"]),
                npc=int(row["npc"]),
                seed=int(row["seed"]),
                level=int(row["level"]),
                telemetry=telemetry,
                labels=pd.Series(labels, index=telemetry.index, dtype="int8"),
                events=events,
                manifest=manifest,
            )
        )
    if missing_files:
        raise FileNotFoundError(
            "Dataset files are missing:\n" + "\n".join(f"  - {item}" for item in missing_files[:30])
        )
    if not runs:
        raise ValueError("No runs were found for the requested seed split.")
    return runs
