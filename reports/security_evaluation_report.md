# ROS 2 telemetry security evaluation

- **scikit-learn runtime version:** 1.9.1.
- **Security model SHA-256:** `f4ba15b24c9a33a843b733b604cb27e7f9a25ce5fdd0cfd52c3610d811a475af`.
- **Test split:** seed 3, whole runs held out.
- **Test runs:** 102.
- **Selected model:** random_forest.
- **Labels:** `events.csv` intervals; stored `is_attack` is not used as the label source.
- **Event tolerance:** -1.5s before start and +0.5s after stop.

## Overall row metrics

| Method | Precision | Recall | F1 | FPR |
|---|---:|---:|---:|---:|
| rules | 0.9351 | 0.5006 | 0.6521 | 0.0151 |
| isolation_forest | 0.5093 | 0.5109 | 0.5101 | 0.2134 |
| random_forest | 0.9891 | 0.2769 | 0.4327 | 0.0013 |
| rules_plus_model | 0.9351 | 0.5006 | 0.6521 | 0.0151 |

## Per-class row-level metrics

| Class | Scope | Method | Precision | Recall | F1 | FPR |
|---|---|---|---:|---:|---:|---:|
| bias_drift | unusable | rules | 0.0000 | 0.0000 | 0.0000 | 0.0012 |
| bias_drift | unusable | isolation_forest | 0.1283 | 0.0815 | 0.0997 | 0.1721 |
| bias_drift | unusable | random_forest | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| bias_drift | unusable | rules_plus_model | 0.0000 | 0.0000 | 0.0000 | 0.0012 |
| clock_skew | limited | rules | 0.3333 | 0.0037 | 0.0073 | 0.0023 |
| clock_skew | limited | isolation_forest | 0.3118 | 0.3315 | 0.3214 | 0.2271 |
| clock_skew | limited | random_forest | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| clock_skew | limited | rules_plus_model | 0.3333 | 0.0037 | 0.0073 | 0.0023 |
| delay | limited | rules | 0.9607 | 0.9963 | 0.9782 | 0.0127 |
| delay | limited | isolation_forest | 0.5884 | 0.9981 | 0.7404 | 0.2170 |
| delay | limited | random_forest | 0.0000 | 0.0000 | 0.0000 | 0.0017 |
| delay | limited | rules_plus_model | 0.9607 | 0.9963 | 0.9782 | 0.0127 |
| drop | limited | rules | 0.9096 | 0.9500 | 0.9293 | 0.0284 |
| drop | limited | isolation_forest | 0.5681 | 0.9889 | 0.7216 | 0.2261 |
| drop | limited | random_forest | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| drop | limited | rules_plus_model | 0.9096 | 0.9500 | 0.9293 | 0.0284 |
| duplicate | limited | rules | 0.9707 | 0.9204 | 0.9449 | 0.0086 |
| duplicate | limited | isolation_forest | 0.4618 | 0.4926 | 0.4767 | 0.1782 |
| duplicate | limited | random_forest | 0.9922 | 0.4704 | 0.6382 | 0.0011 |
| duplicate | limited | rules_plus_model | 0.9707 | 0.9204 | 0.9449 | 0.0086 |
| false_contact | unusable | rules | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| false_contact | unusable | isolation_forest | 0.0867 | 0.0944 | 0.0904 | 0.1817 |
| false_contact | unusable | random_forest | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| false_contact | unusable | rules_plus_model | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| flood | usable | rules | 0.9694 | 0.9963 | 0.9826 | 0.0098 |
| flood | usable | isolation_forest | 0.5836 | 0.8852 | 0.7035 | 0.1970 |
| flood | usable | random_forest | 0.9945 | 0.9963 | 0.9954 | 0.0017 |
| flood | usable | rules_plus_model | 0.9694 | 0.9963 | 0.9826 | 0.0098 |
| freeze | unusable | rules | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| freeze | unusable | isolation_forest | 0.0675 | 0.0611 | 0.0641 | 0.1588 |
| freeze | unusable | random_forest | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| freeze | unusable | rules_plus_model | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| jump | unusable | rules | 0.4286 | 0.0056 | 0.0110 | 0.0023 |
| jump | unusable | isolation_forest | 0.0920 | 0.0574 | 0.0707 | 0.1762 |
| jump | unusable | random_forest | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| jump | unusable | rules_plus_model | 0.4286 | 0.0056 | 0.0110 | 0.0023 |
| missed_contact | unusable | rules | 0.0000 | 0.0000 | 0.0000 | 0.0010 |
| missed_contact | unusable | isolation_forest | 0.0245 | 0.0222 | 0.0233 | 0.1661 |
| missed_contact | unusable | random_forest | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| missed_contact | unusable | rules_plus_model | 0.0000 | 0.0000 | 0.0000 | 0.0010 |
| noise | unusable | rules | 0.0000 | 0.0000 | 0.0000 | 0.0063 |
| noise | unusable | isolation_forest | 0.0952 | 0.0630 | 0.0758 | 0.1864 |
| noise | unusable | random_forest | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| noise | unusable | rules_plus_model | 0.0000 | 0.0000 | 0.0000 | 0.0063 |
| param_tamper | limited | rules | 0.9355 | 1.0000 | 0.9667 | 0.0125 |
| param_tamper | limited | isolation_forest | 0.4929 | 1.0000 | 0.6603 | 0.1859 |
| param_tamper | limited | random_forest | 1.0000 | 0.9138 | 0.9550 | 0.0000 |
| param_tamper | limited | rules_plus_model | 0.9355 | 1.0000 | 0.9667 | 0.0125 |
| replay | unusable | rules | 0.5000 | 0.0167 | 0.0323 | 0.0031 |
| replay | unusable | isolation_forest | 0.0895 | 0.0944 | 0.0919 | 0.1804 |
| replay | unusable | random_forest | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| replay | unusable | rules_plus_model | 0.5000 | 0.0167 | 0.0323 | 0.0031 |
| service_abuse | limited | rules | 0.9405 | 1.0000 | 0.9694 | 0.0114 |
| service_abuse | limited | isolation_forest | 0.4416 | 1.0000 | 0.6127 | 0.2282 |
| service_abuse | limited | random_forest | 0.9830 | 0.9943 | 0.9886 | 0.0031 |
| service_abuse | limited | rules_plus_model | 0.9405 | 1.0000 | 0.9694 | 0.0114 |
| spoof | usable | rules | 0.8777 | 1.0000 | 0.9348 | 0.0237 |
| spoof | usable | isolation_forest | 0.4728 | 1.0000 | 0.6420 | 0.1895 |
| spoof | usable | random_forest | 0.9706 | 1.0000 | 0.9851 | 0.0051 |
| spoof | usable | rules_plus_model | 0.8777 | 1.0000 | 0.9348 | 0.0237 |
| unauthorized_node | usable | rules | 0.9667 | 1.0000 | 0.9831 | 0.0062 |
| unauthorized_node | usable | isolation_forest | 0.5000 | 1.0000 | 0.6667 | 0.1811 |
| unauthorized_node | usable | random_forest | 0.9885 | 0.9885 | 0.9885 | 0.0021 |
| unauthorized_node | usable | rules_plus_model | 0.9667 | 1.0000 | 0.9831 | 0.0062 |
| unauthorized_subscription | usable | rules | 0.8827 | 0.9943 | 0.9351 | 0.0222 |
| unauthorized_subscription | usable | isolation_forest | 0.4123 | 1.0000 | 0.5839 | 0.2398 |
| unauthorized_subscription | usable | random_forest | 1.0000 | 0.9943 | 0.9971 | 0.0000 |
| unauthorized_subscription | usable | rules_plus_model | 0.8827 | 0.9943 | 0.9351 | 0.0222 |

## Event-level metrics by class

| Class | Method | Detected / total | Precision | Recall | 95% Wilson CI | F1 | Median latency from label (s) |
|---|---|---:|---:|---:|---|---:|---:|
| bias_drift | rules | 0/9 | 0.0000 | 0.0000 | [0.000, 0.299] | 0.0000 | n/a |
| bias_drift | isolation_forest | 8/9 | 0.0851 | 0.8889 | [0.565, 0.980] | 0.1553 | 1.4000000000000001 |
| bias_drift | random_forest | 0/9 | 0.0000 | 0.0000 | [0.000, 0.299] | 0.0000 | n/a |
| bias_drift | rules_plus_model | 0/9 | 0.0000 | 0.0000 | [0.000, 0.299] | 0.0000 | n/a |
| clock_skew | rules | 1/9 | 0.2500 | 0.1111 | [0.020, 0.435] | 0.1538 | 13.3 |
| clock_skew | isolation_forest | 9/9 | 0.0726 | 1.0000 | [0.701, 1.000] | 0.1353 | -0.4 |
| clock_skew | random_forest | 0/9 | 0.0000 | 0.0000 | [0.000, 0.299] | 0.0000 | n/a |
| clock_skew | rules_plus_model | 1/9 | 0.2500 | 0.1111 | [0.020, 0.435] | 0.1538 | 13.3 |
| delay | rules | 9/9 | 0.4500 | 1.0000 | [0.701, 1.000] | 0.6207 | 0.4 |
| delay | isolation_forest | 9/9 | 0.0738 | 1.0000 | [0.701, 1.000] | 0.1374 | 0.35 |
| delay | random_forest | 3/9 | 1.0000 | 0.3333 | [0.121, 0.646] | 0.5000 | 30.266666666 |
| delay | rules_plus_model | 9/9 | 0.4500 | 1.0000 | [0.701, 1.000] | 0.6207 | 0.4 |
| drop | rules | 9/9 | 0.5000 | 1.0000 | [0.701, 1.000] | 0.6667 | 0.3 |
| drop | isolation_forest | 9/9 | 0.0865 | 1.0000 | [0.701, 1.000] | 0.1593 | 0.283333333 |
| drop | random_forest | 0/9 | 0.0000 | 0.0000 | [0.000, 0.299] | 0.0000 | n/a |
| drop | rules_plus_model | 9/9 | 0.5000 | 1.0000 | [0.701, 1.000] | 0.6667 | 0.3 |
| duplicate | rules | 9/9 | 0.6000 | 1.0000 | [0.701, 1.000] | 0.7500 | 0.4 |
| duplicate | isolation_forest | 9/9 | 0.0783 | 1.0000 | [0.701, 1.000] | 0.1452 | 0.616666667 |
| duplicate | random_forest | 9/9 | 1.0000 | 1.0000 | [0.701, 1.000] | 1.0000 | 0.55 |
| duplicate | rules_plus_model | 9/9 | 0.6000 | 1.0000 | [0.701, 1.000] | 0.7500 | 0.4 |
| false_contact | rules | 0/3 | 0.0000 | 0.0000 | [0.000, 0.561] | 0.0000 | n/a |
| false_contact | isolation_forest | 2/3 | 0.0339 | 0.6667 | [0.208, 0.939] | 0.0645 | 0.6916666669999999 |
| false_contact | random_forest | 0/3 | 0.0000 | 0.0000 | [0.000, 0.561] | 0.0000 | n/a |
| false_contact | rules_plus_model | 0/3 | 0.0000 | 0.0000 | [0.000, 0.561] | 0.0000 | n/a |
| flood | rules | 9/9 | 0.5294 | 1.0000 | [0.701, 1.000] | 0.6923 | 0.216666667 |
| flood | isolation_forest | 9/9 | 0.0841 | 1.0000 | [0.701, 1.000] | 0.1552 | 0.483333333 |
| flood | random_forest | 9/9 | 1.0000 | 1.0000 | [0.701, 1.000] | 1.0000 | 0.216666667 |
| flood | rules_plus_model | 9/9 | 0.5294 | 1.0000 | [0.701, 1.000] | 0.6923 | 0.216666667 |
| freeze | rules | 0/3 | 0.0000 | 0.0000 | [0.000, 0.561] | 0.0000 | n/a |
| freeze | isolation_forest | 3/3 | 0.0545 | 1.0000 | [0.439, 1.000] | 0.1034 | 2.95 |
| freeze | random_forest | 0/3 | 0.0000 | 0.0000 | [0.000, 0.561] | 0.0000 | n/a |
| freeze | rules_plus_model | 0/3 | 0.0000 | 0.0000 | [0.000, 0.561] | 0.0000 | n/a |
| jump | rules | 1/9 | 0.3333 | 0.1111 | [0.020, 0.435] | 0.1667 | 22.383333334 |
| jump | isolation_forest | 8/9 | 0.0808 | 0.8889 | [0.565, 0.980] | 0.1481 | 1.025 |
| jump | random_forest | 0/9 | 0.0000 | 0.0000 | [0.000, 0.299] | 0.0000 | n/a |
| jump | rules_plus_model | 1/9 | 0.3333 | 0.1111 | [0.020, 0.435] | 0.1667 | 22.383333334 |
| missed_contact | rules | 0/3 | 0.0000 | 0.0000 | [0.000, 0.561] | 0.0000 | n/a |
| missed_contact | isolation_forest | 2/3 | 0.0370 | 0.6667 | [0.208, 0.939] | 0.0702 | 17.5333333335 |
| missed_contact | random_forest | 0/3 | 0.0000 | 0.0000 | [0.000, 0.561] | 0.0000 | n/a |
| missed_contact | rules_plus_model | 0/3 | 0.0000 | 0.0000 | [0.000, 0.561] | 0.0000 | n/a |
| noise | rules | 0/9 | 0.0000 | 0.0000 | [0.000, 0.299] | 0.0000 | n/a |
| noise | isolation_forest | 9/9 | 0.0874 | 1.0000 | [0.701, 1.000] | 0.1607 | 0.016666666 |
| noise | random_forest | 0/9 | 0.0000 | 0.0000 | [0.000, 0.299] | 0.0000 | n/a |
| noise | rules_plus_model | 0/9 | 0.0000 | 0.0000 | [0.000, 0.299] | 0.0000 | n/a |
| param_tamper | rules | 3/3 | 0.6000 | 1.0000 | [0.439, 1.000] | 0.7500 | -0.966666667 |
| param_tamper | isolation_forest | 3/3 | 0.0462 | 1.0000 | [0.439, 1.000] | 0.0882 | -0.966666667 |
| param_tamper | random_forest | 3/3 | 1.0000 | 1.0000 | [0.439, 1.000] | 1.0000 | 2.533333333 |
| param_tamper | rules_plus_model | 3/3 | 0.6000 | 1.0000 | [0.439, 1.000] | 0.7500 | -0.966666667 |
| replay | rules | 1/3 | 0.5000 | 0.3333 | [0.061, 0.792] | 0.4000 | 20.449999999 |
| replay | isolation_forest | 3/3 | 0.0545 | 1.0000 | [0.439, 1.000] | 0.1034 | 11.949999999 |
| replay | random_forest | 0/3 | 0.0000 | 0.0000 | [0.000, 0.561] | 0.0000 | n/a |
| replay | rules_plus_model | 1/3 | 0.5000 | 0.3333 | [0.061, 0.792] | 0.4000 | 20.449999999 |
| service_abuse | rules | 3/3 | 0.7500 | 1.0000 | [0.439, 1.000] | 0.8571 | -0.85 |
| service_abuse | isolation_forest | 3/3 | 0.0517 | 1.0000 | [0.439, 1.000] | 0.0984 | -0.85 |
| service_abuse | random_forest | 3/3 | 1.0000 | 1.0000 | [0.439, 1.000] | 1.0000 | -0.35 |
| service_abuse | rules_plus_model | 3/3 | 0.7500 | 1.0000 | [0.439, 1.000] | 0.8571 | -0.85 |
| spoof | rules | 3/3 | 0.3000 | 1.0000 | [0.439, 1.000] | 0.4615 | -1.25 |
| spoof | isolation_forest | 3/3 | 0.0469 | 1.0000 | [0.439, 1.000] | 0.0896 | -1.25 |
| spoof | random_forest | 3/3 | 0.7500 | 1.0000 | [0.439, 1.000] | 0.8571 | -1.05 |
| spoof | rules_plus_model | 3/3 | 0.3000 | 1.0000 | [0.439, 1.000] | 0.4615 | -1.25 |
| unauthorized_node | rules | 3/3 | 1.0000 | 1.0000 | [0.439, 1.000] | 1.0000 | -0.766666667 |
| unauthorized_node | isolation_forest | 3/3 | 0.0484 | 1.0000 | [0.439, 1.000] | 0.0923 | -1.083333333 |
| unauthorized_node | random_forest | 3/3 | 1.0000 | 1.0000 | [0.439, 1.000] | 1.0000 | -0.083333333 |
| unauthorized_node | rules_plus_model | 3/3 | 1.0000 | 1.0000 | [0.439, 1.000] | 1.0000 | -0.766666667 |
| unauthorized_subscription | rules | 3/3 | 0.7500 | 1.0000 | [0.439, 1.000] | 0.8571 | -0.6 |
| unauthorized_subscription | isolation_forest | 3/3 | 0.0484 | 1.0000 | [0.439, 1.000] | 0.0923 | -0.6 |
| unauthorized_subscription | random_forest | 3/3 | 1.0000 | 1.0000 | [0.439, 1.000] | 1.0000 | 0.4 |
| unauthorized_subscription | rules_plus_model | 3/3 | 0.7500 | 1.0000 | [0.439, 1.000] | 0.8571 | -0.6 |

There are only 3 held-out events for spoof, unauthorized_node, and unauthorized_subscription. Their point estimates and confidence intervals are too imprecise to claim reliability.

## False alerts per hour

| Method | Scope | False alert incidents | Normal hours | Alerts/hour |
|---|---|---:|---:|---:|
| rules | normal_runs | 0 | 0.066 | 0.000 |
| rules | normal_segments | 58 | 1.411 | 41.115 |
| isolation_forest | normal_runs | 39 | 0.066 | 587.448 |
| isolation_forest | normal_segments | 683 | 1.411 | 484.159 |
| random_forest | normal_runs | 0 | 0.066 | 0.000 |
| random_forest | normal_segments | 1 | 1.411 | 0.709 |
| rules_plus_model | normal_runs | 0 | 0.066 | 0.000 |
| rules_plus_model | normal_segments | 58 | 1.411 | 41.115 |

## Rules false-alert breakdown

- Combined false-alert episodes in normal segments: 58 across 1.411 hours (41.115/hour).
- Policy-alert ticks inside the evaluation tolerance windows: 80; none of those false-alert episodes count inside the false-positive mask.
- Startup policy-alert ticks excluded from evaluation: 0.
- Per-rule episode counts can overlap; see `security_false_alert_breakdown.csv` for rule, class, and boundary detail.

### Combined false episodes by run class

| Run class | Episodes |
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

### Combined false episodes by nearest boundary

| Boundary bucket | Episodes |
|---|---:|
| elsewhere | 22 |
| within_1.5s_of_boundary | 36 |

## Limitations

- Seed 3 is a single held-out simulation seed, not external validation.
- Metrics for classes not used as supervised training positives are diagnostic only.
- Telemetry has no host/IP/MAC/DDS participant identity or topic-payload access evidence.
- There is no movement-command topic or live bridge/domain change stream in the recordings.
- No real-time, real-vehicle, or safety-critical performance is established.
