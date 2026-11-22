"""Frozen v1/v2 comparison, reset-mode stress, and leakage checks."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy.stats import chi2

from ziaxen_agent.blind_evaluation import _inject_sensor_noise, _row_metrics
from ziaxen_agent.monitor import monitor_frames

CLASSES = ["noise", "delay", "drop", "duplicate", "flood", "spoof", "unauthorized_node", "unauthorized_subscription", "param_tamper", "service_abuse", "bias_drift", "jump", "replay", "clock_skew", "freeze", "false_contact", "missed_contact"]


def wilson(k: int, n: int) -> list[float] | None:
    if not n:
        return None
    z, p = 1.959963984540054, k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, centre - spread), min(1.0, centre + spread)]


def poisson(k: int, hours: float) -> list[float]:
    lower = 0.0 if k == 0 else float(chi2.ppf(0.025, 2 * k) / 2)
    upper = float(chi2.ppf(0.975, 2 * (k + 1)) / 2)
    return [lower / hours, upper / hours]


def hit(incident: dict[str, Any], event: dict[str, Any]) -> bool:
    return incident["end_sim_ns"] >= event["start_sim_ns"] - 1_500_000_000 and incident["start_sim_ns"] <= event["stop_sim_ns"] + 500_000_000


def events_from_frame(events: pd.DataFrame) -> list[dict[str, Any]]:
    output = []
    for attack_id, group in events.groupby("attack_id"):
        starts = group.loc[group.event.eq("start"), "sim_time_ns"]
        stops = group.loc[group.event.eq("stop"), "sim_time_ns"]
        if len(starts) and len(stops):
            output.append({"class_name": str(group["attack_type"].iloc[0]), "start_sim_ns": int(starts.iloc[0]), "stop_sim_ns": int(stops.iloc[0])})
    return output


def score(frame: pd.DataFrame, telemetry: pd.DataFrame, inventory: dict[str, Any], noise: dict[str, Any], security: dict[str, Any], config: dict[str, Any], events: list[dict[str, Any]], joins: list[int], profile: str) -> dict[str, Any]:
    result = monitor_frames(aligned=frame, telemetry=telemetry, inventory=inventory, noise_bundle=noise, security_bundle=security, join_points_ns=joins, reset_at_joins=True, allow_draft_inventory_for_offline_eval=True, offline_demo=True, profile=profile, v2_config=config if profile == "v2" else None)
    by_class = {}
    for cls in CLASSES:
        selected = [e for e in events if e["class_name"] == cls]
        matches = [e for e in selected if any(hit(i, e) for i in result.incidents)]
        detectors = sorted({component["rule_or_model"] for i in result.incidents if any(hit(i, e) for e in selected) for component in i["evidence"]})
        by_class[cls] = {"events": len(selected), "detected": len(matches), "recall": len(matches) / len(selected) if selected else None, "wilson_95": wilson(len(matches), len(selected)), "detector": detectors}
    matching_incidents = sum(any(hit(incident, event) for event in events) for incident in result.incidents)
    false_by_rule: dict[str, int] = {}
    for incident in result.incidents:
        if not any(hit(incident, event) for event in events):
            for component in incident["evidence"]:
                rule = str(component["rule_or_model"])
                false_by_rule[rule] = false_by_rule.get(rule, 0) + 1
    return {"incidents": result.incidents, "matching_incidents": matching_incidents, "false_by_rule": false_by_rule, "classes": by_class, "row_metrics": _row_metrics(frame, result.findings, events), "warnings": result.warnings}


def aggregate(scores: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {cls: {"events": 0, "detected": 0, "detectors": set()} for cls in CLASSES}
    confusion = {key: 0 for key in ("true_positive", "false_positive", "false_negative", "true_negative")}
    incident_count = matching_incidents = 0
    for item in scores:
        incident_count += len(item["incidents"])
        matching_incidents += item["matching_incidents"]
        for cls, value in item["classes"].items():
            totals[cls]["events"] += value["events"]
            totals[cls]["detected"] += value["detected"]
            totals[cls]["detectors"].update(value["detector"])
        for key in confusion:
            confusion[key] += item["row_metrics"][key]
    classes = {cls: {"events": val["events"], "detected": val["detected"], "recall": val["detected"] / val["events"] if val["events"] else None, "wilson_95": wilson(val["detected"], val["events"]), "detector": sorted(val["detectors"])} for cls, val in totals.items()}
    total_events = sum(val["events"] for val in totals.values())
    detected_events = sum(val["detected"] for val in totals.values())
    tp, fp, fn, tn = (confusion[key] for key in ("true_positive", "false_positive", "false_negative", "true_negative"))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return {"classes": classes, "micro_event_recall": detected_events / total_events if total_events else None, "macro_event_recall": float(np.mean([v["recall"] for v in classes.values() if v["recall"] is not None])), "classes_detected": sum(v["detected"] > 0 for v in totals.values()), "classes_total": 17, "incident_count": incident_count, "incident_matching": matching_incidents, "incident_precision": matching_incidents / incident_count if incident_count else 0.0, "row_metrics": {"precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0, "balanced_accuracy": (recall + specificity) / 2, "mcc": (tp * tn - fp * fn) / denominator if denominator else 0.0, "accuracy": (tp + tn) / sum(confusion.values()) if sum(confusion.values()) else 0.0, **confusion}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).parents[1])
    parser.add_argument("--stream-dir", type=Path, default=None)
    args = parser.parse_args()
    root, stream_dir = args.project_root, args.stream_dir or args.project_root / "reports" / "blind_streams"
    config = json.loads((root / "config" / "v2" / "detector.json").read_text(encoding="utf-8"))
    inventory = json.loads((root / "config" / "v2" / "approved_inventory.json").read_text(encoding="utf-8"))
    noise = joblib.load(root / "models" / "noise_detector.joblib")
    security = joblib.load(root / "models" / "security_detector.joblib")
    index = pd.read_csv(args.data_root / "dataset_index.csv")
    per_run: dict[str, list[dict[str, Any]]] = {"v1": [], "v2": []}
    crop_items: list[dict[str, Any]] = []
    crop_offsets: list[float] = []
    for row in index[pd.to_numeric(index.seed, errors="coerce").eq(3)].itertuples(index=False):
        path = args.data_root / str(row.relative_path)
        aligned, telemetry = pd.read_csv(path / "aligned.csv.gz"), pd.read_csv(path / "telemetry.csv.gz")
        events = events_from_frame(pd.read_csv(path / "events.csv"))
        for profile in per_run:
            per_run[profile].append(score(aligned, telemetry, inventory, noise, security, config, events, [], profile))
        if events:
            first_time = int(aligned["sim_time_ns"].iloc[0])
            offset_s = (sum(str(row.relative_path).encode("utf-8")) % 2001) / 100.0
            cropped = aligned.loc[aligned["sim_time_ns"] >= first_time + int(offset_s * 1e9)].copy()
            crop_items.append(score(cropped, telemetry.loc[telemetry["sim_time_ns"] >= first_time + int(offset_s * 1e9)].copy(), inventory, noise, security, config, events, [], "v2"))
            crop_offsets.append(offset_s)
    streams: dict[str, Any] = {}
    manifest_paths = sorted(stream_dir.glob("stream_b_seed_*_manifest.json")) + [stream_dir / "stream_c_manifest.json"]
    for manifest_path in manifest_paths:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        aligned, telemetry = pd.read_csv(stream_dir / manifest["aligned_file"]), pd.read_csv(stream_dir / manifest["telemetry_file"])
        streams[manifest["stream_id"]] = {"normal_hours": float(manifest.get("normal_seconds", 0.0)) / 3600.0}
        for profile in ("v1", "v2"):
            streams[manifest["stream_id"]][profile] = score(aligned, telemetry, inventory, noise, security, config, manifest["ground_truth"], manifest["join_points_sim_ns"], profile)
    comparison: dict[str, Any] = {"seed3_per_run": {profile: aggregate(items) for profile, items in per_run.items()}, "streams": {name: {profile: aggregate([item]) for profile, item in values.items() if profile in ("v1", "v2")} for name, values in streams.items()}, "config_roles": config.get("data_roles"), "seed2_audit": config.get("seed2_normal_audit"), "chance_check": config.get("chance_check"), "noise_stress_v2": {}, "timing_crop_v2": {"status": "completed", "offsets_s": crop_offsets, "v2": aggregate(crop_items)}}
    for name, values in streams.items():
        if name != "stream_c":
            continue
        hours = values["normal_hours"]
        comparison["streams"][name]["false_alerts_by_rule"] = {}
        for profile in ("v1", "v2"):
            counts: dict[str, int] = {}
            for rule, count in values[profile]["false_by_rule"].items():
                counts[rule] = count
            comparison["streams"][name]["false_alerts_by_rule"][profile] = {rule: {"count": count, "per_hour": count / hours if hours else None, "poisson_ci_95": poisson(count, hours)} for rule, count in counts.items()}
    c_manifest = json.loads((stream_dir / "stream_c_manifest.json").read_text(encoding="utf-8"))
    c_aligned, c_telemetry = pd.read_csv(stream_dir / c_manifest["aligned_file"]), pd.read_csv(stream_dir / c_manifest["telemetry_file"])
    hours = float(c_manifest["normal_seconds"]) / 3600.0
    for level, seed in (("low", 9100), ("moderate", 9101), ("moderate_high_1", 9103), ("moderate_high_2", 9104), ("high", 9102)):
        stress = score(_inject_sensor_noise(c_aligned, seed, level), c_telemetry, inventory, noise, security, config, [], c_manifest["join_points_sim_ns"], "v2")
        comparison["noise_stress_v2"][level] = {"incidents_per_hour": len(stress["incidents"]) / hours, "poisson_ci_95": poisson(len(stress["incidents"]), hours)}
    (root / "reports" / "v2_evaluation.json").write_text(json.dumps(comparison, indent=2, default=list) + "\n", encoding="utf-8")
    a, b = comparison["seed3_per_run"]["v1"], comparison["seed3_per_run"]["v2"]
    lines = ["# Detector v2 evaluation", "", "Seed-3 per-run and reset-mode Stream B/Stream C comparison; v1 artifacts were not modified.", "", "| Class | v1 | v2 | v1 Wilson CI | v2 Wilson CI | v2 detector |", "|---|---:|---:|---|---|---|"]
    for cls in CLASSES:
        lines.append(f"| {cls} | {a['classes'][cls]['detected']}/{a['classes'][cls]['events']} | {b['classes'][cls]['detected']}/{b['classes'][cls]['events']} | {a['classes'][cls]['wilson_95']} | {b['classes'][cls]['wilson_95']} | {','.join(b['classes'][cls]['detector']) or 'none'} |")
    lines += ["", "## Overall", "", f"v1 micro/macro recall {a['micro_event_recall']:.3f}/{a['macro_event_recall']:.3f}; v2 {b['micro_event_recall']:.3f}/{b['macro_event_recall']:.3f}. Classes: v1 {a['classes_detected']}/17; v2 {b['classes_detected']}/17.", f"Incident precision v1/v2: {a['incident_precision']:.3f}/{b['incident_precision']:.3f}.", f"Row metrics v1: balanced accuracy {a['row_metrics']['balanced_accuracy']:.3f}, MCC {a['row_metrics']['mcc']:.3f}, accuracy {a['row_metrics']['accuracy']:.3f}, F1 {a['row_metrics']['f1']:.3f}. v2: balanced accuracy {b['row_metrics']['balanced_accuracy']:.3f}, MCC {b['row_metrics']['mcc']:.3f}, accuracy {b['row_metrics']['accuracy']:.3f}, F1 {b['row_metrics']['f1']:.3f}. Plain accuracy is misleading because normal rows dominate.", "", "Stream-C false-alert counts/rates and exact Poisson CIs by rule are in JSON; the seed-2 rule audit is in v2_class_signal_analysis.md.", "", "Noise stress and timing-crop leakage checks ran after freeze; crop offsets and results are in JSON.", "", "If false_contact or missed_contact has v2 detections despite the signal analysis, the result is invalid."]
    (root / "reports" / "v2_evaluation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
