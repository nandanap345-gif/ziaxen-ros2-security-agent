"""Build the seed-1/2-only v2 bundle and signal audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import numpy as np

from ziaxen_agent.data import load_runs
from ziaxen_agent.security.inventory import bootstrap_inventory
from ziaxen_agent.v2 import detect_v2, fit_v2_config


def _normal_frames(root: Path, seed: int) -> list[pd.DataFrame]:
    runs = load_runs(root, seeds={seed}, expected_counts=True)
    return [run.aligned for run in runs if not run.metadata.get("event_types")]


def _calibration_runs(root: Path, seed: int, *, attack_windows: bool) -> list[pd.DataFrame]:
    index = pd.read_csv(root / "dataset_index.csv")
    selected = index[pd.to_numeric(index["seed"], errors="coerce").eq(seed)]
    frames: list[pd.DataFrame] = []
    for row in selected.itertuples(index=False):
        path = root / str(row.relative_path)
        aligned = pd.read_csv(path / "aligned.csv.gz")
        times = pd.to_numeric(aligned["sim_time_s"], errors="coerce")
        events = pd.read_csv(path / "events.csv")
        if attack_windows and events.empty:
            continue
        keep = times >= 15.0
        if attack_windows and not events.empty:
            for event_id, group in events.groupby("attack_id"):
                start = float(group.loc[group.event.eq("start"), "sim_time_ns"].iloc[0])
                stop = float(group.loc[group.event.eq("stop"), "sim_time_ns"].iloc[0])
                keep &= ~((aligned.sim_time_ns >= start) & (aligned.sim_time_ns < stop))
        elif not attack_windows and not events.empty:
            continue
        part = aligned.loc[keep].copy()
        if not part.empty:
            frames.append(part)
    return frames


def _rule_rates(frames: list[pd.DataFrame], config: dict) -> dict[str, float]:
    hours = sum(len(frame) / 50.0 for frame in frames) / 3600.0
    counts = {rule: 0 for rule in ("freeze", "jump", "clock_skew", "false_contact")}
    for frame in frames:
        for finding in detect_v2(frame, config):
            rule = finding.rule_id.removeprefix("v2_")
            if rule in counts:
                counts[rule] += 1
    return {rule: count / hours if hours else 0.0 for rule, count in counts.items()}


def _attack_cases(root: Path, seed: int) -> list[tuple[str, pd.DataFrame, int, int]]:
    index = pd.read_csv(root / "dataset_index.csv")
    cases: list[tuple[str, pd.DataFrame, int, int]] = []
    for row in index[pd.to_numeric(index["seed"], errors="coerce").eq(seed) & index["type"].eq("attack")].itertuples(index=False):
        path = root / str(row.relative_path)
        frame = pd.read_csv(path / "aligned.csv.gz")
        events = pd.read_csv(path / "events.csv")
        for attack_id, group in events.groupby("attack_id"):
            start = int(group.loc[group.event.eq("start"), "sim_time_ns"].iloc[0])
            stop = int(group.loc[group.event.eq("stop"), "sim_time_ns"].iloc[0])
            cases.append((str(group["attack_type"].iloc[0]), frame, start, stop))
    return cases


def _chance_check(normal_frames: list[pd.DataFrame], attack_cases: list[tuple[str, pd.DataFrame, int, int]], config: dict) -> list[dict[str, object]]:
    rules = ("freeze", "jump", "clock_skew", "false_contact")
    normal_cursor = 0
    rows: list[dict[str, object]] = []
    for class_name, frame, start, stop in attack_cases:
        attack_part = frame.loc[(frame.sim_time_ns >= start) & (frame.sim_time_ns < stop)]
        attack_hits = {rule: 0 for rule in rules}
        for finding in detect_v2(attack_part, config):
            rule = finding.rule_id.removeprefix("v2_")
            if rule in attack_hits:
                attack_hits[rule] = 1
        duration = len(attack_part)
        normal_hits = {rule: 0 for rule in rules}
        remaining = duration
        for normal in normal_frames:
            if remaining <= 0:
                break
            take = normal.iloc[normal_cursor % max(1, len(normal)):]
            take = take.iloc[:remaining]
            normal_cursor += len(take)
            remaining -= len(take)
            for finding in detect_v2(take, config):
                rule = finding.rule_id.removeprefix("v2_")
                if rule in normal_hits:
                    normal_hits[rule] = 1
        for rule in rules:
            rows.append({"class": class_name, "rule": rule, "attack_detection": attack_hits[rule], "matched_normal_chance": normal_hits[rule], "recall_minus_chance": attack_hits[rule] - normal_hits[rule], "counts_for_class": bool(attack_hits[rule] > normal_hits[rule])})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).parents[1])
    args = parser.parse_args()
    config_dir = args.project_root / "config" / "v2"
    model_dir = args.project_root / "models" / "v2"
    report_dir = args.project_root / "reports"
    config_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    seed1_normal = _calibration_runs(args.data_root, 1, attack_windows=False)
    seed2_normal = _calibration_runs(args.data_root, 2, attack_windows=False)
    seed2_attack_normal = _calibration_runs(args.data_root, 2, attack_windows=True)
    bundle = fit_v2_config(seed1_normal, seed2_normal + seed2_attack_normal)
    seed2_rate = _rule_rates(seed2_normal + seed2_attack_normal, bundle)
    bundle["seed2_normal_audit"] = {"hours": sum(len(f) / 50.0 for f in seed2_normal + seed2_attack_normal) / 3600.0, "alerts_per_hour": seed2_rate, "budget_per_rule": 2.0}
    bundle["disabled_rules"] = [rule for rule, rate in seed2_rate.items() if rate > 2.0]
    bundle["chance_check"] = _chance_check(seed2_normal, _attack_cases(args.data_root, 2), bundle)
    target_rule_class = {"freeze": "freeze", "jump": "jump", "clock_skew": "clock_skew", "false_contact": "false_contact"}
    for rule, class_name in target_rule_class.items():
        target_rows = [row for row in bundle["chance_check"] if row["rule"] == rule and row["class"] == class_name]
        if not any(row["counts_for_class"] for row in target_rows):
            bundle["disabled_rules"].append(rule)
    bundle["disabled_rules"] = sorted(set(bundle["disabled_rules"]))
    bundle["data_roles"] = {"fit": [1], "threshold_selection": [2], "score": [3]}
    (config_dir / "detector.json").write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    bootstrap_inventory(args.data_root, config_dir / "approved_inventory.json", seeds={1, 2})
    lines = [
        "# v2 class signal analysis", "", 
        "All limits were fit from seed-1 normal recordings and selected on seed-2 normal recordings. Seed 3 was not read by this build.", "",
        "| Class | Signal decision | Evidence boundary |", "|---|---|---|",
    ]
    for name, decision in {
        "freeze": "usable: flatline/zero first-difference in target channels",
        "jump": "usable only after per-column calibration; mixed-unit/global thresholds were invalid",
        "replay": "not implemented as a positive rule until a stable repeated sequence is demonstrated",
        "clock_skew": "usable when stamp lag columns are present",
        "bias_drift": "candidate only; residual calibration requires a validated cross-sensor pairing",
        "false_contact": "disabled if seed-2 normal firing exceeds 2 alerts/hour or does not beat matched-window chance",
        "missed_contact": "undetectable with the available recorded channels when no independent collision signature exists",
    }.items():
        lines.append(f"| {name} | {decision} | Manifest/event definitions remain the label authority; no labels are detector inputs. |")
    lines += ["", "## Seed-2 normal firing audit", "", f"Normal exposure: {bundle['seed2_normal_audit']['hours']:.4f} h; budget: <=2.000 alerts/hour/rule.", "", "| Rule | Alerts/hour | Status |", "|---|---:|---|"]
    for rule, rate in seed2_rate.items():
        lines.append(f"| {rule} | {rate:.6f} | {'disabled' if rule in bundle['disabled_rules'] else 'within budget'} |")
    lines += ["", "The previous over-trigger was caused by a single global jump limit applied across mixed-unit sensor/contact columns and by state crossing artificial joins. v2 now uses per-column limits and reset slices; seed-3 was not used for calibration.", "", "## Seed-2 attack-vs-chance check", "", "The JSON contains one row per event and rule; `counts_for_class` is true only when the matched-duration normal-window chance indicator is lower than the attack-window indicator."]
    (report_dir / "v2_chance_check.csv").write_text(pd.DataFrame(bundle["chance_check"]).to_csv(index=False), encoding="utf-8")
    (report_dir / "v2_class_signal_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
