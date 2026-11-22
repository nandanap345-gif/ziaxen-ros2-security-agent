# Blind robustness stress tests

- **scikit-learn runtime version:** 1.9.1.
- **Model SHA-256:** noise `cb850fc408f62eee9fbf7080baa927ab9da35c39c2204062364778522a8c8880`; security `f4ba15b24c9a33a843b733b604cb27e7f9a25ce5fdd0cfd52c3610d811a475af`.
- **Inventory status:** approved_for_offline_demo.

- **Normal-only duration:** 1.724 hours.
- **Noise levels:** Assumptions, not sensor specifications: additive zero-mean Gaussian noise is applied to linear acceleration (m/s^2), angular velocity (rad/s), odometry position (m), and linear velocity (m/s). Quaternion, age, timestamp, and contact fields are not perturbed.
- **Scope:** All outcomes are under these simulated conditions. The source sensors are idealized and the in-sim driver is not ROS-driven; this does not establish real-world performance.

| Scenario | Incidents | Health incidents | Non-health incidents | Incidents/hour |
|---|---:|---:|---:|---:|
| sensor_noise_low | 27 | 0 | 27 | 15.663 |
| sensor_noise_moderate | 29 | 0 | 29 | 16.823 |
| sensor_noise_moderate_high_1 | 45 | 0 | 45 | 26.104 |
| sensor_noise_moderate_high_2 | 153 | 0 | 153 | 88.754 |
| sensor_noise_high | 315 | 0 | 315 | 182.730 |
| telemetry_missing_ticks | 26 | 1 | 25 | 15.082 |
| telemetry_duplicated_tick | 26 | 1 | 25 | 15.082 |
| telemetry_out_of_order_ticks | 27 | 2 | 25 | 15.663 |
| telemetry_stale_period | 26 | 1 | 25 | 15.082 |
| telemetry_nan_signal_column | 211 | 201 | 10 | 122.400 |
| telemetry_timestamp_jitter | 25 | 1 | 25 | 14.502 |
| approved_maintenance_node_negative_control | 25 | 0 | 25 | 14.502 |
| unapproved_maintenance_node_positive_control | 25 | 0 | 25 | 14.502 |

## Sensor-noise robustness curve

| Level | Field sigmas (1-sigma) | Source | Incidents | Normal hours | Incidents/hour (95% Poisson CI) | Sensor-model share | Detectors |
|---|---|---|---:|---:|---|---:|---|
| low | imu.linear_acceleration_m_s2=0.01, imu.angular_velocity_rad_s=0.001, odom.pose.pose.position_m=0.005, odom.twist.twist.linear_m_s=0.01, odom.twist.twist.angular_rad_s=0.001 | Engineering assumptions for stress testing; no device datasheet was selected. | 27 | 1.724 | 15.663 (10.322, 22.788) | 7.4% | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy, sensor_noise_model, telemetry_model |
| moderate | imu.linear_acceleration_m_s2=0.05, imu.angular_velocity_rad_s=0.005, odom.pose.pose.position_m=0.02, odom.twist.twist.linear_m_s=0.05, odom.twist.twist.angular_rad_s=0.005 | Engineering assumptions for stress testing; no device datasheet was selected. | 29 | 1.724 | 16.823 (11.266, 24.160) | 13.8% | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy, sensor_noise_model, telemetry_model |
| moderate_high_1 | imu.linear_acceleration_m_s2=0.0666667, imu.angular_velocity_rad_s=0.00666667, odom.pose.pose.position_m=0.03, odom.twist.twist.linear_m_s=0.0666667, odom.twist.twist.angular_rad_s=0.00666667 | Engineering assumptions for stress testing; no device datasheet was selected. | 45 | 1.724 | 26.104 (19.041, 34.930) | 44.4% | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy, sensor_noise_model, telemetry_model |
| moderate_high_2 | imu.linear_acceleration_m_s2=0.0833333, imu.angular_velocity_rad_s=0.00833333, odom.pose.pose.position_m=0.04, odom.twist.twist.linear_m_s=0.0833333, odom.twist.twist.angular_rad_s=0.00833333 | Engineering assumptions for stress testing; no device datasheet was selected. | 153 | 1.724 | 88.754 (75.248, 103.985) | 84.3% | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy, sensor_noise_model, telemetry_model |
| high | imu.linear_acceleration_m_s2=0.1, imu.angular_velocity_rad_s=0.01, odom.pose.pose.position_m=0.05, odom.twist.twist.linear_m_s=0.1, odom.twist.twist.angular_rad_s=0.01 | Engineering assumptions for stress testing; no device datasheet was selected. | 315 | 1.724 | 182.730 (163.106, 204.065) | 93.3% | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy, sensor_noise_model, telemetry_model |

## Scenario definitions

{
  "missing_ticks": "Remove four consecutive 2 Hz rows.",
  "duplicated_tick": "Duplicate one row and its timestamp.",
  "out_of_order_ticks": "Swap two adjacent rows.",
  "stale_period": "Remove eight consecutive 2 Hz rows.",
  "nan_signal_column": "Set one numeric signal column entirely to NaN.",
  "timestamp_jitter": "Add seeded uniform \u00b10.1 s offsets to 21 timestamps."
}

## Timestamp jitter health-check assumption

{
  "deviation_threshold_s": 0.05,
  "basis": "Unvalidated monitor heuristic; not a sensor or network specification."
}

## Graph change controls

{
  "negative_control": "Add the maintenance node and its node hash to the inventory, with node count adjusted to match.",
  "positive_control": "Inject the same node/hash without adding them to the inventory."
}

## NaN telemetry case

The injected all-NaN signal column was `imu_mon.rate_hz`. The 10 non-health incidents are independent baseline timing-policy findings; they do not use that NaN column. The health findings report the empty field. The telemetry model now receives fitted-imputer replacements rather than NaN values.

| Start sim ns | End sim ns | Suspected category | Detector/rule | Evidence column |
|---:|---:|---|---|---|
| 114043333334 | 114543333334 | timing anomaly | topic_stamp_lag_above_policy | imu_mon.stamp_lag_mean_s |
| 114043333334 | 114543333334 | timing anomaly | late_messages_observed | imu_mon.late_count |
| 202636666666 | 205636666666 | timing anomaly | late_messages_observed | imu_mon.late_count |
| 202636666666 | 205636666666 | timing anomaly | late_messages_observed | odom_mon.late_count |
| 202636666666 | 205636666666 | timing anomaly | topic_gap_above_policy | contact_mon.max_gap_s |
| 202636666666 | 205636666666 | timing anomaly | topic_stamp_lag_above_policy | imu_mon.stamp_lag_mean_s |
| 408993333334 | 409993333334 | timing anomaly | topic_rate_out_of_band | contact_mon.rate_hz |
| 408993333334 | 409993333334 | timing anomaly | topic_rate_out_of_band | odom_mon.rate_hz |
| 408993333334 | 409993333334 | timing anomaly | late_messages_observed | imu_mon.late_count |
| 408993333334 | 409993333334 | timing anomaly | late_messages_observed | odom_mon.late_count |
| 408993333334 | 409993333334 | timing anomaly | topic_stamp_lag_above_policy | imu_mon.stamp_lag_mean_s |
| 408993333334 | 409993333334 | timing anomaly | topic_stamp_lag_above_policy | odom_mon.stamp_lag_mean_s |
| 1131373333332 | 1131873333332 | timing anomaly | late_messages_observed | imu_mon.late_count |
| 1310393333332 | 1310893333332 | timing anomaly | late_messages_observed | imu_mon.late_count |
| 1310393333332 | 1310893333332 | timing anomaly | late_messages_observed | odom_mon.late_count |
| 1310393333332 | 1310893333332 | timing anomaly | topic_gap_above_policy | contact_mon.max_gap_s |
| 1310393333332 | 1310893333332 | timing anomaly | topic_gap_above_policy | imu_mon.max_gap_s |
| 1310393333332 | 1310893333332 | timing anomaly | topic_stamp_lag_above_policy | imu_mon.stamp_lag_mean_s |
| 1310393333332 | 1310893333332 | timing anomaly | topic_stamp_lag_above_policy | odom_mon.stamp_lag_mean_s |
| 2240746666666 | 2240746666666 | timing anomaly | topic_rate_out_of_band | contact_mon.rate_hz |
| 2240746666666 | 2240746666666 | timing anomaly | topic_rate_out_of_band | odom_mon.rate_hz |
| 2361959999999 | 2362459999999 | timing anomaly | late_messages_observed | imu_mon.late_count |
| 2361959999999 | 2362459999999 | timing anomaly | late_messages_observed | odom_mon.late_count |
| 2361959999999 | 2362459999999 | timing anomaly | topic_gap_above_policy | contact_mon.max_gap_s |
| 2361959999999 | 2362459999999 | timing anomaly | topic_gap_above_policy | imu_mon.max_gap_s |
| 2361959999999 | 2362459999999 | timing anomaly | topic_stamp_lag_above_policy | imu_mon.stamp_lag_mean_s |
| 2361959999999 | 2362459999999 | timing anomaly | topic_stamp_lag_above_policy | odom_mon.stamp_lag_mean_s |
| 2698329999999 | 2698329999999 | timing anomaly | topic_rate_out_of_band | contact_mon.rate_hz |
| 2698329999999 | 2698329999999 | timing anomaly | topic_rate_out_of_band | odom_mon.rate_hz |
| 3112376666666 | 3112876666666 | timing anomaly | topic_gap_above_policy | contact_mon.max_gap_s |
| 3112376666666 | 3112876666666 | timing anomaly | topic_stamp_lag_above_policy | odom_mon.stamp_lag_mean_s |
| 3112376666666 | 3112876666666 | timing anomaly | late_messages_observed | imu_mon.late_count |
| 3112376666666 | 3112876666666 | timing anomaly | late_messages_observed | odom_mon.late_count |
| 3112376666666 | 3112876666666 | timing anomaly | topic_stamp_lag_above_policy | imu_mon.stamp_lag_mean_s |
| 4250503333332 | 4251003333332 | timing anomaly | late_messages_observed | imu_mon.late_count |
