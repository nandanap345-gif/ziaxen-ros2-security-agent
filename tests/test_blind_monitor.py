import json
from types import SimpleNamespace

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.impute import SimpleImputer

from ziaxen_agent import monitor
from ziaxen_agent.cli import main
from ziaxen_agent.security.telemetry import telemetry_features


def _inventory(status="approved"):
    return {
        "version": 1,
        "approval_status": status,
        "ros_distro": "humble",
        "rmw": "rmw_fastrtps_cpp",
        "domain_ids": [0],
        "discovery": {"mode": "simple", "server": None},
        "bridges": [],
        "nodes": [{"name": "/allowed", "namespace": "/"}],
        "topics": [],
        "limits": {
            "startup_warmup_s": 0.0,
            "stale_tick_multiple": 3,
            "max_service_calls_per_window": None,
            "max_parameter_events_per_window": None,
        },
        "approved_change_windows": [],
    }


def _bundles():
    return (
        {
            "task": "normal_vs_sensor_noise",
            "selected_model": "random_forest",
            "models": {"random_forest": object()},
            "thresholds": {"random_forest": 0.5},
            "raw_sensor_columns": ["imu.linear_acceleration.x"],
            "feature_columns": [
                "raw::imu.linear_acceleration.x",
                "rate::imu.linear_acceleration.x",
                "rolling_std::imu.linear_acceleration.x",
            ],
            "normal_reference": {"median": {}, "scale": {}},
        },
        {
            "task": "ros2_telemetry_security_anomaly",
            "selected_model": "random_forest",
            "models": {"random_forest": object()},
            "thresholds": {"random_forest": 0.5},
            "feature_columns": [],
        },
    )


def _frames():
    times = np.arange(4, dtype=np.int64) * 20_000_000 + 20_000_000_000
    aligned = pd.DataFrame(
        {
            "sim_time_ns": times,
            "sim_time_s": times / 1e9,
            "imu.linear_acceleration.x": [0.0, 0.1, 0.0, 0.1],
            "is_attack": [0, 1, 1, 0],
            "attack_type": ["none", "spoof", "spoof", "none"],
            "attack_id": ["none", "a", "a", "none"],
            "run_id": ["secret-run"] * 4,
        }
    )
    telemetry = pd.DataFrame(
        {
            "sim_time_ns": times[::2],
            "sim_time_s": times[::2] / 1e9,
            "node_count": [1, 1],
            "node_list_hash": ["normal-hash", "normal-hash"],
            "new_nodes": ["", ""],
            "param_event_count": [0, 0],
            "is_attack": [0, 1],
            "attack_type": ["none", "spoof"],
            "run_id": ["secret-run"] * 2,
        }
    )
    return aligned, telemetry


def test_monitor_strips_labels_and_run_identity_before_all_detector_calls(monkeypatch):
    aligned, telemetry = _frames()
    noise_bundle, security_bundle = _bundles()
    observed = []
    real_engineer = monitor.engineer_features
    real_telemetry_features = monitor.telemetry_features
    real_evaluate_rules = monitor.evaluate_rules

    def assert_clean(frame, *args, **kwargs):
        assert not any(
            name in {"is_attack", "is_attack_event", "run_id"}
            or name.startswith("attack_")
            for name in frame.columns
        )
        observed.append("noise")
        return real_engineer(frame, *args, **kwargs)

    def assert_clean_telemetry(frame):
        assert not any(
            name in {"is_attack", "is_attack_event", "run_id"}
            or name.startswith("attack_")
            for name in frame.columns
        )
        observed.append("telemetry-model")
        return real_telemetry_features(frame)

    def assert_clean_rules(frame, *args, **kwargs):
        assert not any(
            name in {"is_attack", "is_attack_event", "run_id"}
            or name.startswith("attack_")
            for name in frame.columns
        )
        observed.append("rules")
        return real_evaluate_rules(frame, *args, **kwargs)

    monkeypatch.setattr(monitor, "engineer_features", assert_clean)
    monkeypatch.setattr(monitor, "telemetry_features", assert_clean_telemetry)
    monkeypatch.setattr(monitor, "evaluate_rules", assert_clean_rules)
    monkeypatch.setattr(
        monitor, "anomaly_scores", lambda model, name, features: np.zeros(len(features))
    )
    monkeypatch.setattr(
        monitor, "security_scores", lambda model, name, features: np.zeros(len(telemetry))
    )

    result = monitor.monitor_frames(
        aligned=aligned,
        telemetry=telemetry,
        inventory=_inventory(),
        noise_bundle=noise_bundle,
        security_bundle=security_bundle,
    )
    assert set(observed) == {"noise", "telemetry-model", "rules"}
    assert result.incidents == []


def test_monitor_merges_detectors_in_time_order_and_never_takes_action(monkeypatch):
    aligned, telemetry = _frames()
    noise_bundle, security_bundle = _bundles()
    monkeypatch.setattr(
        monitor, "anomaly_scores", lambda model, name, features: np.full(len(features), 0.9)
    )
    monkeypatch.setattr(
        monitor, "security_scores", lambda model, name, features: np.full(len(telemetry), 0.9)
    )
    result = monitor.monitor_frames(
        aligned=aligned,
        telemetry=telemetry,
        inventory=_inventory(),
        noise_bundle=noise_bundle,
        security_bundle=security_bundle,
    )
    assert result.incidents
    assert [item["start_sim_ns"] for item in result.incidents] == sorted(
        item["start_sim_ns"] for item in result.incidents
    )
    first = result.incidents[0]
    assert "sensor_noise_model" in first["detectors"]
    assert "telemetry_model" in first["detectors"]
    assert all(item["requires_human_approval"] is True for item in result.incidents)
    assert all(item["automatic_action_taken"] is False for item in result.incidents)


def test_monitor_requires_explicit_draft_override_and_marks_alerts(monkeypatch):
    aligned, telemetry = _frames()
    noise_bundle, security_bundle = _bundles()
    monkeypatch.setattr(
        monitor, "anomaly_scores", lambda model, name, features: np.full(len(features), 0.9)
    )
    monkeypatch.setattr(
        monitor, "security_scores", lambda model, name, features: np.zeros(len(telemetry))
    )
    with pytest.raises(ValueError, match="allow-draft-inventory-for-offline-eval"):
        monitor.monitor_frames(
            aligned=aligned,
            telemetry=telemetry,
            inventory=_inventory("draft"),
            noise_bundle=noise_bundle,
            security_bundle=security_bundle,
        )
    result = monitor.monitor_frames(
        aligned=aligned,
        telemetry=None,
        inventory=_inventory("draft"),
        noise_bundle=noise_bundle,
        security_bundle=security_bundle,
        allow_draft_inventory_for_offline_eval=True,
    )
    assert result.draft_override_used
    assert any("DRAFT INVENTORY OVERRIDE" in item["confidence_notes"] for item in result.incidents)
    assert any("DRAFT INVENTORY OVERRIDE" in warning for warning in result.warnings)
    assert any("telemetry input missing" in warning for warning in result.warnings)


@pytest.mark.parametrize(
    ("missing_input", "reduced_key"),
    [
        ("aligned", "sensor_noise_model"),
        ("telemetry", "telemetry_policy_rules"),
    ],
)
def test_monitor_cli_warns_and_reports_reduced_coverage(
    tmp_path, monkeypatch, capsys, missing_input, reduced_key
):
    aligned, telemetry = _frames()
    noise_bundle, security_bundle = _bundles()
    monkeypatch.setattr(
        monitor, "anomaly_scores", lambda model, name, features: np.zeros(len(features))
    )
    monkeypatch.setattr(
        monitor, "security_scores", lambda model, name, features: np.zeros(len(features))
    )

    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(json.dumps(_inventory()), encoding="utf-8")
    noise_path = tmp_path / "noise.joblib"
    security_path = tmp_path / "security.joblib"
    joblib.dump(noise_bundle, noise_path)
    joblib.dump(security_bundle, security_path)
    output_path = tmp_path / "alerts.jsonl"
    args = [
        "monitor",
        "--inventory",
        str(inventory_path),
        "--output",
        str(output_path),
        "--model",
        str(noise_path),
        "--security-model",
        str(security_path),
    ]
    if missing_input == "aligned":
        telemetry_path = tmp_path / "telemetry.csv"
        telemetry.to_csv(telemetry_path, index=False)
        args.extend(["--telemetry", str(telemetry_path)])
    else:
        aligned_path = tmp_path / "aligned.csv"
        aligned.to_csv(aligned_path, index=False)
        args.extend(["--aligned", str(aligned_path)])

    assert main(args) == 0
    captured = capsys.readouterr()
    assert f"{missing_input} input missing" in captured.err
    coverage_line = next(
        line
        for line in captured.err.splitlines()
        if line.startswith("WARNING: Reduced detector coverage: ")
    )
    coverage = json.loads(
        coverage_line.split("WARNING: Reduced detector coverage: ", 1)[1]
    )
    assert coverage[reduced_key] is False
    assert "Coverage is reduced" in captured.err
    assert output_path.is_file()


def test_monitor_can_disable_telemetry_model_without_scoring(monkeypatch):
    aligned, telemetry = _frames()
    noise_bundle, security_bundle = _bundles()
    monkeypatch.setattr(
        monitor, "anomaly_scores", lambda model, name, features: np.zeros(len(features))
    )
    monkeypatch.setattr(
        monitor,
        "security_scores",
        lambda *args, **kwargs: pytest.fail("Telemetry model was scored during ablation."),
    )

    result = monitor.monitor_frames(
        aligned=aligned,
        telemetry=telemetry,
        inventory=_inventory(),
        noise_bundle=noise_bundle,
        security_bundle=security_bundle,
        include_telemetry_model=False,
    )

    assert result.coverage == {
        "sensor_noise_model": True,
        "telemetry_policy_rules": True,
        "telemetry_model": False,
    }
    assert any("disabled for ablation" in warning for warning in result.warnings)
    assert all(finding.source != "telemetry_model" for finding in result.findings)


def test_monitor_resets_rolling_state_at_join_points(monkeypatch):
    aligned, telemetry = _frames()
    noise_bundle, security_bundle = _bundles()
    calls = []
    rule_calls = []
    real_engineer = monitor.engineer_features
    real_evaluate_rules = monitor.evaluate_rules

    def record_calls(frame, *args, **kwargs):
        calls.append(len(frame))
        return real_engineer(frame, *args, **kwargs)

    def record_rule_calls(frame, *args, **kwargs):
        rule_calls.append(len(frame))
        return real_evaluate_rules(frame, *args, **kwargs)

    monkeypatch.setattr(monitor, "engineer_features", record_calls)
    monkeypatch.setattr(monitor, "evaluate_rules", record_rule_calls)
    monkeypatch.setattr(
        monitor, "anomaly_scores", lambda model, name, features: np.zeros(len(features))
    )
    monkeypatch.setattr(
        monitor, "security_scores", lambda model, name, features: np.zeros(len(telemetry))
    )
    monitor.monitor_frames(
        aligned=aligned,
        telemetry=telemetry,
        inventory=_inventory(),
        noise_bundle=noise_bundle,
        security_bundle=security_bundle,
        join_points_ns=[20_040_000_000],
        reset_at_joins=True,
    )
    assert calls == [2, 2]
    assert rule_calls == [1, 1]


def test_monitor_imputes_nan_features_before_model_scoring(monkeypatch):
    aligned, telemetry = _frames()
    telemetry["node_count"] = np.nan
    baseline_features = telemetry_features(_frames()[1])
    imputer = SimpleImputer(strategy="median", keep_empty_features=True).fit(
        baseline_features.fillna(0.0)
    )
    security_bundle = {
        "task": "ros2_telemetry_security_anomaly",
        "selected_model": "random_forest",
        "models": {"random_forest": SimpleNamespace(named_steps={"imputer": imputer})},
        "thresholds": {"random_forest": 0.5},
        "feature_columns": list(baseline_features.columns),
    }
    received = []

    def assert_finite(model, name, features):
        assert np.isfinite(features.to_numpy(dtype=float)).all()
        received.append(True)
        return np.zeros(len(features))

    monkeypatch.setattr(monitor, "security_scores", assert_finite)
    monkeypatch.setattr(
        monitor, "anomaly_scores", lambda model, name, features: np.zeros(len(features))
    )
    noise_bundle, _ = _bundles()
    result = monitor.monitor_frames(
        aligned=aligned,
        telemetry=telemetry,
        inventory=_inventory(),
        noise_bundle=noise_bundle,
        security_bundle=security_bundle,
    )

    assert received
    assert any(
        component["rule_or_model"] == "all_nan_column"
        for incident in result.incidents
        for component in incident["evidence"]
    )
