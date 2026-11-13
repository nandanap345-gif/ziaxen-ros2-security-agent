"""Focused tests for event labels, features, and inference input validation."""

import numpy as np
import pandas as pd
import pytest

from ziaxen_agent.agent import SensorNoiseAgent
from ziaxen_agent.data import event_labels
from ziaxen_agent.features import engineer_features
from ziaxen_agent.models import binary_metrics


def test_event_labels_use_start_inclusive_stop_exclusive_interval():
    aligned = pd.DataFrame({"sim_time_ns": [99, 100, 199, 200]})
    events = pd.DataFrame(
        {
            "sim_time_ns": [100, 200],
            "event": ["start", "stop"],
            "attack_id": ["a", "a"],
            "attack_type": ["noise", "noise"],
        }
    )
    assert event_labels(aligned, events).tolist() == [0, 1, 1, 0]


def test_features_include_causal_changes_and_temporal_variability():
    frame = pd.DataFrame(
        {
            "sim_time_s": np.arange(30) * 0.02,
            "imu.linear_acceleration.x": np.arange(30, dtype=float),
            "is_attack": np.zeros(30, dtype=int),
        }
    )
    features = engineer_features(frame)
    assert "raw::imu.linear_acceleration.x" in features
    assert "rate::imu.linear_acceleration.x" in features
    assert "rolling_std::imu.linear_acceleration.x" in features
    assert features.iloc[-1]["rate::imu.linear_acceleration.x"] == pytest.approx(50.0)


def test_agent_rejects_missing_time_and_sensor_inputs():
    bundle = {
        "task": "normal_vs_sensor_noise",
        "selected_model": "random_forest",
        "models": {"random_forest": object()},
        "thresholds": {"random_forest": 0.5},
        "raw_sensor_columns": ["imu.angular_velocity.x"],
        "feature_columns": [],
        "normal_reference": {"median": {}, "scale": {}},
    }
    agent = SensorNoiseAgent(bundle)
    with pytest.raises(ValueError, match="sim_time_s or sim_time_ns"):
        agent.predict(pd.DataFrame({"imu.angular_velocity.x": [0.0]}))
    with pytest.raises(ValueError, match="at least one numeric"):
        agent.predict(pd.DataFrame({"sim_time_s": [0.0]}))


def test_binary_metrics_reports_accuracy_from_confusion_matrix():
    labels = np.array([0, 0, 1, 1])
    predictions = np.array([0, 1, 1, 1])
    scores = np.array([0.1, 0.7, 0.8, 0.9])
    metrics = binary_metrics(labels, predictions, scores, threshold=0.5)
    assert metrics["accuracy"] == pytest.approx(0.75)
    assert metrics["confusion_matrix"] == [[1, 1], [0, 2]]
