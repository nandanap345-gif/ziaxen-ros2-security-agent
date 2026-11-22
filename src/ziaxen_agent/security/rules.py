"""Deterministic policy checks over recorded ROS 2 telemetry."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .alerts import Finding
from .inventory import validate_inventory
from .telemetry import telemetry_health_findings


def _topic_key(name: str) -> str:
    return name.strip("/").replace("/", "_")


def _severity(topic: dict[str, Any] | None, fallback: str = "medium") -> str:
    return "critical" if topic and topic.get("safety_critical") else fallback


def _inside_approved_window(
    timestamp: int, run_id: str, windows: list[dict[str, Any]]
) -> bool:
    return any(
        window["start_sim_ns"] <= timestamp < window["stop_sim_ns"]
        and (window.get("run_id") is None or window.get("run_id") == run_id)
        for window in windows
    )


def _finding(
    rule_id: str,
    timestamp: int,
    run_id: str,
    evidence: dict[str, Any],
    *,
    affected: dict[str, str] | None = None,
    severity: str = "medium",
    not_prove: str = "An observed anomaly does not by itself establish malicious intent.",
    next_step: str = "Review the evidence and verify the approved system configuration.",
) -> Finding:
    return Finding(
        rule_id=rule_id,
        timestamp_sim_ns=timestamp,
        run_id=run_id,
        evidence=evidence,
        affected=affected,
        severity=severity,
        what_this_does_not_prove=not_prove,
        recommended_next_step=next_step,
    )


def evaluate_rules(
    frame: pd.DataFrame,
    inventory: dict[str, Any],
    run_id: str,
    *,
    manifest: dict[str, Any] | None = None,
) -> list[Finding]:
    """Return policy and telemetry-health findings without taking any action."""
    inventory = validate_inventory(inventory, require_approved=False)
    if "sim_time_ns" not in frame or frame.empty:
        raise ValueError("Telemetry must be non-empty and contain sim_time_ns.")
    times = pd.to_numeric(frame["sim_time_ns"], errors="coerce")
    if times.isna().any():
        return telemetry_health_findings(frame, run_id)
    findings = telemetry_health_findings(
        frame,
        run_id,
        stale_tick_multiple=inventory["limits"]["stale_tick_multiple"],
    )
    expected_columns = {
        "node_count",
        "node_list_hash",
        "new_nodes",
        "param_event_count",
    }
    if inventory["limits"]["max_service_calls_per_window"] is not None:
        expected_columns.add("service_call_count")
    for topic in inventory["topics"]:
        key = _topic_key(topic["name"])
        expected_columns.update(
            {
                f"{key}.pub_count",
                f"{key}.sub_count",
            }
        )
        if topic["rate_hz"] is not None:
            expected_columns.add(f"{key}.rate_hz")
        if topic["max_gap_s"] is not None:
            expected_columns.add(f"{key}.max_gap_s")
        if topic["max_stamp_lag_s"] is not None:
            expected_columns.add(f"{key}.stamp_lag_mean_s")
        if topic["max_late_count"] is not None:
            expected_columns.add(f"{key}.late_count")
    for column in sorted(expected_columns.difference(frame.columns)):
        findings.append(
            _finding(
                "missing_telemetry_column",
                int(times.iloc[-1]),
                run_id,
                {"missing_column": column},
                severity="medium",
                not_prove="A missing field may reflect collector configuration rather than an attack.",
                next_step="Verify the telemetry schema and collector configuration before interpreting the scan.",
            )
        )
    startup_s = float(inventory["limits"]["startup_warmup_s"])
    if "sim_time_s" in frame:
        elapsed = pd.to_numeric(frame["sim_time_s"], errors="coerce")
    else:
        elapsed = times / 1e9
    elapsed = elapsed - float(elapsed.iloc[0])

    approved_nodes = {node["name"] for node in inventory["nodes"]}
    node_column = frame.get("new_nodes", pd.Series("", index=frame.index))
    node_names = node_column.fillna("").astype(str)
    for position, (index, row) in enumerate(frame.iterrows()):
        if elapsed.iloc[position] < startup_s:
            continue
        timestamp = int(times.iloc[position])
        observed_nodes = [
            item.strip() for item in node_names.loc[index].split(";") if item.strip()
        ]
        for node in observed_nodes:
            if node not in approved_nodes:
                findings.append(
                    _finding(
                        "unapproved_node",
                        timestamp,
                        run_id,
                        {
                            "observed_node": node,
                            "column": "new_nodes",
                            "approved_nodes": sorted(approved_nodes),
                        },
                        affected={"type": "node", "name": node},
                        severity="high",
                        not_prove="A new ROS node name does not identify its host, prove a person joined the network, or establish malicious intent.",
                        next_step="Verify the node against the authorized deployment inventory and review its owner.",
                    )
                )
        if "node_count" in frame and pd.notna(row["node_count"]):
            expected_count = len(approved_nodes)
            observed_count = int(row["node_count"])
            if observed_count > expected_count:
                findings.append(
                    _finding(
                        "unapproved_node",
                        timestamp,
                        run_id,
                        {
                            "observed_node_count": observed_count,
                            "approved_node_count": expected_count,
                            "column": "node_count",
                        },
                        affected={"type": "domain", "name": "ros_graph"},
                        severity="high",
                        not_prove="An excess node count does not identify the node or device responsible.",
                        next_step="Inspect the authorized ROS graph and compare node identities with the approved inventory.",
                    )
                )
        if "node_list_hash" in frame:
            current = row["node_list_hash"]
            approved_hashes = set(inventory.get("approved_node_hashes", []))
            previous = frame["node_list_hash"].iloc[position - 1] if position > 0 else None
            changed = (
                str(current) not in approved_hashes
                if approved_hashes
                else (
                    previous is not None
                    and pd.notna(previous)
                    and pd.notna(current)
                    and str(previous) != str(current)
                )
            )
            if pd.notna(current) and changed:
                findings.append(
                    _finding(
                        "node_set_hash_change",
                        timestamp,
                        run_id,
                        {
                            "observed_hash": str(current),
                            "approved_hashes": sorted(approved_hashes),
                            "column": "node_list_hash",
                        },
                        affected={"type": "domain", "name": "ros_graph"},
                        severity="medium",
                        not_prove="A graph hash change does not identify which node changed or the device hosting it.",
                        next_step="Compare the ROS graph against the approved node inventory.",
                    )
                )

        for topic in inventory["topics"]:
            key = _topic_key(topic["name"])
            for kind, column_key in (
                ("publisher", "approved_publishers"),
                ("subscriber", "approved_subscribers"),
            ):
                column = f"{key}.{kind[:3]}_count"
                policy = topic[column_key]
                maximum = policy.get("max_count")
                if column not in frame or maximum is None or pd.isna(row[column]):
                    continue
                observed = float(row[column])
                if observed > maximum:
                    subscriber_note = (
                        "A subscriber count increase does not identify the subscriber or prove that payloads were read."
                        if kind == "subscriber"
                        else "A publisher count increase does not identify the publisher or prove that its messages were accepted."
                    )
                    findings.append(
                        _finding(
                            f"{kind}_count_above_policy",
                            timestamp,
                            run_id,
                            {
                                "topic": topic["name"],
                                "column": column,
                                "observed_count": observed,
                                "approved_max_count": maximum,
                            },
                            affected={"type": "topic", "name": topic["name"]},
                            severity=_severity(topic, "high"),
                            not_prove=subscriber_note,
                            next_step="Inspect endpoint identities using an authorized ROS graph source and verify the topic policy.",
                        )
                    )

            rate_column = f"{key}.rate_hz"
            band = topic["rate_hz"]
            if band and rate_column in frame and pd.notna(row[rate_column]):
                rate = float(row[rate_column])
                if rate < band["min"] or rate > band["max"]:
                    findings.append(
                        _finding(
                            "topic_rate_out_of_band",
                            timestamp,
                            run_id,
                            {
                                "topic": topic["name"],
                                "column": rate_column,
                                "observed_hz": rate,
                                "approved_band_hz": band,
                            },
                            affected={"type": "topic", "name": topic["name"]},
                            severity=_severity(topic, "medium"),
                            not_prove="An unexpected rate does not establish whether the cause is malicious or operational.",
                            next_step="Check publisher health, expected operating mode, and recent authorized changes.",
                        )
                    )
            gap_column = f"{key}.max_gap_s"
            if (
                topic["max_gap_s"] is not None
                and gap_column in frame
                and pd.notna(row[gap_column])
                and float(row[gap_column]) > topic["max_gap_s"]
            ):
                findings.append(
                    _finding(
                        "topic_gap_above_policy",
                        timestamp,
                        run_id,
                        {
                            "topic": topic["name"],
                            "column": gap_column,
                            "observed_gap_s": float(row[gap_column]),
                            "approved_max_gap_s": topic["max_gap_s"],
                        },
                        affected={"type": "topic", "name": topic["name"]},
                        severity=_severity(topic, "medium"),
                        next_step="Check message production, transport, and collector health.",
                    )
                )
            lag_column = f"{key}.stamp_lag_mean_s"
            if (
                topic["max_stamp_lag_s"] is not None
                and lag_column in frame
                and pd.notna(row[lag_column])
                and float(row[lag_column]) > topic["max_stamp_lag_s"]
            ):
                findings.append(
                    _finding(
                        "topic_stamp_lag_above_policy",
                        timestamp,
                        run_id,
                        {
                            "topic": topic["name"],
                            "column": lag_column,
                            "observed_lag_s": float(row[lag_column]),
                            "approved_max_stamp_lag_s": topic["max_stamp_lag_s"],
                        },
                        affected={"type": "topic", "name": topic["name"]},
                        severity=_severity(topic, "medium"),
                        next_step="Check message timestamps, clock configuration, and transport delay.",
                    )
                )
            late_column = f"{key}.late_count"
            if (
                topic["max_late_count"] is not None
                and late_column in frame
                and pd.notna(row[late_column])
                and float(row[late_column]) > topic["max_late_count"]
            ):
                findings.append(
                    _finding(
                        "late_messages_observed",
                        timestamp,
                        run_id,
                        {
                            "topic": topic["name"],
                            "column": late_column,
                            "observed_late_count": float(row[late_column]),
                            "approved_max_late_count": topic["max_late_count"],
                        },
                        affected={"type": "topic", "name": topic["name"]},
                        severity=_severity(topic, "low"),
                        not_prove="Late messages may result from normal scheduling or transport variation.",
                        next_step="Compare with the approved latency budget and collector clock.",
                    )
                )

        parameter_count = inventory["limits"]["max_parameter_events_per_window"]
        if (
            "param_event_count" in frame
            and pd.notna(row["param_event_count"])
            and float(row["param_event_count"]) > (parameter_count or 0)
            and not _inside_approved_window(
                timestamp, run_id, inventory["approved_change_windows"]
            )
        ):
            findings.append(
                _finding(
                    "parameter_event_outside_approved_window",
                    timestamp,
                    run_id,
                    {
                        "column": "param_event_count",
                        "observed_count": float(row["param_event_count"]),
                        "approved_max_count": parameter_count,
                    },
                    affected={"type": "domain", "name": "ros_parameters"},
                    severity="medium",
                    not_prove="A parameter event does not establish whether the change was unauthorized or unsafe.",
                    next_step="Compare the event with change-management records and node parameter logs.",
                )
            )
        service_limit = inventory["limits"]["max_service_calls_per_window"]
        if (
            service_limit is not None
            and "service_call_count" in frame
            and pd.notna(row["service_call_count"])
            and float(row["service_call_count"]) > service_limit
        ):
            findings.append(
                _finding(
                    "service_call_rate_above_policy",
                    timestamp,
                    run_id,
                    {
                        "column": "service_call_count",
                        "observed_calls_in_window": float(row["service_call_count"]),
                        "approved_max_calls_in_window": service_limit,
                    },
                    affected={"type": "domain", "name": "ros_services"},
                    severity="medium",
                    not_prove="The dataset's service counter is team instrumentation and does not identify the caller.",
                    next_step="Review authorized service clients and node-side service logs.",
                )
            )

    if manifest:
        bridge = manifest.get("bridge", {})
        observed_domains = {
            value
            for value in (bridge.get("local_domain_id"), bridge.get("sim_domain_id"))
            if isinstance(value, int)
        }
        if observed_domains and not observed_domains.issubset(set(inventory["domain_ids"])):
            timestamp = int(times.iloc[-1])
            findings.append(
                _finding(
                    "domain_config_mismatch",
                    timestamp,
                    run_id,
                    {
                        "observed_domain_ids": sorted(observed_domains),
                        "approved_domain_ids": inventory["domain_ids"],
                        "source": "manifest.bridge",
                    },
                    affected={"type": "domain", "name": "ros_domain"},
                    severity="high",
                    not_prove="A static manifest mismatch does not establish the live domain configuration.",
                    next_step="Verify ROS_DOMAIN_ID and the bridge configuration on the authorized system.",
                )
            )
        observed_discovery = bridge.get("ROS_DISCOVERY_SERVER")
        approved_discovery = inventory["discovery"].get("server")
        if observed_discovery is not None and observed_discovery != approved_discovery:
            findings.append(
                _finding(
                    "discovery_config_mismatch",
                    int(times.iloc[-1]),
                    run_id,
                    {
                        "observed_server": observed_discovery,
                        "approved_server": approved_discovery,
                        "source": "manifest.bridge.ROS_DISCOVERY_SERVER",
                    },
                    affected={"type": "domain", "name": "discovery_server"},
                    severity="high",
                    not_prove="A manifest value does not prove which discovery server is active at runtime.",
                    next_step="Verify the discovery configuration and listening interfaces on the authorized system.",
                )
            )
        observed_bridge = manifest.get("bridge")
        if observed_bridge is not None:
            for expected_bridge in inventory["bridges"]:
                observed_fields = {
                    "local_domain_id": bridge.get("local_domain_id"),
                    "remote_domain_id": bridge.get("sim_domain_id"),
                    "endpoint": bridge.get("ROS_DISCOVERY_SERVER"),
                }
                mismatched = {
                    field: {
                        "approved": expected_bridge[field],
                        "observed": observed_fields.get(field),
                    }
                    for field in ("local_domain_id", "remote_domain_id", "endpoint")
                    if field in expected_bridge
                    and expected_bridge[field] != observed_fields.get(field)
                }
                if mismatched:
                    findings.append(
                        _finding(
                            "bridge_config_mismatch",
                            int(times.iloc[-1]),
                            run_id,
                            {
                                "bridge": expected_bridge["name"],
                                "mismatched_fields": mismatched,
                                "source": "manifest.bridge",
                            },
                            affected={"type": "bridge", "name": expected_bridge["name"]},
                            severity="high",
                            not_prove="Static manifest fields do not establish which bridge endpoint is active at runtime.",
                            next_step="Verify the bridge endpoints and domain mapping on the authorized system.",
                        )
                    )
        if inventory["bridges"] and observed_bridge is None:
            findings.append(
                _finding(
                    "bridge_config_not_observable",
                    int(times.iloc[-1]),
                    run_id,
                    {
                        "approved_bridges": [bridge["name"] for bridge in inventory["bridges"]],
                        "manifest_bridge_metadata_present": False,
                    },
                    affected={"type": "bridge", "name": "unknown"},
                    severity="info",
                    not_prove="Missing manifest bridge metadata does not establish a live bridge failure.",
                    next_step="Collect an authorized bridge inventory; this recording cannot verify endpoints.",
                )
            )
    return findings
