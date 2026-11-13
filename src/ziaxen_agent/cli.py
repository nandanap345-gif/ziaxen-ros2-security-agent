"""Command-line entry points for inspection, training, evaluation, and inference."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from .agent import SensorNoiseAgent
from .data import inspect_runs, load_runs
from .evaluation import evaluate_detector
from .training import train_detector


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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command in {"inspect", "train", "evaluate"} and not args.data_root:
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
        return 0
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
