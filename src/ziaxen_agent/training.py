"""Run-grouped training and validation for normal-vs-noise detection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .data import RunData, load_runs
from .features import engineer_features, sensor_columns
from .models import (
    anomaly_scores,
    build_candidates,
    choose_candidate,
    normal_reference,
    validation_threshold_metrics,
)


def _prepare(runs: list[RunData]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for run in runs:
        features = engineer_features(run.aligned)
        labels = run.aligned["is_attack_event"].to_numpy(dtype=np.int8)
        prepared.append(
            {
                "run": run,
                "features": features,
                "labels": labels,
                "seed": int(run.metadata["seed"]),
            }
        )
    return prepared


def train_detector(
    data_root: str | Path,
    model_path: str | Path,
    report_path: str | Path,
    random_state: int = 42,
) -> dict[str, Any]:
    """Select on seed 2, refit on seeds 1-2, and reserve seed 3 for evaluation."""
    runs = load_runs(data_root, expected_counts=True)
    prepared = _prepare(runs)
    train_runs = [item for item in prepared if item["seed"] == 1]
    validation_runs = [item for item in prepared if item["seed"] == 2]
    if not train_runs or not validation_runs:
        raise ValueError("Training requires complete seed-1 and seed-2 run groups.")

    feature_columns = list(train_runs[0]["features"].columns)
    for item in prepared:
        if list(item["features"].columns) != feature_columns:
            raise ValueError(f"{item['run'].run_id}: engineered feature schema differs.")
    x_train = pd.concat([item["features"] for item in train_runs], ignore_index=True)
    y_train = np.concatenate([item["labels"] for item in train_runs])
    x_validation = pd.concat(
        [item["features"] for item in validation_runs], ignore_index=True
    )
    y_validation = np.concatenate([item["labels"] for item in validation_runs])
    if set(np.unique(y_train)) != {0, 1} or set(np.unique(y_validation)) != {0, 1}:
        raise ValueError("Both normal and noise-labeled windows are required in each split.")

    candidates = build_candidates(random_state)
    train_normal = x_train.loc[y_train == 0]
    models = {
        "isolation_forest": candidates["isolation_forest"].fit(train_normal),
        "random_forest": candidates["random_forest"].fit(x_train, y_train),
    }
    validation_metrics: dict[str, dict[str, Any]] = {}
    thresholds: dict[str, float] = {}
    for name, model in models.items():
        scores = anomaly_scores(model, name, x_validation)
        threshold, metrics = validation_threshold_metrics(y_validation, scores)
        validation_metrics[name] = metrics
        thresholds[name] = threshold

    selected_name = choose_candidate(validation_metrics)

    final_training_runs = train_runs + validation_runs
    x_final = pd.concat([x_train, x_validation], ignore_index=True)
    y_final = np.concatenate([y_train, y_validation])
    final_candidates = build_candidates(random_state)
    models = {
        "isolation_forest": final_candidates["isolation_forest"].fit(
            x_final.loc[y_final == 0]
        ),
        "random_forest": final_candidates["random_forest"].fit(x_final, y_final),
    }
    normal_train_features = x_final.loc[y_final == 0]
    bundle = {
        "format_version": 1,
        "task": "normal_vs_sensor_noise",
        "selected_model": selected_name,
        "models": models,
        "thresholds": thresholds,
        "feature_columns": feature_columns,
        "raw_sensor_columns": sensor_columns(train_runs[0]["run"].aligned),
        "normal_reference": normal_reference(normal_train_features),
        "training_seeds": [1, 2],
        "candidate_fit_seeds": [1],
        "validation_seeds": [2],
        "threshold_source_fit_seeds": [1],
        "held_out_test_seeds": [3],
        "validation_metrics": validation_metrics,
        "random_state": random_state,
        "source_dataset": "AI_team_data/dataset_index.csv",
    }
    model_file = Path(model_path)
    model_file.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_file, compress=3)

    report = {
        "task": bundle["task"],
        "split": {
            "training_seeds": bundle["training_seeds"],
            "candidate_fit_seeds": bundle["candidate_fit_seeds"],
            "validation_seeds": bundle["validation_seeds"],
            "threshold_source_fit_seeds": bundle["threshold_source_fit_seeds"],
            "held_out_test_seeds": bundle["held_out_test_seeds"],
            "final_training_runs": len(final_training_runs),
            "candidate_fit_runs": len(train_runs),
            "validation_runs": len(validation_runs),
        },
        "candidate_validation_metrics": validation_metrics,
        "validation_metrics_describe": (
            "Candidate selection and threshold metrics are from models fit on seed 1, "
            "before the final refit on seeds 1 and 2."
        ),
        "selected_model": selected_name,
        "selected_threshold": thresholds[selected_name],
        "feature_count": len(feature_columns),
        "feature_columns": feature_columns,
        "model_path": str(model_file.resolve()),
    }
    report_file = Path(report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
