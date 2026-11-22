"""Reproducible blind mixed-stream construction and evaluation helpers."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .data import event_labels

STREAM_A_ATTACK_SEED = 20261122
STREAM_B_SHUFFLE_SEEDS = (1701, 2903, 4307)
STREAM_A_ATTACK_PREVALENCE = 0.05
_FORBIDDEN_INPUT_COLUMNS = {
    "is_attack",
    "is_attack_event",
    "attack_id",
    "attack_target",
    "attack_type",
    "run_id",
    "run_name",
    "relative_path",
    "scenario",
    "seed",
    "class",
    "class_name",
    "event_label",
    "label",
    "labels",
}


@dataclass
class _Run:
    relative_path: str
    run_id: str
    class_name: str
    run_type: str
    t0_sim_s: float
    duration_s: float
    aligned: pd.DataFrame
    telemetry: pd.DataFrame
    event_intervals: list[tuple[float, float]]


def _is_forbidden_column(name: str) -> bool:
    lowered = str(name).strip().lower()
    return (
        lowered in _FORBIDDEN_INPUT_COLUMNS
        or lowered.startswith("attack_")
        or lowered.startswith("label_")
    )


def _strip_input_metadata(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.drop(
        columns=[column for column in frame if _is_forbidden_column(column)]
    )


def _event_intervals(events: pd.DataFrame, t0_sim_s: float) -> list[tuple[float, float]]:
    if events.empty:
        return []
    required = {"sim_time_ns", "event", "attack_id"}
    missing = required.difference(events.columns)
    if missing:
        raise ValueError(f"events.csv is missing columns: {sorted(missing)}")
    t0_sim_ns = int(round(t0_sim_s * 1e9))
    names = events["event"].astype(str).str.lower()
    intervals: list[tuple[float, float]] = []
    for _, group in events.assign(_event=names).groupby("attack_id", dropna=False):
        starts = pd.to_numeric(
            group.loc[group["_event"].eq("start"), "sim_time_ns"], errors="raise"
        )
        stops = pd.to_numeric(
            group.loc[group["_event"].eq("stop"), "sim_time_ns"], errors="raise"
        )
        if len(starts) != 1 or len(stops) != 1:
            raise ValueError("Each attack ID must have exactly one start and one stop.")
        start = (int(starts.iloc[0]) - t0_sim_ns) / 1e9
        stop = (int(stops.iloc[0]) - t0_sim_ns) / 1e9
        if not math.isfinite(start) or not math.isfinite(stop) or stop <= start:
            raise ValueError("events.csv contains invalid attack boundaries.")
        intervals.append((start, stop))
    return sorted(intervals)


def _load_seed3_runs(data_root: str | Path) -> list[_Run]:
    root = Path(data_root).expanduser().resolve()
    index_path = root / "dataset_index.csv"
    if not index_path.is_file():
        raise FileNotFoundError(f"dataset_index.csv was not found under {root}.")
    index = pd.read_csv(index_path)
    required = {
        "relative_path",
        "type",
        "attack_name",
        "seed",
        "duration_s",
        "t0_sim_s",
        "status",
    }
    missing = required.difference(index.columns)
    if missing:
        raise ValueError(f"dataset_index.csv is missing columns: {sorted(missing)}")
    index = index.loc[pd.to_numeric(index["seed"], errors="coerce").eq(3)]
    if len(index) != 102:
        raise ValueError(f"Expected 102 seed-3 runs; found {len(index)}.")
    runs: list[_Run] = []
    for row in index.itertuples(index=False):
        relative = str(row.relative_path)
        run_path = (root / relative).resolve()
        if root not in run_path.parents:
            raise ValueError(f"Unsafe dataset_index.csv path: {relative}")
        aligned_path = run_path / "aligned.csv.gz"
        telemetry_path = run_path / "telemetry.csv.gz"
        events_path = run_path / "events.csv"
        for required_path in (aligned_path, telemetry_path, events_path):
            if not required_path.is_file():
                raise FileNotFoundError(f"Required run file is missing: {required_path}")
        aligned = pd.read_csv(aligned_path)
        telemetry = pd.read_csv(telemetry_path)
        events = pd.read_csv(events_path)
        if aligned.empty or "sim_time_s" not in aligned:
            raise ValueError(f"{relative}: aligned recording lacks sim_time_s rows.")
        first_time_ns = int(
            pd.to_numeric(aligned["sim_time_ns"], errors="raise").iloc[0]
        )
        t0_sim_s = first_time_ns / 1e9
        labels = event_labels(aligned, events)
        intervals = _event_intervals(events, t0_sim_s)
        t0_sim_ns = int(round(t0_sim_s * 1e9))
        relative_times_ns = (
            pd.to_numeric(aligned["sim_time_ns"], errors="raise").to_numpy(dtype=np.int64)
            - t0_sim_ns
        )
        for start, stop in intervals:
            expected_labels = (
                (relative_times_ns >= int(round(start * 1e9)))
                & (relative_times_ns < int(round(stop * 1e9)))
            )
            if not np.array_equal(expected_labels.astype(np.int8), labels):
                raise ValueError(f"{relative}: could not reconcile event labels.")
        runs.append(
            _Run(
                relative_path=relative,
                run_id=Path(relative).name,
                class_name=str(row.attack_name),
                run_type=str(row.type),
                t0_sim_s=t0_sim_s,
                duration_s=float(row.duration_s),
                aligned=aligned,
                telemetry=telemetry,
                event_intervals=intervals,
            )
        )
    return sorted(runs, key=lambda run: run.relative_path)


def _normal_slices(run: _Run) -> list[tuple[float, float]]:
    if run.run_type == "normal":
        return [(0.0, 90.0)]
    if len(run.event_intervals) != 1:
        raise ValueError(f"{run.run_id}: expected one attack interval.")
    start, stop = run.event_intervals[0]
    return [(0.0, min(30.0, start)), (max(60.0, stop), 90.0)]


def _segment(
    run: _Run,
    start_s: float,
    stop_s: float,
    *,
    attack: bool = False,
) -> dict[str, Any]:
    if not 0 <= start_s < stop_s <= 90.0:
        raise ValueError(f"Invalid source slice [{start_s}, {stop_s}) for {run.run_id}.")
    t0_sim_ns = int(round(run.t0_sim_s * 1e9))
    aligned_rel = (
        pd.to_numeric(run.aligned["sim_time_ns"], errors="coerce") - t0_sim_ns
    ) / 1e9
    aligned = run.aligned.loc[
        (aligned_rel >= start_s) & (aligned_rel < stop_s)
    ].copy()
    telemetry_rel = (
        pd.to_numeric(run.telemetry["sim_time_ns"], errors="coerce") - t0_sim_ns
    ) / 1e9
    telemetry = run.telemetry.loc[
        (telemetry_rel >= start_s) & (telemetry_rel < stop_s)
    ].copy()
    aligned = _strip_input_metadata(aligned)
    telemetry = _strip_input_metadata(telemetry)
    if aligned.empty or telemetry.empty:
        raise ValueError(f"{run.run_id}: source slice has no rows in both input streams.")
    if "t_rel_s" in aligned:
        aligned = aligned.drop(columns=["t_rel_s"])
    return {
        "run": run,
        "source_start_s": float(start_s),
        "source_stop_s": float(stop_s),
        "class_name": run.class_name,
        "inserted_attack": attack,
        "aligned": aligned,
        "telemetry": telemetry,
    }


def _make_segment_specs(runs: list[_Run]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normal_segments: list[dict[str, Any]] = []
    attacks: list[dict[str, Any]] = []
    for run in runs:
        if run.run_type == "normal":
            normal_segments.append(_segment(run, 0.0, 90.0))
            continue
        for start, stop in _normal_slices(run):
            if stop - start > 1e-6:
                normal_segments.append(_segment(run, start, stop))
        for start, stop in run.event_intervals:
            attacks.append(_segment(run, start, stop, attack=True))
    return normal_segments, attacks


def _select_attack_windows(
    attacks: list[dict[str, Any]], normal_seconds: float, seed: int
) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(attacks))
    target = normal_seconds * STREAM_A_ATTACK_PREVALENCE / (
        1.0 - STREAM_A_ATTACK_PREVALENCE
    )
    selected: list[dict[str, Any]] = []
    total = 0.0
    for position in order:
        candidate = attacks[int(position)]
        duration = candidate["source_stop_s"] - candidate["source_start_s"]
        if abs(total + duration - target) < abs(total - target):
            selected.append(candidate)
            total += duration
        if total >= target:
            break
    if not selected:
        raise ValueError("Unable to select an attack window for the 5% prevalence stream.")
    return selected


def _insert_attacks(
    normal_segments: list[dict[str, Any]],
    attacks: list[dict[str, Any]],
    seed: int,
) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed)
    placements = sorted(
        zip(
            rng.choice(len(normal_segments) + 1, size=len(attacks), replace=False),
            rng.permutation(attacks),
        ),
        key=lambda item: int(item[0]),
    )
    by_slot: dict[int, list[dict[str, Any]]] = {}
    for slot, attack in placements:
        by_slot.setdefault(int(slot), []).append(attack)
    result: list[dict[str, Any]] = []
    for slot in range(len(normal_segments) + 1):
        result.extend(by_slot.get(slot, []))
        if slot < len(normal_segments):
            result.append(normal_segments[slot])
    return result


def _apply_counter_offsets(
    frame: pd.DataFrame, totals: dict[str, float]
) -> tuple[pd.DataFrame, dict[str, float]]:
    result = frame.copy()
    updated = dict(totals)
    for column in ("collector_queue_drops", "collector_late_writes"):
        if column not in result:
            continue
        values = pd.to_numeric(result[column], errors="coerce")
        if values.isna().any():
            raise ValueError(f"{column} contains missing or invalid values.")
        increments = values.diff().fillna(0).clip(lower=0)
        cumulative = increments.cumsum() + updated.get(column, 0.0)
        result[column] = cumulative
        updated[column] = float(cumulative.iloc[-1])
    return result, updated


def _stitch(
    stream_id: str,
    segments: list[dict[str, Any]],
    output_dir: Path,
    *,
    rng_seeds: dict[str, int],
) -> dict[str, Any]:
    aligned_parts: list[pd.DataFrame] = []
    telemetry_parts: list[pd.DataFrame] = []
    segment_manifest: list[dict[str, Any]] = []
    ground_truth: list[dict[str, Any]] = []
    join_points: list[int] = []
    cursor_s = 0.0
    counter_totals: dict[str, float] = {}
    normal_seconds = 0.0
    attack_seconds = 0.0
    for index, segment in enumerate(segments):
        run: _Run = segment["run"]
        start_s = segment["source_start_s"]
        stop_s = segment["source_stop_s"]
        duration_s = stop_s - start_s
        if index:
            join_points.append(int(round(cursor_s * 1e9)))
        for key, target in (("aligned", aligned_parts), ("telemetry", telemetry_parts)):
            part = segment[key].copy()
            source_times = pd.to_numeric(part["sim_time_ns"], errors="coerce")
            source_relative = (source_times - int(round(run.t0_sim_s * 1e9))) / 1e9
            rebased_s = cursor_s + (source_relative - start_s)
            part["sim_time_s"] = rebased_s.astype(float)
            part["sim_time_ns"] = np.rint(rebased_s.to_numpy() * 1e9).astype(np.int64)
            if key == "telemetry":
                part, counter_totals = _apply_counter_offsets(part, counter_totals)
            target.append(part.reset_index(drop=True))
        segment_manifest.append(
            {
                "segment_index": index,
                "source_run": run.run_id,
                "source_relative_path": run.relative_path,
                "class_name": run.class_name,
                "source_run_type": run.run_type,
                "source_start_s": start_s,
                "source_stop_s": stop_s,
                "source_event_intervals_s": [
                    {"start_s": event_start, "stop_s": event_stop}
                    for event_start, event_stop in run.event_intervals
                ],
                "duration_s": duration_s,
                "output_start_sim_ns": int(round(cursor_s * 1e9)),
                "output_end_sim_ns": int(round((cursor_s + duration_s) * 1e9)),
                "inserted_attack": bool(segment["inserted_attack"]),
            }
        )
        segment_attack_seconds = 0.0
        for event_start, event_stop in run.event_intervals:
            start = max(event_start, start_s)
            stop = min(event_stop, stop_s)
            if stop - start > 1e-6:
                segment_attack_seconds += stop - start
                ground_truth.append(
                    {
                        "class_name": run.class_name,
                        "source_run": run.run_id,
                        "start_sim_ns": int(round((cursor_s + start - start_s) * 1e9)),
                        "stop_sim_ns": int(round((cursor_s + stop - start_s) * 1e9)),
                    }
                )
        attack_seconds += segment_attack_seconds
        normal_seconds += max(0.0, duration_s - segment_attack_seconds)
        cursor_s += duration_s + 0.02

    aligned_stream = pd.concat(aligned_parts, ignore_index=True)
    telemetry_stream = pd.concat(telemetry_parts, ignore_index=True)
    for name, frame in (("aligned", aligned_stream), ("telemetry", telemetry_stream)):
        if any(_is_forbidden_column(column) for column in frame.columns):
            raise ValueError(f"Ground-truth or identity fields leaked into {name} stream.")
        times = pd.to_numeric(frame["sim_time_ns"], errors="raise").to_numpy(dtype=np.int64)
        if np.any(np.diff(times) <= 0):
            raise ValueError(f"{stream_id}: {name} timestamps are not strictly increasing.")
    output_dir.mkdir(parents=True, exist_ok=True)
    aligned_path = output_dir / f"{stream_id}_aligned.csv.gz"
    telemetry_path = output_dir / f"{stream_id}_telemetry.csv.gz"
    aligned_stream.to_csv(aligned_path, index=False, compression="gzip")
    telemetry_stream.to_csv(telemetry_path, index=False, compression="gzip")
    stream_duration = max(
        float(aligned_stream["sim_time_s"].iloc[-1]),
        float(telemetry_stream["sim_time_s"].iloc[-1]),
    )
    manifest = {
        "format_version": 1,
        "stream_id": stream_id,
        "random_seeds": rng_seeds,
        "duration_s": stream_duration,
        "normal_seconds": normal_seconds,
        "attack_seconds": attack_seconds,
        "attack_prevalence": (
            attack_seconds / (attack_seconds + normal_seconds)
            if attack_seconds + normal_seconds
            else 0.0
        ),
        "join_points_sim_ns": join_points,
        "counter_handling": (
            "Cumulative collector counters are differenced per segment, negative "
            "resets are clipped to zero, then deltas are accumulated across joins."
        ),
        "aligned_file": aligned_path.name,
        "telemetry_file": telemetry_path.name,
        "segments": segment_manifest,
        "ground_truth": ground_truth,
        "label_source": "events.csv start-inclusive, stop-exclusive intervals",
    }
    manifest_path = output_dir / f"{stream_id}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def build_blind_streams(
    data_root: str | Path,
    output_dir: str | Path,
    *,
    attack_seed: int = STREAM_A_ATTACK_SEED,
    shuffle_seeds: tuple[int, ...] = STREAM_B_SHUFFLE_SEEDS,
) -> dict[str, dict[str, Any]]:
    """Build Stream A, three Stream B shuffles, and the normal-only Stream C."""
    runs = _load_seed3_runs(data_root)
    normal_segments, attack_segments = _make_segment_specs(runs)
    normal_seconds = sum(
        segment["source_stop_s"] - segment["source_start_s"]
        for segment in normal_segments
    )
    output = Path(output_dir)
    selected_attacks = _select_attack_windows(
        attack_segments, normal_seconds, attack_seed
    )
    stream_a = _insert_attacks(
        normal_segments,
        selected_attacks,
        seed=attack_seed + 1,
    )
    manifests = {
        "stream_a": _stitch(
            "stream_a",
            stream_a,
            output,
            rng_seeds={
                "attack_selection": attack_seed,
                "attack_insertion": attack_seed + 1,
            },
        )
    }
    full_run_segments = [_segment(run, 0.0, 90.0) for run in runs]
    for shuffle_seed in shuffle_seeds:
        shuffled = [
            full_run_segments[int(position)]
            for position in np.random.default_rng(shuffle_seed).permutation(
                len(full_run_segments)
            )
        ]
        stream_id = f"stream_b_seed_{shuffle_seed}"
        manifests[stream_id] = _stitch(
            stream_id,
            shuffled,
            output,
            rng_seeds={"shuffle": shuffle_seed},
        )
    manifests["stream_c"] = _stitch(
        "stream_c",
        normal_segments,
        output,
        rng_seeds={"normal_segment_order": 0},
    )
    return manifests
