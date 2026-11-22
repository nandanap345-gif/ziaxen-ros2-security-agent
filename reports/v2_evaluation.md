# Detector v2 evaluation

Seed-3 per-run and reset-mode Stream B/Stream C comparison; v1 artifacts were not modified.

| Class | v1 | v2 | v1 Wilson CI | v2 Wilson CI | v2 detector |
|---|---:|---:|---|---|---|
| noise | 9/9 | 9/9 | [0.7008549515804559, 1.0] | [0.7008549515804559, 1.0] | sensor_random_forest,v2_jump |
| delay | 9/9 | 9/9 | [0.7008549515804559, 1.0] | [0.7008549515804559, 1.0] | late_messages_observed,telemetry_random_forest,topic_gap_above_policy,topic_rate_out_of_band,topic_stamp_lag_above_policy,v2_freeze,v2_jump |
| drop | 9/9 | 9/9 | [0.7008549515804559, 1.0] | [0.7008549515804559, 1.0] | topic_gap_above_policy,topic_rate_out_of_band,v2_freeze |
| duplicate | 9/9 | 9/9 | [0.7008549515804559, 1.0] | [0.7008549515804559, 1.0] | late_messages_observed,telemetry_random_forest,topic_rate_out_of_band |
| flood | 9/9 | 9/9 | [0.7008549515804559, 1.0] | [0.7008549515804559, 1.0] | telemetry_random_forest,topic_rate_out_of_band |
| spoof | 3/3 | 3/3 | [0.4385029682449546, 1.0] | [0.4385029682449546, 1.0] | node_set_hash_change,parameter_event_outside_approved_window,publisher_count_above_policy,telemetry_random_forest,topic_rate_out_of_band,unapproved_node,v2_jump |
| unauthorized_node | 3/3 | 3/3 | [0.4385029682449546, 1.0] | [0.4385029682449546, 1.0] | node_set_hash_change,parameter_event_outside_approved_window,telemetry_random_forest,unapproved_node |
| unauthorized_subscription | 3/3 | 3/3 | [0.4385029682449546, 1.0] | [0.4385029682449546, 1.0] | node_set_hash_change,parameter_event_outside_approved_window,subscriber_count_above_policy,telemetry_random_forest,unapproved_node |
| param_tamper | 3/3 | 3/3 | [0.4385029682449546, 1.0] | [0.4385029682449546, 1.0] | node_set_hash_change,parameter_event_outside_approved_window,telemetry_random_forest,topic_rate_out_of_band,unapproved_node,v2_freeze |
| service_abuse | 3/3 | 3/3 | [0.4385029682449546, 1.0] | [0.4385029682449546, 1.0] | node_set_hash_change,parameter_event_outside_approved_window,service_call_rate_above_policy,telemetry_random_forest,unapproved_node |
| bias_drift | 6/9 | 6/9 | [0.3542021355803963, 0.879416181613089] | [0.3542021355803963, 0.879416181613089] | sensor_random_forest,v2_jump |
| jump | 2/9 | 9/9 | [0.06322510711784671, 0.5474110308930111] | [0.7008549515804559, 1.0] | sensor_random_forest,topic_rate_out_of_band,v2_jump |
| replay | 1/3 | 1/3 | [0.06149194472039621, 0.7923403991979522] | [0.06149194472039621, 0.7923403991979522] | late_messages_observed,topic_rate_out_of_band,topic_stamp_lag_above_policy |
| clock_skew | 1/9 | 1/9 | [0.019890887638544907, 0.434999705576656] | [0.019890887638544907, 0.434999705576656] | late_messages_observed,topic_stamp_lag_above_policy |
| freeze | 0/3 | 3/3 | [5.551115123125783e-17, 0.5614970317550454] | [0.4385029682449546, 1.0] | v2_freeze |
| false_contact | 0/3 | 0/3 | [5.551115123125783e-17, 0.5614970317550454] | [5.551115123125783e-17, 0.5614970317550454] | none |
| missed_contact | 0/3 | 0/3 | [5.551115123125783e-17, 0.5614970317550454] | [5.551115123125783e-17, 0.5614970317550454] | none |

## Overall

v1 micro/macro recall 0.707/0.667; v2 0.808/0.771. Classes: v1 14/17; v2 15/17.
Incident precision v1/v2: 0.862/0.871.
Row metrics v1: balanced accuracy 0.556, MCC 0.279, accuracy 0.718, F1 0.202. v2: balanced accuracy 0.556, MCC 0.279, accuracy 0.718, F1 0.202. Plain accuracy is misleading because normal rows dominate.

Stream-C false-alert counts/rates and exact Poisson CIs by rule are in JSON; the seed-2 rule audit is in v2_class_signal_analysis.md.

Noise stress and timing-crop leakage checks ran after freeze; crop offsets and results are in JSON.

If false_contact or missed_contact has v2 detections despite the signal analysis, the result is invalid.
