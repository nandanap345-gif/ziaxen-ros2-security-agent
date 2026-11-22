"""Strict loading and draft generation for approved ROS 2 inventories."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


_TOP_LEVEL_KEYS = {
    "version",
    "approval_status",
    "ros_distro",
    "rmw",
    "domain_ids",
    "discovery",
    "bridges",
    "nodes",
    "topics",
    "limits",
    "approved_change_windows",
    "draft_note",
    "approved_node_hashes",
    "reviewer",
}
_TOPIC_KEYS = {
    "name",
    "msg_type",
    "approved_publishers",
    "approved_subscribers",
    "rate_hz",
    "max_gap_s",
    "max_stamp_lag_s",
    "max_late_count",
    "safety_critical",
}
_ENDPOINT_POLICY_KEYS = {"names", "max_count"}
_LIMIT_KEYS = {
    "startup_warmup_s",
    "stale_tick_multiple",
    "max_service_calls_per_window",
    "max_parameter_events_per_window",
}


def _reject_unknown(value: dict[str, Any], allowed: set[str], context: str) -> None:
    unknown = set(value).difference(allowed)
    if unknown:
        raise ValueError(f"{context} contains unknown keys: {sorted(unknown)}")


def _nonnegative_number(value: Any, context: str, *, nullable: bool = False) -> float | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{context} must be a non-negative number.")
    return float(value)


def validate_inventory(
    inventory: Any, *, require_approved: bool = False, allow_offline_demo: bool = False
) -> dict[str, Any]:
    """Validate the documented JSON schema and return a normalized copy."""
    if not isinstance(inventory, dict):
        raise ValueError("Inventory root must be a JSON object.")
    _reject_unknown(inventory, _TOP_LEVEL_KEYS, "Inventory")
    required = {
        "version",
        "approval_status",
        "ros_distro",
        "rmw",
        "domain_ids",
        "discovery",
        "bridges",
        "nodes",
        "topics",
        "limits",
        "approved_change_windows",
    }
    missing = required.difference(inventory)
    if missing:
        raise ValueError(f"Inventory is missing required keys: {sorted(missing)}")
    if inventory["version"] != 1:
        raise ValueError("Inventory version must be 1.")
    if inventory["approval_status"] not in {
        "draft",
        "approved",
        "approved_for_offline_demo",
    }:
        raise ValueError(
            "approval_status must be 'draft', 'approved', or "
            "'approved_for_offline_demo'."
        )
    if "reviewer" in inventory and not isinstance(inventory["reviewer"], str):
        raise ValueError("reviewer must be a string.")
    if "draft_note" in inventory and not isinstance(inventory["draft_note"], str):
        raise ValueError("draft_note must be a string.")
    if "approved_node_hashes" in inventory and (
        not isinstance(inventory["approved_node_hashes"], list)
        or not all(isinstance(item, str) and item for item in inventory["approved_node_hashes"])
    ):
        raise ValueError("approved_node_hashes must be a list of non-empty strings.")
    if (
        require_approved
        and inventory["approval_status"] != "approved"
        and not (
            allow_offline_demo
            and inventory["approval_status"] == "approved_for_offline_demo"
            and inventory.get("reviewer") == "PENDING HUMAN REVIEW"
        )
    ):
        raise ValueError(
            "Inventory is not approved for this scan. A human must review it and "
            "set approval_status to 'approved'; for recorded-file demos only, use "
            "'approved_for_offline_demo' with reviewer 'PENDING HUMAN REVIEW' and "
            "pass --offline-demo."
        )
    for key in ("ros_distro", "rmw"):
        if not isinstance(inventory[key], str) or not inventory[key].strip():
            raise ValueError(f"{key} must be a non-empty string.")
    if not isinstance(inventory["domain_ids"], list) or not all(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0
        for value in inventory["domain_ids"]
    ):
        raise ValueError("domain_ids must be a list of non-negative integers.")
    if len(set(inventory["domain_ids"])) != len(inventory["domain_ids"]):
        raise ValueError("domain_ids must not contain duplicates.")

    discovery = inventory["discovery"]
    if not isinstance(discovery, dict):
        raise ValueError("discovery must be an object.")
    _reject_unknown(discovery, {"mode", "server"}, "discovery")
    if set(discovery) != {"mode", "server"}:
        raise ValueError("discovery must contain exactly 'mode' and 'server'.")
    if not isinstance(discovery["mode"], str) or not discovery["mode"].strip():
        raise ValueError("discovery.mode must be a non-empty string.")
    if discovery["server"] is not None and not isinstance(discovery["server"], str):
        raise ValueError("discovery.server must be a string or null.")

    bridges = inventory["bridges"]
    if not isinstance(bridges, list):
        raise ValueError("bridges must be a list.")
    bridge_names: set[str] = set()
    for position, bridge in enumerate(bridges):
        context = f"bridges[{position}]"
        if not isinstance(bridge, dict):
            raise ValueError(f"{context} must be an object.")
        _reject_unknown(
            bridge,
            {"name", "local_domain_id", "remote_domain_id", "endpoint"},
            context,
        )
        if not isinstance(bridge.get("name"), str) or not bridge["name"].strip():
            raise ValueError(f"{context}.name must be a non-empty string.")
        if bridge["name"] in bridge_names:
            raise ValueError(f"Duplicate bridge name: {bridge['name']}")
        bridge_names.add(bridge["name"])
        for key in ("local_domain_id", "remote_domain_id"):
            if key in bridge and (
                not isinstance(bridge[key], int)
                or isinstance(bridge[key], bool)
                or bridge[key] < 0
            ):
                raise ValueError(f"{context}.{key} must be a non-negative integer.")
        if "endpoint" in bridge and bridge["endpoint"] is not None and not isinstance(
            bridge["endpoint"], str
        ):
            raise ValueError(f"{context}.endpoint must be a string or null.")

    nodes = inventory["nodes"]
    if not isinstance(nodes, list):
        raise ValueError("nodes must be a list.")
    node_names: set[str] = set()
    for position, node in enumerate(nodes):
        context = f"nodes[{position}]"
        if not isinstance(node, dict):
            raise ValueError(f"{context} must be an object.")
        _reject_unknown(node, {"name", "namespace", "host", "enclave"}, context)
        if not isinstance(node.get("name"), str) or not node["name"].strip():
            raise ValueError(f"{context}.name must be a non-empty string.")
        if node["name"] in node_names:
            raise ValueError(f"Duplicate node name: {node['name']}")
        node_names.add(node["name"])
        if not isinstance(node.get("namespace"), str) or not node["namespace"].startswith("/"):
            raise ValueError(f"{context}.namespace must be an absolute ROS namespace.")
        for optional in ("host", "enclave"):
            if optional in node and node[optional] is not None and not isinstance(
                node[optional], str
            ):
                raise ValueError(f"{context}.{optional} must be a string or null.")

    topics = inventory["topics"]
    if not isinstance(topics, list):
        raise ValueError("topics must be a list.")
    topic_names: set[str] = set()
    for position, topic in enumerate(topics):
        context = f"topics[{position}]"
        if not isinstance(topic, dict):
            raise ValueError(f"{context} must be an object.")
        _reject_unknown(topic, _TOPIC_KEYS, context)
        missing_topic = _TOPIC_KEYS.difference(topic)
        if missing_topic:
            raise ValueError(f"{context} is missing keys: {sorted(missing_topic)}")
        name = topic["name"]
        if not isinstance(name, str) or not name.startswith("/"):
            raise ValueError(f"{context}.name must be an absolute ROS topic name.")
        if name in topic_names:
            raise ValueError(f"Duplicate topic name: {name}")
        topic_names.add(name)
        if not isinstance(topic["msg_type"], str) or not topic["msg_type"].strip():
            raise ValueError(f"{context}.msg_type must be a non-empty string.")
        if not isinstance(topic["safety_critical"], bool):
            raise ValueError(f"{context}.safety_critical must be boolean.")
        for key in ("approved_publishers", "approved_subscribers"):
            policy = topic[key]
            if not isinstance(policy, dict):
                raise ValueError(f"{context}.{key} must be an object.")
            _reject_unknown(policy, _ENDPOINT_POLICY_KEYS, f"{context}.{key}")
            if not policy:
                raise ValueError(f"{context}.{key} must specify names and/or max_count.")
            names = policy.get("names", [])
            if not names and "max_count" not in policy:
                raise ValueError(f"{context}.{key} must specify names and/or max_count.")
            if not isinstance(names, list) or not all(
                isinstance(item, str) and item.strip() for item in names
            ):
                raise ValueError(f"{context}.{key}.names must be a list of non-empty strings.")
            if "max_count" in policy:
                count = policy["max_count"]
                if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                    raise ValueError(f"{context}.{key}.max_count must be a non-negative integer.")
        rate = topic["rate_hz"]
        if rate is not None:
            if not isinstance(rate, dict):
                raise ValueError(f"{context}.rate_hz must be an object or null.")
            _reject_unknown(rate, {"min", "max"}, f"{context}.rate_hz")
            if set(rate) != {"min", "max"}:
                raise ValueError(f"{context}.rate_hz must contain min and max.")
            lower = _nonnegative_number(rate["min"], f"{context}.rate_hz.min")
            upper = _nonnegative_number(rate["max"], f"{context}.rate_hz.max")
            if lower > upper:
                raise ValueError(f"{context}.rate_hz.min cannot exceed max.")
        _nonnegative_number(topic["max_gap_s"], f"{context}.max_gap_s", nullable=True)
        _nonnegative_number(
            topic["max_stamp_lag_s"], f"{context}.max_stamp_lag_s", nullable=True
        )
        if topic["max_late_count"] is not None and (
            not isinstance(topic["max_late_count"], int)
            or isinstance(topic["max_late_count"], bool)
            or topic["max_late_count"] < 0
        ):
            raise ValueError(f"{context}.max_late_count must be a non-negative integer or null.")

    limits = inventory["limits"]
    if not isinstance(limits, dict):
        raise ValueError("limits must be an object.")
    _reject_unknown(limits, _LIMIT_KEYS, "limits")
    if set(limits) != _LIMIT_KEYS:
        raise ValueError(f"limits must contain exactly {sorted(_LIMIT_KEYS)}.")
    _nonnegative_number(limits["startup_warmup_s"], "limits.startup_warmup_s")
    stale_multiple = limits["stale_tick_multiple"]
    if not isinstance(stale_multiple, int) or isinstance(stale_multiple, bool) or stale_multiple < 1:
        raise ValueError("limits.stale_tick_multiple must be a positive integer.")
    for key in ("max_service_calls_per_window", "max_parameter_events_per_window"):
        value = limits[key]
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or value < 0
        ):
            raise ValueError(f"limits.{key} must be a non-negative integer or null.")

    windows = inventory["approved_change_windows"]
    if not isinstance(windows, list):
        raise ValueError("approved_change_windows must be a list.")
    for position, window in enumerate(windows):
        context = f"approved_change_windows[{position}]"
        if not isinstance(window, dict):
            raise ValueError(f"{context} must be an object.")
        _reject_unknown(window, {"start_sim_ns", "stop_sim_ns", "run_id"}, context)
        if set(window).difference({"run_id"}) != {"start_sim_ns", "stop_sim_ns"}:
            raise ValueError(f"{context} requires start_sim_ns and stop_sim_ns.")
        start = window["start_sim_ns"]
        stop = window["stop_sim_ns"]
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(stop, int)
            or isinstance(stop, bool)
            or stop <= start
        ):
            raise ValueError(f"{context} must have increasing integer timestamps.")
        if "run_id" in window and not isinstance(window["run_id"], str):
            raise ValueError(f"{context}.run_id must be a string.")

    return inventory


def load_inventory(
    path: str | Path,
    *,
    require_approved: bool = True,
    allow_offline_demo: bool = False,
) -> dict[str, Any]:
    inventory_path = Path(path)
    if not inventory_path.is_file():
        raise FileNotFoundError(f"Inventory file was not found: {inventory_path}")
    try:
        raw = json.loads(inventory_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid inventory JSON: {error}") from error
    return validate_inventory(
        raw,
        require_approved=require_approved,
        allow_offline_demo=allow_offline_demo,
    )


def bootstrap_inventory(
    data_root: str | Path,
    output_path: str | Path,
    *,
    seeds: set[int] | None = None,
) -> dict[str, Any]:
    """Write an explicitly unapproved draft from normal runs in selected seeds."""
    root = Path(data_root).expanduser().resolve()
    import pandas as pd

    index_frame = pd.read_csv(root / "dataset_index.csv")
    if seeds is not None:
        if not seeds:
            raise ValueError("At least one seed is required for inventory bootstrapping.")
        if "seed" not in index_frame:
            raise ValueError("dataset_index.csv has no seed column.")
        seed_values = pd.to_numeric(index_frame["seed"], errors="coerce")
        index_frame = index_frame.loc[seed_values.isin(seeds)]
    normal_rows = index_frame.loc[index_frame["type"].eq("normal")]
    if normal_rows.empty:
        raise ValueError("No normal run is available to bootstrap an inventory draft.")
    run_path = root / str(normal_rows.iloc[0]["relative_path"])
    manifest_path = run_path / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Normal run is missing manifest: {run_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    baseline = manifest.get("telemetry_baseline")
    if not isinstance(baseline, dict):
        raise ValueError("Normal run manifest has no telemetry_baseline object.")
    telemetry_frames = []
    manifests = []
    for _, normal_row in normal_rows.iterrows():
        current_path = root / str(normal_row["relative_path"])
        current_manifest_path = current_path / "manifest.json"
        telemetry_path = current_path / "telemetry.csv.gz"
        if not current_manifest_path.is_file() or not telemetry_path.is_file():
            raise FileNotFoundError(f"Normal run is missing manifest or telemetry: {current_path}")
        manifests.append(json.loads(current_manifest_path.read_text(encoding="utf-8")))
        current_telemetry = pd.read_csv(telemetry_path)
        if "sim_time_s" in current_telemetry and len(current_telemetry):
            elapsed = current_telemetry["sim_time_s"] - current_telemetry["sim_time_s"].iloc[0]
            current_telemetry = current_telemetry.loc[elapsed >= 15.0]
        telemetry_frames.append(current_telemetry)
    telemetry = pd.concat(telemetry_frames, ignore_index=True)

    packages = manifest.get("package_versions", {})
    bridge_info = manifest.get("bridge", {})
    topics = []
    for topic_name, publisher_count in baseline.get("pub_count", {}).items():
        key = str(topic_name).strip("/").replace("/", "_")
        rate_column = f"{key}.rate_hz"
        gap_column = f"{key}.max_gap_s"
        lag_column = f"{key}.stamp_lag_mean_s"
        rates = (
            pd.to_numeric(telemetry[rate_column], errors="coerce").dropna()
            if rate_column in telemetry
            else pd.Series(dtype=float)
        )
        gaps = (
            pd.to_numeric(telemetry[gap_column], errors="coerce").dropna()
            if gap_column in telemetry
            else pd.Series(dtype=float)
        )
        lags = (
            pd.to_numeric(telemetry[lag_column], errors="coerce").dropna()
            if lag_column in telemetry
            else pd.Series(dtype=float)
        )
        rate_band = (
            {
                "min": max(0.0, float(rates.quantile(0.005)) - max(0.5, abs(float(rates.quantile(0.005))) * 0.05)),
                "max": float(rates.quantile(0.995)) + max(0.5, abs(float(rates.quantile(0.995))) * 0.05),
            }
            if not rates.empty
            else None
        )
        topics.append(
            {
                "name": str(topic_name),
                "msg_type": "unknown",
                "approved_publishers": {"names": [], "max_count": int(publisher_count)},
                "approved_subscribers": {
                    "names": [],
                    "max_count": int(baseline.get("sub_count", {}).get(topic_name, 0)),
                },
                "rate_hz": rate_band,
                "max_gap_s": float(gaps.quantile(0.995)) * 1.5 if not gaps.empty else None,
                "max_stamp_lag_s": float(lags.quantile(0.995)) * 1.5 if not lags.empty else None,
                "max_late_count": (
                    int(np.ceil(pd.to_numeric(telemetry[f"{key}.late_count"], errors="coerce").dropna().quantile(0.995)))
                    if f"{key}.late_count" in telemetry
                    and not pd.to_numeric(telemetry[f"{key}.late_count"], errors="coerce").dropna().empty
                    else None
                ),
                "safety_critical": False,
            }
        )
    nodes = [
        {"name": name, "namespace": "/", "host": None, "enclave": None}
        for name in baseline.get("nodes", [])
    ]
    index_entries = index_frame
    domain_manifests = []
    for relative in index_entries["relative_path"].astype(str):
        manifest_path = root / relative / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Dataset run is missing manifest: {manifest_path}")
        domain_manifests.append(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
    domain_ids = sorted(
        {
            int(value)
            for entry in domain_manifests
            for value in (
                entry.get("bridge", {}).get("local_domain_id"),
                entry.get("bridge", {}).get("sim_domain_id"),
            )
            if isinstance(value, int)
        }
    )
    approved_hashes = sorted(
        {
            str(value)
            for frame in telemetry_frames
            if "node_list_hash" in frame
            for value in frame["node_list_hash"].dropna().unique()
        }
    )
    draft = {
        "version": 1,
        "approval_status": "draft",
        "ros_distro": str(packages.get("ROS_DISTRO", "unknown")),
        "rmw": str(packages.get("RMW_IMPLEMENTATION", "unknown")),
        "domain_ids": domain_ids,
        "approved_node_hashes": approved_hashes,
        "discovery": {
            "mode": "fastdds_discovery_server",
            "server": bridge_info.get("ROS_DISCOVERY_SERVER"),
        },
        "bridges": [],
        "nodes": nodes,
        "topics": topics,
        "limits": {
            "startup_warmup_s": 15.0,
            "stale_tick_multiple": 3,
            "max_service_calls_per_window": 0,
            "max_parameter_events_per_window": 0,
        },
        "approved_change_windows": [],
        "draft_note": (
            "This is an unapproved proposal. Topic/node baselines are derived from normal "
            "recordings and domain IDs are collected from indexed manifests. Review every "
            "entry and change approval_status to 'approved' only after confirming the "
            "intended system configuration."
        ),
    }
    validate_inventory(draft, require_approved=False)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")
    return draft
