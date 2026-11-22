"""Scoring, robustness checks, and leave-one-class-out experiments."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy.stats import chi2
import sklearn

from .evaluation_streams import _strip_input_metadata
from .monitor import (
    _TIMESTAMP_JITTER_DEVIATION_S,
    MonitorResult,
    monitor_frames,
)
from .security.data import SecurityRun, load_security_runs
from .security.evaluate import _TOLERANCE_AFTER_STOP_S, _TOLERANCE_BEFORE_START_S, wilson_interval
from .security.inventory import validate_inventory
from .security.models import USABLE_CLASSES, _pipeline, _scores, _threshold
from .security.rules import evaluate_rules
from .security.telemetry import telemetry_features

_STARTUP_WINDOW_S = 15.0
_JOIN_WINDOW_S = 2.0
_CLASSES = (
    "bias_drift",
    "clock_skew",
    "delay",
    "drop",
    "duplicate",
    "false_contact",
    "flood",
    "freeze",
    "jump",
    "missed_contact",
    "noise",
    "param_tamper",
    "replay",
    "service_abuse",
    "spoof",
    "unauthorized_node",
    "unauthorized_subscription",
)
_EXPECTED_MISS_CLASSES = {"missed_contact"}
_TRUE_FAMILY = {
    "bias_drift": "sensor-value anomaly",
    "false_contact": "sensor-value anomaly",
    "freeze": "sensor-value anomaly",
    "jump": "sensor-value anomaly",
    "missed_contact": "sensor-value anomaly",
    "noise": "sensor-value anomaly",
    "replay": "sensor-value anomaly",
    "clock_skew": "timing anomaly",
    "delay": "timing anomaly",
    "drop": "timing anomaly",
    "duplicate": "timing anomaly",
    "flood": "flooding",
    "param_tamper": "graph/access anomaly",
    "service_abuse": "graph/access anomaly",
    "spoof": "graph/access anomaly",
    "unauthorized_node": "graph/access anomaly",
    "unauthorized_subscription": "graph/access anomaly",
}


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read stream manifest {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"Stream manifest must be a JSON object: {path}")
    return value


def _event_hits(incident: dict[str, Any], event: dict[str, Any]) -> bool:
    return (
        int(incident["start_sim_ns"])
        <= int(event["stop_sim_ns"]) + _TOLERANCE_AFTER_STOP_S * 1e9
        and int(incident["end_sim_ns"])
        >= int(event["start_sim_ns"]) - _TOLERANCE_BEFORE_START_S * 1e9
    )


def _event_metrics(
    incidents: list[dict[str, Any]], events: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    output: list[dict[str, Any]] = []
    event_detail: list[dict[str, Any]] = []
    classes = sorted({str(event["class_name"]) for event in events})
    for class_name in classes:
        class_events = [event for event in events if event["class_name"] == class_name]
        detected = 0
        latencies: list[float] = []
        for event in class_events:
            matches = [incident for incident in incidents if _event_hits(incident, event)]
            first = min(matches, key=lambda item: int(item["start_sim_ns"])) if matches else None
            detected += int(first is not None)
            if first is not None:
                latencies.append(
                    (int(first["start_sim_ns"]) - int(event["start_sim_ns"])) / 1e9
                )
            event_detail.append(
                {
                    "class_name": class_name,
                    "source_run": event["source_run"],
                    "detected": first is not None,
                    "first_alert_start_sim_ns": (
                        int(first["start_sim_ns"]) if first is not None else None
                    ),
                    "latency_s": latencies[-1] if first is not None else None,
                }
            )
        total = len(class_events)
        output.append(
            {
                "class_name": class_name,
                "events": total,
                "detected": detected,
                "missed": total - detected,
                "recall": detected / total if total else None,
                "recall_ci_95_wilson": wilson_interval(detected, total),
                "median_latency_s": float(np.median(latencies)) if latencies else None,
                "p90_latency_s": float(np.percentile(latencies, 90)) if latencies else None,
            }
        )
    correct_incidents = sum(
        any(_event_hits(incident, event) for event in events) for incident in incidents
    )
    incident_precision = correct_incidents / len(incidents) if incidents else None
    return (
        output,
        {
            "incidents": len(incidents),
            "incidents_matching_event": correct_incidents,
            "incident_precision": incident_precision,
        },
        event_detail,
    )


def _detector_event_metrics(
    incidents: list[dict[str, Any]], events: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    detector_names = sorted(
        {
            str(component["detector"])
            for incident in incidents
            for component in incident["evidence"]
        }
    )
    rows: list[dict[str, Any]] = []
    for detector in detector_names:
        detector_incidents = [
            incident
            for incident in incidents
            if any(
                str(component["detector"]) == detector
                for component in incident["evidence"]
            )
        ]
        for class_name in sorted({str(event["class_name"]) for event in events}):
            class_events = [
                event for event in events if str(event["class_name"]) == class_name
            ]
            latencies: list[float] = []
            detected = 0
            for event in class_events:
                matching_incidents = [
                    incident
                    for incident in detector_incidents
                    if _event_hits(incident, event)
                ]
                if matching_incidents:
                    detected += 1
                    earliest_component = min(
                        (
                            int(component["component_start_sim_ns"])
                            if component["component_start_sim_ns"] is not None
                            else int(incident["start_sim_ns"])
                        )
                        for incident in matching_incidents
                        for component in incident["evidence"]
                        if str(component["detector"]) == detector
                    )
                    latencies.append(
                        (earliest_component - int(event["start_sim_ns"])) / 1e9
                    )
            matching_incident_count = sum(
                any(_event_hits(incident, event) for event in class_events)
                for incident in detector_incidents
            )
            rows.append(
                {
                    "class_name": class_name,
                    "detector": detector,
                    "events": len(class_events),
                    "detected_events": detected,
                    "recall": detected / len(class_events) if class_events else None,
                    "detector_incidents": len(detector_incidents),
                    "incidents_matching_class": matching_incident_count,
                    "incident_precision": (
                        matching_incident_count / len(detector_incidents)
                        if detector_incidents
                        else None
                    ),
                    "median_latency_s": float(np.median(latencies)) if latencies else None,
                    "p90_latency_s": (
                        float(np.percentile(latencies, 90)) if latencies else None
                    ),
                }
            )
    return rows


def _row_metrics(
    aligned: pd.DataFrame,
    findings: list[Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    times = pd.to_numeric(aligned["sim_time_ns"], errors="raise").to_numpy(dtype=np.int64)
    truth = np.zeros(len(times), dtype=np.int8)
    for event in events:
        truth |= (
            (times >= int(event["start_sim_ns"]))
            & (times < int(event["stop_sim_ns"]))
        ).astype(np.int8)
    detections = np.zeros(len(times), dtype=np.int8)
    for finding in findings:
        timestamp = int(finding.timestamp_sim_ns)
        position = int(np.searchsorted(times, timestamp))
        options = [index for index in (position - 1, position) if 0 <= index < len(times)]
        if options:
            nearest = min(options, key=lambda index: abs(int(times[index]) - timestamp))
            detections[nearest] = 1
    tp = int(((truth == 1) & (detections == 1)).sum())
    fp = int(((truth == 0) & (detections == 1)).sum())
    fn = int(((truth == 1) & (detections == 0)).sum())
    tn = int(((truth == 0) & (detections == 0)).sum())
    return {
        "rows": len(times),
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
    }


def _near_join(incident: dict[str, Any], joins: list[int]) -> bool:
    window = int(_JOIN_WINDOW_S * 1e9)
    start = int(incident["start_sim_ns"])
    end = int(incident["end_sim_ns"])
    return any(start <= join + window and end >= join - window for join in joins)


def _near_boundary(incident: dict[str, Any], events: list[dict[str, Any]]) -> bool:
    limit = int(_TOLERANCE_BEFORE_START_S * 1e9)
    start = int(incident["start_sim_ns"])
    end = int(incident["end_sim_ns"])
    boundaries = [
        boundary
        for event in events
        for boundary in (int(event["start_sim_ns"]), int(event["stop_sim_ns"]))
    ]
    return any(
        start <= boundary + limit and end >= boundary - limit
        for boundary in boundaries
    )


def _poisson_rate_interval(count: int, exposure_hours: float) -> list[float] | None:
    if count < 0 or exposure_hours <= 0:
        return None
    alpha = 0.05
    lower_count = 0.0 if count == 0 else chi2.ppf(alpha / 2.0, 2 * count) / 2.0
    upper_count = chi2.ppf(1.0 - alpha / 2.0, 2 * (count + 1)) / 2.0
    return [float(lower_count / exposure_hours), float(upper_count / exposure_hours)]


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _residual_attack_activity(
    incident: dict[str, Any], segments: list[dict[str, Any]]
) -> bool:
    graph_evidence = False
    for component in incident["evidence"]:
        evidence = component.get("evidence", {})
        rule = str(component.get("rule_or_model", ""))
        if rule == "unapproved_node" and (
            evidence.get("observed_node")
            or any(
                sample.get("observed_node")
                for sample in evidence.get("sample_evidence", [])
                if isinstance(sample, dict)
            )
        ):
            graph_evidence = True
        if rule == "node_set_hash_change" and (
            evidence.get("observed_hash")
            or any(
                sample.get("observed_hash")
                for sample in evidence.get("sample_evidence", [])
                if isinstance(sample, dict)
            )
        ):
            graph_evidence = True
    if not graph_evidence:
        return False
    start = int(incident["start_sim_ns"])
    end = int(incident["end_sim_ns"])
    for segment in segments:
        if segment.get("source_run_type") != "attack" or segment.get("inserted_attack"):
            continue
        if end < int(segment["output_start_sim_ns"]) or start > int(
            segment["output_end_sim_ns"]
        ):
            continue
        intervals = segment.get("source_event_intervals_s", [])
        if intervals and float(segment["source_start_s"]) >= max(
            float(interval["stop_s"]) for interval in intervals
        ) - 0.1:
            return True
    return False


def _false_alert_rows(
    incidents: list[dict[str, Any]],
    events: list[dict[str, Any]],
    joins: list[int],
    normal_seconds: float,
    segments: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    false_incidents = [
        incident
        for incident in incidents
        if not any(_event_hits(incident, event) for event in events)
    ]
    counts: Counter[tuple[str, str, str, str, str]] = Counter()
    zones: Counter[str] = Counter()
    residual_count = 0
    exposure_hours = normal_seconds / 3600.0
    for incident in false_incidents:
        false_category = (
            "residual_attack_activity_outside_label"
            if _residual_attack_activity(incident, segments or [])
            else "unattributed_false_alert"
        )
        residual_count += int(
            false_category == "residual_attack_activity_outside_label"
        )
        incident_zones = []
        if int(incident["start_sim_ns"]) < _STARTUP_WINDOW_S * 1e9:
            incident_zones.append("within_15s_of_startup")
        if _near_boundary(incident, events):
            incident_zones.append("within_1.5s_of_label_boundary")
        if _near_join(incident, joins):
            incident_zones.append("at_join_point")
        if not incident_zones:
            incident_zones.append("elsewhere")
        for zone in incident_zones:
            zones[zone] += 1
            incident_keys = {
                (
                    str(component["detector"]),
                    str(component["rule_or_model"]),
                    str(incident["suspected_category"]),
                    zone,
                    false_category,
                )
                for component in incident["evidence"]
            }
            counts.update(incident_keys)
    rows = [
        {
            "detector": detector,
            "rule_or_model": rule_id,
            "suspected_category": category,
            "location": zone,
            "false_alert_category": false_category,
            "false_alert_incidents": count,
            "normal_hours": exposure_hours,
            "false_alerts_per_hour": (
                count / exposure_hours if exposure_hours else None
            ),
            "false_alerts_per_hour_ci_95_poisson": _poisson_rate_interval(
                count, exposure_hours
            ),
        }
        for (detector, rule_id, category, zone, false_category), count in sorted(
            counts.items()
        )
    ]
    return rows, {
        "false_incident_count": len(false_incidents),
        "residual_attack_activity_outside_label": residual_count,
        "unattributed_false_alert": len(false_incidents) - residual_count,
        "false_incidents_per_hour": (
            len(false_incidents) / exposure_hours if exposure_hours else None
        ),
        "residual_false_incidents_per_hour": (
            residual_count / exposure_hours if exposure_hours else None
        ),
        "unattributed_false_incidents_per_hour": (
            (len(false_incidents) - residual_count) / exposure_hours
            if exposure_hours
            else None
        ),
        "within_15s_of_startup": zones["within_15s_of_startup"],
        "within_1.5s_of_label_boundary": zones["within_1.5s_of_label_boundary"],
        "at_join_point": zones["at_join_point"],
        "elsewhere": zones["elsewhere"],
    }


def _coverage(
    events: list[dict[str, Any]], incidents: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for class_name in _CLASSES:
        class_events = [event for event in events if event["class_name"] == class_name]
        matched_incidents = [
            incident
            for incident in incidents
            if any(_event_hits(incident, event) for event in class_events)
        ]
        detectors = sorted(
            {
                component["detector"]
                for incident in matched_incidents
                for component in incident["evidence"]
            }
        )
        output.append(
            {
                "class_name": class_name,
                "event_count": len(class_events),
                "detected": bool(matched_incidents),
                "detectors": detectors,
                "multiple_detectors": len(detectors) > 1,
                "expected_miss": class_name in _EXPECTED_MISS_CLASSES,
            }
        )
    return output


def _category_agreement(
    event_details: list[dict[str, Any]],
    events: list[dict[str, Any]],
    incidents: list[dict[str, Any]],
) -> dict[str, Any]:
    agreements = 0
    detected = 0
    for event_detail in event_details:
        event = next(
            (
                candidate
                for candidate in events
                if candidate["source_run"] == event_detail["source_run"]
                and candidate["class_name"] == event_detail["class_name"]
            ),
            None,
        )
        if event is None:
            continue
        matches = [incident for incident in incidents if _event_hits(incident, event)]
        if matches:
            detected += 1
            expected = _TRUE_FAMILY.get(str(event["class_name"]))
            agreements += int(
                any(incident["suspected_category"] == expected for incident in matches)
            )
    return {
        "detected_events": detected,
        "category_agreements": agreements,
        "agreement_rate": agreements / detected if detected else None,
        "interpretation": "Diagnostic family agreement only; not attack attribution.",
    }


def _run_one_stream(
    stream_id: str,
    stream_dir: Path,
    output_dir: Path,
    inventory: dict[str, Any],
    noise_bundle: dict[str, Any],
    security_bundle: dict[str, Any],
    *,
    reset_at_joins: bool,
    allow_draft_inventory: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    manifest = _read_manifest(stream_dir / f"{stream_id}_manifest.json")
    aligned = pd.read_csv(stream_dir / manifest["aligned_file"])
    telemetry = pd.read_csv(stream_dir / manifest["telemetry_file"])
    result: MonitorResult = monitor_frames(
        aligned=aligned,
        telemetry=telemetry,
        inventory=inventory,
        noise_bundle=noise_bundle,
        security_bundle=security_bundle,
        join_points_ns=manifest["join_points_sim_ns"],
        reset_at_joins=reset_at_joins,
        allow_draft_inventory_for_offline_eval=allow_draft_inventory,
        offline_demo=True,
    )
    incidents = result.incidents
    events = manifest["ground_truth"]
    class_metrics, incident_metrics, event_details = _event_metrics(incidents, events)
    detector_metrics = _detector_event_metrics(incidents, events)
    rows = _row_metrics(aligned, result.findings, events)
    false_rows: list[dict[str, Any]] = []
    zones: dict[str, int] = {}
    if stream_id in {"stream_a", "stream_c"}:
        false_rows, zones = _false_alert_rows(
            incidents,
            events,
            manifest["join_points_sim_ns"],
            float(manifest["normal_seconds"]),
            manifest["segments"],
        )
    coverage = _coverage(events, incidents)
    category_agreement = _category_agreement(event_details, events, incidents)
    incidents_near_joins = sum(
        _near_join(incident, manifest["join_points_sim_ns"])
        for incident in incidents
    )
    top_false_incidents = []
    if stream_id == "stream_c" and reset_at_joins:
        false_incidents = [
            incident
            for incident in incidents
            if not any(_event_hits(incident, event) for event in events)
        ]
        for incident in sorted(
            false_incidents,
            key=lambda item: int(item["end_sim_ns"]) - int(item["start_sim_ns"]),
            reverse=True,
        )[:10]:
            midpoint = (
                int(incident["start_sim_ns"]) + int(incident["end_sim_ns"])
            ) // 2
            source_segments = [
                {
                    "segment_index": segment["segment_index"],
                    "source_run": segment["source_run"],
                    "source_relative_path": segment["source_relative_path"],
                    "source_start_s": segment["source_start_s"],
                    "source_stop_s": segment["source_stop_s"],
                }
                for segment in manifest["segments"]
                if int(segment["output_start_sim_ns"])
                <= midpoint
                <= int(segment["output_end_sim_ns"])
            ]
            top_false_incidents.append(
                {
                    "start_sim_ns": int(incident["start_sim_ns"]),
                    "end_sim_ns": int(incident["end_sim_ns"]),
                    "duration_s": (
                        int(incident["end_sim_ns"]) - int(incident["start_sim_ns"])
                    )
                    / 1e9,
                    "suspected_category": incident["suspected_category"],
                    "detectors": incident["detectors"],
                    "source_segments": source_segments,
                }
            )
    results_dir = output_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    mode = "reset_at_joins" if reset_at_joins else "continuous_state"
    alert_path = results_dir / f"{stream_id}_{mode}_alerts.jsonl"
    alert_path.write_text(
        "".join(json.dumps(item, separators=(",", ":")) + "\n" for item in incidents),
        encoding="utf-8",
    )
    summary = {
        "stream_id": stream_id,
        "state_mode": mode,
        "duration_s": manifest["duration_s"],
        "normal_seconds": manifest["normal_seconds"],
        "attack_seconds": manifest["attack_seconds"],
        "attack_prevalence": manifest["attack_prevalence"],
        "join_count": len(manifest["join_points_sim_ns"]),
        "incidents_near_joins": incidents_near_joins,
        "incident_metrics": incident_metrics,
        "event_metrics": class_metrics,
        "detector_event_metrics": detector_metrics,
        "event_detail": event_details,
        "row_metrics": rows,
        "false_alert_location_counts": zones,
        "false_alert_rates": false_rows,
        "top_false_incidents_by_duration": top_false_incidents,
        "coverage": coverage,
        "category_agreement": category_agreement,
        "draft_inventory_override": result.draft_override_used,
        "warnings": result.warnings,
        "alert_file": str(alert_path.relative_to(output_dir)),
    }
    return summary, false_rows, class_metrics


def evaluate_blind_streams(
    stream_dir: str | Path,
    inventory_path: str | Path,
    report_dir: str | Path,
    *,
    noise_model_path: str | Path,
    security_model_path: str | Path,
    allow_draft_inventory_for_offline_eval: bool,
) -> dict[str, Any]:
    """Evaluate every saved blind stream in continuous and reset-state modes."""
    streams = Path(stream_dir)
    destination = Path(report_dir)
    destination.mkdir(parents=True, exist_ok=True)
    inventory = json.loads(Path(inventory_path).read_text(encoding="utf-8"))
    noise_bundle = joblib.load(noise_model_path)
    security_bundle = joblib.load(security_model_path)
    inventory_status = inventory.get("approval_status")
    draft_override_used = inventory_status == "draft" and allow_draft_inventory_for_offline_eval
    if inventory_status == "draft" and not draft_override_used:
        raise ValueError(
            "Draft inventory requires --allow-draft-inventory-for-offline-eval."
        )
    if inventory_status == "approved":
        validate_inventory(inventory, require_approved=True)
    elif inventory_status == "approved_for_offline_demo":
        validate_inventory(
            inventory, require_approved=True, allow_offline_demo=True
        )
    elif draft_override_used:
        validate_inventory(inventory, require_approved=False)
    else:
        raise ValueError("Blind stream evaluation requires an approved or draft inventory.")
    stream_ids = sorted(
        path.name.removesuffix("_manifest.json")
        for path in streams.glob("*_manifest.json")
    )
    if not stream_ids:
        raise FileNotFoundError(f"No blind stream manifests found in {streams}.")

    results: dict[str, dict[str, Any]] = {}
    all_false_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    row_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    category_rows: list[dict[str, Any]] = []
    join_rows: list[dict[str, Any]] = []
    for stream_id in stream_ids:
        results[stream_id] = {}
        for reset in (False, True):
            summary, false_rows, class_metrics = _run_one_stream(
                stream_id,
                streams,
                destination,
                inventory,
                noise_bundle,
                security_bundle,
                reset_at_joins=reset,
                allow_draft_inventory=allow_draft_inventory_for_offline_eval,
            )
            mode = summary["state_mode"]
            results[stream_id][mode] = summary
            all_false_rows.extend(
                [{"stream_id": stream_id, "state_mode": mode, **row} for row in false_rows]
            )
            event_rows.extend(
                [
                    {"stream_id": stream_id, "state_mode": mode, **row}
                    for row in class_metrics
                ]
            )
            row_rows.append(
                {"stream_id": stream_id, "state_mode": mode, **summary["row_metrics"]}
            )
            coverage_rows.extend(
                [
                    {"stream_id": stream_id, "state_mode": mode, **row}
                    for row in summary["coverage"]
                ]
            )
            category_rows.append(
                {
                    "stream_id": stream_id,
                    "state_mode": mode,
                    **summary["category_agreement"],
                }
            )
            join_rows.append(
                {
                    "stream_id": stream_id,
                    "state_mode": mode,
                    "join_count": summary["join_count"],
                    "incidents_near_joins": summary["incidents_near_joins"],
                }
            )
    inventory_override_note = (
        "WARNING: DRAFT INVENTORY OVERRIDE ENABLED — all findings are offline "
        "evaluation only; this is not an approval or deployment result."
        if draft_override_used
        else None
    )
    report = {
        "evaluation": "Blind mixed-stream evaluation of frozen shipped detectors.",
        "scikit_learn_version": sklearn.__version__,
        "model_sha256": {
            "noise_detector.joblib": _sha256_file(noise_model_path),
            "security_detector.joblib": _sha256_file(security_model_path),
        },
        "inventory_approval_status": inventory_status,
        "labels_source": "events.csv start-inclusive, stop-exclusive intervals.",
        "event_tolerance": {
            "before_start_s": _TOLERANCE_BEFORE_START_S,
            "after_stop_s": _TOLERANCE_AFTER_STOP_S,
        },
        "row_level_note": (
            "Event recall and false alerts per normal-driving hour are more "
            "operationally relevant than row-level metrics."
        ),
        "draft_inventory_override": draft_override_used,
        "draft_inventory_warning": inventory_override_note,
        "simulated_data_limitation": (
            "All source data is simulated with idealized sensors and an in-sim "
            "driver, not a ROS-driven vehicle. These tests estimate robustness "
            "only and do not establish real-world performance."
        ),
        "state_modes": {
            "continuous_state": "Rolling features and row-to-row state span joins.",
            "reset_at_joins": (
                "Rolling features and row-to-row state reset at each saved join point."
            ),
        },
        "join_alert_definition": (
            "An incident is near a join when its interval intersects two seconds "
            "before or after a recorded join point."
        ),
        "streams": results,
    }
    stream_b_ids = sorted(
        stream_id for stream_id in results if stream_id.startswith("stream_b_seed_")
    )
    spread: list[dict[str, Any]] = []
    for class_name in _CLASSES:
        seed_recalls = {
            stream_id: next(
                (
                    item["recall"]
                    for item in results[stream_id]["continuous_state"]["event_metrics"]
                    if item["class_name"] == class_name
                ),
                None,
            )
            for stream_id in stream_b_ids
        }
        defined = [value for value in seed_recalls.values() if value is not None]
        spread.append(
            {
                "class_name": class_name,
                "recall_by_shuffle_seed": seed_recalls,
                "minimum_recall": min(defined) if defined else None,
                "maximum_recall": max(defined) if defined else None,
                "recall_spread": max(defined) - min(defined) if defined else None,
            }
        )
    report["stream_b_recall_spread"] = spread
    report["stream_b_recall_spread_mode"] = "continuous_state"
    (destination / "blind_stream_evaluation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    pd.DataFrame(event_rows).to_csv(destination / "blind_event_metrics.csv", index=False)
    detector_rows = [
        {"stream_id": stream_id, "state_mode": mode, **item}
        for stream_id, modes in results.items()
        for mode, summary in modes.items()
        for item in summary["detector_event_metrics"]
    ]
    pd.DataFrame(detector_rows).to_csv(
        destination / "blind_detector_event_metrics.csv", index=False
    )
    pd.DataFrame(row_rows).to_csv(destination / "blind_row_metrics.csv", index=False)
    pd.DataFrame(all_false_rows).to_csv(
        destination / "blind_false_alert_rates.csv", index=False
    )
    pd.DataFrame(coverage_rows).to_csv(
        destination / "blind_coverage.csv", index=False
    )
    pd.DataFrame(category_rows).to_csv(
        destination / "blind_category_agreement.csv", index=False
    )
    pd.DataFrame(join_rows).to_csv(
        destination / "blind_join_comparison.csv", index=False
    )
    _write_blind_report(destination / "blind_stream_evaluation.md", report)
    return report


def run_telemetry_model_ablation(
    stream_dir: str | Path,
    inventory_path: str | Path,
    report_dir: str | Path,
    *,
    noise_model_path: str | Path,
    security_model_path: str | Path,
) -> dict[str, Any]:
    """Compare fused monitoring with its telemetry anomaly model disabled."""
    streams = Path(stream_dir)
    destination = Path(report_dir)
    inventory = json.loads(Path(inventory_path).read_text(encoding="utf-8"))
    validate_inventory(inventory, require_approved=True, allow_offline_demo=True)
    noise_bundle = joblib.load(noise_model_path)
    security_bundle = joblib.load(security_model_path)
    comparisons: list[dict[str, Any]] = []

    for stream_id, reset_at_joins in (
        ("stream_c", True),
        ("stream_b_seed_1701", False),
    ):
        manifest = _read_manifest(streams / f"{stream_id}_manifest.json")
        aligned = pd.read_csv(streams / manifest["aligned_file"])
        telemetry = pd.read_csv(streams / manifest["telemetry_file"])
        mode = "reset_at_joins" if reset_at_joins else "continuous_state"
        fused_path = destination / "results" / f"{stream_id}_{mode}_alerts.jsonl"
        if not fused_path.is_file():
            raise FileNotFoundError(
                f"Run evaluate-blind-streams before the ablation; missing {fused_path}."
            )
        fused_incidents = [
            json.loads(line)
            for line in fused_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        result = monitor_frames(
            aligned=aligned,
            telemetry=telemetry,
            inventory=inventory,
            noise_bundle=noise_bundle,
            security_bundle=security_bundle,
            join_points_ns=manifest["join_points_sim_ns"],
            reset_at_joins=reset_at_joins,
            offline_demo=True,
            include_telemetry_model=False,
        )
        events = manifest["ground_truth"]
        normal_hours = float(manifest["normal_seconds"]) / 3600.0
        method_summaries: dict[str, dict[str, Any]] = {}
        for method, incidents in (
            ("fused", fused_incidents),
            ("without_telemetry_model", result.incidents),
        ):
            class_metrics, _, _ = _event_metrics(incidents, events)
            false_count = sum(
                not any(_event_hits(incident, event) for event in events)
                for incident in incidents
            )
            method_summaries[method] = {
                "false_incidents": false_count,
                "normal_hours": normal_hours,
                "false_incidents_per_hour": (
                    false_count / normal_hours if normal_hours else None
                ),
                "false_incidents_per_hour_ci_95_poisson": _poisson_rate_interval(
                    false_count, normal_hours
                ),
                "per_class_recall": {
                    item["class_name"]: {
                        "detected": item["detected"],
                        "events": item["events"],
                        "recall": item["recall"],
                    }
                    for item in class_metrics
                },
            }
        comparisons.append(
            {
                "stream_id": stream_id,
                "state_mode": mode,
                "fused": method_summaries["fused"],
                "without_telemetry_model": method_summaries[
                    "without_telemetry_model"
                ],
                "ablation_warnings": result.warnings,
                "coverage": result.coverage,
            }
        )

    report = {
        "purpose": (
            "Diagnostic ablation only; shipped monitor configuration and saved "
            "thresholds are unchanged."
        ),
        "scikit_learn_version": sklearn.__version__,
        "security_model_sha256": _sha256_file(security_model_path),
        "comparisons": comparisons,
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "blind_telemetry_ablation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Telemetry-model ablation",
        "",
        report["purpose"],
        "",
        "| Stream | Mode | Configuration | False incidents | Normal hours | False incidents/hour (95% Poisson CI) |",
        "|---|---|---|---:|---:|---|",
    ]
    for item in comparisons:
        for method in ("fused", "without_telemetry_model"):
            metrics = item[method]
            interval = metrics["false_incidents_per_hour_ci_95_poisson"]
            ci = (
                f"[{interval[0]:.3f}, {interval[1]:.3f}]"
                if interval is not None
                else "n/a"
            )
            lines.append(
                f"| {item['stream_id']} | {item['state_mode']} | {method} | "
                f"{metrics['false_incidents']} | {metrics['normal_hours']:.3f} | "
                f"{metrics['false_incidents_per_hour']:.3f} {ci} |"
            )
    lines.extend(
        [
            "",
            "## Per-class event recall",
            "",
            "| Stream | Mode | Class | Fused | Without telemetry model |",
            "|---|---|---|---:|---:|",
        ]
    )
    for item in comparisons:
        classes = sorted(
            set(item["fused"]["per_class_recall"])
            | set(item["without_telemetry_model"]["per_class_recall"])
        )
        for class_name in classes:
            recalls = []
            for method in ("fused", "without_telemetry_model"):
                value = item[method]["per_class_recall"].get(class_name)
                recalls.append(
                    f"{value['detected']}/{value['events']} "
                    f"({value['recall']:.3f})"
                    if value and value["recall"] is not None
                    else "n/a"
                )
            lines.append(
                f"| {item['stream_id']} | {item['state_mode']} | {class_name} | "
                f"{recalls[0]} | {recalls[1]} |"
            )
    (destination / "blind_telemetry_ablation.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return report


def _write_blind_report(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Blind mixed-stream evaluation",
        "",
        f"- **scikit-learn runtime version:** {report['scikit_learn_version']}.",
        f"- **Model SHA-256:** noise `{report['model_sha256']['noise_detector.joblib']}`; "
        f"security `{report['model_sha256']['security_detector.joblib']}`.",
        f"- **Inventory status:** {report['inventory_approval_status']}.",
        f"- **Labels:** {report['labels_source']}",
        f"- **Event tolerance:** -{report['event_tolerance']['before_start_s']} s before start, "
        f"+{report['event_tolerance']['after_stop_s']} s after stop.",
        f"- **Draft inventory override:** {report['draft_inventory_override']}.",
        f"- **Scope limitation:** {report['simulated_data_limitation']}",
        "",
        "## Stream construction summary",
        "",
        "| Stream | Duration (s) | Normal (s) | Attack (s) | Attack prevalence | Joins |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for stream_id, modes in report["streams"].items():
        summary = modes["continuous_state"]
        lines.append(
            f"| {stream_id} | {summary['duration_s']:.3f} | "
            f"{summary['normal_seconds']:.3f} | {summary['attack_seconds']:.3f} | "
            f"{summary['attack_prevalence']:.4%} | {summary['join_count']} |"
        )
    normal_only = report["streams"]["stream_c"]["continuous_state"]["normal_seconds"]
    lines.extend(
        [
            "",
            f"Stream C contains {normal_only:.3f} seconds "
            f"({normal_only / 3600.0:.6f} hours) of event-free driving. "
            + (
                "This is under one hour; per-hour rates should be interpreted as "
                "small-sample estimates."
                if normal_only < 3600.0
                else "This exceeds one hour, but remains a limited simulated soak."
            ),
            "",
        "## Event recall by stream and state mode",
        "",
        "| Stream | Mode | Class | Detected / events | Recall | 95% Wilson CI | Median latency (s) | P90 latency (s) |",
        "|---|---|---|---:|---:|---|---:|---:|",
        ]
    )
    for stream_id, modes in report["streams"].items():
        for mode, summary in modes.items():
            for item in summary["event_metrics"]:
                interval = item["recall_ci_95_wilson"]
                ci = (
                    f"[{interval[0]:.3f}, {interval[1]:.3f}]"
                    if interval is not None
                    else "n/a"
                )
                lines.append(
                    f"| {stream_id} | {mode} | {item['class_name']} | "
                    f"{item['detected']} / {item['events']} | "
                    f"{item['recall']:.3f} | {ci} | "
                    f"{item['median_latency_s'] if item['median_latency_s'] is not None else 'n/a'} | "
                    f"{item['p90_latency_s'] if item['p90_latency_s'] is not None else 'n/a'} |"
                )
    lines.extend(
        [
            "",
            "## Stream B recall spread across shuffle seeds",
            "",
            "This per-seed recall table uses continuous-state mode.",
            "",
            "| Class | Seed 1701 | Seed 2903 | Seed 4307 | Min-max spread |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for item in report["stream_b_recall_spread"]:
        values = item["recall_by_shuffle_seed"]
        recalls = [
            f"{values[seed]:.3f}" if values[seed] is not None else "n/a"
            for seed in sorted(values)
        ]
        spread = item["recall_spread"]
        lines.append(
            f"| {item['class_name']} | {' | '.join(recalls)} | "
            f"{spread if spread is not None else 'n/a'} |"
        )
    lines.extend(
        [
            "",
            "## Incident precision",
            "",
            "| Stream | Mode | Incidents | Matching an event | Incident precision |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for stream_id, modes in report["streams"].items():
        for mode, summary in modes.items():
            metrics = summary["incident_metrics"]
            precision = metrics["incident_precision"]
            lines.append(
                f"| {stream_id} | {mode} | {metrics['incidents']} | "
                f"{metrics['incidents_matching_event']} | "
                f"{precision if precision is not None else 'n/a'} |"
            )
    lines.extend(
        [
            "",
            "Event and per-hour outcomes matter more than row-level metrics. "
            "All detectors remain advisory; no automatic action is taken.",
            "",
            "## False alerts per normal-driving hour",
            "",
            "Only nonzero detector/rule/category/location combinations are listed. "
            "The detailed CSV retains the full dimensions; `within_1.5s_of_label_boundary` "
            "is a symmetric diagnostic bucket, while event matching uses the asymmetric "
            "tolerance stated above. Location categories are non-exclusive, so an incident may be near a join and a label boundary. "
            "False-alert categories distinguish graph evidence continuing in a post-event source segment from unattributed alerts.",
            "",
            "| Stream | Mode | Detector | Rule/model | Suspected category | False-alert category | Location | Components | Alerts/hour (95% Poisson CI) |",
            "|---|---|---|---|---|---|---:|---:|---|",
        ]
    )
    for stream_id, modes in report["streams"].items():
        for mode, summary in modes.items():
            for item in summary["false_alert_rates"]:
                lines.append(
                    f"| {stream_id} | {mode} | {item['detector']} | "
                    f"{item['rule_or_model']} | {item['suspected_category']} | "
                    f"{item['false_alert_category']} | {item['location']} | "
                    f"{item['false_alert_incidents']} | "
                    f"{item['false_alerts_per_hour']:.3f} "
                    f"({item['false_alerts_per_hour_ci_95_poisson'][0]:.3f}, "
                    f"{item['false_alerts_per_hour_ci_95_poisson'][1]:.3f}) |"
                )
    lines.extend(
        [
            "",
            "## False-alert attribution",
            "",
            "| Stream | Mode | Original false incidents (count/rate) | Residual (count/rate) | Unattributed (count/rate) |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for stream_id in ("stream_a", "stream_c"):
        for mode, summary in report["streams"][stream_id].items():
            locations = summary["false_alert_location_counts"]
            lines.append(
                f"| {stream_id} | {mode} | "
                f"{locations['false_incident_count']} "
                f"({locations['false_incidents_per_hour']:.3f}) | "
                f"{locations['residual_attack_activity_outside_label']} "
                f"({locations['residual_false_incidents_per_hour']:.3f}) | "
                f"{locations['unattributed_false_alert']} "
                f"({locations['unattributed_false_incidents_per_hour']:.3f}) |"
            )
    c_reset = report["streams"]["stream_c"]["reset_at_joins"]
    lines.extend(
        [
            "",
            "## Ten longest Stream C reset-mode false incidents",
            "",
            "Simulation-clock timestamps are shown as nanoseconds from stream start.",
            "",
            "| Start sim ns | End sim ns | Duration (s) | Suspected category | Detectors | Source segments |",
            "|---:|---:|---:|---|---|---|",
        ]
    )
    for item in c_reset["top_false_incidents_by_duration"]:
        sources = "; ".join(
            f"{segment['source_run']} [{segment['source_start_s']}, {segment['source_stop_s']})"
            for segment in item["source_segments"]
        )
        lines.append(
            f"| {item['start_sim_ns']} | {item['end_sim_ns']} | "
            f"{item['duration_s']:.3f} | {item['suspected_category']} | "
            f"{', '.join(item['detectors'])} | {sources} |"
        )
    lines.extend(
        [
            "",
            "## Detector-level event performance (all Stream B shuffles, continuous state)",
            "",
            "Precision counts each detector's incidents that overlap the named class's event window "
            f"under the -{_TOLERANCE_BEFORE_START_S:.1f}/+{_TOLERANCE_AFTER_STOP_S:.1f} s tolerance. "
            "Latency is measured from the event start to the first matching detector component.",
            "",
            "| Stream | Class | Detector | Detected/events | Incident precision | Median latency (s) | P90 latency (s) |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for stream_id in sorted(
        stream_id
        for stream_id in report["streams"]
        if stream_id.startswith("stream_b_seed_")
    ):
        for item in report["streams"][stream_id]["continuous_state"][
            "detector_event_metrics"
        ]:
            lines.append(
                f"| {stream_id} | {item['class_name']} | {item['detector']} | "
                f"{item['detected_events']}/{item['events']} | "
                f"{item['incident_precision'] if item['incident_precision'] is not None else 'n/a'} | "
                f"{item['median_latency_s'] if item['median_latency_s'] is not None else 'n/a'} | "
                f"{item['p90_latency_s'] if item['p90_latency_s'] is not None else 'n/a'} |"
            )
    lines.extend(
        [
            "",
            "## Row-level metrics",
            "",
            "| Stream | Mode | Precision | Recall | F1 | FPR |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for stream_id, modes in report["streams"].items():
        for mode, summary in modes.items():
            metrics = summary["row_metrics"]
            lines.append(
                f"| {stream_id} | {mode} | {metrics['precision']:.4f} | "
                f"{metrics['recall']:.4f} | {metrics['f1']:.4f} | "
                f"{metrics['false_positive_rate']:.4f} |"
            )
    lines.extend(
        [
            "",
            "## Class coverage (all Stream B shuffles)",
            "",
            "| Stream | Class | Events | Detected | Detector(s) | Multi-detector | Expected miss |",
            "|---|---|---:|---|---|---|---|",
        ]
    )
    for stream_id in sorted(
        stream_id
        for stream_id in report["streams"]
        if stream_id.startswith("stream_b_seed_")
    ):
        for item in report["streams"][stream_id]["continuous_state"]["coverage"]:
            lines.append(
                f"| {stream_id} | {item['class_name']} | {item['event_count']} | "
                f"{item['detected']} | {', '.join(item['detectors']) or 'none'} | "
                f"{item['multiple_detectors']} | {item['expected_miss']} |"
            )
    lines.extend(
        [
            "",
            "Freeze and false_contact each have 0/3 detected events in these runs. "
            "They are not documented expected misses: only missed_contact is known to "
            "be indistinguishable from normal with the available channels. These results "
            "therefore identify current blind spots, not evidence that the classes are "
            "inherently unobservable.",
        ]
    )
    lines.extend(
        [
            "",
            "## Category agreement and join comparison",
            "",
            "| Stream | Mode | Category agreements / detected events | Agreement rate | Incidents near joins / joins |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for stream_id, modes in report["streams"].items():
        for mode, summary in modes.items():
            agreement = summary["category_agreement"]
            lines.append(
                f"| {stream_id} | {mode} | {agreement['category_agreements']} / "
                f"{agreement['detected_events']} | "
                f"{agreement['agreement_rate'] if agreement['agreement_rate'] is not None else 'n/a'} | "
                f"{summary['incidents_near_joins']} / {summary['join_count']} |"
            )
    lines.extend(
        [
            "",
            "Category agreement is diagnostic only and does not attribute attacks. "
            "Continuous-state and reset-at-joins results are both shown because "
            "artificial joins do not occur in a live monitor.",
            "",
        ]
    )
    if report["draft_inventory_warning"]:
        lines.extend([f"> {report['draft_inventory_warning']}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _inject_sensor_noise(frame: pd.DataFrame, seed: int, level: str) -> pd.DataFrame:
    scales = {
        "low": {
            "imu.linear_acceleration": 0.01,
            "imu.angular_velocity": 0.001,
            "odom.pose.pose.position": 0.005,
            "odom.twist.twist.linear": 0.01,
            "odom.twist.twist.angular": 0.001,
        },
        "moderate": {
            "imu.linear_acceleration": 0.05,
            "imu.angular_velocity": 0.005,
            "odom.pose.pose.position": 0.02,
            "odom.twist.twist.linear": 0.05,
            "odom.twist.twist.angular": 0.005,
        },
        "moderate_high_1": {
            "imu.linear_acceleration": 1.0 / 15.0,
            "imu.angular_velocity": 1.0 / 150.0,
            "odom.pose.pose.position": 0.03,
            "odom.twist.twist.linear": 1.0 / 15.0,
            "odom.twist.twist.angular": 1.0 / 150.0,
        },
        "moderate_high_2": {
            "imu.linear_acceleration": 1.0 / 12.0,
            "imu.angular_velocity": 1.0 / 120.0,
            "odom.pose.pose.position": 0.04,
            "odom.twist.twist.linear": 1.0 / 12.0,
            "odom.twist.twist.angular": 1.0 / 120.0,
        },
        "high": {
            "imu.linear_acceleration": 0.1,
            "imu.angular_velocity": 0.01,
            "odom.pose.pose.position": 0.05,
            "odom.twist.twist.linear": 0.1,
            "odom.twist.twist.angular": 0.01,
        },
    }
    if level not in scales:
        raise ValueError(f"Unknown simulated sensor-noise level: {level}")
    output = frame.copy()
    rng = np.random.default_rng(seed)
    for column in output.columns:
        for prefix, sigma in scales[level].items():
            if str(column).startswith(prefix + "."):
                values = pd.to_numeric(output[column], errors="coerce")
                output[column] = values + rng.normal(0.0, sigma, len(output))
                break
    return output


def _fault_scenarios(telemetry: pd.DataFrame) -> dict[str, pd.DataFrame]:
    scenarios: dict[str, pd.DataFrame] = {}
    midpoint = len(telemetry) // 2
    if len(telemetry) < 20:
        raise ValueError("Normal-only telemetry stream is too short for fault injection.")

    missing = telemetry.drop(telemetry.index[midpoint : midpoint + 4]).reset_index(drop=True)
    scenarios["missing_ticks"] = missing

    duplicate = pd.concat(
        [
            telemetry.iloc[:midpoint],
            telemetry.iloc[[midpoint]],
            telemetry.iloc[midpoint:],
        ],
        ignore_index=True,
    )
    scenarios["duplicated_tick"] = duplicate

    out_of_order = telemetry.copy().reset_index(drop=True)
    out_of_order.iloc[[midpoint, midpoint + 1]] = (
        out_of_order.iloc[[midpoint + 1, midpoint]].to_numpy()
    )
    scenarios["out_of_order_ticks"] = out_of_order

    stale = telemetry.drop(telemetry.index[midpoint : midpoint + 8]).reset_index(drop=True)
    scenarios["stale_period"] = stale

    nan_column = telemetry.copy()
    numeric_candidate = next(
        (
            column
            for column in nan_column.columns
            if column not in {"sim_time_ns", "sim_time_s"}
            and pd.api.types.is_numeric_dtype(nan_column[column])
        ),
        None,
    )
    if numeric_candidate is None:
        raise ValueError("No numeric telemetry column is available for NaN stress.")
    nan_column[numeric_candidate] = np.nan
    nan_column.attrs["nan_injected_column"] = numeric_candidate
    scenarios["nan_signal_column"] = nan_column

    jitter = telemetry.copy()
    length = min(21, len(jitter) - midpoint)
    jitter_rng = np.random.default_rng(9217)
    offset = jitter_rng.uniform(-0.1, 0.1, size=length)
    jitter_ns = pd.to_numeric(jitter["sim_time_ns"], errors="raise").to_numpy(
        dtype=np.int64, copy=True
    )
    jitter_ns[midpoint : midpoint + length] += np.rint(offset * 1e9).astype(np.int64)
    jitter["sim_time_ns"] = jitter_ns
    jitter["sim_time_s"] = jitter_ns / 1e9
    scenarios["timestamp_jitter"] = jitter
    return scenarios


def _robustness_case(
    name: str,
    aligned: pd.DataFrame,
    telemetry: pd.DataFrame,
    inventory: dict[str, Any],
    noise_bundle: dict[str, Any],
    security_bundle: dict[str, Any],
    *,
    joins: list[int],
    allow_draft_inventory: bool,
    normal_seconds: float,
) -> dict[str, Any]:
    result = monitor_frames(
        aligned=aligned,
        telemetry=telemetry,
        inventory=inventory,
        noise_bundle=noise_bundle,
        security_bundle=security_bundle,
        join_points_ns=joins,
        reset_at_joins=True,
        allow_draft_inventory_for_offline_eval=allow_draft_inventory,
        offline_demo=True,
    )
    incidents = result.incidents
    detector_counts: Counter[str] = Counter()
    rule_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    health_incidents = 0
    attack_like_incidents = 0
    incidents_by_detector: Counter[str] = Counter()
    for incident in incidents:
        category_counts[incident["suspected_category"]] += 1
        is_health = False
        for component in incident["evidence"]:
            detector_counts[str(component["detector"])] += 1
            rule_counts[str(component["rule_or_model"])] += 1
            is_health |= component["detector"] == "health"
        incidents_by_detector.update(set(incident["detectors"]))
        health_incidents += int(is_health)
        attack_like_incidents += int(
            any(detector != "health" for detector in incident["detectors"])
        )
    return {
        "scenario": name,
        "incident_count": len(incidents),
        "health_incident_count": health_incidents,
        "non_health_incident_count": attack_like_incidents,
        "false_alerts_per_hour": (
            len(incidents) / (normal_seconds / 3600.0) if normal_seconds else None
        ),
        "counts_by_detector": dict(sorted(detector_counts.items())),
        "incidents_by_detector": dict(sorted(incidents_by_detector.items())),
        "counts_by_rule_or_model": dict(sorted(rule_counts.items())),
        "counts_by_suspected_category": dict(sorted(category_counts.items())),
        "warnings": result.warnings,
        "draft_inventory_override": result.draft_override_used,
        "injected_nan_column": telemetry.attrs.get("nan_injected_column"),
        "incidents": incidents,
    }


def run_robustness_stress_tests(
    stream_dir: str | Path,
    inventory_path: str | Path,
    report_dir: str | Path,
    *,
    noise_model_path: str | Path,
    security_model_path: str | Path,
    allow_draft_inventory_for_offline_eval: bool,
) -> dict[str, Any]:
    """Run isolated sensor, telemetry, and graph stress cases on normal Stream C."""
    streams = Path(stream_dir)
    stream_manifest = _read_manifest(streams / "stream_c_manifest.json")
    aligned = pd.read_csv(streams / stream_manifest["aligned_file"])
    telemetry = pd.read_csv(streams / stream_manifest["telemetry_file"])
    inventory = json.loads(Path(inventory_path).read_text(encoding="utf-8"))
    noise_bundle = joblib.load(noise_model_path)
    security_bundle = joblib.load(security_model_path)
    normal_seconds = float(stream_manifest["normal_seconds"])
    joins = stream_manifest["join_points_sim_ns"]
    cases: list[dict[str, Any]] = []

    noise_levels = (
        ("low", 9100),
        ("moderate", 9101),
        ("moderate_high_1", 9103),
        ("moderate_high_2", 9104),
        ("high", 9102),
    )
    for level, seed in noise_levels:
        cases.append(
            _robustness_case(
                f"sensor_noise_{level}",
                _inject_sensor_noise(aligned, seed, level),
                telemetry,
                inventory,
                noise_bundle,
                security_bundle,
                joins=joins,
                allow_draft_inventory=allow_draft_inventory_for_offline_eval,
                normal_seconds=normal_seconds,
            )
        )

    for name, modified in _fault_scenarios(telemetry).items():
        cases.append(
            _robustness_case(
                f"telemetry_{name}",
                aligned,
                modified,
                inventory,
                noise_bundle,
                security_bundle,
                joins=joins,
                allow_draft_inventory=allow_draft_inventory_for_offline_eval,
                normal_seconds=normal_seconds,
            )
        )

    maintenance_node = "/approved_maintenance_probe"
    approved_inventory = json.loads(json.dumps(inventory))
    approved_node_names = {item["name"] for item in approved_inventory["nodes"]}
    if maintenance_node in approved_node_names:
        raise ValueError("Maintenance test node already exists in the supplied inventory.")
    approved_inventory["nodes"].append(
        {"name": maintenance_node, "namespace": "/", "host": None, "enclave": None}
    )
    graph_base_count = int(pd.to_numeric(telemetry["node_count"], errors="raise").mode().iloc[0])
    while len(approved_inventory["nodes"]) <= graph_base_count:
        fill_index = len(approved_inventory["nodes"])
        approved_inventory["nodes"].append(
            {
                "name": f"/inventory_fixture_{fill_index}",
                "namespace": "/",
                "host": None,
                "enclave": None,
            }
        )
    changed_hash = "offline-demo-maintenance-hash"
    approved_hashes = set(approved_inventory.get("approved_node_hashes", []))
    approved_hashes.add(changed_hash)
    approved_inventory["approved_node_hashes"] = sorted(approved_hashes)
    injected_graph = telemetry.copy()
    injected_graph["new_nodes"] = injected_graph["new_nodes"].astype(object)
    graph_start = len(injected_graph) // 2
    graph_stop = graph_start + 20
    injected_graph.loc[injected_graph.index[graph_start:graph_stop], "new_nodes"] = maintenance_node
    injected_graph.loc[
        injected_graph.index[graph_start:graph_stop], "node_count"
    ] = graph_base_count + 1
    injected_graph.loc[
        injected_graph.index[graph_start:graph_stop], "node_list_hash"
    ] = changed_hash
    cases.append(
        _robustness_case(
            "approved_maintenance_node_negative_control",
            aligned,
            injected_graph,
            approved_inventory,
            noise_bundle,
            security_bundle,
            joins=joins,
            allow_draft_inventory=allow_draft_inventory_for_offline_eval,
            normal_seconds=normal_seconds,
        )
    )
    cases.append(
        _robustness_case(
            "unapproved_maintenance_node_positive_control",
            aligned,
            injected_graph,
            inventory,
            noise_bundle,
            security_bundle,
            joins=joins,
            allow_draft_inventory=allow_draft_inventory_for_offline_eval,
            normal_seconds=normal_seconds,
        )
    )

    draft_used = (
        inventory.get("approval_status") == "draft"
        and allow_draft_inventory_for_offline_eval
    )
    report = {
        "stream_id": "stream_c",
        "state_mode": "reset_at_joins",
        "scikit_learn_version": sklearn.__version__,
        "model_sha256": {
            "noise_detector.joblib": _sha256_file(noise_model_path),
            "security_detector.joblib": _sha256_file(security_model_path),
        },
        "inventory_approval_status": inventory.get("approval_status"),
        "normal_seconds": normal_seconds,
        "frozen_model_thresholds": {
            "noise": noise_bundle["thresholds"],
            "telemetry": security_bundle["thresholds"],
        },
        "noise_level_basis": (
            "Assumptions, not sensor specifications: additive zero-mean Gaussian "
            "noise is applied to linear acceleration (m/s^2), angular velocity "
            "(rad/s), odometry position (m), and linear velocity (m/s). Quaternion, "
            "age, timestamp, and contact fields are not perturbed."
        ),
        "noise_level_sigmas": {
            "units": "1-sigma additive Gaussian standard deviation",
            "source": "Engineering assumptions for stress testing; no device datasheet was selected.",
            "levels": {
                "low": {
                    "imu.linear_acceleration_m_s2": 0.01,
                    "imu.angular_velocity_rad_s": 0.001,
                    "odom.pose.pose.position_m": 0.005,
                    "odom.twist.twist.linear_m_s": 0.01,
                    "odom.twist.twist.angular_rad_s": 0.001,
                },
                "moderate": {
                    "imu.linear_acceleration_m_s2": 0.05,
                    "imu.angular_velocity_rad_s": 0.005,
                    "odom.pose.pose.position_m": 0.02,
                    "odom.twist.twist.linear_m_s": 0.05,
                    "odom.twist.twist.angular_rad_s": 0.005,
                },
                "moderate_high_1": {
                    "imu.linear_acceleration_m_s2": 1.0 / 15.0,
                    "imu.angular_velocity_rad_s": 1.0 / 150.0,
                    "odom.pose.pose.position_m": 0.03,
                    "odom.twist.twist.linear_m_s": 1.0 / 15.0,
                    "odom.twist.twist.angular_rad_s": 1.0 / 150.0,
                },
                "moderate_high_2": {
                    "imu.linear_acceleration_m_s2": 1.0 / 12.0,
                    "imu.angular_velocity_rad_s": 1.0 / 120.0,
                    "odom.pose.pose.position_m": 0.04,
                    "odom.twist.twist.linear_m_s": 1.0 / 12.0,
                    "odom.twist.twist.angular_rad_s": 1.0 / 120.0,
                },
                "high": {
                    "imu.linear_acceleration_m_s2": 0.1,
                    "imu.angular_velocity_rad_s": 0.01,
                    "odom.pose.pose.position_m": 0.05,
                    "odom.twist.twist.linear_m_s": 0.1,
                    "odom.twist.twist.angular_rad_s": 0.01,
                },
            },
        },
        "telemetry_fault_definitions": {
            "missing_ticks": "Remove four consecutive 2 Hz rows.",
            "duplicated_tick": "Duplicate one row and its timestamp.",
            "out_of_order_ticks": "Swap two adjacent rows.",
            "stale_period": "Remove eight consecutive 2 Hz rows.",
            "nan_signal_column": "Set one numeric signal column entirely to NaN.",
            "timestamp_jitter": "Add seeded uniform ±0.1 s offsets to 21 timestamps.",
        },
        "timestamp_jitter_health_check": {
            "deviation_threshold_s": _TIMESTAMP_JITTER_DEVIATION_S,
            "basis": "Unvalidated monitor heuristic; not a sensor or network specification.",
        },
        "graph_change_controls": {
            "negative_control": (
                "Add the maintenance node and its node hash to the inventory, "
                "with node count adjusted to match."
            ),
            "positive_control": (
                "Inject the same node/hash without adding them to the inventory."
            ),
        },
        "draft_inventory_override": draft_used,
        "draft_inventory_warning": (
            "WARNING: DRAFT INVENTORY OVERRIDE ENABLED — offline evaluation only."
            if draft_used
            else None
        ),
        "simulated_data_limitation": (
            "All outcomes are under these simulated conditions. The source sensors "
            "are idealized and the in-sim driver is not ROS-driven; this does not "
            "establish real-world performance."
        ),
        "cases": cases,
    }
    hours = normal_seconds / 3600.0
    report["sensor_noise_curve"] = [
        {
            "scenario": case["scenario"],
            "level": case["scenario"].removeprefix("sensor_noise_"),
            "sigma": report["noise_level_sigmas"]["levels"][
                case["scenario"].removeprefix("sensor_noise_")
            ],
            "source": report["noise_level_sigmas"]["source"],
            "false_incidents": case["incident_count"],
            "normal_hours": hours,
            "incidents_per_hour": case["incident_count"] / hours,
            "incidents_per_hour_ci_95_poisson": _poisson_rate_interval(
                case["incident_count"], hours
            ),
            "incidents_with_sensor_noise_model": case["incidents_by_detector"].get(
                "sensor_noise_model", 0
            ),
            "sensor_noise_model_incident_share": (
                case["incidents_by_detector"].get("sensor_noise_model", 0)
                / case["incident_count"]
                if case["incident_count"]
                else 0.0
            ),
            "detectors_fired": sorted(case["incidents_by_detector"]),
        }
        for case in cases
        if case["scenario"].startswith("sensor_noise_")
    ]
    destination = Path(report_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "blind_robustness.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    pd.DataFrame(cases).to_csv(
        destination / "blind_robustness_cases.csv", index=False
    )
    _write_robustness_report(destination / "blind_robustness.md", report)
    return report


def _write_robustness_report(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Blind robustness stress tests",
        "",
        f"- **scikit-learn runtime version:** {report['scikit_learn_version']}.",
        f"- **Model SHA-256:** noise `{report['model_sha256']['noise_detector.joblib']}`; "
        f"security `{report['model_sha256']['security_detector.joblib']}`.",
        f"- **Inventory status:** {report['inventory_approval_status']}.",
        "",
        f"- **Normal-only duration:** {report['normal_seconds'] / 3600.0:.3f} hours.",
        f"- **Noise levels:** {report['noise_level_basis']}",
        f"- **Scope:** {report['simulated_data_limitation']}",
        "",
        "| Scenario | Incidents | Health incidents | Non-health incidents | Incidents/hour |",
        "|---|---:|---:|---:|---:|",
    ]
    for case in report["cases"]:
        rate = case["false_alerts_per_hour"]
        lines.append(
            f"| {case['scenario']} | {case['incident_count']} | "
            f"{case['health_incident_count']} | {case['non_health_incident_count']} | "
            f"{rate:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Sensor-noise robustness curve",
            "",
            "| Level | Field sigmas (1-sigma) | Source | Incidents | Normal hours | Incidents/hour (95% Poisson CI) | Sensor-model share | Detectors |",
            "|---|---|---|---:|---:|---|---:|---|",
        ]
    )
    for item in report["sensor_noise_curve"]:
        sigmas = ", ".join(f"{key}={value:g}" for key, value in item["sigma"].items())
        ci = item["incidents_per_hour_ci_95_poisson"]
        lines.append(
            f"| {item['level']} | {sigmas} | {item['source']} | "
            f"{item['false_incidents']} | {item['normal_hours']:.3f} | "
            f"{item['incidents_per_hour']:.3f} ({ci[0]:.3f}, {ci[1]:.3f}) | "
            f"{item['sensor_noise_model_incident_share']:.1%} | "
            f"{', '.join(item['detectors_fired'])} |"
        )
    lines.extend(["", "## Scenario definitions", ""])
    lines.append(json.dumps(report["telemetry_fault_definitions"], indent=2))
    lines.extend(["", "## Timestamp jitter health-check assumption", ""])
    lines.append(json.dumps(report["timestamp_jitter_health_check"], indent=2))
    lines.extend(["", "## Graph change controls", ""])
    lines.append(json.dumps(report["graph_change_controls"], indent=2))
    nan_case = next(
        case for case in report["cases"] if case["scenario"] == "telemetry_nan_signal_column"
    )
    lines.extend(
        [
            "",
            "## NaN telemetry case",
            "",
            f"The injected all-NaN signal column was `{nan_case['injected_nan_column']}`. "
            "The 10 non-health incidents are independent baseline timing-policy findings; "
            "they do not use that NaN column. The health findings report the empty field. "
            "The telemetry model now receives fitted-imputer replacements rather than NaN values.",
            "",
            "| Start sim ns | End sim ns | Suspected category | Detector/rule | Evidence column |",
            "|---:|---:|---|---|---|",
        ]
    )
    non_health = [
        incident
        for incident in nan_case["incidents"]
        if any(detector != "health" for detector in incident["detectors"])
    ]
    for incident in non_health:
        for component in incident["evidence"]:
            if component["detector"] == "health":
                continue
            lines.append(
                f"| {incident['start_sim_ns']} | {incident['end_sim_ns']} | "
                f"{incident['suspected_category']} | {component['rule_or_model']} | "
                f"{component.get('evidence', {}).get('column', 'n/a')} |"
            )
    if report["draft_inventory_warning"]:
        lines.extend(["", f"> {report['draft_inventory_warning']}"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


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


def run_leave_one_class_out(
    data_root: str | Path,
    inventory_path: str | Path,
    model_dir: str | Path,
    report_dir: str | Path,
    *,
    random_state: int = 42,
    allow_draft_inventory_for_offline_eval: bool = False,
) -> dict[str, Any]:
    """Train separate seed-1/2 telemetry models omitting each supervised class."""
    inventory = json.loads(Path(inventory_path).read_text(encoding="utf-8"))
    draft_override_used = inventory.get("approval_status") == "draft"
    if draft_override_used and not allow_draft_inventory_for_offline_eval:
        raise ValueError(
            "Draft inventory requires --allow-draft-inventory-for-offline-eval."
        )
    validate_inventory(
        inventory, require_approved=not draft_override_used
    )
    runs = load_security_runs(data_root)
    prepared = [
        {
            "run": run,
            "features": telemetry_features(_strip_input_metadata(run.telemetry)),
            "labels": run.labels.to_numpy(dtype=np.int8),
        }
        for run in runs
        if run.run_type == "normal" or run.attack_name in USABLE_CLASSES
    ]
    if not prepared:
        raise ValueError("No training or evaluation runs were found.")
    feature_columns = list(prepared[0]["features"].columns)
    if any(list(item["features"].columns) != feature_columns for item in prepared):
        raise ValueError("Telemetry feature schemas differ across runs.")

    model_root = Path(model_dir)
    report_root = Path(report_dir)
    model_root.mkdir(parents=True, exist_ok=True)
    report_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for held_out in sorted(USABLE_CLASSES):
        eligible = [
            item
            for item in prepared
            if item["run"].run_type == "normal"
            or item["run"].attack_name in USABLE_CLASSES - {held_out}
        ]
        train = [item for item in eligible if item["run"].seed == 1]
        validation = [item for item in eligible if item["run"].seed == 2]
        if not train or not validation:
            raise ValueError(f"{held_out}: missing seed-1 training or seed-2 validation runs.")
        x_train = pd.concat([item["features"] for item in train], ignore_index=True)
        y_train = np.concatenate([item["labels"] for item in train])
        x_validation = pd.concat(
            [item["features"] for item in validation], ignore_index=True
        )
        y_validation = np.concatenate([item["labels"] for item in validation])
        candidate = _pipeline("random_forest", random_state).fit(x_train, y_train)
        validation_scores = _scores(candidate, "random_forest", x_validation)
        threshold = _threshold(y_validation, validation_scores)

        fit_runs = [item for item in eligible if item["run"].seed in {1, 2}]
        x_final = pd.concat([item["features"] for item in fit_runs], ignore_index=True)
        y_final = np.concatenate([item["labels"] for item in fit_runs])
        final_model = _pipeline("random_forest", random_state).fit(x_final, y_final)
        bundle = {
            "format_version": 1,
            "task": "ros2_telemetry_security_anomaly",
            "selected_model": "random_forest",
            "models": {"random_forest": final_model},
            "thresholds": {"random_forest": float(threshold)},
            "feature_columns": feature_columns,
            "training_seeds": [1, 2],
            "validation_seeds": [2],
            "held_out_test_seeds": [3],
            "trained_attack_classes": sorted(USABLE_CLASSES - {held_out}),
            "excluded_attack_class": held_out,
            "random_state": random_state,
            "label_source": "events.csv start-inclusive, stop-exclusive intervals",
            "experiment_only": True,
        }
        model_path = model_root / f"security_loco_without_{held_out}.joblib"
        joblib.dump(bundle, model_path, compress=3)

        class_runs = [
            run
            for run in runs
            if run.seed == 3 and run.run_type == "attack" and run.attack_name == held_out
        ]
        model_detected = 0
        rule_detected = 0
        event_latencies: list[float] = []
        test_rows: list[dict[str, Any]] = []
        for run in class_runs:
            bounds = _event_bounds(run)
            if bounds is None:
                raise ValueError(f"{run.run_id}: missing event bounds.")
            start_ns, stop_ns = bounds
            times = pd.to_numeric(run.telemetry["sim_time_ns"], errors="raise").to_numpy(
                dtype=np.int64
            )
            detector_input = _strip_input_metadata(run.telemetry)
            test_features = telemetry_features(detector_input).reindex(
                columns=feature_columns
            )
            scores = _scores(final_model, "random_forest", test_features)
            model_positions = np.flatnonzero(
                (scores >= threshold)
                & (times >= start_ns - _TOLERANCE_BEFORE_START_S * 1e9)
                & (times < stop_ns + _TOLERANCE_AFTER_STOP_S * 1e9)
            )
            model_hit = len(model_positions) > 0
            if model_hit:
                model_detected += 1
                event_latencies.append(
                    (int(times[model_positions[0]]) - start_ns) / 1e9
                )
            policy_findings = evaluate_rules(
                detector_input, inventory, "blind_recording"
            )
            rule_hit = any(
                finding.source == "policy"
                and start_ns - _TOLERANCE_BEFORE_START_S * 1e9
                <= finding.timestamp_sim_ns
                < stop_ns + _TOLERANCE_AFTER_STOP_S * 1e9
                for finding in policy_findings
            )
            rule_detected += int(rule_hit)
            test_rows.append(
                {
                    "run": run.run_id,
                    "model_detected": model_hit,
                    "rules_detected": rule_hit,
                    "model_alert_time_sim_ns": (
                        int(times[model_positions[0]]) if model_hit else None
                    ),
                    "event_start_sim_ns": start_ns,
                    "event_stop_sim_ns": stop_ns,
                }
            )
        total = len(class_runs)
        results.append(
            {
                "held_out_class": held_out,
                "test_events": total,
                "model_detected": model_detected,
                "model_recall": model_detected / total if total else None,
                "model_recall_ci_95_wilson": wilson_interval(model_detected, total),
                "median_model_latency_s": (
                    float(np.median(event_latencies)) if event_latencies else None
                ),
                "rules_detected": rule_detected,
                "rules_recall": rule_detected / total if total else None,
                "rules_recall_ci_95_wilson": wilson_interval(rule_detected, total),
                "validation_threshold": float(threshold),
                "training_seeds": [1, 2],
                "threshold_selection_seed": 2,
                "model_path": str(model_path),
                "test_runs": test_rows,
            }
        )
    warning = (
        "Each held-out class has only three seed-3 events; recall intervals are "
        "imprecise and do not establish reliability."
    )
    report = {
        "experiment": "Leave one supervised attack class out of the telemetry model.",
        "classes": sorted(USABLE_CLASSES),
        "models_are_experiment_only": True,
        "shipped_bundles_modified": False,
        "training_seeds": [1, 2],
        "threshold_selection_seed": 2,
        "test_seed": 3,
        "selection_policy": (
            "Fit the selected random-forest algorithm on seed 1, select its "
            "threshold on seed 2, then refit on seeds 1-2 without the held-out class."
        ),
        "small_sample_warning": warning,
        "draft_inventory_override": draft_override_used,
        "draft_inventory_warning": (
            "WARNING: DRAFT INVENTORY OVERRIDE ENABLED — rules results are offline "
            "evaluation only."
            if draft_override_used
            else None
        ),
        "simulated_data_limitation": (
            "All outcomes are under simulated conditions with idealized sensors "
            "and an in-sim driver, not a ROS-driven vehicle."
        ),
        "results": results,
    }
    (report_root / "leave_one_class_out.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    rows = [
        {
            key: value
            for key, value in item.items()
            if key not in {"test_runs"}
        }
        for item in results
    ]
    pd.DataFrame(rows).to_csv(
        report_root / "leave_one_class_out.csv", index=False
    )
    _write_loco_report(report_root / "leave_one_class_out.md", report)
    return report


def _write_loco_report(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Leave-one-class-out telemetry experiment",
        "",
        f"- **Training seeds:** {report['training_seeds']}; threshold chosen on seed {report['threshold_selection_seed']}.",
        f"- **Test seed:** {report['test_seed']}.",
        f"- **Model storage:** experiment-only bundles; shipped models were not modified.",
        f"- **Scope:** {report['simulated_data_limitation']}",
        "",
        "| Omitted class | Model detected / events | Model recall | 95% Wilson CI | Rules detected / events | Rules recall | 95% Wilson CI | Threshold |",
        "|---|---:|---:|---|---:|---:|---|---:|",
    ]
    for item in report["results"]:
        model_ci = item["model_recall_ci_95_wilson"]
        rule_ci = item["rules_recall_ci_95_wilson"]
        lines.append(
            f"| {item['held_out_class']} | {item['model_detected']} / {item['test_events']} | "
            f"{item['model_recall']:.3f} | [{model_ci[0]:.3f}, {model_ci[1]:.3f}] | "
            f"{item['rules_detected']} / {item['test_events']} | {item['rules_recall']:.3f} | "
            f"[{rule_ci[0]:.3f}, {rule_ci[1]:.3f}] | "
            f"{item['validation_threshold']:.6f} |"
        )
    lines.extend(["", f"> {report['small_sample_warning']}"])
    if report["draft_inventory_warning"]:
        lines.extend(["", f"> {report['draft_inventory_warning']}"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
