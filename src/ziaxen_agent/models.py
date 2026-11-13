"""Model construction, validation thresholds, metrics, and explanations."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler


def build_candidates(random_state: int = 42) -> dict[str, Pipeline]:
    """Build an unsupervised normal-only baseline and a supervised comparator."""
    return {
        "isolation_forest": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                ("scaler", RobustScaler()),
                (
                    "detector",
                    IsolationForest(
                        n_estimators=200,
                        contamination="auto",
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                (
                    "detector",
                    RandomForestClassifier(
                        n_estimators=240,
                        min_samples_leaf=2,
                        class_weight="balanced_subsample",
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
    }


def anomaly_scores(model: Pipeline, name: str, features: pd.DataFrame) -> np.ndarray:
    """Return scores where larger values always mean more anomalous."""
    if name == "isolation_forest":
        transformed = model[:-1].transform(features)
        return -model.named_steps["detector"].decision_function(transformed)
    if name == "random_forest":
        return model.predict_proba(features)[:, 1]
    raise ValueError(f"Unsupported model name: {name}")


def select_threshold(labels: np.ndarray, scores: np.ndarray) -> float:
    """Choose the validation threshold with the highest F1 score."""
    precision, recall, thresholds = precision_recall_curve(labels, scores)
    if len(thresholds) == 0:
        return float(np.nextafter(float(scores[0]), -np.inf))
    f1_values = 2 * precision[:-1] * recall[:-1] / (
        precision[:-1] + recall[:-1] + 1e-12
    )
    best = int(np.nanargmax(f1_values))
    return float(thresholds[best])


def binary_metrics(labels: np.ndarray, predictions: np.ndarray, scores: np.ndarray,
                   threshold: float) -> dict[str, Any]:
    """Compute required binary metrics and the confusion matrix."""
    matrix = confusion_matrix(labels, predictions, labels=[0, 1])
    tn, fp, fn, tp = (int(value) for value in matrix.ravel())
    negatives = tn + fp
    return {
        "accuracy": float((tn + tp) / len(labels)) if len(labels) else 0.0,
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "false_positive_rate": float(fp / negatives) if negatives else 0.0,
        "average_precision": float(average_precision_score(labels, scores)),
        "threshold": float(threshold),
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "true_positive": tp,
        "rows": int(len(labels)),
    }


def choose_candidate(validation_metrics: dict[str, dict[str, Any]]) -> str:
    """Choose by validation F1, then validation false-positive rate."""
    return max(
        validation_metrics,
        key=lambda name: (
            validation_metrics[name]["f1"],
            -validation_metrics[name]["false_positive_rate"],
        ),
    )


def normal_reference(features: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Compute robust normal medians and scales for human-readable alert context."""
    medians = features.median(axis=0)
    lower = features.quantile(0.25)
    upper = features.quantile(0.75)
    scales = (upper - lower).replace(0, np.nan).fillna(1.0)
    scales = scales.replace([np.inf, -np.inf], 1.0).fillna(1.0)
    return {
        "median": {str(key): float(value) for key, value in medians.items()},
        "scale": {str(key): float(value) for key, value in scales.items()},
    }


def explain_row(
    row: pd.Series,
    reference: dict[str, dict[str, float]],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Rank feature deviations against the training normal reference."""
    details: list[dict[str, Any]] = []
    for feature, raw_value in row.items():
        if pd.isna(raw_value):
            continue
        center = reference["median"].get(feature)
        scale = reference["scale"].get(feature)
        if center is None or scale is None:
            continue
        deviation = abs(float(raw_value) - center) / max(scale, 1e-9)
        if deviation == 0:
            continue
        _, feature_name = feature.split("::", 1)
        sensor = feature_name.split(".", 1)[0]
        details.append(
            {
                "feature": feature,
                "sensor": sensor,
                "robust_deviation": float(deviation),
            }
        )
    details.sort(key=lambda item: item["robust_deviation"], reverse=True)
    return details[:limit]


def validation_threshold_metrics(
    labels: np.ndarray, scores: np.ndarray
) -> tuple[float, dict[str, Any]]:
    threshold = select_threshold(labels, scores)
    predictions = (scores >= threshold).astype(np.int8)
    return threshold, binary_metrics(labels, predictions, scores, threshold)
