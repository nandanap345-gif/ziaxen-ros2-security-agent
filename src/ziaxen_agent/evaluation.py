"""Held-out run evaluation, scenario metrics, confusion matrix, and report files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import ConfusionMatrixDisplay

from .data import RunData, load_runs
from .features import engineer_features
from .models import anomaly_scores, binary_metrics


def _latency_seconds(run: RunData, predictions: np.ndarray) -> float | None:
    if run.events.empty:
        return None
    event_names = run.events["event"].astype(str).str.lower()
    starts = run.events.loc[event_names.eq("start"), "sim_time_ns"]
    stops = run.events.loc[event_names.eq("stop"), "sim_time_ns"]
    if starts.empty or stops.empty:
        return None
    start_seconds = float(pd.to_numeric(starts.min(), errors="raise")) / 1e9
    stop_seconds = float(pd.to_numeric(stops.max(), errors="raise")) / 1e9
    time_seconds = pd.to_numeric(run.aligned["sim_time_s"], errors="coerce").to_numpy()
    alerted_after_start = time_seconds[
        (predictions == 1)
        & (time_seconds >= start_seconds)
        & (time_seconds < stop_seconds)
    ]
    if not len(alerted_after_start):
        return None
    return float(alerted_after_start.min() - start_seconds)


def _evaluate_model(
    model_name: str,
    model: Any,
    threshold: float,
    runs: list[RunData],
) -> tuple[dict[str, Any], pd.DataFrame, list[dict[str, Any]]]:
    labels_all: list[np.ndarray] = []
    predictions_all: list[np.ndarray] = []
    scores_all: list[np.ndarray] = []
    prediction_frames: list[pd.DataFrame] = []
    run_metrics: list[dict[str, Any]] = []
    for run in runs:
        features = engineer_features(run.aligned)
        scores = anomaly_scores(model, model_name, features)
        labels = run.aligned["is_attack_event"].to_numpy(dtype=np.int8)
        predictions = (scores >= threshold).astype(np.int8)
        labels_all.append(labels)
        predictions_all.append(predictions)
        scores_all.append(scores)
        prediction_frames.append(
            pd.DataFrame(
                {
                    "run_id": run.run_id,
                    "relative_path": run.relative_path,
                    "type": run.metadata["type"],
                    "attack_name": run.metadata["attack_name"],
                    "npc": run.metadata["npc"],
                    "seed": run.metadata["seed"],
                    "level": run.metadata["level"],
                    "sim_time_ns": run.aligned["sim_time_ns"],
                    "sim_time_s": run.aligned["sim_time_s"],
                    "event_label": labels,
                    "anomaly_score": scores,
                    "predicted_anomaly": predictions,
                    "attack_type": run.aligned.get("attack_type", "none"),
                    "attack_target": run.aligned.get("attack_target", "none"),
                    "attack_id": run.aligned.get("attack_id", "none"),
                }
            )
        )
        latency = _latency_seconds(run, predictions)
        run_metrics.append(
            {
                "run_id": run.run_id,
                "relative_path": run.relative_path,
                "type": run.metadata["type"],
                "attack_name": run.metadata["attack_name"],
                "npc": int(run.metadata["npc"]),
                "seed": int(run.metadata["seed"]),
                "level": int(run.metadata["level"]),
                "attack_start_s": float(
                    run.events.loc[
                        run.events["event"].astype(str).str.lower().eq("start"),
                        "sim_time_ns",
                    ].min()
                )
                / 1e9
                if not run.events.empty
                else None,
                "detection_latency_s": latency,
                "detected": latency is not None,
            }
        )

    labels_joined = np.concatenate(labels_all)
    predictions_joined = np.concatenate(predictions_all)
    scores_joined = np.concatenate(scores_all)
    metrics = binary_metrics(
        labels_joined, predictions_joined, scores_joined, threshold
    )
    detected_latencies = [
        row["detection_latency_s"]
        for row in run_metrics
        if row["detection_latency_s"] is not None
    ]
    attack_runs = [row for row in run_metrics if row["type"] == "attack"]
    metrics["attack_runs"] = len(attack_runs)
    metrics["attack_runs_detected"] = sum(row["detected"] for row in attack_runs)
    metrics["attack_runs_missed"] = len(attack_runs) - metrics["attack_runs_detected"]
    metrics["detection_latency_s"] = {
        "median_detected_runs": float(np.median(detected_latencies))
        if detected_latencies
        else None,
        "mean_detected_runs": float(np.mean(detected_latencies))
        if detected_latencies
        else None,
        "detected_run_count": len(detected_latencies),
        "interpretation": (
            "Time from event start to first predicted alert at or after start; "
            "missed runs are excluded from mean/median."
        ),
    }
    frame = pd.concat(prediction_frames, ignore_index=True)
    return metrics, frame, run_metrics


def evaluate_detector(
    data_root: str | Path,
    model_path: str | Path,
    report_dir: str | Path,
) -> dict[str, Any]:
    """Evaluate every saved candidate on seed-3 runs, without fitting or tuning."""
    bundle = joblib.load(model_path)
    runs = load_runs(data_root, seeds={3}, expected_counts=True)
    candidate_results: dict[str, Any] = {}
    prediction_frames: dict[str, pd.DataFrame] = {}
    per_run: dict[str, list[dict[str, Any]]] = {}
    for model_name, model in bundle["models"].items():
        metrics, frame, run_metrics = _evaluate_model(
            model_name, model, bundle["thresholds"][model_name], runs
        )
        candidate_results[model_name] = metrics
        prediction_frames[model_name] = frame
        per_run[model_name] = run_metrics

    selected = bundle["selected_model"]
    selected_frame = prediction_frames[selected]
    selected_runs = per_run[selected]
    grouped = (
        selected_frame.loc[selected_frame["type"].eq("attack")]
        .groupby(["level", "npc"], dropna=False)
        .apply(
            lambda group: _group_metrics(group),
            include_groups=False,
        )
        .reset_index()
    )

    destination = Path(report_dir)
    destination.mkdir(parents=True, exist_ok=True)
    selected_frame.to_csv(destination / "predictions.csv", index=False)
    pd.DataFrame(selected_runs).to_csv(destination / "scenario_metrics.csv", index=False)
    grouped.to_csv(destination / "noise_level_metrics.csv", index=False)

    matrix = np.asarray(candidate_results[selected]["confusion_matrix"])
    display = ConfusionMatrixDisplay(
        confusion_matrix=matrix, display_labels=["Normal", "Noise"]
    )
    display.plot(cmap="Blues", values_format="d", colorbar=False)
    plt.title(f"Held-out seed 3: {selected.replace('_', ' ').title()}")
    plt.tight_layout()
    plt.savefig(destination / "confusion_matrix.png", dpi=160)
    plt.close()

    report = {
        "task": bundle["task"],
        "dataset_scope": {
            "test_seed": 3,
            "test_runs": len(runs),
            "normal_runs": sum(run.metadata["type"] == "normal" for run in runs),
            "noise_runs": sum(run.metadata["attack_name"] == "noise" for run in runs),
            "labels_source": "events.csv start/stop intervals",
            "final_model_training_seeds": bundle.get("training_seeds"),
            "threshold_selection_seed": bundle.get("validation_seeds"),
        },
        "selected_model": selected,
        "candidate_metrics": candidate_results,
        "selected_scenario_metrics": selected_runs,
        "noise_level_npc_metrics": grouped.to_dict(orient="records"),
        "files": {
            "confusion_matrix": str((destination / "confusion_matrix.png").resolve()),
            "predictions": str((destination / "predictions.csv").resolve()),
            "scenario_metrics": str((destination / "scenario_metrics.csv").resolve()),
            "noise_level_metrics": str((destination / "noise_level_metrics.csv").resolve()),
        },
        "limitations": [
            "Results apply only to normal-versus-simulated-sensor-noise detection.",
            "The detector has not been validated on real vehicle data.",
            "The supplied simulator sensors are documented as idealized and noise-free.",
            "The ego vehicle is driven by an in-simulation callback, not ROS/CAN.",
        ],
    }
    (destination / "evaluation_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    metrics = candidate_results[selected]
    latency = metrics["detection_latency_s"]
    median_latency = latency["median_detected_runs"]
    latency_text = f"{median_latency:.4f} s" if median_latency is not None else "not measurable"
    markdown = [
        "# Held-out evaluation report",
        "",
        f"- **Task:** {bundle['task']}",
        f"- **Selected model:** {selected}",
        "- **Test split:** all normal/noise runs with seed 3 (run-grouped; no row shuffle)",
        f"- **Test runs:** {len(runs)} ({report['dataset_scope']['normal_runs']} normal, "
        f"{report['dataset_scope']['noise_runs']} noise)",
        f"- **Final model fit:** seeds {bundle.get('training_seeds')}",
        f"- **Model/threshold selection:** seed {bundle.get('validation_seeds')} "
        "(using candidate models initially fit on seed "
        f"{bundle.get('candidate_fit_seeds')})",
        "- **Labels:** derived from `events.csv` start/stop intervals",
        "",
        "## Candidate comparison",
        "",
        "| Model | Accuracy | Precision | Recall | F1 | False-positive rate | Threshold |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, result in candidate_results.items():
        markdown.append(
            f"| {name} | {result['accuracy']:.4f} | {result['precision']:.4f} | "
            f"{result['recall']:.4f} | "
            f"{result['f1']:.4f} | {result['false_positive_rate']:.4f} | "
            f"{result['threshold']:.6g} |"
        )
    markdown.extend(
        [
            "",
            "## Selected-model metrics",
            "",
            f"- Confusion matrix (rows=actual [normal, noise], columns=predicted): "
            f"`{metrics['confusion_matrix']}`",
            f"- Accuracy: {metrics['accuracy']:.4%}",
            f"- Average precision: {metrics['average_precision']:.4f}",
            f"- False positives: {metrics['false_positive']}",
            f"- False negatives: {metrics['false_negative']}",
            f"- Detected noise runs: {metrics['attack_runs_detected']}/{metrics['attack_runs']}",
            f"- Missed noise runs: {metrics['attack_runs_missed']}",
            f"- Median detection latency on detected runs: {latency_text}",
            "",
            "## Performance by noise level and NPC count",
            "",
            "| Level | NPCs | Precision | Recall | F1 | False-positive rate | Rows |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in report["noise_level_npc_metrics"]:
        markdown.append(
            f"| L{int(row['level'])} | {int(row['npc'])} | "
            f"{row['precision']:.4f} | {row['recall']:.4f} | {row['f1']:.4f} | "
            f"{row['false_positive_rate']:.4f} | {int(row['rows'])} |"
        )
    markdown.extend(
        [
            "",
            "## Caveats",
            "",
            *[f"- {limitation}" for limitation in report["limitations"]],
            "",
            "The output `confusion_matrix.png`, `predictions.csv`, "
            "`scenario_metrics.csv`, and `noise_level_metrics.csv` accompany this report.",
        ]
    )
    (destination / "evaluation_report.md").write_text(
        "\n".join(markdown) + "\n", encoding="utf-8"
    )
    return report


def _group_metrics(group: pd.DataFrame) -> pd.Series:
    labels = group["event_label"].to_numpy(dtype=np.int8)
    predictions = group["predicted_anomaly"].to_numpy(dtype=np.int8)
    true_positive = int(((labels == 1) & (predictions == 1)).sum())
    false_positive = int(((labels == 0) & (predictions == 1)).sum())
    false_negative = int(((labels == 1) & (predictions == 0)).sum())
    true_negative = int(((labels == 0) & (predictions == 0)).sum())
    precision = true_positive / max(1, true_positive + false_positive)
    recall = true_positive / max(1, true_positive + false_negative)
    return pd.Series(
        {
            "rows": len(group),
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / max(1e-12, precision + recall),
            "false_positive_rate": false_positive / max(1, false_positive + true_negative),
        }
    )
