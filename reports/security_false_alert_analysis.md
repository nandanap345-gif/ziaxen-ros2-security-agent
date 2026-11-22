# Rules false-alert analysis (seed 3)

Matches the evaluation false-alert mask: after 15 seconds of startup and outside event start-1.5 seconds through event stop+0.5 seconds. Episodes are contiguous flagged telemetry ticks; rule-specific episode counts can overlap and therefore do not sum to the combined episode count.

- **Combined false-alert episodes:** 58
- **False-alerted telemetry ticks:** 125
- **Normal-segment hours:** 1.410694
- **Rate:** 41.115/hour
- **Policy-alert ticks in the evaluation tolerance windows:** 80
- **False episodes inside those tolerance windows:** 0
- **Startup alert ticks excluded from evaluation:** 0
- **Before attribution:** 58 combined episodes had no source category assigned.
- **After attribution:** 58 combined episodes remain; 8 independent graph-rule episodes are categorized as residual attack activity outside the label.

The evaluation tolerance is 1.5 s before event start and 0.5 s after event stop. The separate boundary bucket uses symmetric ±1.5 s around either event boundary. Thus a rule episode just after the stop tolerance can be counted as a false normal-segment episode while still lying within ±1.5 s of the stop.

## Combined episodes by run class

| Run class | Combined false episodes |
|---|---:|
| bias_drift | 1 |
| clock_skew | 3 |
| delay | 11 |
| drop | 9 |
| duplicate | 6 |
| flood | 8 |
| jump | 2 |
| missed_contact | 1 |
| noise | 5 |
| param_tamper | 2 |
| replay | 1 |
| service_abuse | 1 |
| spoof | 7 |
| unauthorized_subscription | 1 |

## Combined episodes by boundary bucket

| Bucket | Combined false episodes |
|---|---:|
| elsewhere | 22 |
| within_1.5s_of_boundary | 36 |

## Independent per-rule episodes

Counts below are computed per rule and can overlap across rules, so do not sum them to obtain the combined episode count.

| Rule ID | False-alert category | Episodes |
|---|---|---:|
| late_messages_observed | unattributed | 21 |
| node_set_hash_change | residual_attack_activity_outside_label | 5 |
| parameter_event_outside_approved_window | unattributed | 5 |
| service_call_rate_above_policy | unattributed | 1 |
| topic_gap_above_policy | unattributed | 8 |
| topic_rate_out_of_band | unattributed | 44 |
| topic_stamp_lag_above_policy | unattributed | 19 |
| unapproved_node | residual_attack_activity_outside_label | 3 |

## Per-rule, run-class, and boundary breakdown

| Rule ID | Run class | Boundary bucket | False-alert category | Episodes |
|---|---|---|---|---:|
| late_messages_observed | bias_drift | elsewhere | unattributed | 1 |
| late_messages_observed | clock_skew | elsewhere | unattributed | 1 |
| late_messages_observed | delay | elsewhere | unattributed | 1 |
| late_messages_observed | delay | within_1.5s_of_boundary | unattributed | 6 |
| late_messages_observed | drop | elsewhere | unattributed | 2 |
| late_messages_observed | jump | elsewhere | unattributed | 2 |
| late_messages_observed | noise | elsewhere | unattributed | 5 |
| late_messages_observed | replay | elsewhere | unattributed | 1 |
| late_messages_observed | spoof | elsewhere | unattributed | 1 |
| late_messages_observed | unauthorized_subscription | elsewhere | unattributed | 1 |
| node_set_hash_change | drop | elsewhere | residual_attack_activity_outside_label | 1 |
| node_set_hash_change | spoof | elsewhere | residual_attack_activity_outside_label | 3 |
| node_set_hash_change | unauthorized_subscription | elsewhere | residual_attack_activity_outside_label | 1 |
| parameter_event_outside_approved_window | param_tamper | within_1.5s_of_boundary | unattributed | 2 |
| parameter_event_outside_approved_window | spoof | elsewhere | unattributed | 3 |
| service_call_rate_above_policy | service_abuse | within_1.5s_of_boundary | unattributed | 1 |
| topic_gap_above_policy | bias_drift | elsewhere | unattributed | 1 |
| topic_gap_above_policy | delay | elsewhere | unattributed | 1 |
| topic_gap_above_policy | drop | elsewhere | unattributed | 2 |
| topic_gap_above_policy | jump | elsewhere | unattributed | 1 |
| topic_gap_above_policy | noise | elsewhere | unattributed | 1 |
| topic_gap_above_policy | replay | elsewhere | unattributed | 1 |
| topic_gap_above_policy | unauthorized_subscription | elsewhere | unattributed | 1 |
| topic_rate_out_of_band | clock_skew | elsewhere | unattributed | 2 |
| topic_rate_out_of_band | delay | elsewhere | unattributed | 1 |
| topic_rate_out_of_band | delay | within_1.5s_of_boundary | unattributed | 9 |
| topic_rate_out_of_band | drop | elsewhere | unattributed | 1 |
| topic_rate_out_of_band | drop | within_1.5s_of_boundary | unattributed | 7 |
| topic_rate_out_of_band | duplicate | within_1.5s_of_boundary | unattributed | 6 |
| topic_rate_out_of_band | flood | within_1.5s_of_boundary | unattributed | 8 |
| topic_rate_out_of_band | missed_contact | elsewhere | unattributed | 1 |
| topic_rate_out_of_band | noise | elsewhere | unattributed | 2 |
| topic_rate_out_of_band | param_tamper | within_1.5s_of_boundary | unattributed | 1 |
| topic_rate_out_of_band | replay | elsewhere | unattributed | 2 |
| topic_rate_out_of_band | spoof | within_1.5s_of_boundary | unattributed | 3 |
| topic_rate_out_of_band | unauthorized_subscription | elsewhere | unattributed | 1 |
| topic_stamp_lag_above_policy | bias_drift | elsewhere | unattributed | 1 |
| topic_stamp_lag_above_policy | delay | elsewhere | unattributed | 1 |
| topic_stamp_lag_above_policy | delay | within_1.5s_of_boundary | unattributed | 8 |
| topic_stamp_lag_above_policy | drop | elsewhere | unattributed | 2 |
| topic_stamp_lag_above_policy | jump | elsewhere | unattributed | 1 |
| topic_stamp_lag_above_policy | noise | elsewhere | unattributed | 4 |
| topic_stamp_lag_above_policy | replay | elsewhere | unattributed | 1 |
| topic_stamp_lag_above_policy | unauthorized_subscription | elsewhere | unattributed | 1 |
| unapproved_node | spoof | elsewhere | residual_attack_activity_outside_label | 3 |

## False-alert attribution before and after

The original combined episode count and rate are unchanged by attribution. The 5 `node_set_hash_change` and 3 `unapproved_node` independent rule episodes are marked `residual_attack_activity_outside_label`; rule-level episodes can overlap, so these 8 attributions are not subtracted from the combined total.

| Category | Combined episodes | Episodes/hour |
|---|---:|---:|
| residual_attack_activity_outside_label | 5 | 3.544 |
| unattributed | 53 | 37.570 |

### Independent graph-rule attribution

| Rule ID | Episodes categorized as residual activity |
|---|---:|
| node_set_hash_change | 5 |
| unapproved_node | 3 |
