# Data-leakage audit and external-data test

## Summary

- Dataset: 306 indexed simulator runs, 102 per seed; no external data folder was present.
- Overall verdict: **Leakage was found: the checked-in ROS policy limits use seed-3 normal telemetry, and the same scenario definitions recur in the held-out seed. The two fitted ML models and their imputers/scalers do not use seed 3. Near-duplicate trajectory checks did not find copied runs. Startup missingness and constant/cumulative inputs are small or non-informative; continuous joined-stream inference can span segments. The shuffled-label event metric is inconclusive because the selected threshold saturates alerts.**
- Shipped models and thresholds were not retrained or re-thresholded; separate within-run label-shuffle experiment bundles were saved under `models/experiments/`.

## Check results

| Check | Result | Finding |
|---|---|---|
| split_integrity | **FAIL** | No run paths cross splits, but all 102 logical class/attack/level/NPC scenario keys recur in all three seeds. Noise subset repeats all 12 of its scenario keys. Seed 3 is a replicate split, not unseen-scenario generalization. |
| near_duplicate_runs | **PASS** | 306 within-scenario seed-pair comparisons across 23 physical IMU/odometry fields; median pairwise median column correlation is low; no exact sensor rows or correlations >=0.99. |
| feature_leakage | **FAIL** | No direct time/ID/label/path feature names. Found per-run constants, small label-dependent startup missingness, and two cumulative collector counters that are constant zero. |
| model_preprocessing_fit_scope | **PASS** | Saved model imputer/scaler statistics match seed-1/2 recomputation to floating-point tolerance; training code fits only seeds 1-2. |
| approved_inventory_fit_scope | **FAIL** | Hash set and publisher/subscriber counts match training-only provenance, but rule gap/lag/late limits match all-normal seed1-3 data. A seed1-2-only sensitivity changes seed3 rule false alerts from 58 (41.115/h) to 52 (36.861/h). |
| test_tuning | **FAIL** | Model thresholds/hyperparameters are chosen on seed 1/2 only, but the checked-in inventory rule limits were estimated from seed-3 normal telemetry; this is test-informed policy tuning. |
| causal_run_bounded_features | **FAIL** | Training features are causal and constructed per run. In monitor continuous mode, _ordered_slices returns one frame across manifest joins, so differences/rolling windows can span segments unless reset_at_joins is enabled. |
| random_prefix_timing | **PASS** | With fixed random 0-20 s cuts, selected noise recall stayed 9/9; selected telemetry-model recall stayed 36/99, with per-class results recorded below. No evidence of an absolute-start-time shortcut. |
| within_run_label_shuffle | **FAIL** | Event recall remained high after within-run shuffling, but the validation-selected thresholds flagged 74.1% of noise rows and 97.5% of security rows; precision was near test prevalence and false alerts exploded. The test is inconclusive, not proof of feature leakage. |
| inference_path_or_name_hints | **PASS** | Paths/run IDs are used for file loading or alert metadata only; model features drop time/labels and monitor strips identity columns before scoring. |
| external_real_data | **NOT CHECKED** | No external_data/ folder or external CSV was supplied; no external metrics were fabricated. |

## 1. Split integrity

Each split's run IDs are listed in `leakage_audit.json` under `splits`. Noise-model candidate fit and threshold-selection lists contain 12 run IDs each; the security model fits 21 eligible run IDs per seed (normal plus supported telemetry attack classes), and evaluates all 102 seed-3 runs. There is no identical run path across splits. However, the logical scenario key `(type, attack_name, npc, level)` repeats in all seeds: 102/102 security keys and 12/12 noise keys. This is a fixed-seed replicate test, not unseen-scenario generalization.

## 2. Cross-seed near duplicates

For each scenario, each seed pair was compared by row position over the 23 common physical IMU/odometry columns, excluding age and stamp-lag metadata. Each pair statistic is in JSON; the table below reports the median of the three pairwise median column correlations for every class/level/NPC combination. Exact row fractions were zero for all pairs.

| Class | Level | NPC | Median correlation (3 pairs) | Max pair correlation | Exact-row fraction |
|---|---:|---:|---:|---:|---:|
| bias_drift | 1 | 10 | 0.0880 | 0.2452 | 0.0000 |
| bias_drift | 2 | 10 | 0.1499 | 0.2445 | 0.0000 |
| bias_drift | 3 | 10 | 0.6002 | 0.6812 | 0.0000 |
| bias_drift | 1 | 20 | 0.0678 | 0.2532 | 0.0000 |
| bias_drift | 2 | 20 | 0.2224 | 0.4370 | 0.0000 |
| bias_drift | 3 | 20 | 0.6642 | 0.6875 | 0.0000 |
| bias_drift | 1 | 30 | 0.1408 | 0.2708 | 0.0000 |
| bias_drift | 2 | 30 | 0.3105 | 0.3322 | 0.0000 |
| bias_drift | 3 | 30 | 0.6685 | 0.7461 | 0.0000 |
| clock_skew | 1 | 10 | 0.0001 | 0.0880 | 0.0000 |
| clock_skew | 2 | 10 | 0.0748 | 0.4717 | 0.0000 |
| clock_skew | 3 | 10 | -0.0617 | -0.0152 | 0.0000 |
| clock_skew | 1 | 20 | -0.0897 | 0.7376 | 0.0000 |
| clock_skew | 2 | 20 | 0.0039 | 0.0372 | 0.0000 |
| clock_skew | 3 | 20 | -0.1574 | 0.4536 | 0.0000 |
| clock_skew | 1 | 30 | 0.0665 | 0.0839 | 0.0000 |
| clock_skew | 2 | 30 | -0.0531 | 0.0441 | 0.0000 |
| clock_skew | 3 | 30 | 0.0093 | 0.0251 | 0.0000 |
| delay | 1 | 10 | -0.1128 | -0.0872 | 0.0000 |
| delay | 2 | 10 | -0.1067 | -0.1028 | 0.0000 |
| delay | 3 | 10 | -0.0432 | 0.1197 | 0.0000 |
| delay | 1 | 20 | -0.0950 | 0.0045 | 0.0000 |
| delay | 2 | 20 | 0.0237 | 0.0999 | 0.0000 |
| delay | 3 | 20 | 0.0554 | 0.0891 | 0.0000 |
| delay | 1 | 30 | 0.0737 | 0.3872 | 0.0000 |
| delay | 2 | 30 | 0.1115 | 0.3883 | 0.0000 |
| delay | 3 | 30 | 0.0926 | 0.1134 | 0.0000 |
| drop | 1 | 10 | -0.0295 | 0.0100 | 0.0000 |
| drop | 2 | 10 | -0.0597 | -0.0323 | 0.0000 |
| drop | 3 | 10 | -0.1088 | 0.4758 | 0.0000 |
| drop | 1 | 20 | 0.2106 | 0.4818 | 0.0000 |
| drop | 2 | 20 | 0.4853 | 0.5094 | 0.0000 |
| drop | 3 | 20 | 0.0999 | 0.3112 | 0.0000 |
| drop | 1 | 30 | 0.1010 | 0.2320 | 0.0000 |
| drop | 2 | 30 | 0.0390 | 0.4308 | 0.0000 |
| drop | 3 | 30 | 0.0040 | 0.0527 | 0.0000 |
| duplicate | 1 | 10 | 0.0585 | 0.4221 | 0.0000 |
| duplicate | 2 | 10 | -0.1466 | 0.4217 | 0.0000 |
| duplicate | 3 | 10 | -0.0985 | -0.0128 | 0.0000 |
| duplicate | 1 | 20 | -0.0256 | 0.0010 | 0.0000 |
| duplicate | 2 | 20 | 0.0147 | 0.4767 | 0.0000 |
| duplicate | 3 | 20 | -0.1039 | 0.4849 | 0.0000 |
| duplicate | 1 | 30 | -0.0236 | 0.0886 | 0.0000 |
| duplicate | 2 | 30 | -0.0620 | 0.0514 | 0.0000 |
| duplicate | 3 | 30 | -0.0309 | 0.0874 | 0.0000 |
| false_contact | 1 | 10 | -0.0811 | -0.0348 | 0.0000 |
| false_contact | 1 | 20 | -0.0802 | 0.0018 | 0.0000 |
| false_contact | 1 | 30 | 0.1511 | 0.4044 | 0.0000 |
| flood | 1 | 10 | 0.0595 | 0.6562 | 0.0000 |
| flood | 2 | 10 | -0.0972 | 0.7585 | 0.0000 |
| flood | 3 | 10 | 0.0506 | 0.0722 | 0.0000 |
| flood | 1 | 20 | -0.0397 | 0.1262 | 0.0000 |
| flood | 2 | 20 | 0.0737 | 0.2633 | 0.0000 |
| flood | 3 | 20 | 0.0302 | 0.0534 | 0.0000 |
| flood | 1 | 30 | -0.0956 | 0.0621 | 0.0000 |
| flood | 2 | 30 | -0.1858 | 0.0519 | 0.0000 |
| flood | 3 | 30 | -0.0738 | 0.0688 | 0.0000 |
| freeze | 1 | 10 | -0.0382 | 0.0030 | 0.0000 |
| freeze | 1 | 20 | -0.0016 | 0.1570 | 0.0000 |
| freeze | 1 | 30 | -0.0036 | 0.5013 | 0.0000 |
| jump | 1 | 10 | -0.1008 | 0.0020 | 0.0000 |
| jump | 2 | 10 | 0.0067 | 0.0767 | 0.0000 |
| jump | 3 | 10 | -0.0019 | 0.0110 | 0.0000 |
| jump | 1 | 20 | -0.0544 | -0.0425 | 0.0000 |
| jump | 2 | 20 | -0.0367 | 0.0447 | 0.0000 |
| jump | 3 | 20 | 0.0139 | 0.0807 | 0.0000 |
| jump | 1 | 30 | 0.0999 | 0.5145 | 0.0000 |
| jump | 2 | 30 | 0.0643 | 0.1042 | 0.0000 |
| jump | 3 | 30 | 0.0100 | 0.2189 | 0.0000 |
| missed_contact | 1 | 10 | -0.1207 | -0.0049 | 0.0000 |
| missed_contact | 1 | 20 | -0.0596 | 0.0831 | 0.0000 |
| missed_contact | 1 | 30 | 0.1387 | 0.3619 | 0.0000 |
| noise | 1 | 10 | 0.0042 | 0.0205 | 0.0000 |
| noise | 2 | 10 | 0.0517 | 0.5387 | 0.0000 |
| noise | 3 | 10 | 0.0314 | 0.0562 | 0.0000 |
| noise | 1 | 20 | -0.0501 | 0.0912 | 0.0000 |
| noise | 2 | 20 | 0.0508 | 0.7171 | 0.0000 |
| noise | 3 | 20 | 0.0003 | 0.0448 | 0.0000 |
| noise | 1 | 30 | 0.0432 | 0.4584 | 0.0000 |
| noise | 2 | 30 | 0.0494 | 0.0682 | 0.0000 |
| noise | 3 | 30 | 0.0505 | 0.0884 | 0.0000 |
| param_tamper | 1 | 10 | -0.0356 | 0.6231 | 0.0000 |
| param_tamper | 1 | 20 | 0.0831 | 0.4351 | 0.0000 |
| param_tamper | 1 | 30 | 0.1289 | 0.4161 | 0.0000 |
| replay | 1 | 10 | -0.0992 | -0.0821 | 0.0000 |
| replay | 1 | 20 | -0.0205 | 0.1080 | 0.0000 |
| replay | 1 | 30 | 0.4196 | 0.4298 | 0.0000 |
| service_abuse | 1 | 10 | -0.0272 | 0.0776 | 0.0000 |
| service_abuse | 1 | 20 | -0.0845 | 0.0957 | 0.0000 |
| service_abuse | 1 | 30 | -0.0462 | 0.1174 | 0.0000 |
| spoof | 1 | 10 | -0.0616 | 0.4928 | 0.0000 |
| spoof | 1 | 20 | 0.2862 | 0.5058 | 0.0000 |
| spoof | 1 | 30 | -0.0874 | 0.6930 | 0.0000 |
| unauthorized_node | 1 | 10 | 0.0388 | 0.0774 | 0.0000 |
| unauthorized_node | 1 | 20 | -0.0243 | 0.0694 | 0.0000 |
| unauthorized_node | 1 | 30 | -0.0090 | 0.0227 | 0.0000 |
| unauthorized_subscription | 1 | 10 | -0.0847 | -0.0063 | 0.0000 |
| unauthorized_subscription | 1 | 20 | 0.1227 | 0.4736 | 0.0000 |
| unauthorized_subscription | 1 | 30 | -0.1155 | 0.5842 | 0.0000 |
| none | 0 | 10 | 0.0367 | 0.2085 | 0.0000 |
| none | 0 | 20 | -0.0236 | 0.1201 | 0.0000 |
| none | 0 | 30 | 0.0982 | 0.1091 | 0.0000 |

Across 306 seed pairs: median pair-median correlation 0.0190; 10th percentile -0.1111 and 90th percentile 0.4453; maximum 0.7585; no pair reached 0.99; median exact-row fraction 0.0000. No copied/near-identical sensor trajectories were found, but scenario identity still overlaps.

## 3. Feature leakage and risks

Neither feature list contains a direct absolute-time, row-index, run/folder ID, seed, label, attack-class, path, or scenario-name input. Time is used to calculate first differences per second; values and labels are not included as features. The complete feature list is represented by the arrays in JSON and repeated below.
### noise_detector

Input features (87):

`rate::contact.age_s`, `rate::contact.data`, `rate::imu.age_s`, `rate::imu.angular_velocity.x`, `rate::imu.angular_velocity.y`, `rate::imu.angular_velocity.z`, `rate::imu.linear_acceleration.x`, `rate::imu.linear_acceleration.y`, `rate::imu.linear_acceleration.z`, `rate::imu.orientation.w`, `rate::imu.orientation.x`, `rate::imu.orientation.y`, `rate::imu.orientation.z`, `rate::imu.stamp_lag_s`, `rate::odom.age_s`, `rate::odom.pose.pose.orientation.w`, `rate::odom.pose.pose.orientation.x`, `rate::odom.pose.pose.orientation.y`, `rate::odom.pose.pose.orientation.z`, `rate::odom.pose.pose.position.x`, `rate::odom.pose.pose.position.y`, `rate::odom.pose.pose.position.z`, `rate::odom.stamp_lag_s`, `rate::odom.twist.twist.angular.x`, `rate::odom.twist.twist.angular.y`, `rate::odom.twist.twist.angular.z`, `rate::odom.twist.twist.linear.x`, `rate::odom.twist.twist.linear.y`, `rate::odom.twist.twist.linear.z`, `raw::contact.age_s`, `raw::contact.data`, `raw::imu.age_s`, `raw::imu.angular_velocity.x`, `raw::imu.angular_velocity.y`, `raw::imu.angular_velocity.z`, `raw::imu.linear_acceleration.x`, `raw::imu.linear_acceleration.y`, `raw::imu.linear_acceleration.z`, `raw::imu.orientation.w`, `raw::imu.orientation.x`, `raw::imu.orientation.y`, `raw::imu.orientation.z`, `raw::imu.stamp_lag_s`, `raw::odom.age_s`, `raw::odom.pose.pose.orientation.w`, `raw::odom.pose.pose.orientation.x`, `raw::odom.pose.pose.orientation.y`, `raw::odom.pose.pose.orientation.z`, `raw::odom.pose.pose.position.x`, `raw::odom.pose.pose.position.y`, `raw::odom.pose.pose.position.z`, `raw::odom.stamp_lag_s`, `raw::odom.twist.twist.angular.x`, `raw::odom.twist.twist.angular.y`, `raw::odom.twist.twist.angular.z`, `raw::odom.twist.twist.linear.x`, `raw::odom.twist.twist.linear.y`, `raw::odom.twist.twist.linear.z`, `rolling_std::contact.age_s`, `rolling_std::contact.data`, `rolling_std::imu.age_s`, `rolling_std::imu.angular_velocity.x`, `rolling_std::imu.angular_velocity.y`, `rolling_std::imu.angular_velocity.z`, `rolling_std::imu.linear_acceleration.x`, `rolling_std::imu.linear_acceleration.y`, `rolling_std::imu.linear_acceleration.z`, `rolling_std::imu.orientation.w`, `rolling_std::imu.orientation.x`, `rolling_std::imu.orientation.y`, `rolling_std::imu.orientation.z`, `rolling_std::imu.stamp_lag_s`, `rolling_std::odom.age_s`, `rolling_std::odom.pose.pose.orientation.w`, `rolling_std::odom.pose.pose.orientation.x`, `rolling_std::odom.pose.pose.orientation.y`, `rolling_std::odom.pose.pose.orientation.z`, `rolling_std::odom.pose.pose.position.x`, `rolling_std::odom.pose.pose.position.y`, `rolling_std::odom.pose.pose.position.z`, `rolling_std::odom.stamp_lag_s`, `rolling_std::odom.twist.twist.angular.x`, `rolling_std::odom.twist.twist.angular.y`, `rolling_std::odom.twist.twist.angular.z`, `rolling_std::odom.twist.twist.linear.x`, `rolling_std::odom.twist.twist.linear.y`, `rolling_std::odom.twist.twist.linear.z`

Features constant within at least one run (3):

- `rate::contact.data`: 36 runs
- `raw::contact.data`: 36 runs
- `rolling_std::contact.data`: 36 runs

Features with normal/attack NaN-rate differences (58):

- `rolling_std::contact.age_s`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::contact.data`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::imu.age_s`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::imu.angular_velocity.x`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::imu.angular_velocity.y`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::imu.angular_velocity.z`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::imu.linear_acceleration.x`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::imu.linear_acceleration.y`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::imu.linear_acceleration.z`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::imu.orientation.w`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::imu.orientation.x`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::imu.orientation.y`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::imu.orientation.z`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::imu.stamp_lag_s`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::odom.age_s`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::odom.pose.pose.orientation.w`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::odom.pose.pose.orientation.x`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::odom.pose.pose.orientation.y`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::odom.pose.pose.orientation.z`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::odom.pose.pose.position.x`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::odom.pose.pose.position.y`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::odom.pose.pose.position.z`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::odom.stamp_lag_s`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::odom.twist.twist.angular.x`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::odom.twist.twist.angular.y`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::odom.twist.twist.angular.z`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::odom.twist.twist.linear.x`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::odom.twist.twist.linear.y`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rolling_std::odom.twist.twist.linear.z`: normal 0.116378%, attack 0.000000%, delta 0.116378%
- `rate::contact.age_s`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::contact.data`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::imu.age_s`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::imu.angular_velocity.x`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::imu.angular_velocity.y`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::imu.angular_velocity.z`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::imu.linear_acceleration.x`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::imu.linear_acceleration.y`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::imu.linear_acceleration.z`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::imu.orientation.w`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::imu.orientation.x`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::imu.orientation.y`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::imu.orientation.z`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::imu.stamp_lag_s`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::odom.age_s`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::odom.pose.pose.orientation.w`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::odom.pose.pose.orientation.x`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::odom.pose.pose.orientation.y`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::odom.pose.pose.orientation.z`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::odom.pose.pose.position.x`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::odom.pose.pose.position.y`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::odom.pose.pose.position.z`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::odom.stamp_lag_s`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::odom.twist.twist.angular.x`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::odom.twist.twist.angular.y`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::odom.twist.twist.angular.z`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::odom.twist.twist.linear.x`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::odom.twist.twist.linear.y`: normal 0.029094%, attack 0.000000%, delta 0.029094%
- `rate::odom.twist.twist.linear.z`: normal 0.029094%, attack 0.000000%, delta 0.029094%

### security_telemetry_model

Input features (69):

`collector_late_writes`, `collector_queue_drops`, `contact_mon.late_count`, `contact_mon.max_gap_s`, `contact_mon.pub_count`, `contact_mon.rate_hz`, `contact_mon.sub_count`, `derived::has_new_nodes`, `derived::new_node_count`, `derived::node_hash_changed`, `derived::rate::collector_late_writes`, `derived::rate::collector_queue_drops`, `derived::rate::contact_mon.late_count`, `derived::rate::contact_mon.max_gap_s`, `derived::rate::contact_mon.pub_count`, `derived::rate::contact_mon.rate_hz`, `derived::rate::contact_mon.sub_count`, `derived::rate::imu_mon.late_count`, `derived::rate::imu_mon.max_gap_s`, `derived::rate::imu_mon.pub_count`, `derived::rate::imu_mon.rate_hz`, `derived::rate::imu_mon.stamp_lag_mean_s`, `derived::rate::imu_mon.sub_count`, `derived::rate::node_count`, `derived::rate::odom_mon.late_count`, `derived::rate::odom_mon.max_gap_s`, `derived::rate::odom_mon.pub_count`, `derived::rate::odom_mon.rate_hz`, `derived::rate::odom_mon.stamp_lag_mean_s`, `derived::rate::odom_mon.sub_count`, `derived::rate::param_event_count`, `derived::rate::service_call_count`, `derived::rolling_std::collector_late_writes`, `derived::rolling_std::collector_queue_drops`, `derived::rolling_std::contact_mon.late_count`, `derived::rolling_std::contact_mon.max_gap_s`, `derived::rolling_std::contact_mon.pub_count`, `derived::rolling_std::contact_mon.rate_hz`, `derived::rolling_std::contact_mon.sub_count`, `derived::rolling_std::imu_mon.late_count`, `derived::rolling_std::imu_mon.max_gap_s`, `derived::rolling_std::imu_mon.pub_count`, `derived::rolling_std::imu_mon.rate_hz`, `derived::rolling_std::imu_mon.stamp_lag_mean_s`, `derived::rolling_std::imu_mon.sub_count`, `derived::rolling_std::node_count`, `derived::rolling_std::odom_mon.late_count`, `derived::rolling_std::odom_mon.max_gap_s`, `derived::rolling_std::odom_mon.pub_count`, `derived::rolling_std::odom_mon.rate_hz`, `derived::rolling_std::odom_mon.stamp_lag_mean_s`, `derived::rolling_std::odom_mon.sub_count`, `derived::rolling_std::param_event_count`, `derived::rolling_std::service_call_count`, `imu_mon.late_count`, `imu_mon.max_gap_s`, `imu_mon.pub_count`, `imu_mon.rate_hz`, `imu_mon.stamp_lag_mean_s`, `imu_mon.sub_count`, `node_count`, `odom_mon.late_count`, `odom_mon.max_gap_s`, `odom_mon.pub_count`, `odom_mon.rate_hz`, `odom_mon.stamp_lag_mean_s`, `odom_mon.sub_count`, `param_event_count`, `service_call_count`

Features constant within at least one run (50):

- `collector_late_writes`: 306 runs
- `collector_queue_drops`: 306 runs
- `contact_mon.late_count`: 306 runs
- `contact_mon.max_gap_s`: 96 runs
- `contact_mon.pub_count`: 290 runs
- `contact_mon.sub_count`: 306 runs
- `derived::has_new_nodes`: 261 runs
- `derived::new_node_count`: 261 runs
- `derived::rate::collector_late_writes`: 306 runs
- `derived::rate::collector_queue_drops`: 306 runs
- `derived::rate::contact_mon.late_count`: 306 runs
- `derived::rate::contact_mon.max_gap_s`: 96 runs
- `derived::rate::contact_mon.pub_count`: 290 runs
- `derived::rate::contact_mon.sub_count`: 306 runs
- `derived::rate::imu_mon.late_count`: 159 runs
- `derived::rate::imu_mon.max_gap_s`: 95 runs
- `derived::rate::imu_mon.pub_count`: 282 runs
- `derived::rate::imu_mon.sub_count`: 297 runs
- `derived::rate::odom_mon.late_count`: 171 runs
- `derived::rate::odom_mon.max_gap_s`: 87 runs
- `derived::rate::odom_mon.pub_count`: 290 runs
- `derived::rate::odom_mon.sub_count`: 297 runs
- `derived::rate::param_event_count`: 17 runs
- `derived::rate::service_call_count`: 297 runs
- `derived::rolling_std::collector_late_writes`: 306 runs
- `derived::rolling_std::collector_queue_drops`: 306 runs
- `derived::rolling_std::contact_mon.late_count`: 306 runs
- `derived::rolling_std::contact_mon.max_gap_s`: 96 runs
- `derived::rolling_std::contact_mon.pub_count`: 290 runs
- `derived::rolling_std::contact_mon.sub_count`: 306 runs
- `derived::rolling_std::imu_mon.late_count`: 159 runs
- `derived::rolling_std::imu_mon.max_gap_s`: 95 runs
- `derived::rolling_std::imu_mon.pub_count`: 282 runs
- `derived::rolling_std::imu_mon.sub_count`: 297 runs
- `derived::rolling_std::odom_mon.late_count`: 171 runs
- `derived::rolling_std::odom_mon.max_gap_s`: 87 runs
- `derived::rolling_std::odom_mon.pub_count`: 290 runs
- `derived::rolling_std::odom_mon.sub_count`: 297 runs
- `derived::rolling_std::param_event_count`: 17 runs
- `derived::rolling_std::service_call_count`: 297 runs
- `imu_mon.late_count`: 159 runs
- `imu_mon.max_gap_s`: 95 runs
- `imu_mon.pub_count`: 282 runs
- `imu_mon.sub_count`: 297 runs
- `odom_mon.late_count`: 171 runs
- `odom_mon.max_gap_s`: 87 runs
- `odom_mon.pub_count`: 290 runs
- `odom_mon.sub_count`: 297 runs
- `param_event_count`: 17 runs
- `service_call_count`: 297 runs

Features with normal/attack NaN-rate differences (46):

- `derived::rate::imu_mon.stamp_lag_mean_s`: normal 1.618568%, attack 0.000000%, delta 1.618568%
- `derived::rate::odom_mon.stamp_lag_mean_s`: normal 1.618568%, attack 0.000000%, delta 1.618568%
- `derived::rolling_std::imu_mon.stamp_lag_mean_s`: normal 1.618568%, attack 0.000000%, delta 1.618568%
- `derived::rolling_std::odom_mon.stamp_lag_mean_s`: normal 1.618568%, attack 0.000000%, delta 1.618568%
- `imu_mon.stamp_lag_mean_s`: normal 0.867002%, attack 0.000000%, delta 0.867002%
- `odom_mon.stamp_lag_mean_s`: normal 0.867002%, attack 0.000000%, delta 0.867002%
- `derived::rate::collector_late_writes`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::collector_queue_drops`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::contact_mon.late_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::contact_mon.max_gap_s`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::contact_mon.pub_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::contact_mon.rate_hz`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::contact_mon.sub_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::imu_mon.late_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::imu_mon.max_gap_s`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::imu_mon.pub_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::imu_mon.rate_hz`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::imu_mon.sub_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::node_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::odom_mon.late_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::odom_mon.max_gap_s`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::odom_mon.pub_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::odom_mon.rate_hz`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::odom_mon.sub_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::param_event_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rate::service_call_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::collector_late_writes`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::collector_queue_drops`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::contact_mon.late_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::contact_mon.max_gap_s`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::contact_mon.pub_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::contact_mon.rate_hz`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::contact_mon.sub_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::imu_mon.late_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::imu_mon.max_gap_s`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::imu_mon.pub_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::imu_mon.rate_hz`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::imu_mon.sub_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::node_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::odom_mon.late_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::odom_mon.max_gap_s`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::odom_mon.pub_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::odom_mon.rate_hz`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::odom_mon.sub_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::param_event_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%
- `derived::rolling_std::service_call_count`: normal 0.751566%, attack 0.000000%, delta 0.751566%

### Cumulative counter and constant-value note

The dataset guide defines `collector_queue_drops` and `collector_late_writes` as cumulative counters. They were zero in every run; their raw and derived inputs are constant/non-informative. `param_event_count`, `service_call_count`, and `*.late_count` are one-second-window counts, not cumulative counters. Several graph/monitor fields are also constant within individual runs; complete per-feature counts are above and in JSON.

## 4. Fitting and preprocessing provenance

| Model | Evidence | Result |
|---|---|---|
| Noise detector | `src/ziaxen_agent/training.py:49-107`; recomputed feature medians on seed 1-2 | Imputer max absolute difference: Isolation Forest 2.51e-15; Random Forest 6.74e-14. IF scaler center difference 0. Seed 3 not used for fitting, median imputation, scaler, or normal reference. |
| Security telemetry model | `src/ziaxen_agent/security/models.py:104-162`; recomputed feature medians on eligible seed 1-2 | Imputer max absolute difference 0 for both models; IF scaler center difference 0. Seed 3 not loaded by training. |
| Inventory hashes | `src/ziaxen_agent/security/inventory.py:430-433` and values recomputed by seed | Approved hash set equals seed1-2 normal values; seed3 adds no unique hash. Code still iterates all normal runs. |
| Publisher/subscriber counts | `src/ziaxen_agent/security/inventory.py:327-378` | Baseline is the first normal manifest, `normal_npc10_seed1`; publisher max 1 and subscriber max 2 for each topic. Training split only. |
| Inventory rate/gap/lag/late limits | `src/ziaxen_agent/security/inventory.py:338-433` | **Not training-only:** normal telemetry from all seeds feeds quantiles; every indexed manifest is read for domains. Seed3 contributes no new domain ID, but its telemetry changes limits. |

### Seed-3 contribution to policy metrics

The checked-in all-seed inventory gives 58 false rule episodes / 1.410694 h = 41.115/h. A temporary inventory recomputed from normal seed 1-2 only gives 52 / 1.410694 h = 36.861/h. The all-seed policy therefore adds 6 seed-3 false episodes (+4.253/h) and 12 negative-row false positives (205 vs 193); event detections by class are unchanged. The shipped inventory was not modified. Hash set, publisher/subscriber counts, and domain-ID set matched training-only values. Full values are in JSON.

## 5. Tuning choices and history search

Source code and current training/evaluation report search found no seed-3 selection of model thresholds, hyperparameters, or event tolerances. Noise candidates are fit on seed 1, selected and thresholded on seed 2, then refit on seeds 1-2; security training explicitly loads only seeds 1-2. Seed-3 references in the training/evaluation reports are reserved for test scoring. The exception is inventory rule limits: the checked-in bootstrap uses all seeds for some policy quantiles, as measured above.

## 6. Causality and run boundaries

Noise rolling standard deviations are trailing 25-row windows (0.5 s at 50 Hz); security rolling standard deviations are trailing 5 telemetry rows. Neither is centered or forward-looking. Training feature extraction runs separately per recording. In monitor continuous mode, however, `_ordered_slices` returns one frame when `reset_at_joins` is false, so `diff` and rolling windows can cross synthetic joins; reset-at-joins must be enabled to keep stream segments bounded.

## 7. Random 0-20 s prefix cut

Offsets were drawn from a fixed RNG seed and applied per seed-3 run. Models and thresholds were frozen; causal features were re-engineered from the retained rows. False alerts are contiguous positive episodes over label-negative rows after the 15 s startup exclusion and outside event tolerances, divided by negative exposure time.

| Detector | Event recall current | Event recall after cut | False alert episodes/hour current | After cut |
|---|---:|---:|---:|---:|
| noise detector | 1.000 (9/9) | 1.000 (9/9) | 83.729 | 111.973 |
| security telemetry model | 0.364 (36/99) | 0.364 (36/99) | 0.709 | 0.904 |

Security per-class event detections were unchanged by the cut:
- `bias_drift`: 0/9 current and after cut
- `clock_skew`: 0/9 current and after cut
- `delay`: 3/9 current and after cut
- `drop`: 0/9 current and after cut
- `duplicate`: 9/9 current and after cut
- `false_contact`: 0/3 current and after cut
- `flood`: 9/9 current and after cut
- `freeze`: 0/3 current and after cut
- `jump`: 0/9 current and after cut
- `missed_contact`: 0/3 current and after cut
- `noise`: 0/9 current and after cut
- `param_tamper`: 3/3 current and after cut
- `replay`: 0/3 current and after cut
- `service_abuse`: 3/3 current and after cut
- `spoof`: 3/3 current and after cut
- `unauthorized_node`: 3/3 current and after cut
- `unauthorized_subscription`: 3/3 current and after cut

No event-recall drop was observed. False-alert rates shift partly because cutting prefixes changes negative exposure hours; this is not evidence that the start timestamp is an input feature. Exact offsets and all metrics are in JSON.

## 8. Within-run label shuffle sanity check

Each training run's labels were shuffled independently with a recorded fixed seed, preserving its positive-row count. Candidate models used the same pipelines; thresholds were selected on shuffled seed 2 and final experiment models were fit on seeds 1-2. Experiment bundles are ignored under `models/experiments/`.

| Model | Selected | Shuffled validation threshold | Seed-3 event recall | Predicted-positive rows | Test precision | Test FPR | False alert episodes/hour |
|---|---|---:|---:|---:|---:|---:|---:|
| noise | random_forest | 0.209852 | 1.000 (9/9) | 74.1% | 0.333 | 0.656 | 17331.8 |
| security telemetry | random_forest | 0.193143 | 1.000 (99/99) | 97.5% | 0.304 | 0.972 | 250.2 |

Both shuffled models had high event recall, but nearly every test row was flagged for security (97.5%) and 74.1% for noise. Test precision was approximately the positive-row prevalence (30.4% vs 30.2% security; 33.3% vs 24.7% noise), with very high false-positive rates. This is a degenerate alert-saturation outcome: the high per-event recall is not meaningful evidence of generalization or proof of label leakage. The sanity check does not clear the feature pipeline; report it as inconclusive.

## 9. Inference identity/path checks

Feature engineering excludes time and labels. Monitor drops identity columns including `run_id`, `relative_path`, scenario, class, and seed before scoring. The `agent.py` input path is used to read the requested CSV; run IDs/path values may appear as separate alert metadata, not as model inputs. `node_list_hash` contributes only a change indicator, not a run/folder name.

## Part B. External real-data test

No `external_data/` directory or external CSV was supplied. No data was downloaded, and no external false-alert or fault-detection metrics are claimed. The adapter writes a mapping JSON when provided a mapping path; future datasets with more than half the expected raw sensor columns missing are marked not applicable and must not be scored. The security telemetry model cannot be tested on external sensor-only CSVs because they do not contain this project's ROS graph counters and node inventory. These results, if collected later, will be transfer estimates rather than proof of real-world performance. A valid test needs written approval, recordings from an owned ROS 2 robot/vehicle, realistic sensor noise, a ROS-driven controller, and the same telemetry collector.

## Part C. Previously completed fixes

Current security model loads under scikit-learn 1.9.1 with SHA-256 `f4ba15b24c9a33a843b733b604cb27e7f9a25ce5fdd0cfd52c3610d811a475af`; the prior 1.9.0 artifact hash was `8bcc4c491cca4d1f31f3ec657d2ef6733a371147db751643ad9f3bca44fff88e`. Earlier verification recorded 0 differing predictions across 19,514 seed-3 rows. Separate missing-`--aligned` and missing-`--telemetry` coverage tests are present. No shipped model was changed for this audit.

## Final verdict

Leaks found: the seed-3-derived inventory quantiles alter the reported rule false-alert count/rate, and the fixed scenario grid repeats in all seeds. The ML model imputers/scalers are training-only, and no near-duplicate trajectories were found. Feature missingness has a small startup-dependent label-rate difference; cumulative collector fields are constant zero. Monitor continuous state can bridge joined segments. The label-shuffle result is inconclusive because its thresholded output saturates alerts.
