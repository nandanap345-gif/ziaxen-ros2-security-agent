# Seed-3 security scan diagnostics

Scans use only local recorded telemetry, the offline-demo inventory, and the frozen model. Event windows are start-inclusive and stop-exclusive. Alerts remain advisory; no live ROS access or action occurs.

## normal_npc10_seed3

- Class: `none`; seed `3`; total alerts: **0**.
- Attack window: none (normal run).

| Rule ID | Alerts | First fired | Last fired |
|---|---:|---|---|

No alert was emitted; therefore no sample alert exists for this scan.

## spoof_L1_npc10_seed3

- Class: `spoof`; seed `3`; total alerts: **9**.
- Attack window: `2467783333333` to `2495150000000` sim ns.

| Rule ID | Alerts | First fired | Last fired |
|---|---:|---|---|
| late_messages_observed | 2 | after (+5.083s from stop) | after (+5.083s from stop) |
| node_set_hash_change | 1 | before (-2.550s from start) | before (-2.550s from start) |
| parameter_event_outside_approved_window | 1 | before (-2.550s from start) | before (-2.550s from start) |
| publisher_count_above_policy | 1 | before (-0.550s from start) | before (-0.550s from start) |
| random_forest | 1 | before (-1.550s from start) | before (-1.550s from start) |
| topic_rate_out_of_band | 1 | before (-0.550s from start) | before (-0.550s from start) |
| unapproved_node | 2 | before (-2.550s from start) | before (-2.550s from start) |

Most relevant alert: `unapproved_node` at before (-2.550s from start).

```json
{
  "alert_id": "8dee50a1732a6f4e4403",
  "timestamp_sim_ns": 2465233333333,
  "run_id": "spoof_L1_npc10_seed3",
  "source": "policy",
  "rule_or_model": "unapproved_node",
  "affected": {
    "type": "domain",
    "name": "ros_graph"
  },
  "evidence": {
    "observed_node_count": 5,
    "approved_node_count": 4,
    "column": "node_count",
    "merged_finding_count": 60,
    "sample_evidence": [
      {
        "observed_node_count": 5,
        "approved_node_count": 4,
        "column": "node_count"
      },
      {
        "observed_node_count": 5,
        "approved_node_count": 4,
        "column": "node_count"
      },
      {
        "observed_node_count": 5,
        "approved_node_count": 4,
        "column": "node_count"
      },
      {
        "observed_node_count": 5,
        "approved_node_count": 4,
        "column": "node_count"
      },
      {
        "observed_node_count": 5,
        "approved_node_count": 4,
        "column": "node_count"
      }
    ]
  },
  "what_this_does_not_prove": "An excess node count does not identify the node or device responsible.",
  "severity": "high",
  "score": null,
  "threshold": null,
  "confidence_notes": "Based only on recorded telemetry and the supplied inventory.",
  "recommended_next_step": "Inspect the authorized ROS graph and compare node identities with the approved inventory.",
  "requires_human_approval": true,
  "automatic_action_taken": false,
  "incident_start_sim_ns": 2465233333333,
  "incident_end_sim_ns": 2494733333333
}
```

## unauthorized_node_L1_npc10_seed3

- Class: `unauthorized_node`; seed `3`; total alerts: **5**.
- Attack window: `2542766666666` to `2571666666666` sim ns.

| Rule ID | Alerts | First fired | Last fired |
|---|---:|---|---|
| node_set_hash_change | 1 | before (-1.083s from start) | before (-1.083s from start) |
| parameter_event_outside_approved_window | 1 | before (-1.083s from start) | before (-1.083s from start) |
| random_forest | 1 | before (-0.083s from start) | before (-0.083s from start) |
| unapproved_node | 2 | before (-1.083s from start) | before (-1.083s from start) |

Most relevant alert: `unapproved_node` at before (-1.083s from start).

```json
{
  "alert_id": "7331236d508b7b9df6eb",
  "timestamp_sim_ns": 2541683333333,
  "run_id": "unauthorized_node_L1_npc10_seed3",
  "source": "policy",
  "rule_or_model": "unapproved_node",
  "affected": {
    "type": "domain",
    "name": "ros_graph"
  },
  "evidence": {
    "observed_node_count": 5,
    "approved_node_count": 4,
    "column": "node_count",
    "merged_finding_count": 60,
    "sample_evidence": [
      {
        "observed_node_count": 5,
        "approved_node_count": 4,
        "column": "node_count"
      },
      {
        "observed_node_count": 5,
        "approved_node_count": 4,
        "column": "node_count"
      },
      {
        "observed_node_count": 5,
        "approved_node_count": 4,
        "column": "node_count"
      },
      {
        "observed_node_count": 5,
        "approved_node_count": 4,
        "column": "node_count"
      },
      {
        "observed_node_count": 5,
        "approved_node_count": 4,
        "column": "node_count"
      }
    ]
  },
  "what_this_does_not_prove": "An excess node count does not identify the node or device responsible.",
  "severity": "high",
  "score": null,
  "threshold": null,
  "confidence_notes": "Based only on recorded telemetry and the supplied inventory.",
  "recommended_next_step": "Inspect the authorized ROS graph and compare node identities with the approved inventory.",
  "requires_human_approval": true,
  "automatic_action_taken": false,
  "incident_start_sim_ns": 2541683333333,
  "incident_end_sim_ns": 2571183333333
}
```

## unauthorized_subscription_L1_npc10_seed3

- Class: `unauthorized_subscription`; seed `3`; total alerts: **18**.
- Attack window: `2655583333333` to `2684566666666` sim ns.

| Rule ID | Alerts | First fired | Last fired |
|---|---:|---|---|
| late_messages_observed | 2 | before (-34.817s from start) | before (-34.817s from start) |
| node_set_hash_change | 2 | before (-42.317s from start) | before (-0.817s from start) |
| parameter_event_outside_approved_window | 1 | before (-0.817s from start) | before (-0.817s from start) |
| random_forest | 1 | inside (+0.183s from start) | inside (+0.183s from start) |
| subscriber_count_above_policy | 2 | before (-0.317s from start) | before (-0.317s from start) |
| topic_gap_above_policy | 3 | before (-42.317s from start) | before (-42.317s from start) |
| topic_rate_out_of_band | 3 | before (-42.317s from start) | before (-42.317s from start) |
| topic_stamp_lag_above_policy | 2 | before (-34.817s from start) | before (-34.817s from start) |
| unapproved_node | 2 | before (-0.817s from start) | before (-0.817s from start) |

Most relevant alert: `subscriber_count_above_policy` at before (-0.317s from start).

```json
{
  "alert_id": "410d53798e511a9a08e8",
  "timestamp_sim_ns": 2655266666666,
  "run_id": "unauthorized_subscription_L1_npc10_seed3",
  "source": "policy",
  "rule_or_model": "subscriber_count_above_policy",
  "affected": {
    "type": "topic",
    "name": "/imu_mon"
  },
  "evidence": {
    "topic": "/imu_mon",
    "column": "imu_mon.sub_count",
    "observed_count": 3.0,
    "approved_max_count": 2,
    "merged_finding_count": 59,
    "sample_evidence": [
      {
        "topic": "/imu_mon",
        "column": "imu_mon.sub_count",
        "observed_count": 3.0,
        "approved_max_count": 2
      },
      {
        "topic": "/imu_mon",
        "column": "imu_mon.sub_count",
        "observed_count": 3.0,
        "approved_max_count": 2
      },
      {
        "topic": "/imu_mon",
        "column": "imu_mon.sub_count",
        "observed_count": 3.0,
        "approved_max_count": 2
      },
      {
        "topic": "/imu_mon",
        "column": "imu_mon.sub_count",
        "observed_count": 3.0,
        "approved_max_count": 2
      },
      {
        "topic": "/imu_mon",
        "column": "imu_mon.sub_count",
        "observed_count": 3.0,
        "approved_max_count": 2
      }
    ]
  },
  "what_this_does_not_prove": "A subscriber count increase does not identify the subscriber or prove that payloads were read.",
  "severity": "high",
  "score": null,
  "threshold": null,
  "confidence_notes": "Based only on recorded telemetry and the supplied inventory.",
  "recommended_next_step": "Inspect endpoint identities using an authorized ROS graph source and verify the topic policy.",
  "requires_human_approval": true,
  "automatic_action_taken": false,
  "incident_start_sim_ns": 2655266666666,
  "incident_end_sim_ns": 2684266666666
}
```

Alert ID check: **32 IDs**, all exactly 20 lowercase hexadecimal characters.
