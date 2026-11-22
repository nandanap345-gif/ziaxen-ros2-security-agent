"""Run-grouped comparison of telemetry policy rules and anomaly models."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from .alerts import Finding, merge_alerts
from .data import SecurityRun, load_security_runs
from .inspection import _first_observable_change, _class_status
from .inventory import load_inventory
from .models import security_scores
from .rules import evaluate_rules
from .telemetry import telemetry_features


_TOLERANCE_BEFORE_START_S = 1.5
_TOLERANCE_AFTER_STOP_S = 0.5


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wilson_interval(successes: int, trials: int, z_score: float = 1.959963984540054) -> list[float] | None:
    """Return a two-sided 95% Wilson score interval for a binomial proportion."""
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("Wilson interval requires 0 <= successes <= trials.")
    if trials == 0:
        return None
    proportion = successes / trials
    z_squared = z_score * z_score
    denominator = 1.0 + z_squared / trials
    center = (proportion + z_squared / (2.0 * trials)) / denominator
    half_width = (
        z_score
        * np.sqrt(
            proportion * (1.0 - proportion) / trials
            + z_squared / (4.0 * trials * trials)
        )
        / denominator
    )
    return [float(max(0.0, center - half_width)), float(min(1.0, center + half_width))]


def _metrics(labels: np.ndarray, predictions: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    matrix = confusion_matrix(labels, predictions, labels=[0, 1])
    tn, fp, fn, tp = (int(value) for value in matrix.ravel())
    return {
        "rows": int(len(labels)),
        "accuracy": float((tn + tp) / len(labels)) if len(labels) else 0.0,
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else 0.0,
        "average_precision": (
            float(average_precision_score(labels, scores))
            if len(np.unique(labels)) > 1
            else None
        ),
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "true_positive": tp,
    }


def _event_bounds(run: SecurityRun) -> tuple[int, int] | None:
    if run.events.empty:
        return None
    names = run.events["event"].astype(str).str.lower()
    starts = pd.to_numeric(
        run.events.loc[names.eq("start"), "sim_time_ns"], errors="coerce"
    ).dropna()
    stops = pd.to_numeric(
        run.events.loc[names.eq("stop"), "sim_time_ns"], errors="coerce"
    ).dropna()
    if len(starts) != 1 or len(stops) != 1:
        return None
    return int(starts.iloc[0]), int(stops.iloc[0])


def _row_flags(frame: pd.DataFrame, findings: list[Finding]) -> np.ndarray:
    flagged_times = {int(item.timestamp_sim_ns) for item in findings}
    times = pd.to_numeric(frame["sim_time_ns"], errors="coerce").to_numpy()
    return np.asarray([int(value) in flagged_times for value in times], dtype=np.int8)


def _alert_findings(
    run: SecurityRun,
    model: Any,
    model_name: str,
    threshold: float,
) -> tuple[np.ndarray, np.ndarray, list[Finding]]:
    features = telemetry_features(run.telemetry)
    scores = security_scores(
        model, model_name, features.reindex(columns=model.feature_names_in_)
        if hasattr(model, "feature_names_in_")
        else features,
    )
    predictions = (scores >= threshold).astype(np.int8)
    findings: list[Finding] = []
    for position in np.flatnonzero(predictions):
        row = run.telemetry.iloc[position]
        findings.append(
            Finding(
                rule_id=model_name,
                timestamp_sim_ns=int(row["sim_time_ns"]),
                run_id=run.run_id,
                source="anomaly_model",
                severity="medium",
                score=float(scores[position]),
                threshold=float(threshold),
                evidence={
                    "anomaly_score": float(scores[position]),
                    "threshold": float(threshold),
                    "model": model_name,
                },
                what_this_does_not_prove="An anomaly score is not a probability or proof of unauthorized access.",
                recommended_next_step="Review the contributing telemetry and verify the activity with the authorized system owner.",
            )
        )
    return predictions, scores, findings


def _event_metrics(
    runs: list[SecurityRun],
    predictions: dict[str, dict[str, np.ndarray]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    output: dict[str, Any] = {}
    events_report: list[dict[str, Any]] = []
    methods = ["rules", "isolation_forest", "random_forest", "rules_plus_model"]
    for class_name in sorted({run.attack_name for run in runs if run.run_type == "attack"}):
        class_runs = [run for run in runs if run.run_type == "attack" and run.attack_name == class_name]
        per_method: dict[str, Any] = {}
        for method in methods:
            detections = 0
            latencies: list[float] = []
            observable_latencies: list[float] = []
            for run in class_runs:
                bounds = _event_bounds(run)
                if bounds is None:
                    continue
                start_ns, stop_ns = bounds
                values = predictions[method][run.run_id]
                times = pd.to_numeric(run.telemetry["sim_time_ns"], errors="coerce").to_numpy()
                window = (
                    (times >= start_ns - _TOLERANCE_BEFORE_START_S * 1e9)
                    & (times < stop_ns + _TOLERANCE_AFTER_STOP_S * 1e9)
                    & (values == 1)
                )
                alerted = np.flatnonzero(window)
                first_alert_ns = int(times[alerted[0]]) if len(alerted) else None
                if first_alert_ns is not None:
                    detections += 1
                    latencies.append((first_alert_ns - start_ns) / 1e9)
                    change = _first_observable_change(run.telemetry, run.events)
                    if change is not None:
                        observable_latencies.append(
                            (first_alert_ns - int(change["sim_time_ns"])) / 1e9
                        )
                events_report.append(
                    {
                        "run_id": run.run_id,
                        "attack_name": class_name,
                        "method": method,
                        "event_detected": first_alert_ns is not None,
                        "event_start_sim_ns": start_ns,
                        "first_alert_sim_ns": first_alert_ns,
                        "latency_from_label_start_s": (
                            (first_alert_ns - start_ns) / 1e9
                            if first_alert_ns is not None
                            else None
                        ),
                        "latency_from_first_observable_change_s": (
                            (
                                first_alert_ns - int(change["sim_time_ns"])
                            ) / 1e9
                            if first_alert_ns is not None
                            and (change := _first_observable_change(run.telemetry, run.events))
                            is not None
                            else None
                        ),
                    }
                )
            false_incidents = 0
            negative_runs = [
                run
                for run in runs
                if run.run_type == "normal"
                or (run.run_type == "attack" and run.attack_name == class_name)
            ]
            for run in negative_runs:
                times = pd.to_numeric(run.telemetry["sim_time_ns"], errors="coerce").to_numpy()
                flags = predictions[method][run.run_id].astype(bool)
                elapsed = (times - times[0]) / 1e9
                valid_negative = elapsed >= 15.0
                bounds = _event_bounds(run)
                if bounds:
                    start_ns, stop_ns = bounds
                    valid_negative &= (
                        (times < start_ns - _TOLERANCE_BEFORE_START_S * 1e9)
                        | (times >= stop_ns + _TOLERANCE_AFTER_STOP_S * 1e9)
                    )
                active = flags & valid_negative
                previous = False
                last_alert_ns: int | None = None
                for timestamp, is_active in zip(times, active):
                    if is_active and (
                        not previous
                        or last_alert_ns is None
                        or timestamp - last_alert_ns > 2.0e9
                    ):
                        false_incidents += 1
                    previous = bool(is_active)
                    last_alert_ns = int(timestamp) if is_active else None
            precision = detections / (detections + false_incidents) if detections + false_incidents else 0.0
            per_method[method] = {
                "events": len(class_runs),
                "detected_events": detections,
                "missed_events": len(class_runs) - detections,
                "event_recall": detections / len(class_runs) if class_runs else 0.0,
                "event_recall_ci_95_wilson": wilson_interval(
                    detections, len(class_runs)
                ),
                "false_positive_incidents": false_incidents,
                "event_precision": precision,
                "event_f1": (
                    2 * precision * (detections / len(class_runs))
                    / (precision + detections / len(class_runs))
                    if precision + (detections / len(class_runs)) > 0
                    else 0.0
                ),
                "median_latency_from_label_start_s": (
                    float(np.median(latencies)) if latencies else None
                ),
                "median_latency_from_first_observable_change_s": (
                    float(np.median(observable_latencies)) if observable_latencies else None
                ),
                "tolerance_before_start_s": _TOLERANCE_BEFORE_START_S,
                "tolerance_after_stop_s": _TOLERANCE_AFTER_STOP_S,
            }
        output[class_name] = per_method
    return output, events_report


def _false_alert_rates(
    runs: list[SecurityRun], predictions: dict[str, dict[str, np.ndarray]]
) -> dict[str, Any]:
    methods = ["rules", "isolation_forest", "random_forest", "rules_plus_model"]
    results: dict[str, Any] = {}
    for method in methods:
        scopes = {
            "normal_runs": [run for run in runs if run.run_type == "normal"],
            "normal_segments": runs,
        }
        results[method] = {}
        for scope, scope_runs in scopes.items():
            alerts = 0
            normal_seconds = 0.0
            for run in scope_runs:
                times = pd.to_numeric(run.telemetry["sim_time_ns"], errors="coerce").to_numpy()
                values = predictions[method][run.run_id]
                elapsed = (times - times[0]) / 1e9
                valid_normal = elapsed >= 15.0
                bounds = _event_bounds(run)
                if bounds:
                    start, stop = bounds
                    valid_normal &= (times < start - _TOLERANCE_BEFORE_START_S * 1e9) | (
                        times >= stop + _TOLERANCE_AFTER_STOP_S * 1e9
                    )
                normal_seconds += float(valid_normal.sum()) * 0.5
                selected = values.astype(bool) & valid_normal
                previous = False
                last_time = None
                for timestamp, active in zip(times, selected):
                    if active and (
                        not previous
                        or last_time is None
                        or timestamp - last_time > 2.0e9
                    ):
                        alerts += 1
                    previous = bool(active)
                    last_time = timestamp if active else None
            results[method][scope] = {
                "false_alert_incidents": alerts,
                "normal_hours": normal_seconds / 3600.0,
                "false_alerts_per_hour": alerts / (normal_seconds / 3600.0)
                if normal_seconds
                else None,
            }
    return results


def evaluate_tolerance_sensitivity(
    data_root: str | Path,
    model_path: str | Path,
    inventory_path: str | Path,
    report_dir: str | Path,
) -> dict[str, Any]:
    """Compare post-event tolerances on seeds 1-2 without changing model thresholds."""
    bundle = joblib.load(model_path)
    if bundle.get("task") != "ros2_telemetry_security_anomaly":
        raise ValueError("The saved bundle is not a ROS 2 telemetry security model.")
    inventory = load_inventory(inventory_path, require_approved=False)
    runs = load_security_runs(data_root, seeds={1, 2})
    methods = {
        "policy_rules": {},
        "selected_telemetry_model": {},
        "rules_plus_selected_model": {},
    }
    cached: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    model_name = str(bundle["selected_model"])
    for run in runs:
        times = pd.to_numeric(
            run.telemetry["sim_time_ns"], errors="raise"
        ).to_numpy(dtype=np.int64)
        rule_findings = evaluate_rules(
            run.telemetry, inventory, run.run_id, manifest=run.manifest
        )
        rule_flags = _row_flags(
            run.telemetry,
            [finding for finding in rule_findings if finding.source == "policy"],
        ).astype(bool)
        features = telemetry_features(run.telemetry).reindex(
            columns=bundle["feature_columns"]
        )
        scores = security_scores(bundle["models"][model_name], model_name, features)
        model_flags = scores >= float(bundle["thresholds"][model_name])
        cached[run.run_id] = (times, rule_flags, model_flags)
        methods["policy_rules"][run.run_id] = rule_flags
        methods["selected_telemetry_model"][run.run_id] = model_flags
        methods["rules_plus_selected_model"][run.run_id] = rule_flags | model_flags

    tolerance_values = (0.0, 0.5, 1.0, 1.5, 2.0)
    reports: list[dict[str, Any]] = []
    for after_stop_s in tolerance_values:
        method_reports = []
        for method, predictions in methods.items():
            total_events = detected_events = 0
            class_results: dict[str, dict[str, int]] = {}
            false_incidents = 0
            normal_seconds = 0.0
            for run in runs:
                times, _, _ = cached[run.run_id]
                flags = predictions[run.run_id]
                elapsed = (times - times[0]) / 1e9
                valid_normal = elapsed >= 15.0
                bounds = _event_bounds(run)
                if bounds is not None:
                    start_ns, stop_ns = bounds
                    in_event_window = (
                        (times >= start_ns - _TOLERANCE_BEFORE_START_S * 1e9)
                        & (times < stop_ns + after_stop_s * 1e9)
                    )
                    valid_normal &= ~in_event_window
                    if run.run_type == "attack":
                        class_name = run.attack_name
                        counts = class_results.setdefault(
                            class_name, {"events": 0, "detected_events": 0}
                        )
                        counts["events"] += 1
                        total_events += 1
                        event_detected = bool(np.any(flags & in_event_window))
                        counts["detected_events"] += int(event_detected)
                        detected_events += int(event_detected)
                positive_times: list[int] = []
                previous = False
                for timestamp, active in zip(times, flags & valid_normal):
                    if active and (
                        not previous
                        or not positive_times
                        or timestamp - positive_times[-1] > 2_000_000_000
                    ):
                        false_incidents += 1
                    previous = bool(active)
                    if active:
                        positive_times.append(int(timestamp))
                differences = np.diff(times)
                tick_seconds = (
                    float(np.median(differences[differences > 0]) / 1e9)
                    if np.any(differences > 0)
                    else 0.5
                )
                normal_seconds += float(valid_normal.sum()) * tick_seconds
            normal_hours = normal_seconds / 3600.0
            for values in class_results.values():
                values["recall"] = (
                    values["detected_events"] / values["events"]
                    if values["events"]
                    else 0.0
                )
            method_reports.append(
                {
                    "method": method,
                    "events": total_events,
                    "detected_events": detected_events,
                    "event_recall": (
                        detected_events / total_events if total_events else 0.0
                    ),
                    "false_alert_incidents": false_incidents,
                    "normal_hours": normal_hours,
                    "false_alerts_per_hour": (
                        false_incidents / normal_hours if normal_hours else None
                    ),
                    "per_class": class_results,
                }
            )
        reports.append(
            {
                "tolerance_after_stop_s": after_stop_s,
                "methods": method_reports,
            }
        )

    report = {
        "analysis": "Post-event tolerance sensitivity using seeds 1 and 2 only.",
        "scikit_learn_version": sklearn.__version__,
        "security_model_sha256": _sha256_file(model_path),
        "seeds": [1, 2],
        "run_count": len(runs),
        "pre_start_tolerance_s": _TOLERANCE_BEFORE_START_S,
        "post_stop_tolerances_s": list(tolerance_values),
        "frozen_model_thresholds": bundle["thresholds"],
        "model_thresholds_changed": False,
        "interpretation_note": (
            "The shipped model was trained on seeds 1-2, so these results are "
            "in-sample diagnostics for label-window sensitivity, not independent "
            "performance estimates. Seed 3 was not accessed."
        ),
        "results": reports,
    }
    destination = Path(report_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "security_tolerance_sensitivity.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Security event stop-tolerance sensitivity",
        "",
        f"- **Seeds:** {report['seeds']} only; {report['run_count']} runs.",
        f"- **Pre-start tolerance:** {report['pre_start_tolerance_s']} s.",
        f"- **scikit-learn:** {report['scikit_learn_version']}.",
        f"- **Security model SHA-256:** `{report['security_model_sha256']}`.",
        f"- **Thresholds changed:** {report['model_thresholds_changed']}.",
        f"- **Interpretation:** {report['interpretation_note']}",
        "",
        "| Post-stop tolerance (s) | Method | Detected/events | Event recall | False incidents | Normal hours | False alerts/hour |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for tolerance in reports:
        for item in tolerance["methods"]:
            lines.append(
                f"| {tolerance['tolerance_after_stop_s']:.1f} | {item['method']} | "
                f"{item['detected_events']}/{item['events']} | "
                f"{item['event_recall']:.4f} | {item['false_alert_incidents']} | "
                f"{item['normal_hours']:.3f} | "
                f"{item['false_alerts_per_hour']:.3f} |"
            )
    (destination / "security_tolerance_sensitivity.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return report


def _episode_starts(flags: np.ndarray) -> list[int]:
    starts: list[int] = []
    previous = False
    for position, active in enumerate(flags):
        if active and not previous:
            starts.append(position)
        previous = bool(active)
    return starts


def _rule_alert_diagnostics(
    runs: list[SecurityRun], findings: list[Finding]
) -> dict[str, Any]:
    """Attribute seed-3 rule alert episodes to classes and label boundaries."""
    residual_rule_ids = {"node_set_hash_change", "unapproved_node"}
    by_run: dict[str, list[Finding]] = {}
    for finding in findings:
        if finding.source == "policy":
            by_run.setdefault(finding.run_id, []).append(finding)

    combined_records: list[dict[str, Any]] = []
    per_rule_records: list[dict[str, Any]] = []
    tolerance_ticks = 0
    startup_ticks = 0
    false_alerted_ticks = 0
    normal_seconds = 0.0
    for run in runs:
        run_findings = by_run.get(run.run_id, [])
        times = pd.to_numeric(run.telemetry["sim_time_ns"], errors="coerce").to_numpy(
            dtype=np.int64
        )
        elapsed = (times - times[0]) / 1e9
        event_names = (
            run.events["event"].astype(str).str.lower()
            if not run.events.empty
            else pd.Series(dtype=str)
        )
        starts = (
            pd.to_numeric(
                run.events.loc[event_names.eq("start"), "sim_time_ns"], errors="coerce"
            ).dropna().to_numpy(dtype=np.int64)
            if not run.events.empty
            else np.array([], dtype=np.int64)
        )
        stops = (
            pd.to_numeric(
                run.events.loc[event_names.eq("stop"), "sim_time_ns"], errors="coerce"
            ).dropna().to_numpy(dtype=np.int64)
            if not run.events.empty
            else np.array([], dtype=np.int64)
        )
        tolerance = np.zeros(len(times), dtype=bool)
        normal_segments = elapsed >= 15.0
        boundaries = np.concatenate((starts, stops))
        for start in starts:
            tolerance |= (times >= start - _TOLERANCE_BEFORE_START_S * 1e9) & (
                times < start
            )
        for stop in stops:
            tolerance |= (times >= stop) & (
                times < stop + _TOLERANCE_AFTER_STOP_S * 1e9
            )
        for start, stop in zip(starts, stops):
            normal_segments &= (times < start - _TOLERANCE_BEFORE_START_S * 1e9) | (
                times >= stop + _TOLERANCE_AFTER_STOP_S * 1e9
            )
        normal_seconds += float(normal_segments.sum()) * 0.5

        by_time: dict[int, set[str]] = {}
        by_rule_times: dict[str, set[int]] = {}
        for finding in run_findings:
            timestamp = int(finding.timestamp_sim_ns)
            by_time.setdefault(timestamp, set()).add(finding.rule_id)
            by_rule_times.setdefault(finding.rule_id, set()).add(timestamp)
        all_flags = np.asarray([int(time) in by_time for time in times], dtype=bool)
        tolerance_ticks += int((all_flags & tolerance).sum())
        startup_ticks += int((all_flags & (elapsed < 15.0)).sum())
        run_class = run.attack_name if run.run_type == "attack" else "normal"

        false_flags = all_flags & normal_segments
        false_alerted_ticks += int(false_flags.sum())
        false_starts = _episode_starts(false_flags)
        false_episode_records: list[dict[str, Any]] = []
        for position in false_starts:
            timestamp = int(times[position])
            end_position = position
            while end_position + 1 < len(false_flags) and false_flags[end_position + 1]:
                end_position += 1
            rules_in_episode = sorted(
                {
                    rule_id
                    for episode_time in times[position : end_position + 1]
                    for rule_id in by_time.get(int(episode_time), set())
                }
            )
            distance = (
                float(np.min(np.abs(boundaries - timestamp)) / 1e9)
                if len(boundaries)
                else None
            )
            bucket = (
                "within_1.5s_of_boundary"
                if distance is not None and distance <= 1.5
                else "elsewhere"
            )
            active_rules = sorted(by_time.get(timestamp, set()))
            category = (
                "residual_attack_activity_outside_label"
                if residual_rule_ids.intersection(rules_in_episode)
                else "unattributed"
            )
            record = {
                "run_id": run.run_id,
                "run_class": run_class,
                "timestamp_sim_ns": timestamp,
                "distance_to_nearest_attack_boundary_s": distance,
                "boundary_bucket": bucket,
                "rule_ids_at_episode_start": active_rules,
                "rule_ids_in_episode": rules_in_episode,
                "false_alert_category": category,
            }
            combined_records.append(record)
            false_episode_records.append(record)

        for rule_id, timestamps in by_rule_times.items():
            flags = np.asarray([int(time) in timestamps for time in times], dtype=bool)
            for position in _episode_starts(flags & normal_segments):
                timestamp = int(times[position])
                distance = (
                    float(np.min(np.abs(boundaries - timestamp)) / 1e9)
                    if len(boundaries)
                    else None
                )
                per_rule_records.append(
                    {
                        "run_id": run.run_id,
                        "run_class": run_class,
                        "rule_id": rule_id,
                        "timestamp_sim_ns": timestamp,
                        "distance_to_nearest_attack_boundary_s": distance,
                        "boundary_bucket": (
                            "within_1.5s_of_boundary"
                            if distance is not None and distance <= 1.5
                            else "elsewhere"
                        ),
                        "false_alert_category": (
                            "residual_attack_activity_outside_label"
                            if rule_id in residual_rule_ids
                            else "unattributed"
                        ),
                    }
                )

    by_class = Counter(item["run_class"] for item in combined_records)
    by_boundary = Counter(item["boundary_bucket"] for item in combined_records)
    by_false_alert_category = Counter(
        item["false_alert_category"] for item in combined_records
    )
    by_rule = Counter(item["rule_id"] for item in per_rule_records)
    by_rule_category = Counter(
        (item["rule_id"], item["false_alert_category"])
        for item in per_rule_records
    )
    by_rule_class_boundary = Counter(
        (item["rule_id"], item["run_class"], item["boundary_bucket"])
        for item in per_rule_records
    )
    return {
        "definition": (
            "Matches the evaluation false-alert mask: after 15 seconds of startup and "
            "outside event start-1.5 seconds through event stop+0.5 seconds. Episodes "
            "are contiguous flagged telemetry ticks; rule-specific episode counts can "
            "overlap and therefore do not sum to the combined episode count."
        ),
        "combined_false_alert_episodes": len(combined_records),
        "false_alerted_telemetry_ticks": false_alerted_ticks,
        "normal_segment_hours": normal_seconds / 3600.0,
        "combined_false_alerts_per_hour": (
            len(combined_records) / (normal_seconds / 3600.0)
            if normal_seconds
            else None
        ),
        "false_alert_attribution": {
            "combined_episodes_before_attribution": len(combined_records),
            "combined_episodes_after_attribution": len(combined_records),
            "by_category": [
                {
                    "category": category,
                    "combined_episodes": int(count),
                    "episodes_per_hour": (
                        count / (normal_seconds / 3600.0) if normal_seconds else None
                    ),
                }
                for category, count in sorted(by_false_alert_category.items())
            ],
            "graph_rule_episodes_reclassified": int(
                sum(
                    count
                    for (rule, category), count in by_rule_category.items()
                    if rule in residual_rule_ids
                    and category == "residual_attack_activity_outside_label"
                )
            ),
            "graph_rule_episode_counts": {
                rule_id: int(by_rule[rule_id]) for rule_id in sorted(residual_rule_ids)
            },
        },
        "by_run_class": [
            {"run_class": name, "combined_false_alert_episodes": int(count)}
            for name, count in sorted(by_class.items())
        ],
        "by_boundary_bucket": [
            {"bucket": name, "combined_false_alert_episodes": int(count)}
            for name, count in sorted(by_boundary.items())
        ],
        "by_rule_id": [
            {
                "rule_id": name,
                "independent_false_alert_episodes": int(count),
                "false_alert_category": (
                    "residual_attack_activity_outside_label"
                    if name in residual_rule_ids
                    else "unattributed"
                ),
            }
            for name, count in sorted(by_rule.items())
        ],
        "by_rule_class_boundary": [
            {
                "rule_id": rule,
                "run_class": run_class,
                "boundary_bucket": bucket,
                "independent_false_alert_episodes": int(count),
                "false_alert_category": (
                    "residual_attack_activity_outside_label"
                    if rule in residual_rule_ids
                    else "unattributed"
                ),
            }
            for (rule, run_class, bucket), count in sorted(
                by_rule_class_boundary.items()
            )
        ],
        "by_rule_category": [
            {
                "rule_id": rule,
                "false_alert_category": category,
                "independent_false_alert_episodes": int(count),
            }
            for (rule, category), count in sorted(by_rule_category.items())
        ],
        "policy_alert_ticks_inside_evaluation_tolerance": tolerance_ticks,
        "false_alert_episodes_inside_evaluation_tolerance": 0,
        "startup_policy_alert_ticks_excluded_from_evaluation": startup_ticks,
    }
def evaluate_security_detector(
    data_root: str | Path,
    model_path: str | Path,
    inventory_path: str | Path,
    report_dir: str | Path,
) -> dict[str, Any]:
    """Evaluate on seed 3; thresholds and inventory must be independently reviewed."""
    bundle = joblib.load(model_path)
    if bundle.get("task") != "ros2_telemetry_security_anomaly":
        raise ValueError("The saved bundle is not a ROS 2 telemetry security model.")
    inventory = load_inventory(inventory_path, require_approved=False)
    runs = [run for run in load_security_runs(data_root, seeds={3})]
    method_predictions: dict[str, dict[str, np.ndarray]] = {
        method: {} for method in ("rules", "isolation_forest", "random_forest", "rules_plus_model")
    }
    method_scores: dict[str, dict[str, np.ndarray]] = {
        method: {} for method in method_predictions
    }
    method_findings: dict[str, list[Finding]] = {method: [] for method in method_predictions}
    prediction_rows: list[dict[str, Any]] = []
    for run in runs:
        features = telemetry_features(run.telemetry).reindex(
            columns=bundle["feature_columns"]
        )
        scores_by_model: dict[str, np.ndarray] = {}
        predictions_by_model: dict[str, np.ndarray] = {}
        findings_by_model: dict[str, list[Finding]] = {}
        for model_name, model in bundle["models"].items():
            scores = security_scores(model, model_name, features)
            scores_by_model[model_name] = scores
            predictions_by_model[model_name] = (
                scores >= float(bundle["thresholds"][model_name])
            ).astype(np.int8)
            findings_by_model[model_name] = [
                Finding(
                    rule_id=model_name,
                    timestamp_sim_ns=int(run.telemetry.iloc[position]["sim_time_ns"]),
                    run_id=run.run_id,
                    source="anomaly_model",
                    severity="medium",
                    score=float(scores[position]),
                    threshold=float(bundle["thresholds"][model_name]),
                    evidence={
                        "model": model_name,
                        "score": float(scores[position]),
                        "threshold": float(bundle["thresholds"][model_name]),
                    },
                    what_this_does_not_prove="An anomaly score is not a probability or proof of unauthorized access.",
                    recommended_next_step="Review the contributing telemetry and verify the activity with the authorized system owner.",
                )
                for position in np.flatnonzero(predictions_by_model[model_name])
            ]
        rule_findings = evaluate_rules(
            run.telemetry, inventory, run.run_id, manifest=run.manifest
        )
        rule_flags = _row_flags(
            run.telemetry,
            [finding for finding in rule_findings if finding.source == "policy"],
        )
        method_predictions["rules"][run.run_id] = rule_flags
        method_scores["rules"][run.run_id] = rule_flags.astype(float)
        method_findings["rules"].extend(rule_findings)
        for model_name in ("isolation_forest", "random_forest"):
            method_predictions[model_name][run.run_id] = predictions_by_model[model_name]
            method_scores[model_name][run.run_id] = scores_by_model[model_name]
            method_findings[model_name].extend(findings_by_model[model_name])
        selected_model = bundle["selected_model"]
        combined = np.maximum(rule_flags, predictions_by_model[selected_model])
        method_predictions["rules_plus_model"][run.run_id] = combined
        method_scores["rules_plus_model"][run.run_id] = np.maximum(
            rule_flags.astype(float), scores_by_model[selected_model]
        )
        method_findings["rules_plus_model"].extend(rule_findings)
        method_findings["rules_plus_model"].extend(findings_by_model[selected_model])

        times = run.telemetry["sim_time_ns"].astype("int64").to_numpy()
        for position, row in run.telemetry.iterrows():
            pos = int(position) if isinstance(position, (int, np.integer)) else run.telemetry.index.get_loc(position)
            prediction_rows.append(
                {
                    "run_id": run.run_id,
                    "relative_path": run.relative_path,
                    "attack_name": run.attack_name,
                    "type": run.run_type,
                    "npc": run.npc,
                    "seed": run.seed,
                    "level": run.level,
                    "sim_time_ns": int(times[pos]),
                    "event_label": int(run.labels.iloc[pos]),
                    **{
                        f"predicted_{method}": int(values[run.run_id][pos])
                        for method, values in method_predictions.items()
                    },
                    **{
                        f"score_{model_name}": float(score[pos])
                        for model_name, score in scores_by_model.items()
                    },
                }
            )

    aggregate: dict[str, Any] = {}
    for method in method_predictions:
        labels = np.concatenate([run.labels.to_numpy(dtype=np.int8) for run in runs])
        preds = np.concatenate([method_predictions[method][run.run_id] for run in runs])
        scores = np.concatenate([method_scores[method][run.run_id] for run in runs])
        aggregate[method] = _metrics(labels, preds, scores)
    class_metrics: dict[str, Any] = {}
    supported_classes = set(bundle["trained_attack_classes"])
    for class_name in sorted({run.attack_name for run in runs if run.run_type == "attack"}):
        class_runs = [
            run
            for run in runs
            if run.run_type == "normal" or run.attack_name == class_name
        ]
        labels = np.concatenate([run.labels.to_numpy(dtype=np.int8) for run in class_runs])
        status, reason = _class_status(class_name)
        per_method = {}
        for method in method_predictions:
            preds = np.concatenate(
                [method_predictions[method][run.run_id] for run in class_runs]
            )
            scores = np.concatenate(
                [method_scores[method][run.run_id] for run in class_runs]
            )
            per_method[method] = _metrics(labels, preds, scores)
        class_metrics[class_name] = {
            "telemetry_assessment": status,
            "assessment_reason": reason,
            "trained_as_positive_class": class_name in supported_classes,
            "row_metrics": per_method,
        }

    event_results, event_rows = _event_metrics(runs, method_predictions)
    false_alert_rates = _false_alert_rates(runs, method_predictions)
    rule_diagnostics = _rule_alert_diagnostics(runs, method_findings["rules"])
    alerts_by_method = {
        method: [alert.to_dict() for alert in merge_alerts(findings)]
        for method, findings in method_findings.items()
    }
    severity_counts = {
        method: {
            severity: int(count)
            for severity, count in pd.Series(
                [item["severity"] for item in alerts], dtype="object"
            ).value_counts().items()
        }
        for method, alerts in alerts_by_method.items()
    }
    rows = pd.DataFrame(prediction_rows)
    events_frame = pd.DataFrame(event_rows)
    scenario_records: list[dict[str, Any]] = []
    for run in runs:
        labels = run.labels.to_numpy(dtype=np.int8)
        for method in method_predictions:
            predictions_for_run = method_predictions[method][run.run_id]
            scenario_records.append(
                {
                    "run_id": run.run_id,
                    "attack_name": run.attack_name,
                    "type": run.run_type,
                    "npc": run.npc,
                    "seed": run.seed,
                    "level": run.level,
                    "method": method,
                    **_metrics(
                        labels,
                        predictions_for_run,
                        method_scores[method][run.run_id],
                    ),
                }
            )
    scenario_frame = pd.DataFrame(scenario_records)
    npc_level = (
        scenario_frame.groupby(
            ["attack_name", "npc", "level", "method"], dropna=False
        )[["precision", "recall", "f1", "false_positive_rate"]]
        .mean()
        .reset_index()
    )
    destination = Path(report_dir)
    destination.mkdir(parents=True, exist_ok=True)
    rows.to_csv(destination / "security_predictions.csv", index=False)
    events_frame.to_csv(destination / "security_event_metrics.csv", index=False)
    scenario_frame.to_csv(destination / "security_scenario_metrics.csv", index=False)
    npc_level.to_csv(destination / "security_npc_level_metrics.csv", index=False)
    pd.DataFrame(
        [
            {"attack_name": class_name, "assessment": value["telemetry_assessment"],
             "trained_as_positive_class": value["trained_as_positive_class"],
             "method": method, **metrics}
            for class_name, value in class_metrics.items()
            for method, metrics in value["row_metrics"].items()
        ]
    ).to_csv(destination / "security_class_metrics.csv", index=False)
    alert_rows = [
        {"method": method, **alert}
        for method, alerts in alerts_by_method.items()
        for alert in alerts
    ]
    pd.DataFrame(alert_rows).to_csv(destination / "security_alerts.csv", index=False)
    breakdown_rows = [
        {
            "breakdown": "combined_by_run_class",
            "run_class": item["run_class"],
            "boundary_bucket": None,
            "rule_id": None,
            "episodes": item["combined_false_alert_episodes"],
        }
        for item in rule_diagnostics["by_run_class"]
    ]
    breakdown_rows.extend(
        {
            "breakdown": "combined_by_boundary",
            "run_class": None,
            "boundary_bucket": item["bucket"],
            "rule_id": None,
            "episodes": item["combined_false_alert_episodes"],
        }
        for item in rule_diagnostics["by_boundary_bucket"]
    )
    breakdown_rows.extend(
        {
            "breakdown": "independent_by_rule",
            "run_class": None,
            "boundary_bucket": None,
            "rule_id": item["rule_id"],
            "false_alert_category": item["false_alert_category"],
            "episodes": item["independent_false_alert_episodes"],
        }
        for item in rule_diagnostics["by_rule_id"]
    )
    breakdown_rows.extend(
        {
            "breakdown": "independent_by_rule_class_boundary",
            "run_class": item["run_class"],
            "boundary_bucket": item["boundary_bucket"],
            "rule_id": item["rule_id"],
            "false_alert_category": item["false_alert_category"],
            "episodes": item["independent_false_alert_episodes"],
        }
        for item in rule_diagnostics["by_rule_class_boundary"]
    )
    breakdown_rows.extend(
        {
            "breakdown": "independent_by_rule_category",
            "run_class": None,
            "boundary_bucket": None,
            "rule_id": item["rule_id"],
            "false_alert_category": item["false_alert_category"],
            "episodes": item["independent_false_alert_episodes"],
        }
        for item in rule_diagnostics["by_rule_category"]
    )
    breakdown_rows.extend(
        {
            "breakdown": "combined_by_false_alert_category",
            "run_class": None,
            "boundary_bucket": None,
            "rule_id": None,
            "false_alert_category": item["category"],
            "episodes": item["combined_episodes"],
        }
        for item in rule_diagnostics["false_alert_attribution"]["by_category"]
    )
    pd.DataFrame(breakdown_rows).to_csv(
        destination / "security_false_alert_breakdown.csv", index=False
    )

    report = {
        "task": bundle["task"],
        "scikit_learn_version": sklearn.__version__,
        "security_model_sha256": _sha256_file(model_path),
        "dataset_split": {
            "test_seeds": [3],
            "test_runs": len(runs),
            "split_by_whole_run": True,
            "labels_source": "events.csv start-inclusive, stop-exclusive intervals",
        },
        "event_tolerance": {
            "before_start_s": _TOLERANCE_BEFORE_START_S,
            "after_stop_s": _TOLERANCE_AFTER_STOP_S,
            "rationale": "The dataset guide reports a maximum 1.4167 s label-start offset for telemetry-based rogue-program attacks; 1.5 s rounds this up. A 0.5 s trailing tolerance is one telemetry tick.",
        },
        "thresholds": bundle["thresholds"],
        "inventory_approval_status": inventory["approval_status"],
        "inventory_use_note": (
            "Offline benchmark only; a draft inventory is not accepted by security-scan."
            if inventory["approval_status"] == "draft"
            else (
                "Offline-demo inventory only; this status is not human approval for "
                "deployment or live scanning."
                if inventory["approval_status"] == "approved_for_offline_demo"
                else "The inventory is marked approved by its owner."
            )
        ),
        "selected_model": bundle["selected_model"],
        "trained_attack_classes": bundle["trained_attack_classes"],
        "overall_row_metrics": aggregate,
        "per_class_row_metrics": class_metrics,
        "event_metrics": event_results,
        "event_recall_confidence_interval_method": "95% Wilson score interval",
        "small_sample_warning": (
            "There are only 3 held-out events for spoof, unauthorized_node, and "
            "unauthorized_subscription. Their point estimates and confidence intervals "
            "are too imprecise to claim reliability."
        ),
        "false_alerts_per_hour": false_alert_rates,
        "rules_false_alert_diagnostics": rule_diagnostics,
        "merged_alert_counts_by_severity": severity_counts,
        "per_run_scenario_metrics": scenario_records,
        "mean_metrics_by_npc_level": npc_level.to_dict(orient="records"),
        "merged_alert_counts": {
            method: len(alerts) for method, alerts in alerts_by_method.items()
        },
        "limitations": [
            "Seed 3 is a single held-out simulation seed, not external validation.",
            "Metrics for classes not used as supervised training positives are diagnostic only.",
            "Telemetry has no host/IP/MAC/DDS participant identity or topic-payload access evidence.",
            "There is no movement-command topic or live bridge/domain change stream in the recordings.",
            "No real-time, real-vehicle, or safety-critical performance is established.",
        ],
        "files": [
            "security_predictions.csv",
            "security_event_metrics.csv",
            "security_scenario_metrics.csv",
            "security_npc_level_metrics.csv",
            "security_class_metrics.csv",
            "security_alerts.csv",
            "security_false_alert_breakdown.csv",
            "security_false_alert_analysis.md",
        ],
    }
    (destination / "security_evaluation_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    lines = [
        "# ROS 2 telemetry security evaluation",
        "",
        f"- **scikit-learn runtime version:** {sklearn.__version__}.",
        f"- **Security model SHA-256:** `{_sha256_file(model_path)}`.",
        "- **Test split:** seed 3, whole runs held out.",
        f"- **Test runs:** {len(runs)}.",
        f"- **Selected model:** {bundle['selected_model']}.",
        "- **Labels:** `events.csv` intervals; stored `is_attack` is not used as the label source.",
        f"- **Event tolerance:** -{_TOLERANCE_BEFORE_START_S:.1f}s before start and "
        f"+{_TOLERANCE_AFTER_STOP_S:.1f}s after stop.",
        "",
        "## Overall row metrics",
        "",
        "| Method | Precision | Recall | F1 | FPR |",
        "|---|---:|---:|---:|---:|",
    ]
    for method, metrics in aggregate.items():
        lines.append(
            f"| {method} | {metrics['precision']:.4f} | {metrics['recall']:.4f} | "
            f"{metrics['f1']:.4f} | {metrics['false_positive_rate']:.4f} |"
        )
    lines.extend(["", "## Per-class row-level metrics", "", "| Class | Scope | Method | Precision | Recall | F1 | FPR |", "|---|---|---|---:|---:|---:|---:|"])
    for name, result in class_metrics.items():
        for method, metrics in result["row_metrics"].items():
            lines.append(
                f"| {name} | {result['telemetry_assessment']} | {method} | "
                f"{metrics['precision']:.4f} | {metrics['recall']:.4f} | "
                f"{metrics['f1']:.4f} | {metrics['false_positive_rate']:.4f} |"
            )
    lines.extend(["", "## Event-level metrics by class", "", "| Class | Method | Detected / total | Precision | Recall | 95% Wilson CI | F1 | Median latency from label (s) |", "|---|---|---:|---:|---:|---|---:|---:|"])
    for name, methods in event_results.items():
        for method, metrics in methods.items():
            latency = metrics["median_latency_from_label_start_s"]
            interval = metrics["event_recall_ci_95_wilson"]
            interval_text = (
                f"[{interval[0]:.3f}, {interval[1]:.3f}]"
                if interval is not None
                else "n/a"
            )
            lines.append(
                f"| {name} | {method} | {metrics['detected_events']}/{metrics['events']} | "
                f"{metrics['event_precision']:.4f} | {metrics['event_recall']:.4f} | "
                f"{interval_text} | {metrics['event_f1']:.4f} | "
                f"{latency if latency is not None else 'n/a'} |"
            )
    lines.extend(
        [
            "",
            report["small_sample_warning"],
            "",
            "## False alerts per hour",
            "",
            "| Method | Scope | False alert incidents | Normal hours | Alerts/hour |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for method, scopes in false_alert_rates.items():
        for scope, metrics in scopes.items():
            lines.append(
                f"| {method} | {scope} | {metrics['false_alert_incidents']} | "
                f"{metrics['normal_hours']:.3f} | "
                f"{metrics['false_alerts_per_hour']:.3f} |"
            )
    lines.extend(
        [
            "",
            "## Rules false-alert breakdown",
            "",
            f"- Combined false-alert episodes in normal segments: "
            f"{rule_diagnostics['combined_false_alert_episodes']} across "
            f"{rule_diagnostics['normal_segment_hours']:.3f} hours "
            f"({rule_diagnostics['combined_false_alerts_per_hour']:.3f}/hour).",
            f"- Policy-alert ticks inside the evaluation tolerance windows: "
            f"{rule_diagnostics['policy_alert_ticks_inside_evaluation_tolerance']}; "
            f"none of those false-alert episodes count inside the false-positive mask.",
            f"- Startup policy-alert ticks excluded from evaluation: "
            f"{rule_diagnostics['startup_policy_alert_ticks_excluded_from_evaluation']}.",
            "- Per-rule episode counts can overlap; see "
            "`security_false_alert_breakdown.csv` for rule, class, and boundary detail.",
            "",
            "### Combined false episodes by run class",
            "",
            "| Run class | Episodes |",
            "|---|---:|",
        ]
    )
    for item in rule_diagnostics["by_run_class"]:
        lines.append(
            f"| {item['run_class']} | {item['combined_false_alert_episodes']} |"
        )
    lines.extend(
        [
            "",
            "### Combined false episodes by nearest boundary",
            "",
            "| Boundary bucket | Episodes |",
            "|---|---:|",
        ]
    )
    for item in rule_diagnostics["by_boundary_bucket"]:
        lines.append(f"| {item['bucket']} | {item['combined_false_alert_episodes']} |")
    lines.extend(["", "## Limitations", "", *[f"- {item}" for item in report["limitations"]], ""])
    (destination / "security_evaluation_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    analysis_lines = [
        "# Rules false-alert analysis (seed 3)",
        "",
        rule_diagnostics["definition"],
        "",
        f"- **Combined false-alert episodes:** {rule_diagnostics['combined_false_alert_episodes']}",
        f"- **False-alerted telemetry ticks:** {rule_diagnostics['false_alerted_telemetry_ticks']}",
        f"- **Normal-segment hours:** {rule_diagnostics['normal_segment_hours']:.6f}",
        f"- **Rate:** {rule_diagnostics['combined_false_alerts_per_hour']:.3f}/hour",
        f"- **Policy-alert ticks in the evaluation tolerance windows:** {rule_diagnostics['policy_alert_ticks_inside_evaluation_tolerance']}",
        f"- **False episodes inside those tolerance windows:** {rule_diagnostics['false_alert_episodes_inside_evaluation_tolerance']}",
        f"- **Startup alert ticks excluded from evaluation:** {rule_diagnostics['startup_policy_alert_ticks_excluded_from_evaluation']}",
        f"- **Before attribution:** {rule_diagnostics['false_alert_attribution']['combined_episodes_before_attribution']} combined episodes had no source category assigned.",
        f"- **After attribution:** {rule_diagnostics['false_alert_attribution']['combined_episodes_after_attribution']} combined episodes remain; "
        f"{rule_diagnostics['false_alert_attribution']['graph_rule_episodes_reclassified']} independent graph-rule episodes are categorized as residual attack activity outside the label.",
        "",
        "The evaluation tolerance is 1.5 s before event start and 0.5 s after event stop. "
        "The separate boundary bucket uses symmetric ±1.5 s around either event boundary. "
        "Thus a rule episode just after the stop tolerance can be counted as a false "
        "normal-segment episode while still lying within ±1.5 s of the stop.",
        "",
        "## Combined episodes by run class",
        "",
        "| Run class | Combined false episodes |",
        "|---|---:|",
    ]
    for item in rule_diagnostics["by_run_class"]:
        analysis_lines.append(
            f"| {item['run_class']} | {item['combined_false_alert_episodes']} |"
        )
    analysis_lines.extend(
        [
            "",
            "## Combined episodes by boundary bucket",
            "",
            "| Bucket | Combined false episodes |",
            "|---|---:|",
        ]
    )
    for item in rule_diagnostics["by_boundary_bucket"]:
        analysis_lines.append(
            f"| {item['bucket']} | {item['combined_false_alert_episodes']} |"
        )
    analysis_lines.extend(
        [
            "",
            "## Independent per-rule episodes",
            "",
            "Counts below are computed per rule and can overlap across rules, so do not sum them to obtain the combined episode count.",
            "",
            "| Rule ID | False-alert category | Episodes |",
            "|---|---|---:|",
        ]
    )
    for item in rule_diagnostics["by_rule_id"]:
        analysis_lines.append(
            f"| {item['rule_id']} | {item['false_alert_category']} | "
            f"{item['independent_false_alert_episodes']} |"
        )
    analysis_lines.extend(
        [
            "",
            "## Per-rule, run-class, and boundary breakdown",
            "",
            "| Rule ID | Run class | Boundary bucket | False-alert category | Episodes |",
            "|---|---|---|---|---:|",
        ]
    )
    for item in rule_diagnostics["by_rule_class_boundary"]:
        analysis_lines.append(
            f"| {item['rule_id']} | {item['run_class']} | "
            f"{item['boundary_bucket']} | {item['false_alert_category']} | "
            f"{item['independent_false_alert_episodes']} |"
        )
    analysis_lines.extend(
        [
            "",
            "## False-alert attribution before and after",
            "",
            "The original combined episode count and rate are unchanged by attribution. "
            "The 5 `node_set_hash_change` and 3 `unapproved_node` independent rule episodes "
            "are marked `residual_attack_activity_outside_label`; rule-level episodes can "
            "overlap, so these 8 attributions are not subtracted from the combined total.",
            "",
            "| Category | Combined episodes | Episodes/hour |",
            "|---|---:|---:|",
        ]
    )
    for item in rule_diagnostics["false_alert_attribution"]["by_category"]:
        rate = item["episodes_per_hour"]
        analysis_lines.append(
            f"| {item['category']} | {item['combined_episodes']} | "
            f"{rate:.3f} |"
            if rate is not None
            else f"| {item['category']} | {item['combined_episodes']} | n/a |"
        )
    analysis_lines.extend(
        [
            "",
            "### Independent graph-rule attribution",
            "",
            "| Rule ID | Episodes categorized as residual activity |",
            "|---|---:|",
        ]
    )
    for rule_id, count in rule_diagnostics["false_alert_attribution"][
        "graph_rule_episode_counts"
    ].items():
        analysis_lines.append(f"| {rule_id} | {count} |")
    (destination / "security_false_alert_analysis.md").write_text(
        "\n".join(analysis_lines) + "\n", encoding="utf-8"
    )
    return report
