"""Dataset-free tests for defensive ROS 2 telemetry monitoring."""

import ast
import json
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from ziaxen_agent.cli import main
from ziaxen_agent.security.alerts import merge_alerts
from ziaxen_agent.security.inventory import (
    bootstrap_inventory,
    load_inventory,
    validate_inventory,
)
from ziaxen_agent.security.rules import evaluate_rules
from ziaxen_agent.security.telemetry import (
    telemetry_features,
    telemetry_health_findings,
)
from ziaxen_agent.security.evaluate import wilson_interval
from ziaxen_agent.security.inspection import _label_mismatch_counts
from ziaxen_agent.security.alerts import Finding
from ziaxen_agent.security.data import SecurityRun
from ziaxen_agent.security.evaluate import _rule_alert_diagnostics


def test_label_mismatch_directions_use_events_as_authority():
    result = _label_mismatch_counts(
        np.array([1, 1, 0, 0], dtype=np.int8),
        pd.Series([0, 1, 1, 0]),
    )

    assert result == {
        "mismatch_rows": 2,
        "stored_false_negative_rows": 1,
        "stored_false_positive_rows": 1,
        "invalid_stored_label_rows": 0,
    }


def test_false_alert_analysis_attributes_residual_graph_rule_episodes():
    times = np.arange(121, dtype=np.int64) * 500_000_000
    run = SecurityRun(
        run_id="spoof_seed3_fixture",
        relative_path="fixture",
        attack_name="spoof",
        run_type="attack",
        npc=10,
        seed=3,
        level=1,
        telemetry=pd.DataFrame({"sim_time_ns": times}),
        labels=pd.Series(np.zeros(len(times), dtype=np.int8)),
        events=pd.DataFrame(
            {"event": ["start", "stop"], "sim_time_ns": [20_000_000_000, 22_000_000_000]}
        ),
        manifest={},
    )
    findings = [
        Finding(rule_id="node_set_hash_change", timestamp_sim_ns=23_000_000_000, run_id=run.run_id, evidence={}, severity="medium"),
        Finding(rule_id="unapproved_node", timestamp_sim_ns=23_000_000_000, run_id=run.run_id, evidence={}, severity="medium"),
        Finding(rule_id="unapproved_node", timestamp_sim_ns=23_500_000_000, run_id=run.run_id, evidence={}, severity="medium"),
        Finding(rule_id="other_policy", timestamp_sim_ns=25_000_000_000, run_id=run.run_id, evidence={}, severity="low"),
    ]

    result = _rule_alert_diagnostics([run], findings)

    assert result["combined_false_alert_episodes"] == 2
    assert result["false_alert_attribution"]["combined_episodes_before_attribution"] == 2
    assert result["false_alert_attribution"]["combined_episodes_after_attribution"] == 2
    assert result["false_alert_attribution"]["graph_rule_episode_counts"] == {
        "node_set_hash_change": 1,
        "unapproved_node": 1,
    }
    assert {
        item["category"]: item["combined_episodes"]
        for item in result["false_alert_attribution"]["by_category"]
    } == {
        "residual_attack_activity_outside_label": 1,
        "unattributed": 1,
    }


def _inventory(*, critical=False):
    return {
        "version": 1,
        "approval_status": "approved",
        "ros_distro": "humble",
        "rmw": "rmw_fastrtps_cpp",
        "domain_ids": [0, 60],
        "approved_node_hashes": ["normal-hash"],
        "discovery": {"mode": "fastdds_discovery_server", "server": "127.0.0.1:11811"},
        "bridges": [],
        "nodes": [
            {"name": "/allowed", "namespace": "/", "host": None, "enclave": None}
        ],
        "topics": [
            {
                "name": "/cmd_vel",
                "msg_type": "geometry_msgs/msg/Twist",
                "approved_publishers": {"names": [], "max_count": 1},
                "approved_subscribers": {"names": [], "max_count": 2},
                "rate_hz": {"min": 50.0, "max": 60.0},
                "max_gap_s": 0.1,
                "max_stamp_lag_s": 0.2,
                "max_late_count": 0,
                "safety_critical": critical,
            }
        ],
        "limits": {
            "startup_warmup_s": 0.0,
            "stale_tick_multiple": 3,
            "max_service_calls_per_window": 0,
            "max_parameter_events_per_window": 0,
        },
        "approved_change_windows": [],
    }


def _frame(**overrides):
    frame = pd.DataFrame(
        {
            "sim_time_ns": [15_000_000_000, 15_500_000_000, 16_000_000_000],
            "sim_time_s": [15.0, 15.5, 16.0],
            "node_count": [1, 1, 1],
            "node_list_hash": ["normal-hash"] * 3,
            "new_nodes": [""] * 3,
            "imu_mon.rate_hz": [55.0] * 3,
            "imu_mon.pub_count": [1] * 3,
            "imu_mon.sub_count": [2] * 3,
            "imu_mon.max_gap_s": [0.02] * 3,
            "imu_mon.stamp_lag_mean_s": [0.01] * 3,
            "imu_mon.late_count": [0] * 3,
            "param_event_count": [0] * 3,
            "service_call_count": [0] * 3,
            "collector_queue_drops": [0] * 3,
        }
    )
    for column, values in overrides.items():
        frame[column] = values
    return frame


def _topic_inventory(*, critical=False):
    inventory = _inventory(critical=critical)
    inventory["topics"][0]["name"] = "/imu_mon"
    return inventory


def test_approved_activity_has_no_policy_alerts():
    findings = evaluate_rules(_frame(), _topic_inventory(), "normal-run")
    assert not [item for item in findings if item.source == "policy"]


def test_new_node_name_and_excess_node_count_are_reported():
    frame = _frame(
        **{
            "new_nodes": ["", "/rogue", "/rogue"],
            "node_count": [1, 2, 2],
            "node_list_hash": ["normal-hash", "rogue-hash", "rogue-hash"],
        }
    )
    findings = evaluate_rules(frame, _topic_inventory(), "rogue-run")
    node_alerts = [item for item in findings if item.rule_id == "unapproved_node"]
    assert any(item.evidence.get("observed_node") == "/rogue" for item in node_alerts)
    assert any(item.evidence.get("observed_node_count") == 2 for item in node_alerts)


def test_subscriber_count_alert_does_not_claim_payload_access():
    frame = _frame(**{"imu_mon.sub_count": [2, 3, 3]})
    findings = evaluate_rules(frame, _topic_inventory(), "subscriber-run")
    alert = next(item for item in findings if item.rule_id == "subscriber_count_above_policy")
    assert "does not identify the subscriber" in alert.what_this_does_not_prove
    assert alert.evidence["observed_count"] == 3


def test_critical_topic_publisher_policy_is_critical():
    frame = _frame(**{"imu_mon.pub_count": [1, 2, 2]})
    findings = evaluate_rules(frame, _topic_inventory(critical=True), "publisher-run")
    alert = next(item for item in findings if item.rule_id == "publisher_count_above_policy")
    assert alert.severity == "critical"


def test_rate_spike_and_drop_are_detected_but_in_band_is_not():
    frame = _frame(**{"imu_mon.rate_hz": [55.0, 65.0, 45.0]})
    findings = evaluate_rules(frame, _topic_inventory(), "rate-run")
    alerts = [item for item in findings if item.rule_id == "topic_rate_out_of_band"]
    assert [item.evidence["observed_hz"] for item in alerts] == [65.0, 45.0]
    assert all(item.evidence["approved_band_hz"] == {"min": 50.0, "max": 60.0} for item in alerts)


def test_parameter_and_service_activity_are_checked_against_policy_windows():
    inventory = _topic_inventory()
    frame = _frame(**{"param_event_count": [0, 1, 0], "service_call_count": [0, 0, 2]})
    findings = evaluate_rules(frame, inventory, "change-run")
    assert "parameter_event_outside_approved_window" in {item.rule_id for item in findings}
    assert "service_call_rate_above_policy" in {item.rule_id for item in findings}

    inventory["approved_change_windows"] = [
        {"start_sim_ns": 15_400_000_000, "stop_sim_ns": 15_600_000_000, "run_id": "change-run"}
    ]
    findings = evaluate_rules(frame, inventory, "change-run")
    assert "parameter_event_outside_approved_window" not in {
        item.rule_id for item in findings
    }


def test_manifest_domain_discovery_and_bridge_mismatches_are_explicit():
    inventory = _topic_inventory()
    inventory["bridges"] = [
        {
            "name": "sim-bridge",
            "local_domain_id": 60,
            "remote_domain_id": 0,
            "endpoint": "127.0.0.1:11811",
        }
    ]
    manifest = {
        "bridge": {
            "local_domain_id": 61,
            "sim_domain_id": 0,
            "ROS_DISCOVERY_SERVER": "10.0.0.2:11811",
        }
    }
    findings = evaluate_rules(_frame(), inventory, "bridge-run", manifest=manifest)
    codes = {item.rule_id for item in findings}
    assert {"domain_config_mismatch", "discovery_config_mismatch", "bridge_config_mismatch"} <= codes


def test_wilson_interval_is_bounded_and_shows_small_sample_uncertainty():
    interval = wilson_interval(3, 3)
    assert interval is not None
    assert interval[0] == pytest.approx(0.4385, abs=0.001)
    assert interval[1] == pytest.approx(1.0)
    assert wilson_interval(0, 0) is None


def test_health_checks_missing_nan_stale_out_of_order_and_duplicate_ticks():
    no_timestamp = telemetry_health_findings(pd.DataFrame({"value": [1]}), "missing-time")
    assert no_timestamp[0].rule_id == "missing_timestamp"

    frame = _frame()
    frame["empty_field"] = np.nan
    frame.loc[1, "sim_time_ns"] = frame.loc[0, "sim_time_ns"]
    frame.loc[2, "sim_time_ns"] = frame.loc[0, "sim_time_ns"] - 1
    frame.loc[2, "collector_queue_drops"] = 1
    findings = telemetry_health_findings(frame, "bad-health")
    codes = {item.rule_id for item in findings}
    assert {"all_nan_column", "duplicate_ticks", "out_of_order_ticks", "collector_drops"} <= codes

    stale = _frame()
    stale.loc[2, "sim_time_ns"] += 2_000_000_000
    findings = telemetry_health_findings(stale, "stale")
    assert "stale_telemetry" in {item.rule_id for item in findings}


def test_missing_inventory_required_telemetry_field_is_not_silently_ignored():
    frame = _frame().drop(columns=["imu_mon.sub_count"])
    findings = evaluate_rules(frame, _topic_inventory(), "missing-field")
    assert any(
        item.rule_id == "missing_telemetry_column"
        and item.evidence["missing_column"] == "imu_mon.sub_count"
        for item in findings
    )


def test_features_are_numeric_causal_and_exclude_labels_and_timestamps():
    frame = _frame()
    frame["is_attack"] = [0, 1, 1]
    features = telemetry_features(frame)
    assert "sim_time_ns" not in features
    assert "is_attack" not in features
    assert "derived::rate::imu_mon.rate_hz" in features
    assert pd.isna(features.iloc[0]["derived::rate::imu_mon.rate_hz"])


def test_inventory_rejects_duplicate_topics_negative_rates_and_unknown_keys():
    duplicate = _inventory()
    duplicate["topics"].append(dict(duplicate["topics"][0]))
    with pytest.raises(ValueError, match="Duplicate topic"):
        validate_inventory(duplicate)

    negative = _inventory()
    negative["topics"][0]["rate_hz"]["min"] = -1
    with pytest.raises(ValueError, match="non-negative"):
        validate_inventory(negative)

    unknown = _inventory()
    unknown["unexpected"] = True
    with pytest.raises(ValueError, match="unknown keys"):
        validate_inventory(unknown)


def test_draft_inventory_cannot_be_used_for_scan(tmp_path):
    path = tmp_path / "draft.json"
    draft = _inventory()
    draft["approval_status"] = "draft"
    path.write_text(json.dumps(draft), encoding="utf-8")
    with pytest.raises(ValueError, match="human must review"):
        load_inventory(path)

    offline_demo = _inventory()
    offline_demo["approval_status"] = "approved_for_offline_demo"
    offline_demo["reviewer"] = "PENDING HUMAN REVIEW"
    path.write_text(json.dumps(offline_demo), encoding="utf-8")
    with pytest.raises(ValueError, match="--offline-demo"):
        load_inventory(path)
    assert load_inventory(path, allow_offline_demo=True)["approval_status"] == (
        "approved_for_offline_demo"
    )


def test_bootstrap_inventory_is_a_draft_and_never_auto_approves(tmp_path):
    root = tmp_path / "data"
    run = root / "normal_data" / "normal_seed1"
    run.mkdir(parents=True)
    held_out_run = root / "normal_data" / "normal_seed3"
    held_out_run.mkdir(parents=True)
    (root / "dataset_index.csv").write_text(
        "relative_path,type,attack_name,npc,seed,level,status\n"
        "normal_data/normal_seed1,normal,none,10,1,0,completed\n"
        "normal_data/normal_seed3,normal,none,10,3,0,completed\n",
        encoding="utf-8",
    )
    manifest = {
        "telemetry_baseline": {
            "nodes": ["/allowed"],
            "pub_count": {"/imu_mon": 1},
            "sub_count": {"/imu_mon": 2},
        },
        "package_versions": {"ROS_DISTRO": "humble", "RMW_IMPLEMENTATION": "rmw_fastrtps_cpp"},
        "bridge": {
            "local_domain_id": 60,
            "sim_domain_id": 0,
            "ROS_DISCOVERY_SERVER": "127.0.0.1:11811",
        },
    }
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    held_out_manifest = json.loads(json.dumps(manifest))
    held_out_manifest["bridge"]["local_domain_id"] = 70
    (held_out_run / "manifest.json").write_text(
        json.dumps(held_out_manifest), encoding="utf-8"
    )
    telemetry = pd.DataFrame(
        {
            "sim_time_s": np.arange(41, dtype=float) * 0.5,
            "imu_mon.rate_hz": [55.0] * 41,
            "imu_mon.max_gap_s": [0.02] * 41,
            "imu_mon.stamp_lag_mean_s": [0.01] * 41,
            "imu_mon.late_count": [0] * 41,
        }
    )
    telemetry.to_csv(run / "telemetry.csv.gz", index=False)
    held_out_telemetry = telemetry.copy()
    held_out_telemetry["imu_mon.rate_hz"] = 100.0
    held_out_telemetry.to_csv(held_out_run / "telemetry.csv.gz", index=False)
    destination = tmp_path / "inventory.json"

    draft = bootstrap_inventory(root, destination, seeds={1})

    assert destination.is_file()
    assert draft["approval_status"] == "draft"
    assert draft["nodes"][0]["name"] == "/allowed"
    assert draft["domain_ids"] == [0, 60]
    assert draft["topics"][0]["rate_hz"]["max"] == 57.75
    assert validate_inventory(json.loads(destination.read_text(encoding="utf-8")))["approval_status"] == "draft"


def test_security_scan_cli_replays_telemetry_without_ros(tmp_path):
    inventory_path = tmp_path / "approved.json"
    inventory = _topic_inventory()
    inventory["approval_status"] = "approved_for_offline_demo"
    inventory["reviewer"] = "PENDING HUMAN REVIEW"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    telemetry_path = tmp_path / "telemetry.csv"
    frame = _frame(**{"new_nodes": ["", "/rogue", "/rogue"]})
    frame.to_csv(telemetry_path, index=False)
    model_features = telemetry_features(frame).fillna(0.0)
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("detector", RandomForestClassifier(n_estimators=5, random_state=0)),
        ]
    ).fit(model_features, [0, 1, 1])
    model_path = tmp_path / "security_model.joblib"
    joblib.dump(
        {
            "task": "ros2_telemetry_security_anomaly",
            "selected_model": "random_forest",
            "models": {"random_forest": model},
            "thresholds": {"random_forest": 0.0},
            "feature_columns": list(model_features.columns),
        },
        model_path,
    )
    output_path = tmp_path / "alerts.jsonl"

    assert main(
        [
            "security-scan",
            "--input",
            str(telemetry_path),
            "--inventory",
            str(inventory_path),
            "--offline-demo",
            "--model",
            str(model_path),
            "--output",
            str(output_path),
            "--run-id",
            "synthetic-run",
        ]
    ) == 0
    alerts = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert alerts
    assert any(item["rule_or_model"] == "unapproved_node" for item in alerts)
    assert any(item["source"] == "anomaly_model" for item in alerts)
    assert all(item["automatic_action_taken"] is False for item in alerts)


def test_alerts_are_advisory_and_security_package_has_no_network_tools():
    findings = evaluate_rules(
        _frame(**{"new_nodes": ["", "/rogue", "/rogue"]}),
        _topic_inventory(),
        "safety-run",
    )
    alerts = [item.to_dict() for item in merge_alerts(findings)]
    assert alerts
    assert all(re.fullmatch(r"[0-9a-f]{20}", item["alert_id"]) for item in alerts)
    assert all(item["requires_human_approval"] for item in alerts)
    assert all(item["automatic_action_taken"] is False for item in alerts)
    input_columns = set(_frame(**{"new_nodes": ["", "/rogue", "/rogue"]}).columns)
    for item in alerts:
        evidence_column = item["evidence"].get("column")
        if evidence_column is not None:
            assert evidence_column in input_columns

    package_dir = Path(__file__).parents[1] / "src" / "ziaxen_agent" / "security"
    forbidden = {"rclpy", "socket", "scapy", "pcap", "pyshark"}
    for path in package_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = {node.module.split(".")[0]}
            else:
                continue
            assert not (names & forbidden), f"{path.name} imports {names & forbidden}"


