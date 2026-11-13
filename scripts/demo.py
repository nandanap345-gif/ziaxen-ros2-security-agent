"""Presentation-friendly demonstration using the saved sensor-noise model."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from ziaxen_agent.agent import SensorNoiseAgent


DEFAULT_NORMAL_FILE = Path(
    "normal_data/normal_npc10_seed3/aligned.csv.gz"
)
DEFAULT_NOISE_FILE = Path(
    "abnormal_data/01_noise/noise_L1_npc10_seed3/aligned.csv.gz"
)
DEFAULT_MODEL = PROJECT_ROOT / "models" / "noise_detector.joblib"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare one normal and one noise recording with the saved model."
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        required=True,
        help="Dataset folder containing normal_data and abnormal_data.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL,
        help=f"Saved model path (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--normal-file",
        type=Path,
        default=DEFAULT_NORMAL_FILE,
        help=f"Normal dataset file relative to --data-root (default: {DEFAULT_NORMAL_FILE}).",
    )
    parser.add_argument(
        "--noise-file",
        type=Path,
        default=DEFAULT_NOISE_FILE,
        help=f"Noise dataset file relative to --data-root (default: {DEFAULT_NOISE_FILE}).",
    )
    return parser.parse_args()


def summarize(
    agent: SensorNoiseAgent, data_root: Path, relative_file: Path
) -> dict[str, Any]:
    path = (data_root / relative_file).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Dataset file was not found: {path}")

    results = agent.predict_file(path)
    if not results:
        raise ValueError(f"Dataset file contains no rows: {path}")

    peak = max(results, key=lambda row: row["anomaly_score"])
    alert_count = sum(bool(row["anomaly"]) for row in results)
    return {
        "dataset_name": relative_file.as_posix(),
        "class": "NOISE ANOMALY" if alert_count else "NORMAL",
        "peak_score": float(peak["anomaly_score"]),
        "threshold": float(agent.threshold),
        "rows": len(results),
        "alert_rows": alert_count,
        "peak_timestamp": peak["timestamp"],
        "timestamp_unit": peak["timestamp_unit"],
    }


def print_result(result: dict[str, Any]) -> None:
    print(f"Dataset:          {result['dataset_name']}")
    print(f"Predicted class:  {result['class']}")
    print(f"Peak anomaly score: {result['peak_score']:.4f}")
    print(f"Alert threshold:  {result['threshold']:.4f}")
    print(f"Alert rows:       {result['alert_rows']} / {result['rows']}")
    print(
        f"Peak score time:  {result['peak_timestamp']} "
        f"{result['timestamp_unit']}"
    )


def main() -> int:
    args = parse_args()
    try:
        agent = SensorNoiseAgent.load(args.model)
        if agent.model_name != "random_forest":
            raise ValueError(
                f"Expected the saved Random Forest model, got {agent.model_name!r}."
            )

        data_root = args.data_root.expanduser().resolve()
        normal = summarize(agent, data_root, args.normal_file)
        noise = summarize(agent, data_root, args.noise_file)

        print("Ziaxen Sensor-Noise Model Demo")
        print(f"Model: {agent.model_name.replace('_', ' ').title()}")
        print(f"Alert threshold: {agent.threshold:.4f}")
        print("\n--- Normal recording ---")
        print_result(normal)
        print("\n--- Noise-affected recording ---")
        print_result(noise)
        print("\n--- Comparison ---")
        print(
            f"Normal input: {normal['class']} "
            f"(peak score {normal['peak_score']:.4f})"
        )
        print(
            f"Noise input:  {noise['class']} "
            f"(peak score {noise['peak_score']:.4f})"
        )
        if normal["class"] == "NORMAL" and noise["class"] == "NOISE ANOMALY":
            print("Demo result:  The model distinguished the two recordings.")
        else:
            print("Demo result:  Review the predictions; the expected contrast was not observed.")
        return 0
    except (FileNotFoundError, ValueError, OSError) as error:
        print(f"Demo error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
