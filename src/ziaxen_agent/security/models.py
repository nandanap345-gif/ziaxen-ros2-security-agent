"""Normal-only and supervised telemetry anomaly models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import f1_score, precision_recall_curve
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

from .data import SecurityRun, load_security_runs
from .telemetry import telemetry_features


USABLE_CLASSES = {
    "flood",
    "spoof",
    "unauthorized_node",
    "unauthorized_subscription",
}


def _pipeline(model_name: str, random_state: int) -> Pipeline:
    steps: list[tuple[str, Any]] = [
        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True))
    ]
    if model_name == "isolation_forest":
        steps.append(("scaler", RobustScaler()))
        steps.append(
            (
                "detector",
                IsolationForest(
                    n_estimators=200,
                    contamination="auto",
                    random_state=random_state,
                    n_jobs=-1,
                ),
            )
        )
    elif model_name == "random_forest":
        steps.append(
            (
                "detector",
                RandomForestClassifier(
                    n_estimators=240,
                    min_samples_leaf=2,
                    class_weight="balanced_subsample",
                    random_state=random_state,
                    n_jobs=-1,
                ),
            )
        )
    else:
        raise ValueError(f"Unsupported security model: {model_name}")
    return Pipeline(steps)


def _scores(model: Pipeline, name: str, features: pd.DataFrame) -> np.ndarray:
    if name == "isolation_forest":
        transformed = model[:-1].transform(features)
        return -model.named_steps["detector"].decision_function(transformed)
    if name == "random_forest":
        return model.predict_proba(features)[:, 1]
    raise ValueError(f"Unsupported security model: {name}")


def _threshold(labels: np.ndarray, scores: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(labels, scores)
    if not len(thresholds):
        return float(np.nextafter(float(scores[0]), -np.inf))
    f1 = 2 * precision[:-1] * recall[:-1] / (
        precision[:-1] + recall[:-1] + 1e-12
    )
    return float(thresholds[int(np.nanargmax(f1))])


def _prepare(runs: list[SecurityRun]) -> list[dict[str, Any]]:
    return [
        {
            "run": run,
            "features": telemetry_features(run.telemetry),
            "labels": run.labels.to_numpy(dtype=np.int8),
        }
        for run in runs
        if run.run_type == "normal" or run.attack_name in USABLE_CLASSES
    ]


def train_security_detector(
    data_root: str | Path,
    model_path: str | Path,
    report_path: str | Path,
    *,
    random_state: int = 42,
) -> dict[str, Any]:
    """Select on seed 2, refit on seeds 1-2, and reserve seed 3."""
    runs = load_security_runs(data_root, seeds={1, 2})
    prepared = _prepare(runs)
    train = [item for item in prepared if item["run"].seed == 1]
    validation = [item for item in prepared if item["run"].seed == 2]
    if not train or not validation:
        raise ValueError("Security training requires complete seed-1 and seed-2 groups.")
    columns = list(train[0]["features"].columns)
    for item in prepared:
        if list(item["features"].columns) != columns:
            raise ValueError(f"{item['run'].run_id}: telemetry feature schema differs.")
    x_train = pd.concat([item["features"] for item in train], ignore_index=True)
    y_train = np.concatenate([item["labels"] for item in train])
    x_validation = pd.concat([item["features"] for item in validation], ignore_index=True)
    y_validation = np.concatenate([item["labels"] for item in validation])
    if set(np.unique(y_train)) != {0, 1} or set(np.unique(y_validation)) != {0, 1}:
        raise ValueError("Security training and validation require normal and attack rows.")

    candidates = {
        "isolation_forest": _pipeline("isolation_forest", random_state).fit(
            x_train.loc[y_train == 0]
        ),
        "random_forest": _pipeline("random_forest", random_state).fit(x_train, y_train),
    }
    metrics: dict[str, dict[str, float]] = {}
    thresholds: dict[str, float] = {}
    for name, model in candidates.items():
        scores = _scores(model, name, x_validation)
        threshold = _threshold(y_validation, scores)
        predictions = (scores >= threshold).astype(np.int8)
        thresholds[name] = threshold
        metrics[name] = {
            "f1": float(f1_score(y_validation, predictions, zero_division=0)),
            "threshold": threshold,
        }
    selected = max(
        metrics,
        key=lambda name: (metrics[name]["f1"], name == "random_forest"),
    )

    fit_runs = [item for item in prepared if item["run"].seed in {1, 2}]
    x_final = pd.concat([item["features"] for item in fit_runs], ignore_index=True)
    y_final = np.concatenate([item["labels"] for item in fit_runs])
    models = {
        "isolation_forest": _pipeline("isolation_forest", random_state).fit(
            x_final.loc[y_final == 0]
        ),
        "random_forest": _pipeline("random_forest", random_state).fit(x_final, y_final),
    }
    bundle = {
        "format_version": 1,
        "task": "ros2_telemetry_security_anomaly",
        "selected_model": selected,
        "models": models,
        "thresholds": thresholds,
        "feature_columns": columns,
        "training_seeds": [1, 2],
        "candidate_fit_seeds": [1],
        "validation_seeds": [2],
        "held_out_test_seeds": [3],
        "trained_attack_classes": sorted(USABLE_CLASSES),
        "random_state": random_state,
        "label_source": "events.csv start-inclusive, stop-exclusive intervals",
        "source_dataset": "AI_team_data/dataset_index.csv",
    }
    model_file = Path(model_path)
    model_file.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_file, compress=3)
    report = {
        "task": bundle["task"],
        "selected_model": selected,
        "candidate_validation_metrics": metrics,
        "split": {
            "candidate_fit_runs_seed1": sum(item["run"].seed == 1 for item in train),
            "validation_runs_seed2": len(validation),
            "final_fit_runs_seeds1_2": len(fit_runs),
            "test_seed3_reserved": True,
            "training_seeds": bundle["training_seeds"],
            "validation_seeds": bundle["validation_seeds"],
            "test_seeds": bundle["held_out_test_seeds"],
        },
        "trained_attack_classes": bundle["trained_attack_classes"],
        "feature_count": len(columns),
        "model_path": model_file.name,
    }
    report_file = Path(report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def security_scores(
    model: Pipeline, model_name: str, features: pd.DataFrame
) -> np.ndarray:
    return _scores(model, model_name, features)
