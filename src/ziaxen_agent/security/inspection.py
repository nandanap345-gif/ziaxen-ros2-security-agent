"""Dataset-wide inspection for the offline ROS 2 security monitor."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..data import event_labels


FILES = {
    "aligned": "aligned.csv.gz",
    "telemetry": "telemetry.csv.gz",
    "events": "events.csv",
    "manifest": "manifest.json",
}
LABEL_COLUMNS = {"is_attack", "attack_type", "attack_target", "attack_id"}
GRAPH_COLUMNS = {
    "node_count",
    "node_list_hash",
    "new_nodes",
    "param_event_count",
    "service_call_count",
    "collector_queue_drops",
    "collector_late_writes",
}


def _label_mismatch_counts(
    event_labels_array: np.ndarray, stored_labels: pd.Series
) -> dict[str, int | None]:
    stored = pd.to_numeric(stored_labels, errors="coerce")
    invalid_rows = int(stored.isna().sum())
    if invalid_rows:
        return {
            "mismatch_rows": None,
            "stored_false_negative_rows": None,
            "stored_false_positive_rows": None,
            "invalid_stored_label_rows": invalid_rows,
        }
    event_values = np.asarray(event_labels_array, dtype=np.int8)
    stored_values = stored.to_numpy(dtype=np.int8)
    return {
        "mismatch_rows": int(np.count_nonzero(stored_values != event_values)),
        "stored_false_negative_rows": int(
            np.count_nonzero((stored_values == 0) & (event_values == 1))
        ),
        "stored_false_positive_rows": int(
            np.count_nonzero((stored_values == 1) & (event_values == 0))
        ),
        "invalid_stored_label_rows": 0,
    }


CLASS_ASSESSMENTS = {
    "noise": ("unusable", "Sensor-value attack; telemetry does not carry sensor values."),
    "bias_drift": ("unusable", "Sensor-value attack; use aligned sensor data, not telemetry alone."),
    "jump": ("unusable", "Sensor-value attack; use aligned sensor data, not telemetry alone."),
    "freeze": ("unusable", "Sensor-value attack; use aligned sensor data, not telemetry alone."),
    "replay": ("unusable", "Sensor-value attack; use aligned sensor data, not telemetry alone."),
    "false_contact": ("unusable", "Contact-value attack; telemetry does not carry contact payload values."),
    "missed_contact": ("unusable", "No real collision occurs in these simulations; guide says it looks like normal."),
    "delay": ("limited", "2 Hz aggregates expose some lag/gap effects but cannot resolve message-level timing."),
    "drop": ("limited", "2 Hz rate/gap aggregates may expose drops but hide individual message loss."),
    "duplicate": ("limited", "Aggregate rates may change; telemetry cannot establish message identity or duplication."),
    "clock_skew": ("limited", "Aggregate stamp-lag/late counters may expose changes at low temporal resolution."),
    "flood": ("usable", "Per-topic rate and gap telemetry can expose elevated traffic in the simulated runs."),
    "spoof": ("usable", "New-node and publisher-count telemetry provide an observable indicator; identity is not authenticated."),
    "unauthorized_node": ("usable", "new_nodes and graph-count/hash telemetry identify an unexpected ROS node name."),
    "unauthorized_subscription": ("usable", "New-node and subscriber-count telemetry provide an observable indicator, not proof of payload access."),
    "param_tamper": ("limited", "The guide describes this as a deliberately added weak target; effects may be indirect."),
    "service_abuse": ("limited", "The guide describes this as a deliberately added weak target; service counts are team instrumentation."),
}


def _plain(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def _rate(frame: pd.DataFrame) -> dict[str, Any]:
    if "sim_time_s" not in frame or len(frame) < 2:
        return {"hz": None, "non_increasing_steps": 0}
    times = pd.to_numeric(frame["sim_time_s"], errors="coerce").to_numpy()
    steps = np.diff(times)
    positive = steps[np.isfinite(steps) & (steps > 0)]
    return {
        "hz": float(1.0 / np.median(positive)) if len(positive) else None,
        "non_increasing_steps": int((~np.isfinite(steps) | (steps <= 0)).sum()),
    }


def _first_observable_change(
    telemetry: pd.DataFrame, events: pd.DataFrame
) -> dict[str, Any] | None:
    if telemetry.empty or events.empty:
        return None
    starts = events.loc[events["event"].astype(str).str.lower().eq("start")]
    stops = events.loc[events["event"].astype(str).str.lower().eq("stop")]
    if len(starts) != 1 or len(stops) != 1:
        return None
    start_ns = float(pd.to_numeric(starts.iloc[0]["sim_time_ns"], errors="raise"))
    stop_ns = float(pd.to_numeric(stops.iloc[0]["sim_time_ns"], errors="raise"))
    times = pd.to_numeric(telemetry["sim_time_ns"], errors="coerce")
    before = telemetry.loc[(times < start_ns) & (times >= start_ns - 15e9)]
    active = telemetry.loc[(times >= start_ns) & (times < stop_ns)]
    if before.empty or active.empty:
        return None

    categorical = {"new_nodes", "node_list_hash"}
    counters = GRAPH_COLUMNS | {
        column
        for column in telemetry.columns
        if column.endswith((".pub_count", ".sub_count", ".late_count"))
    }
    rates = {
        column
        for column in telemetry.columns
        if column.endswith((".rate_hz", ".max_gap_s", ".stamp_lag_mean_s"))
    }
    baseline: dict[str, Any] = {}
    thresholds: dict[str, float] = {}
    for column in categorical.intersection(telemetry.columns):
        values = before[column].dropna()
        if len(values):
            baseline[column] = values.iloc[-1]
    for column in counters.intersection(telemetry.columns):
        values = pd.to_numeric(before[column], errors="coerce").dropna()
        if len(values):
            baseline[column] = float(values.median())
            thresholds[column] = 0.0
    for column in rates.intersection(telemetry.columns):
        values = pd.to_numeric(before[column], errors="coerce").dropna().to_numpy()
        if len(values):
            median = float(np.median(values))
            mad = float(np.median(np.abs(values - median)))
            baseline[column] = median
            minimum = max(0.1, abs(median) * 0.25)
            if column.endswith(".stamp_lag_mean_s"):
                minimum = max(minimum, 0.1)
            elif column.endswith(".max_gap_s"):
                minimum = max(minimum, 0.05)
            thresholds[column] = max(minimum, 6.0 * mad)

    for row_index, row in active.iterrows():
        changed: list[str] = []
        for column, value in baseline.items():
            observed = row[column]
            if pd.isna(observed):
                continue
            if column in categorical:
                if str(observed).strip() and str(observed) != str(value):
                    changed.append(column)
            else:
                try:
                    if abs(float(observed) - float(value)) > thresholds.get(column, 0.0):
                        changed.append(column)
                except (TypeError, ValueError):
                    continue
        if changed:
            row_time = float(pd.to_numeric(row["sim_time_ns"], errors="raise"))
            return {
                "sim_time_ns": int(row_time),
                "offset_from_event_start_s": (row_time - start_ns) / 1e9,
                "columns": sorted(changed),
                "method": (
                    "first in-event change from the preceding 15-second median/last-value "
                    "baseline; aggregate thresholds are heuristic, not a trained detector"
                ),
                "row_index": int(row_index),
            }
    return None


def _class_status(name: str) -> tuple[str, str]:
    return CLASS_ASSESSMENTS.get(
        name,
        ("unusable", "No verified telemetry detection basis is defined for this class."),
    )


def inspect_security_dataset(data_root: str | Path) -> dict[str, Any]:
    """Inspect every indexed run; missing or corrupt indexed files are errors."""
    root = Path(data_root).expanduser().resolve()
    index_path = root / "dataset_index.csv"
    if not index_path.is_file():
        raise FileNotFoundError(f"dataset_index.csv was not found under {root}.")
    index = pd.read_csv(index_path)
    required = {"relative_path", "type", "attack_name", "npc", "seed", "status"}
    missing_columns = required.difference(index.columns)
    if missing_columns:
        raise ValueError(f"dataset_index.csv is missing columns: {sorted(missing_columns)}")

    schema_runs: dict[str, dict[tuple[str, ...], list[str]]] = {
        name: defaultdict(list) for name in FILES if name != "manifest"
    }
    row_stats: dict[str, list[int]] = {name: [] for name in FILES if name != "manifest"}
    missing_totals: dict[str, Counter[str]] = {
        "aligned": Counter(),
        "aligned_after_startup": Counter(),
        "telemetry": Counter(),
        "telemetry_after_startup": Counter(),
        "events": Counter(),
    }
    events_by_type: Counter[str] = Counter()
    events_by_action: Counter[str] = Counter()
    node_names: set[str] = set()
    mismatch_runs: list[dict[str, Any]] = []
    missing_files: list[dict[str, Any]] = []
    corrupt_files: list[dict[str, Any]] = []
    run_records: list[dict[str, Any]] = []
    class_runs: Counter[str] = Counter()
    class_rows: dict[str, Counter[str]] = defaultdict(Counter)
    class_offsets: dict[str, list[float]] = defaultdict(list)
    all_baselines: dict[str, Any] = {}

    for _, row in index.iterrows():
        relative = str(row["relative_path"])
        run_path = (root / relative).resolve()
        if root not in run_path.parents:
            raise ValueError(f"Unsafe dataset_index.csv path: {relative}")
        paths = {name: run_path / filename for name, filename in FILES.items()}
        absent = [name for name, path in paths.items() if not path.is_file()]
        if absent:
            missing_files.append({"run": relative, "files": absent})
            continue
        try:
            frames = {
                "aligned": pd.read_csv(paths["aligned"]),
                "telemetry": pd.read_csv(paths["telemetry"]),
                "events": pd.read_csv(paths["events"]),
            }
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        except (OSError, ValueError, pd.errors.ParserError, json.JSONDecodeError) as error:
            corrupt_files.append(
                {"run": relative, "error": f"{type(error).__name__}: {error}"}
            )
            continue

        class_name = (
            str(row["attack_name"])
            if str(row["type"]).lower() == "attack"
            else "normal"
        )
        class_runs[class_name] += 1
        run_record: dict[str, Any] = {
            "run": relative,
            "type": str(row["type"]),
            "attack_name": str(row["attack_name"]),
            "npc": _plain(row["npc"]),
            "seed": _plain(row["seed"]),
            "level": _plain(row["level"]) if "level" in row else None,
            "status": str(row["status"]),
            "files": {},
            "events": [],
            "label_agreement": {},
        }

        for name, frame in frames.items():
            schema_runs[name][tuple(str(col) for col in frame.columns)].append(relative)
            row_stats[name].append(len(frame))
            run_record["files"][name] = {
                "present": True,
                "readable": True,
                "rows": len(frame),
                "columns": [str(column) for column in frame.columns],
                "sample_rate": _rate(frame) if name != "events" else None,
            }
            class_rows[class_name][f"{name}_rows"] += len(frame)
            if name in {"aligned", "telemetry", "events"}:
                for column, count in frame.isna().sum().items():
                    if count:
                        missing_totals[name][str(column)] += int(count)
            if name in {"aligned", "telemetry"} and "sim_time_s" in frame and len(frame):
                elapsed = pd.to_numeric(frame["sim_time_s"], errors="coerce")
                elapsed = elapsed - float(elapsed.iloc[0])
                startup = frame.loc[elapsed >= 15.0]
                startup_key = f"{name}_after_startup"
                for column, count in startup.isna().sum().items():
                    if count:
                        missing_totals[startup_key][str(column)] += int(count)

        events = frames["events"]
        event_type_values = (
            events["attack_type"].dropna().astype(str).tolist()
            if "attack_type" in events
            else []
        )
        event_names = (
            events["event"].dropna().astype(str).str.lower().tolist()
            if "event" in events
            else []
        )
        events_by_type.update(event_type_values)
        events_by_action.update(event_names)
        event_types = sorted(set(event_type_values))
        run_record["events"] = {
            "row_count": len(events),
            "event_counts": dict(Counter(event_names)),
            "attack_types": event_types,
            "index_event_type_match": (
                not event_types
                if class_name == "normal"
                else event_types == [class_name]
            ),
        }
        if not run_record["events"]["index_event_type_match"]:
            mismatch_runs.append(
                {
                    "run": relative,
                    "index_attack_name": class_name,
                    "event_attack_types": event_types,
                }
            )

        for table_name in ("aligned", "telemetry"):
            frame = frames[table_name]
            stored_name = "is_attack"
            if stored_name not in frame:
                run_record["label_agreement"][table_name] = {
                    "available": False,
                    "mismatch_rows": None,
                }
                continue
            labels = event_labels(frame, events)
            stored = pd.to_numeric(frame[stored_name], errors="coerce")
            mismatch_summary = _label_mismatch_counts(labels, stored)
            invalid_stored = int(mismatch_summary["invalid_stored_label_rows"] or 0)
            mismatch_count = mismatch_summary["mismatch_rows"]
            run_record["label_agreement"][table_name] = {
                "available": True,
                "event_label_rows": int(labels.sum()),
                "stored_attack_rows": (
                    int((stored == 1).sum()) if invalid_stored == 0 else None
                ),
                "mismatch_rows": mismatch_count,
                "invalid_stored_label_rows": invalid_stored,
                "stored_false_negative_rows": mismatch_summary[
                    "stored_false_negative_rows"
                ],
                "stored_false_positive_rows": mismatch_summary[
                    "stored_false_positive_rows"
                ],
            }
            if mismatch_count or invalid_stored:
                mismatch_runs.append(
                    {
                        "run": relative,
                        "table": table_name,
                        "index_attack_name": class_name,
                        "seed": _plain(row["seed"]),
                        "row_count": len(frame),
                        "mismatch_rows": mismatch_count,
                        "invalid_stored_label_rows": invalid_stored,
                        "stored_false_negative_rows": mismatch_summary[
                            "stored_false_negative_rows"
                        ],
                        "stored_false_positive_rows": mismatch_summary[
                            "stored_false_positive_rows"
                        ],
                    }
                )

        if "new_nodes" in frames["telemetry"]:
            for value in frames["telemetry"]["new_nodes"].dropna():
                node_names.update(
                    item.strip() for item in str(value).split(";") if item.strip()
                )

        baseline = manifest.get("telemetry_baseline")
        if baseline:
            all_baselines[json.dumps(baseline, sort_keys=True, default=str)] = baseline

        change = _first_observable_change(frames["telemetry"], events)
        run_record["first_observable_telemetry_change"] = change
        if change is not None:
            class_offsets[class_name].append(
                float(change["offset_from_event_start_s"])
            )
        run_records.append(run_record)

    if missing_files or corrupt_files:
        report = {
            "data_root": root.name,
            "indexed_runs": len(index),
            "missing_files": missing_files,
            "corrupt_files": corrupt_files,
        }
        raise ValueError(
            "Dataset inspection failed; missing files="
            f"{len(missing_files)}, corrupt files={len(corrupt_files)}. "
            f"Details: {json.dumps(report, ensure_ascii=False)}"
        )

    classes = []
    for name in sorted(class_runs):
        status, reason = ("usable", "Normal reference runs for approved-behaviour baselines.") if name == "normal" else _class_status(name)
        offsets = class_offsets.get(name, [])
        classes.append(
            {
                "name": name,
                "runs": class_runs[name],
                "assessment": status,
                "reason": reason,
                "aligned_rows": class_rows[name]["aligned_rows"],
                "telemetry_rows": class_rows[name]["telemetry_rows"],
                "first_observable_change_count": len(offsets),
                "first_observable_change_offset_median_s": (
                    float(np.median(offsets)) if offsets else None
                ),
                "first_observable_change_offset_max_s": (
                    float(np.max(offsets)) if offsets else None
                ),
            }
        )

    schemas = {
        name: [
            {"columns": list(columns), "run_count": len(paths), "sample_runs": paths[:3]}
            for columns, paths in variants.items()
        ]
        for name, variants in schema_runs.items()
    }
    report = {
        "data_root": root.name,
        "index_rows": len(index),
        "index_status_counts": {
            str(key): int(value)
            for key, value in index["status"].value_counts(dropna=False).items()
        },
        "runs_inspected": len(run_records),
        "total_rows": {
            name: int(sum(values)) for name, values in row_stats.items()
        },
        "row_count_range": {
            name: {
                "min": int(min(values)),
                "max": int(max(values)),
                "mean": float(np.mean(values)),
            }
            for name, values in row_stats.items()
            if values
        },
        "schema_variants": schemas,
        "class_assessments": classes,
        "event_counts": {
            "by_attack_type": dict(events_by_type),
            "by_event": dict(events_by_action),
        },
        "label_disagreements": {
            "run_count": len(mismatch_runs),
            "details": mismatch_runs,
            "authority": "events.csv start-inclusive, stop-exclusive intervals",
        },
        "missing_values": {
            scope: dict(sorted(counts.items()))
            for scope, counts in missing_totals.items()
        },
        "new_node_names": sorted(node_names),
        "telemetry_baselines": list(all_baselines.values()),
        "first_observable_change_method": (
            "For each run, compare the telemetry rows within the event interval to the "
            "preceding 15-second baseline. Categorical graph fields use last value; "
            "counters use median; aggregate rates/gaps/lags use a robust heuristic "
            "threshold. This is descriptive screening, not detector performance."
        ),
        "runs": run_records,
        "limitations": [
            "The 2 Hz telemetry does not identify a host, IP, MAC, DDS participant GUID, or payload reader.",
            "The dataset has no movement-command topic or live bridge/domain change stream.",
            "Event labels, not stored is_attack values, are authoritative when they disagree.",
            "The dataset guide says sensors are idealized and the ego vehicle is not driven by ROS.",
            "raw_clean.csv is not used or read by this inspection.",
        ],
    }
    return report


def write_security_dataset_report(
    data_root: str | Path, json_path: str | Path, markdown_path: str | Path
) -> dict[str, Any]:
    """Inspect a dataset and write JSON plus a concise Markdown summary."""
    report = inspect_security_dataset(data_root)
    json_file = Path(json_path)
    markdown_file = Path(markdown_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    markdown_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Security dataset inspection",
        "",
        f"- **Data root:** `{report['data_root']}`",
        f"- **Indexed / inspected runs:** {report['index_rows']} / {report['runs_inspected']}",
        f"- **Aligned rows:** {report['total_rows']['aligned']:,}",
        f"- **Telemetry rows:** {report['total_rows']['telemetry']:,}",
        f"- **Runs with label disagreements:** {report['label_disagreements']['run_count']}",
        "",
        "## Per-class suitability for telemetry detection",
        "",
        "| Class | Runs | Assessment | First observable change in event window | Reason |",
        "|---|---:|---|---:|---|",
    ]
    for item in report["class_assessments"]:
        offset = item["first_observable_change_offset_median_s"]
        offset_text = f"{offset:.3f} s (median)" if offset is not None else "not observed"
        lines.append(
            f"| {item['name']} | {item['runs']} | {item['assessment']} | "
            f"{offset_text} | {item['reason']} |"
        )
    lines.extend(["", "## File schemas", ""])
    for name, variants in report["schema_variants"].items():
        lines.append(f"- **{name}:** {len(variants)} schema variant(s)")
        for variant in variants:
            lines.append(
                f"  - {len(variant['columns'])} columns, observed in "
                f"{variant['run_count']} runs"
            )
    lines.extend(
        [
            "",
            "## Missing values",
            "",
            "Counts are summed across the inspected runs. The startup-trimmed scope "
            "uses telemetry rows at least 15 seconds after each run's first timestamp.",
            "",
            "```json",
            json.dumps(report["missing_values"], indent=2, ensure_ascii=False),
            "```",
            "",
            "## Label disagreements",
            "",
            "The event interval is authoritative; stored `is_attack` values are reported "
            "for audit only. A stored false negative means `is_attack=0` when events.csv "
            "labels attack; a stored false positive means `is_attack=1` outside the event.",
            "",
            "| Run | Class | Seed | Rows | Mismatches | Stored false negatives | Stored false positives |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for item in report["label_disagreements"]["details"]:
        if "table" not in item:
            continue
        lines.append(
            f"| {item['run']} | {item['index_attack_name']} | {item['seed']} | "
            f"{item['row_count']} | {item['mismatch_rows']} | "
            f"{item['stored_false_negative_rows']} | "
            f"{item['stored_false_positive_rows']} |"
        )
    lines.extend(
        [
            "",
            "## Observed node names",
            "",
            ", ".join(f"`{node}`" for node in report["new_node_names"]) or "None",
            "",
            "## Caveats",
            "",
            *[f"- {limitation}" for limitation in report["limitations"]],
            "",
            "The first-observable-change offsets are descriptive heuristics over 2 Hz "
            "telemetry, not model metrics or proof of malicious activity.",
        ]
    )
    markdown_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
