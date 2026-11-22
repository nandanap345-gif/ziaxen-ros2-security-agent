"""Blind, offline fusion of the saved sensor and telemetry detectors."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
import pandas as pd

from .features import engineer_features
from .models import anomaly_scores, explain_row
from .security.alerts import Finding, merge_alerts
from .security.inventory import validate_inventory
from .security.models import security_scores
from .security.rules import evaluate_rules
from .security.telemetry import telemetry_features

_LABEL_COLUMNS = {
    "is_attack",
    "is_attack_event",
    "attack_id",
    "attack_target",
    "attack_type",
    "event_label",
    "label",
    "labels",
    "run_id",
    "run_name",
    "relative_path",
    "scenario",
    "seed",
    "class",
    "class_name",
}
_MERGE_GAP_NS = 2_000_000_000
_TIMESTAMP_JITTER_DEVIATION_S = 0.05
_DRAFT_NOTE = (
    "DRAFT INVENTORY OVERRIDE: offline evaluation only; no human-approved "
    "inventory was supplied."
)
_MISSING_INPUT_NOTE = "Coverage is reduced because one detector input was missing."
_TELEMETRY_ABLATION_NOTE = (
    "Telemetry anomaly model disabled for ablation; telemetry-model coverage unavailable."
)
_SEVERITY_ORDER = ("info", "low", "medium", "high", "critical")


@dataclass
class MonitorResult:
    incidents: list[dict[str, Any]]
    findings: list[Finding]
    warnings: list[str]
    draft_override_used: bool
    coverage: dict[str, bool]


def _is_label_or_identity_column(name: str) -> bool:
    normalized = str(name).strip().lower()
    return (
        normalized in _LABEL_COLUMNS
        or normalized.startswith("attack_")
        or normalized.startswith("label_")
    )


def _without_labels(frame: pd.DataFrame) -> pd.DataFrame:
    """Drop ground-truth and recording identity fields before detector input."""
    excluded = [column for column in frame if _is_label_or_identity_column(column)]
    return frame.drop(columns=excluded)


def _time_ns(frame: pd.DataFrame) -> np.ndarray:
    if "sim_time_ns" in frame:
        values = pd.to_numeric(frame["sim_time_ns"], errors="coerce")
        if values.isna().any():
            raise ValueError("Monitor input contains invalid sim_time_ns values.")
        return values.to_numpy(dtype=np.int64)
    if "sim_time_s" in frame:
        values = pd.to_numeric(frame["sim_time_s"], errors="coerce")
        if values.isna().any():
            raise ValueError("Monitor input contains invalid sim_time_s values.")
        return np.rint(values.to_numpy(dtype=float) * 1e9).astype(np.int64)
    raise ValueError("Monitor input must contain sim_time_ns or sim_time_s.")


def _fill_missing_model_features(
    features: pd.DataFrame, model: Any
) -> pd.DataFrame:
    numeric = features.replace([np.inf, -np.inf], np.nan)
    if numeric.notna().all().all():
        return numeric
    named_steps = getattr(model, "named_steps", {})
    imputer = named_steps.get("imputer") if isinstance(named_steps, dict) else None
    statistics = getattr(imputer, "statistics_", None)
    if statistics is None or len(statistics) != len(numeric.columns):
        raise ValueError(
            "Telemetry features contain missing values but the saved model has no "
            "compatible fitted imputer."
        )
    fill_values = pd.Series(
        np.asarray(statistics, dtype=float), index=numeric.columns
    )
    if not np.isfinite(fill_values.to_numpy()).all():
        raise ValueError(
            "The saved telemetry model has no finite imputation value for a feature."
        )
    return numeric.fillna(fill_values)


def _ordered_slices(
    frame: pd.DataFrame | None, join_points_ns: list[int], reset_at_joins: bool
) -> list[pd.DataFrame]:
    if frame is None or frame.empty:
        return []
    clean = _without_labels(frame).copy()
    times = _time_ns(clean)
    if not reset_at_joins or not join_points_ns:
        return [clean]
    regions = np.searchsorted(
        np.asarray(sorted(set(join_points_ns)), dtype=np.int64),
        times,
        side="right",
    )
    boundaries = np.flatnonzero(regions[1:] != regions[:-1]) + 1
    edges = [0, *[int(value) for value in boundaries], len(clean)]
    return [clean.iloc[start:stop].copy() for start, stop in zip(edges, edges[1:]) if stop > start]


def _safe_bridge_manifest(manifest: dict[str, Any] | None) -> dict[str, Any] | None:
    if not manifest:
        return None
    bridge = manifest.get("bridge")
    if not isinstance(bridge, dict):
        return None
    allowed = {
        "local_domain_id",
        "sim_domain_id",
        "ROS_DISCOVERY_SERVER",
    }
    safe_bridge = {key: bridge[key] for key in allowed if key in bridge}
    return {"bridge": safe_bridge} if safe_bridge else None


def _inventory_gate(
    inventory: dict[str, Any],
    *,
    allow_draft_inventory: bool,
    offline_demo: bool,
) -> tuple[dict[str, Any], bool]:
    normalized = validate_inventory(inventory, require_approved=False)
    status = normalized["approval_status"]
    if status == "approved":
        return normalized, False
    if status == "draft" and allow_draft_inventory:
        return normalized, True
    if (
        status == "approved_for_offline_demo"
        and offline_demo
        and normalized.get("reviewer") == "PENDING HUMAN REVIEW"
    ):
        return normalized, False
    if status == "draft":
        raise ValueError(
            "Draft inventory is blocked. For recorded-file evaluation only, "
            "pass --allow-draft-inventory-for-offline-eval."
        )
    raise ValueError(
        "Inventory must be human-approved, or be an explicitly permitted "
        "offline-demo inventory."
    )


def _category(finding: Finding) -> str:
    if finding.source == "health":
        return "telemetry health"
    if finding.source == "sensor_noise_model":
        return "sensor-value anomaly"
    if finding.rule_id == "topic_rate_out_of_band":
        observed = finding.evidence.get("observed_hz")
        band = finding.evidence.get("approved_band_hz", {})
        if (
            isinstance(observed, (int, float))
            and isinstance(band, dict)
            and observed > band.get("max", float("inf"))
        ):
            return "flooding"
        return "timing anomaly"
    if finding.rule_id in {
        "unapproved_node",
        "node_set_hash_change",
        "publisher_count_above_policy",
        "subscriber_count_above_policy",
        "parameter_event_outside_approved_window",
        "service_call_rate_above_policy",
        "domain_config_mismatch",
        "discovery_config_mismatch",
        "bridge_config_mismatch",
    }:
        return "graph/access anomaly"
    if finding.rule_id in {
        "topic_gap_above_policy",
        "topic_stamp_lag_above_policy",
        "late_messages_observed",
        "stale_telemetry",
        "duplicate_ticks",
        "out_of_order_ticks",
        "timestamp_jitter",
    }:
        return "timing anomaly"
    return "telemetry health"


def _incident_groups(findings: list[Finding], warnings: list[str]) -> list[dict[str, Any]]:
    alerts = merge_alerts(findings, merge_gap_ns=_MERGE_GAP_NS)
    ordered = sorted(
        alerts,
        key=lambda alert: (
            int(alert.incident_start_sim_ns or alert.timestamp_sim_ns),
            int(alert.incident_end_sim_ns or alert.timestamp_sim_ns),
        ),
    )
    groups: list[list[Any]] = []
    for alert in ordered:
        start = int(alert.incident_start_sim_ns or alert.timestamp_sim_ns)
        if groups:
            previous_end = max(
                int(item.incident_end_sim_ns or item.timestamp_sim_ns)
                for item in groups[-1]
            )
            if start <= previous_end + _MERGE_GAP_NS:
                groups[-1].append(alert)
                continue
        groups.append([alert])

    incidents: list[dict[str, Any]] = []
    for group in groups:
        categories = Counter()
        components: list[dict[str, Any]] = []
        detector_names: set[str] = set()
        for alert in group:
            detector_names.add(
                f"policy_rule:{alert.rule_or_model}"
                if alert.source == "policy"
                else alert.source
            )
            components.append(
                {
                    "detector": (
                        f"policy_rule:{alert.rule_or_model}"
                        if alert.source == "policy"
                        else alert.source
                    ),
                    "rule_or_model": alert.rule_or_model,
                    "affected": alert.affected,
                    "evidence": alert.evidence,
                    "score": alert.score,
                    "threshold": alert.threshold,
                    "component_start_sim_ns": alert.incident_start_sim_ns,
                    "component_end_sim_ns": alert.incident_end_sim_ns,
                }
            )
            source = alert.source
            rule = alert.rule_or_model
            shim = Finding(
                rule_id=rule,
                timestamp_sim_ns=int(alert.timestamp_sim_ns),
                run_id="blind_recording",
                evidence=alert.evidence,
                severity=alert.severity,
                source=source,
            )
            categories[_category(shim)] += 1
        chosen_category = sorted(
            categories.items(), key=lambda item: (-item[1], item[0])
        )[0][0]
        severity = max(
            (alert.severity for alert in group), key=_SEVERITY_ORDER.index
        )
        confidence_notes = [
            "Category is a signal-based hypothesis, not a confirmed attack type."
        ]
        if _DRAFT_NOTE in warnings:
            confidence_notes.append(_DRAFT_NOTE)
        if _MISSING_INPUT_NOTE in warnings:
            confidence_notes.append(_MISSING_INPUT_NOTE)
        incidents.append(
            {
                "start_sim_ns": min(
                    int(item.incident_start_sim_ns or item.timestamp_sim_ns)
                    for item in group
                ),
                "end_sim_ns": max(
                    int(item.incident_end_sim_ns or item.timestamp_sim_ns)
                    for item in group
                ),
                "detectors": sorted(detector_names),
                "suspected_category": chosen_category,
                "evidence": components,
                "severity": severity,
                "what_this_does_not_prove": (
                    "An anomaly does not by itself establish an attack, identify "
                    "an actor, or prove that vehicle behavior was affected."
                ),
                "confidence_notes": " ".join(confidence_notes),
                "requires_human_approval": True,
                "automatic_action_taken": False,
            }
        )
    return incidents


def _sensor_findings(
    frame: pd.DataFrame,
    bundle: dict[str, Any],
    *,
    allow_draft_inventory: bool,
    missing_input: bool,
) -> list[Finding]:
    if frame.empty:
        return []
    raw_columns = list(bundle["raw_sensor_columns"])
    present_sensor = [column for column in raw_columns if column in frame]
    if not present_sensor:
        raise ValueError(
            "Aligned input has no model-compatible numeric IMU, odometry, or contact fields."
        )
    time_column = "sim_time_s" if "sim_time_s" in frame else "sim_time_ns"
    sanitized = frame[[time_column, *present_sensor]].copy()
    times = _time_ns(sanitized)
    features = engineer_features(
        sanitized, expected_raw_columns=raw_columns
    ).reindex(columns=bundle["feature_columns"])
    name = str(bundle["selected_model"])
    threshold = float(bundle["thresholds"][name])
    scores = anomaly_scores(bundle["models"][name], name, features)
    predictions = np.flatnonzero(scores >= threshold)
    findings: list[Finding] = []
    for position in predictions:
        score = float(scores[position])
        notes = [
            "Score uses saved sensor-noise model and threshold; it is not a probability."
        ]
        if allow_draft_inventory:
            notes.append(_DRAFT_NOTE)
        if missing_input:
            notes.append(_MISSING_INPUT_NOTE)
        findings.append(
            Finding(
                rule_id=f"sensor_{name}",
                timestamp_sim_ns=int(times[position]),
                run_id="blind_recording",
                source="sensor_noise_model",
                severity="medium",
                score=score,
                threshold=threshold,
                evidence={
                    "anomaly_score": score,
                    "threshold": threshold,
                    "responsible_features": explain_row(
                        features.iloc[position], bundle["normal_reference"]
                    ),
                },
                what_this_does_not_prove=(
                    "A sensor-value anomaly does not establish a fault, attack, "
                    "or unsafe vehicle response."
                ),
                recommended_next_step=(
                    "Check the sensor, calibration, timing, and independent "
                    "vehicle-state observations."
                ),
                confidence_notes=" ".join(notes),
            )
        )
    return findings


def _telemetry_findings(
    frame: pd.DataFrame,
    inventory: dict[str, Any],
    bundle: dict[str, Any],
    *,
    manifest: dict[str, Any] | None,
    allow_draft_inventory: bool,
    missing_input: bool,
    include_telemetry_model: bool,
) -> list[Finding]:
    if frame.empty:
        return []
    safe_frame = _without_labels(frame).copy()
    times = _time_ns(safe_frame)
    findings = evaluate_rules(
        safe_frame,
        inventory,
        "blind_recording",
        manifest=_safe_bridge_manifest(manifest),
    )
    if include_telemetry_model:
        features = telemetry_features(safe_frame).reindex(
            columns=bundle["feature_columns"]
        )
        name = str(bundle["selected_model"])
        threshold = float(bundle["thresholds"][name])
        model = bundle["models"][name]
        features = _fill_missing_model_features(features, model)
        scores = security_scores(model, name, features)
        for position in np.flatnonzero(scores >= threshold):
            score = float(scores[position])
            notes = [
                "Score uses saved telemetry model and threshold; it is not a probability."
            ]
            if allow_draft_inventory:
                notes.append(_DRAFT_NOTE)
            if missing_input:
                notes.append(_MISSING_INPUT_NOTE)
            findings.append(
                Finding(
                    rule_id=f"telemetry_{name}",
                    timestamp_sim_ns=int(times[position]),
                    run_id="blind_recording",
                    source="telemetry_model",
                    severity="medium",
                    score=score,
                    threshold=threshold,
                    evidence={
                        "model": name,
                        "anomaly_score": score,
                        "threshold": threshold,
                    },
                    what_this_does_not_prove=(
                        "A telemetry anomaly score is not a probability or proof of "
                        "unauthorized access."
                    ),
                    recommended_next_step=(
                        "Review the ROS graph, topic statistics, and independent "
                        "collector logs."
                    ),
                    confidence_notes=" ".join(notes),
                )
            )
    annotated: list[Finding] = []
    for finding in findings:
        notes = [finding.confidence_notes]
        if allow_draft_inventory and _DRAFT_NOTE not in finding.confidence_notes:
            notes.append(_DRAFT_NOTE)
        if missing_input and _MISSING_INPUT_NOTE not in finding.confidence_notes:
            notes.append(_MISSING_INPUT_NOTE)
        annotated.append(
            replace(finding, confidence_notes=" ".join(notes))
            if len(notes) > 1
            else finding
        )
    annotated.extend(_timestamp_jitter_findings(safe_frame))
    return annotated


def _timestamp_jitter_findings(frame: pd.DataFrame) -> list[Finding]:
    if len(frame) < 3:
        return []
    times = _time_ns(frame)
    steps = np.diff(times).astype(float) / 1e9
    positive = steps[steps > 0]
    if not len(positive):
        return []
    expected = float(np.median(positive))
    threshold = _TIMESTAMP_JITTER_DEVIATION_S
    findings: list[Finding] = []
    for position, step in enumerate(steps):
        if step > 0 and abs(float(step) - expected) > threshold:
            findings.append(
                Finding(
                    rule_id="timestamp_jitter",
                    timestamp_sim_ns=int(times[position + 1]),
                    run_id="blind_recording",
                    source="health",
                    severity="medium",
                    evidence={
                        "observed_interval_s": float(step),
                        "median_interval_s": expected,
                        "deviation_threshold_s": threshold,
                    },
                    what_this_does_not_prove=(
                        "Timestamp jitter does not establish a fault, attack, "
                        "or malicious clock manipulation."
                    ),
                    recommended_next_step=(
                        "Compare simulation timestamps with the collector clock "
                        "and an independent timing source."
                    ),
                )
            )
    return findings


def monitor_frames(
    *,
    aligned: pd.DataFrame | None,
    telemetry: pd.DataFrame | None,
    inventory: dict[str, Any],
    noise_bundle: dict[str, Any],
    security_bundle: dict[str, Any],
    manifest: dict[str, Any] | None = None,
    join_points_ns: list[int] | None = None,
    reset_at_joins: bool = False,
    allow_draft_inventory_for_offline_eval: bool = False,
    offline_demo: bool = False,
    include_telemetry_model: bool = True,
) -> MonitorResult:
    """Run both frozen detectors on one recording without exposing labels or identity."""
    if aligned is None and telemetry is None:
        raise ValueError("Provide at least one of aligned input or telemetry input.")
    checked_inventory, draft_override = _inventory_gate(
        inventory,
        allow_draft_inventory=allow_draft_inventory_for_offline_eval,
        offline_demo=offline_demo,
    )
    if noise_bundle.get("task") != "normal_vs_sensor_noise":
        raise ValueError("The saved noise bundle has an unexpected task.")
    if security_bundle.get("task") != "ros2_telemetry_security_anomaly":
        raise ValueError("The saved telemetry bundle has an unexpected task.")

    warnings: list[str] = []
    if draft_override:
        warnings.append(_DRAFT_NOTE)
    missing_input = aligned is None or telemetry is None
    if aligned is None:
        warnings.append("WARNING: aligned input missing; sensor-noise coverage unavailable.")
    if telemetry is None:
        warnings.append("WARNING: telemetry input missing; policy and telemetry-model coverage unavailable.")
    if telemetry is not None and not include_telemetry_model:
        warnings.append(_TELEMETRY_ABLATION_NOTE)
    if missing_input:
        warnings.append(_MISSING_INPUT_NOTE)

    joins = sorted(set(int(value) for value in (join_points_ns or [])))
    aligned_slices = _ordered_slices(aligned, joins, reset_at_joins)
    telemetry_slices = _ordered_slices(telemetry, joins, reset_at_joins)
    findings: list[Finding] = []
    for frame in aligned_slices:
        findings.extend(
            _sensor_findings(
                frame,
                noise_bundle,
                allow_draft_inventory=draft_override,
                missing_input=missing_input,
            )
        )
    for frame in telemetry_slices:
        findings.extend(
            _telemetry_findings(
                frame,
                checked_inventory,
                security_bundle,
                manifest=manifest,
                allow_draft_inventory=draft_override,
                missing_input=missing_input,
                include_telemetry_model=include_telemetry_model,
            )
        )
    annotated: list[Finding] = []
    for finding in findings:
        notes = [finding.confidence_notes]
        if draft_override and _DRAFT_NOTE not in finding.confidence_notes:
            notes.append(_DRAFT_NOTE)
        if missing_input and _MISSING_INPUT_NOTE not in finding.confidence_notes:
            notes.append(_MISSING_INPUT_NOTE)
        annotated.append(replace(finding, confidence_notes=" ".join(notes)))
    findings = annotated
    incidents = _incident_groups(findings, warnings)
    return MonitorResult(
        incidents=incidents,
        findings=findings,
        warnings=warnings,
        draft_override_used=draft_override,
        coverage={
            "sensor_noise_model": aligned is not None,
            "telemetry_policy_rules": telemetry is not None,
            "telemetry_model": telemetry is not None and include_telemetry_model,
        },
    )
