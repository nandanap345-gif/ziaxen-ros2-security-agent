# Security dataset inspection

- **Data root:** `AI_team_data`
- **Indexed / inspected runs:** 306 / 306
- **Aligned rows:** 1,396,469
- **Telemetry rows:** 58,418
- **Runs with label disagreements:** 12

## Per-class suitability for telemetry detection

| Class | Runs | Assessment | First observable change in event window | Reason |
|---|---:|---|---:|---|
| bias_drift | 27 | unusable | 1.583 s (median) | Sensor-value attack; use aligned sensor data, not telemetry alone. |
| clock_skew | 27 | limited | 0.417 s (median) | Aggregate stamp-lag/late counters may expose changes at low temporal resolution. |
| delay | 27 | limited | 0.383 s (median) | 2 Hz aggregates expose some lag/gap effects but cannot resolve message-level timing. |
| drop | 27 | limited | 1.008 s (median) | 2 Hz rate/gap aggregates may expose drops but hide individual message loss. |
| duplicate | 27 | limited | 0.417 s (median) | Aggregate rates may change; telemetry cannot establish message identity or duplication. |
| false_contact | 9 | unusable | 9.117 s (median) | Contact-value attack; telemetry does not carry contact payload values. |
| flood | 27 | usable | 0.400 s (median) | Per-topic rate and gap telemetry can expose elevated traffic in the simulated runs. |
| freeze | 9 | unusable | not observed | Sensor-value attack; use aligned sensor data, not telemetry alone. |
| jump | 27 | unusable | 22.517 s (median) | Sensor-value attack; use aligned sensor data, not telemetry alone. |
| missed_contact | 9 | unusable | not observed | No real collision occurs in these simulations; guide says it looks like normal. |
| noise | 27 | unusable | 10.517 s (median) | Sensor-value attack; telemetry does not carry sensor values. |
| normal | 9 | usable | not observed | Normal reference runs for approved-behaviour baselines. |
| param_tamper | 9 | limited | 0.200 s (median) | The guide describes this as a deliberately added weak target; effects may be indirect. |
| replay | 9 | unusable | 20.450 s (median) | Sensor-value attack; use aligned sensor data, not telemetry alone. |
| service_abuse | 9 | limited | 0.267 s (median) | The guide describes this as a deliberately added weak target; service counts are team instrumentation. |
| spoof | 9 | usable | 0.233 s (median) | New-node and publisher-count telemetry provide an observable indicator; identity is not authenticated. |
| unauthorized_node | 9 | usable | 0.117 s (median) | new_nodes and graph-count/hash telemetry identify an unexpected ROS node name. |
| unauthorized_subscription | 9 | usable | 0.350 s (median) | New-node and subscriber-count telemetry provide an observable indicator, not proof of payload access. |

## File schemas

- **aligned:** 1 schema variant(s)
  - 36 columns, observed in 306 runs
- **telemetry:** 1 schema variant(s)
  - 31 columns, observed in 306 runs
- **events:** 1 schema variant(s)
  - 8 columns, observed in 306 runs

## Missing values

Counts are summed across the inspected runs. The startup-trimmed scope uses telemetry rows at least 15 seconds after each run's first timestamp.

```json
{
  "aligned": {},
  "aligned_after_startup": {},
  "telemetry": {
    "contact_mon.stamp_lag_mean_s": 58418,
    "imu_mon.stamp_lag_mean_s": 353,
    "new_nodes": 55721,
    "odom_mon.stamp_lag_mean_s": 353
  },
  "telemetry_after_startup": {
    "contact_mon.stamp_lag_mean_s": 49238,
    "imu_mon.stamp_lag_mean_s": 69,
    "new_nodes": 46541,
    "odom_mon.stamp_lag_mean_s": 69
  },
  "events": {}
}
```

## Label disagreements

The event interval is authoritative; stored `is_attack` values are reported for audit only. A stored false negative means `is_attack=0` when events.csv labels attack; a stored false positive means `is_attack=1` outside the event.

| Run | Class | Seed | Rows | Mismatches | Stored false negatives | Stored false positives |
|---|---|---:|---:|---:|---:|---:|
| abnormal_data/02_bias_drift/bias_drift_L1_npc20_seed2 | bias_drift | 2 | 190 | 2 | 1 | 1 |
| abnormal_data/03_jump/jump_L1_npc10_seed2 | jump | 2 | 191 | 2 | 1 | 1 |
| abnormal_data/04_freeze/freeze_L1_npc30_seed3 | freeze | 3 | 188 | 2 | 1 | 1 |
| abnormal_data/08_delay/delay_L1_npc20_seed3 | delay | 3 | 190 | 2 | 1 | 1 |
| abnormal_data/10_duplicate/duplicate_L1_npc20_seed1 | duplicate | 1 | 189 | 2 | 1 | 1 |
| abnormal_data/12_flood/flood_L2_npc10_seed3 | flood | 3 | 190 | 2 | 1 | 1 |
| abnormal_data/13_spoof/spoof_L1_npc10_seed2 | spoof | 2 | 190 | 1 | 0 | 1 |
| abnormal_data/13_spoof/spoof_L1_npc20_seed2 | spoof | 2 | 241 | 1 | 1 | 0 |
| abnormal_data/13_spoof/spoof_L1_npc20_seed3 | spoof | 3 | 189 | 1 | 0 | 1 |
| abnormal_data/14_unauthorized_node/unauthorized_node_L1_npc30_seed1 | unauthorized_node | 1 | 188 | 1 | 1 | 0 |
| abnormal_data/16_param_tamper/param_tamper_L1_npc10_seed2 | param_tamper | 2 | 191 | 1 | 1 | 0 |
| abnormal_data/17_service_abuse/service_abuse_L1_npc30_seed2 | service_abuse | 2 | 188 | 1 | 0 | 1 |

## Observed node names

`/zaixen_rogue_param_tamper`, `/zaixen_rogue_service_abuse`, `/zaixen_rogue_spoof`, `/zaixen_rogue_unauthorized_node`, `/zaixen_rogue_unauthorized_subscription`

## Caveats

- The 2 Hz telemetry does not identify a host, IP, MAC, DDS participant GUID, or payload reader.
- The dataset has no movement-command topic or live bridge/domain change stream.
- Event labels, not stored is_attack values, are authoritative when they disagree.
- The dataset guide says sensors are idealized and the ego vehicle is not driven by ROS.
- raw_clean.csv is not used or read by this inspection.

The first-observable-change offsets are descriptive heuristics over 2 Hz telemetry, not model metrics or proof of malicious activity.
