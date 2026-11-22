# Telemetry-model ablation

Diagnostic ablation only; shipped monitor configuration and saved thresholds are unchanged.

| Stream | Mode | Configuration | False incidents | Normal hours | False incidents/hour (95% Poisson CI) |
|---|---|---|---:|---:|---|
| stream_c | reset_at_joins | fused | 25 | 1.724 | 14.502 [9.385, 21.408] |
| stream_c | reset_at_joins | without_telemetry_model | 10 | 1.724 | 5.801 [2.782, 10.668] |
| stream_b_seed_1701 | continuous_state | fused | 107 | 1.730 | 61.841 [50.681, 74.729] |
| stream_b_seed_1701 | continuous_state | without_telemetry_model | 107 | 1.730 | 61.841 [50.681, 74.729] |

## Per-class event recall

| Stream | Mode | Class | Fused | Without telemetry model |
|---|---|---|---:|---:|
| stream_b_seed_1701 | continuous_state | bias_drift | 6/9 (0.667) | 6/9 (0.667) |
| stream_b_seed_1701 | continuous_state | clock_skew | 1/9 (0.111) | 1/9 (0.111) |
| stream_b_seed_1701 | continuous_state | delay | 9/9 (1.000) | 9/9 (1.000) |
| stream_b_seed_1701 | continuous_state | drop | 9/9 (1.000) | 9/9 (1.000) |
| stream_b_seed_1701 | continuous_state | duplicate | 9/9 (1.000) | 9/9 (1.000) |
| stream_b_seed_1701 | continuous_state | false_contact | 0/3 (0.000) | 0/3 (0.000) |
| stream_b_seed_1701 | continuous_state | flood | 9/9 (1.000) | 9/9 (1.000) |
| stream_b_seed_1701 | continuous_state | freeze | 0/3 (0.000) | 0/3 (0.000) |
| stream_b_seed_1701 | continuous_state | jump | 2/9 (0.222) | 2/9 (0.222) |
| stream_b_seed_1701 | continuous_state | missed_contact | 0/3 (0.000) | 0/3 (0.000) |
| stream_b_seed_1701 | continuous_state | noise | 9/9 (1.000) | 9/9 (1.000) |
| stream_b_seed_1701 | continuous_state | param_tamper | 3/3 (1.000) | 3/3 (1.000) |
| stream_b_seed_1701 | continuous_state | replay | 1/3 (0.333) | 1/3 (0.333) |
| stream_b_seed_1701 | continuous_state | service_abuse | 3/3 (1.000) | 3/3 (1.000) |
| stream_b_seed_1701 | continuous_state | spoof | 3/3 (1.000) | 3/3 (1.000) |
| stream_b_seed_1701 | continuous_state | unauthorized_node | 3/3 (1.000) | 3/3 (1.000) |
| stream_b_seed_1701 | continuous_state | unauthorized_subscription | 3/3 (1.000) | 3/3 (1.000) |
