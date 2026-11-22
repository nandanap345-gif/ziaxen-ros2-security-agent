"""Command-line entry points for inspection, training, evaluation, and inference."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from .agent import SensorNoiseAgent
from .data import inspect_runs, load_runs
from .evaluation import evaluate_detector
from .training import train_detector
from .security.alerts import merge_alerts
from .security.alerts import Finding
from .security.evaluate import (
    evaluate_security_detector,
    evaluate_tolerance_sensitivity,
)
from .security.inspection import write_security_dataset_report
from .security.inventory import bootstrap_inventory, load_inventory
from .security.models import security_scores, train_security_detector
from .security.rules import evaluate_rules
from .security.telemetry import load_telemetry, telemetry_features
from .monitor import _fill_missing_model_features, monitor_frames
from .evaluation_streams import build_blind_streams
from .blind_evaluation import (
    evaluate_blind_streams,
    run_leave_one_class_out,
    run_robustness_stress_tests,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = PROJECT_ROOT / "models" / "noise_detector.joblib"
DEFAULT_REPORTS = PROJECT_ROOT / "reports"


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _data_root_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--data-root",
        default=os.environ.get("ZIAXEN_DATA_ROOT"),
        help=(
            "Path to AI_team_data (or set ZIAXEN_DATA_ROOT). "
            "Must contain dataset_index.csv."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ziaxen-agent",
        description="Inspect, train, evaluate, or run the Ziaxen sensor-noise agent.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    inspect = commands.add_parser("inspect", help="Validate and summarize dataset runs.")
    _data_root_argument(inspect)
    inspect.add_argument("--output", type=Path, help="Optional JSON summary path.")

    train = commands.add_parser("train", help="Train candidates and select on seed 2.")
    _data_root_argument(train)
    train.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    train.add_argument("--report", type=Path, default=DEFAULT_REPORTS / "training_validation.json")
    train.add_argument("--random-state", type=int, default=42)

    evaluate = commands.add_parser("evaluate", help="Evaluate held-out seed-3 runs.")
    _data_root_argument(evaluate)
    evaluate.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    evaluate.add_argument("--report-dir", type=Path, default=DEFAULT_REPORTS)

    infer = commands.add_parser("infer", help="Score a recorded sensor CSV/CSV.GZ file.")
    infer.add_argument("--input", type=Path, required=True)
    infer.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    infer.add_argument("--threshold", type=float, help="Override the saved threshold.")
    infer.add_argument("--output", type=Path, help="Write JSON Lines to this path.")

    security_inspect = commands.add_parser(
        "security-inspect", help="Inspect all indexed runs for security telemetry suitability."
    )
    _data_root_argument(security_inspect)
    security_inspect.add_argument(
        "--report-dir", type=Path, default=DEFAULT_REPORTS
    )

    bootstrap = commands.add_parser(
        "bootstrap-inventory", help="Write a draft inventory from a normal run."
    )
    _data_root_argument(bootstrap)
    bootstrap.add_argument(
        "--output", type=Path, default=PROJECT_ROOT / "config" / "approved_inventory.example.json"
    )

    security_train = commands.add_parser(
        "security-train", help="Train the separate telemetry security detector."
    )
    _data_root_argument(security_train)
    security_train.add_argument(
        "--model", type=Path, default=PROJECT_ROOT / "models" / "security_detector.joblib"
    )
    security_train.add_argument(
        "--report", type=Path, default=DEFAULT_REPORTS / "security_training_validation.json"
    )
    security_train.add_argument("--random-state", type=int, default=42)

    security_evaluate = commands.add_parser(
        "security-evaluate", help="Evaluate security rules and models on seed 3."
    )
    _data_root_argument(security_evaluate)
    security_evaluate.add_argument(
        "--model", type=Path, default=PROJECT_ROOT / "models" / "security_detector.joblib"
    )
    security_evaluate.add_argument(
        "--inventory", type=Path, required=True, help="Human-reviewed approved inventory JSON."
    )
    security_evaluate.add_argument(
        "--report-dir", type=Path, default=DEFAULT_REPORTS
    )

    tolerance_analysis = commands.add_parser(
        "security-tolerance-analysis",
        help="Compare event stop tolerances using seed-1 and seed-2 recordings only.",
    )
    _data_root_argument(tolerance_analysis)
    tolerance_analysis.add_argument(
        "--model",
        type=Path,
        default=PROJECT_ROOT / "models" / "security_detector.joblib",
    )
    tolerance_analysis.add_argument("--inventory", type=Path, required=True)
    tolerance_analysis.add_argument("--report-dir", type=Path, default=DEFAULT_REPORTS)

    security_scan = commands.add_parser(
        "security-scan", help="Replay a telemetry CSV and emit advisory security alerts."
    )
    security_scan.add_argument("--input", type=Path, required=True)
    security_scan.add_argument("--inventory", type=Path, required=True)
    security_scan.add_argument("--manifest", type=Path)
    security_scan.add_argument("--output", type=Path, help="Write alerts as JSON Lines.")
    security_scan.add_argument("--run-id", help="Override the run ID in emitted alerts.")
    security_scan.add_argument(
        "--model", type=Path, default=PROJECT_ROOT / "models" / "security_detector.joblib"
    )
    security_scan.add_argument(
        "--no-model", action="store_true", help="Run policy and health checks only."
    )
    security_scan.add_argument(
        "--offline-demo",
        action="store_true",
        help="Permit approved_for_offline_demo inventories for recorded local files only.",
    )

    monitor = commands.add_parser(
        "monitor",
        help="Fuse saved sensor and telemetry detectors over local recordings only.",
    )
    monitor.add_argument("--aligned", type=Path, help="Optional aligned sensor recording.")
    monitor.add_argument("--telemetry", type=Path, help="Optional telemetry recording.")
    monitor.add_argument("--inventory", type=Path, required=True)
    monitor.add_argument("--manifest", type=Path)
    monitor.add_argument("--output", type=Path, required=True)
    monitor.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    monitor.add_argument(
        "--security-model",
        type=Path,
        default=PROJECT_ROOT / "models" / "security_detector.joblib",
    )
    monitor.add_argument(
        "--allow-draft-inventory-for-offline-eval",
        action="store_true",
        help="Permit a draft inventory for local recorded-file evaluation only.",
    )
    monitor.add_argument(
        "--offline-demo",
        action="store_true",
        help="Permit approved_for_offline_demo inventories for recorded files only.",
    )
    monitor.add_argument(
        "--reset-state-at-joins",
        action="store_true",
        help="Reset rolling and row-to-row detector state at manifest join points.",
    )
    monitor.add_argument(
        "--profile", choices=("v1", "v2"), default="v1",
        help="Detector profile; v1 is the unchanged default.",
    )
    monitor.add_argument(
        "--v2-config", type=Path,
        default=PROJECT_ROOT / "config" / "v2" / "detector.json",
    )

    stream_build = commands.add_parser(
        "build-blind-streams",
        help="Build reproducible seed-3 blind mixed streams for offline evaluation.",
    )
    _data_root_argument(stream_build)
    stream_build.add_argument(
        "--output-dir", type=Path, default=DEFAULT_REPORTS / "blind_streams"
    )
    stream_build.add_argument(
        "--attack-seed", type=int, default=20261122
    )

    stream_evaluate = commands.add_parser(
        "evaluate-blind-streams",
        help="Score built streams with the frozen shipped models.",
    )
    stream_evaluate.add_argument(
        "--stream-dir", type=Path, default=DEFAULT_REPORTS / "blind_streams"
    )
    stream_evaluate.add_argument("--inventory", type=Path, required=True)
    stream_evaluate.add_argument("--report-dir", type=Path, default=DEFAULT_REPORTS)
    stream_evaluate.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    stream_evaluate.add_argument(
        "--security-model",
        type=Path,
        default=PROJECT_ROOT / "models" / "security_detector.joblib",
    )
    stream_evaluate.add_argument(
        "--allow-draft-inventory-for-offline-eval", action="store_true"
    )

    robustness = commands.add_parser(
        "blind-robustness",
        help="Run offline sensor, telemetry, and graph stress cases on Stream C.",
    )
    robustness.add_argument(
        "--stream-dir", type=Path, default=DEFAULT_REPORTS / "blind_streams"
    )
    robustness.add_argument("--inventory", type=Path, required=True)
    robustness.add_argument("--report-dir", type=Path, default=DEFAULT_REPORTS)
    robustness.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    robustness.add_argument(
        "--security-model",
        type=Path,
        default=PROJECT_ROOT / "models" / "security_detector.joblib",
    )
    robustness.add_argument(
        "--allow-draft-inventory-for-offline-eval", action="store_true"
    )

    loco = commands.add_parser(
        "leave-one-class-out",
        help="Run separate seed-grouped held-out-class telemetry experiments.",
    )
    _data_root_argument(loco)
    loco.add_argument("--inventory", type=Path, required=True)
    loco.add_argument(
        "--model-dir",
        type=Path,
        default=PROJECT_ROOT / "models" / "experiments",
    )
    loco.add_argument(
        "--report-dir", type=Path, default=DEFAULT_REPORTS / "experiments"
    )
    loco.add_argument("--random-state", type=int, default=42)
    loco.add_argument(
        "--allow-draft-inventory-for-offline-eval", action="store_true"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command in {
            "inspect",
            "train",
            "evaluate",
            "security-inspect",
            "bootstrap-inventory",
            "security-train",
            "security-evaluate",
            "security-tolerance-analysis",
            "build-blind-streams",
            "leave-one-class-out",
        } and not args.data_root:
            parser.error("Provide --data-root or set ZIAXEN_DATA_ROOT.")
        if args.command == "inspect":
            summary = inspect_runs(load_runs(args.data_root, expected_counts=True))
            rendered = json.dumps(summary, indent=2, default=_json_default)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(rendered, encoding="utf-8")
            print(rendered)
        elif args.command == "train":
            result = train_detector(
                args.data_root, args.model, args.report, args.random_state
            )
            print(json.dumps(result, indent=2, default=_json_default))
        elif args.command == "evaluate":
            result = evaluate_detector(args.data_root, args.model, args.report_dir)
            print(json.dumps(result, indent=2, default=_json_default))
        elif args.command == "infer":
            agent = SensorNoiseAgent.load(args.model, threshold=args.threshold)
            results = agent.predict_file(args.input)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open("w", encoding="utf-8") as handle:
                    for result in results:
                        handle.write(json.dumps(result, default=_json_default) + "\n")
                print(f"Wrote {len(results)} row results to {args.output}")
            else:
                for result in results:
                    print(json.dumps(result, default=_json_default))
        elif args.command == "security-inspect":
            result = write_security_dataset_report(
                args.data_root,
                args.report_dir / "security_dataset_inspection.json",
                args.report_dir / "security_dataset_inspection.md",
            )
            summary = {
                "data_root": result["data_root"],
                "indexed_runs": result["index_rows"],
                "inspected_runs": result["runs_inspected"],
                "total_rows": result["total_rows"],
                "label_disagreement_runs": result["label_disagreements"]["run_count"],
                "class_assessments": result["class_assessments"],
                "reports": [
                    str((args.report_dir / "security_dataset_inspection.json").resolve()),
                    str((args.report_dir / "security_dataset_inspection.md").resolve()),
                ],
            }
            print(json.dumps(summary, indent=2, default=_json_default))
        elif args.command == "bootstrap-inventory":
            result = bootstrap_inventory(args.data_root, args.output)
            print(
                f"Wrote unapproved inventory draft to {args.output}. "
                "Review it; it cannot be used for scanning until approved."
            )
            print(json.dumps(result, indent=2, default=_json_default))
        elif args.command == "security-train":
            result = train_security_detector(
                args.data_root,
                args.model,
                args.report,
                random_state=args.random_state,
            )
            print(json.dumps(result, indent=2, default=_json_default))
        elif args.command == "security-evaluate":
            result = evaluate_security_detector(
                args.data_root,
                args.model,
                args.inventory,
                args.report_dir,
            )
            print(
                json.dumps(
                    {
                        "test_runs": result["dataset_split"]["test_runs"],
                        "inventory_approval_status": result["inventory_approval_status"],
                        "selected_model": result["selected_model"],
                        "overall_row_metrics": result["overall_row_metrics"],
                        "event_metrics": result["event_metrics"],
                        "false_alerts_per_hour": result["false_alerts_per_hour"],
                        "files": result["files"],
                    },
                    indent=2,
                    default=_json_default,
                )
            )
        elif args.command == "security-tolerance-analysis":
            result = evaluate_tolerance_sensitivity(
                args.data_root,
                args.model,
                args.inventory,
                args.report_dir,
            )
            print(
                json.dumps(
                    {
                        "seeds": result["seeds"],
                        "scikit_learn_version": result["scikit_learn_version"],
                        "model_thresholds_changed": result["model_thresholds_changed"],
                        "reports": [
                            str((args.report_dir / "security_tolerance_sensitivity.md").resolve()),
                            str((args.report_dir / "security_tolerance_sensitivity.json").resolve()),
                        ],
                    },
                    indent=2,
                )
            )
        elif args.command == "security-scan":
            inventory = load_inventory(
                args.inventory,
                require_approved=True,
                allow_offline_demo=args.offline_demo,
            )
            telemetry = load_telemetry(args.input)
            manifest = None
            if args.manifest:
                manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            run_id = args.run_id or args.input.stem.replace(".csv", "")
            findings = evaluate_rules(telemetry, inventory, run_id, manifest=manifest)
            if not args.no_model:
                if not args.model.is_file():
                    raise FileNotFoundError(
                        f"Security model was not found: {args.model}. "
                        "Train it first or pass --no-model."
                    )
                bundle = joblib.load(args.model)
                if bundle.get("task") != "ros2_telemetry_security_anomaly":
                    raise ValueError(f"Not a security telemetry model: {args.model}")
                selected = bundle["selected_model"]
                features = telemetry_features(telemetry).reindex(
                    columns=bundle["feature_columns"]
                )
                features = _fill_missing_model_features(
                    features, bundle["models"][selected]
                )
                scores = security_scores(bundle["models"][selected], selected, features)
                threshold = float(bundle["thresholds"][selected])
                for position in (scores >= threshold).nonzero()[0]:
                    findings.append(
                        Finding(
                            rule_id=selected,
                            timestamp_sim_ns=int(telemetry.iloc[position]["sim_time_ns"]),
                            run_id=run_id,
                            source="anomaly_model",
                            severity="medium",
                            score=float(scores[position]),
                            threshold=threshold,
                            evidence={
                                "model": selected,
                                "anomaly_score": float(scores[position]),
                                "threshold": threshold,
                            },
                            what_this_does_not_prove="An anomaly score is not a probability or proof of unauthorized access.",
                            recommended_next_step="Review the evidence and verify the activity with the authorized system owner.",
                        )
                    )
            alerts = merge_alerts(findings)
            rendered = [
                json.dumps(alert.to_dict(), default=_json_default) for alert in alerts
            ]
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(
                    "".join(line + "\n" for line in rendered), encoding="utf-8"
                )
                print(f"Wrote {len(alerts)} advisory alerts to {args.output}")
            else:
                for line in rendered:
                    print(line)
        elif args.command == "monitor":
            if args.aligned is None and args.telemetry is None:
                raise ValueError("Provide at least one of --aligned or --telemetry.")
            if not args.inventory.is_file():
                raise FileNotFoundError(f"Inventory was not found: {args.inventory}")
            inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
            aligned = (
                pd.read_csv(args.aligned) if args.aligned is not None else None
            )
            telemetry = (
                pd.read_csv(args.telemetry) if args.telemetry is not None else None
            )
            manifest = (
                json.loads(args.manifest.read_text(encoding="utf-8"))
                if args.manifest is not None
                else None
            )
            join_points_ns = (
                manifest.get("join_points_sim_ns", [])
                if isinstance(manifest, dict)
                else []
            )
            if not isinstance(join_points_ns, list) or not all(
                isinstance(value, int) for value in join_points_ns
            ):
                raise ValueError("Manifest join_points_sim_ns must be a list of integers.")
            for model_path in (args.model, args.security_model):
                if not model_path.is_file():
                    raise FileNotFoundError(f"Saved detector bundle was not found: {model_path}")
            result = monitor_frames(
                aligned=aligned,
                telemetry=telemetry,
                inventory=inventory,
                noise_bundle=joblib.load(args.model),
                security_bundle=joblib.load(args.security_model),
                manifest=manifest,
                join_points_ns=join_points_ns,
                reset_at_joins=args.reset_state_at_joins,
                allow_draft_inventory_for_offline_eval=(
                    args.allow_draft_inventory_for_offline_eval
                ),
                offline_demo=args.offline_demo,
                profile=args.profile,
                v2_config=(
                    json.loads(args.v2_config.read_text(encoding="utf-8"))
                    if args.profile == "v2" and args.v2_config.is_file()
                    else None
                ),
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                "".join(
                    json.dumps(incident, default=_json_default) + "\n"
                    for incident in result.incidents
                ),
                encoding="utf-8",
            )
            for warning in result.warnings:
                print(warning, file=sys.stderr)
            if not all(result.coverage.values()):
                print(
                    "WARNING: Reduced detector coverage: "
                    + json.dumps(result.coverage, sort_keys=True),
                    file=sys.stderr,
                )
            if result.draft_override_used:
                print(
                    "WARNING: DRAFT INVENTORY OVERRIDE ENABLED; offline evaluation only.",
                    file=sys.stderr,
                )
            print(f"Wrote {len(result.incidents)} advisory incidents to {args.output}")
        elif args.command == "build-blind-streams":
            result = build_blind_streams(
                args.data_root,
                args.output_dir,
                attack_seed=args.attack_seed,
            )
            print(
                json.dumps(
                    {
                        stream_id: {
                            "duration_s": summary["duration_s"],
                            "normal_seconds": summary["normal_seconds"],
                            "attack_seconds": summary["attack_seconds"],
                            "attack_prevalence": summary["attack_prevalence"],
                            "segments": len(summary["segments"]),
                        }
                        for stream_id, summary in result.items()
                    },
                    indent=2,
                )
            )
        elif args.command == "evaluate-blind-streams":
            result = evaluate_blind_streams(
                args.stream_dir,
                args.inventory,
                args.report_dir,
                noise_model_path=args.model,
                security_model_path=args.security_model,
                allow_draft_inventory_for_offline_eval=(
                    args.allow_draft_inventory_for_offline_eval
                ),
            )
            print(
                json.dumps(
                    {
                        "streams": list(result["streams"]),
                        "draft_inventory_override": result["draft_inventory_override"],
                        "reports": [
                            str((args.report_dir / "blind_stream_evaluation.md").resolve()),
                            str((args.report_dir / "blind_stream_evaluation.json").resolve()),
                        ],
                    },
                    indent=2,
                )
            )
        elif args.command == "blind-robustness":
            result = run_robustness_stress_tests(
                args.stream_dir,
                args.inventory,
                args.report_dir,
                noise_model_path=args.model,
                security_model_path=args.security_model,
                allow_draft_inventory_for_offline_eval=(
                    args.allow_draft_inventory_for_offline_eval
                ),
            )
            print(
                json.dumps(
                    {
                        "cases": [
                            {
                                "scenario": item["scenario"],
                                "incidents": item["incident_count"],
                                "health": item["health_incident_count"],
                                "non_health": item["non_health_incident_count"],
                            }
                            for item in result["cases"]
                        ],
                        "report": str((args.report_dir / "blind_robustness.md").resolve()),
                    },
                    indent=2,
                )
            )
        elif args.command == "leave-one-class-out":
            result = run_leave_one_class_out(
                args.data_root,
                args.inventory,
                args.model_dir,
                args.report_dir,
                random_state=args.random_state,
                allow_draft_inventory_for_offline_eval=(
                    args.allow_draft_inventory_for_offline_eval
                ),
            )
            print(
                json.dumps(
                    {
                        "results": result["results"],
                        "models_are_experiment_only": result[
                            "models_are_experiment_only"
                        ],
                        "report": str(
                            (args.report_dir / "leave_one_class_out.md").resolve()
                        ),
                    },
                    indent=2,
                )
            )
        return 0
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
