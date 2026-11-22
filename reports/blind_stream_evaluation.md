# Blind mixed-stream evaluation

- **scikit-learn runtime version:** 1.9.1.
- **Model SHA-256:** noise `cb850fc408f62eee9fbf7080baa927ab9da35c39c2204062364778522a8c8880`; security `f4ba15b24c9a33a843b733b604cb27e7f9a25ce5fdd0cfd52c3610d811a475af`.
- **Inventory status:** approved_for_offline_demo.
- **Labels:** events.csv start-inclusive, stop-exclusive intervals.
- **Event tolerance:** -1.5 s before start, +0.5 s after stop.
- **Draft inventory override:** False.
- **Scope limitation:** All source data is simulated with idealized sensors and an in-sim driver, not a ROS-driven vehicle. These tests estimate robustness only and do not establish real-world performance.

## Stream construction summary

| Stream | Duration (s) | Normal (s) | Attack (s) | Attack prevalence | Joins |
|---|---:|---:|---:|---:|---:|
| stream_a | 6540.083 | 6205.883 | 330.000 | 5.0490% | 211 |
| stream_b_seed_1701 | 9182.000 | 6228.833 | 2951.167 | 32.1478% | 101 |
| stream_b_seed_2903 | 9182.000 | 6228.833 | 2951.167 | 32.1478% | 101 |
| stream_b_seed_4307 | 9182.000 | 6228.833 | 2951.167 | 32.1478% | 101 |
| stream_c | 6209.863 | 6205.883 | 0.000 | 0.0000% | 200 |

Stream C contains 6205.883 seconds (1.723856 hours) of event-free driving. This exceeds one hour, but remains a limited simulated soak.

## Event recall by stream and state mode

| Stream | Mode | Class | Detected / events | Recall | 95% Wilson CI | Median latency (s) | P90 latency (s) |
|---|---|---|---:|---:|---|---:|---:|
| stream_a | continuous_state | bias_drift | 2 / 2 | 1.000 | [0.342, 1.000] | 0.01 | 0.018000000000000002 |
| stream_a | continuous_state | clock_skew | 1 / 1 | 1.000 | [0.207, 1.000] | 0.083333333 | 0.083333333 |
| stream_a | continuous_state | delay | 2 / 2 | 1.000 | [0.342, 1.000] | 0.258333333 | 0.37166666660000003 |
| stream_a | continuous_state | drop | 1 / 1 | 1.000 | [0.207, 1.000] | 0.3 | 0.3 |
| stream_a | continuous_state | duplicate | 1 / 1 | 1.000 | [0.207, 1.000] | 0.216666667 | 0.216666667 |
| stream_a | continuous_state | false_contact | 1 / 1 | 1.000 | [0.207, 1.000] | 30.336666667 | 30.336666667 |
| stream_a | continuous_state | flood | 1 / 1 | 1.000 | [0.207, 1.000] | 0.566666666 | 0.566666666 |
| stream_a | continuous_state | freeze | 1 / 1 | 1.000 | [0.207, 1.000] | 0.0 | 0.0 |
| stream_a | continuous_state | replay | 1 / 1 | 1.000 | [0.207, 1.000] | 0.083333333 | 0.083333333 |
| stream_a | reset_at_joins | bias_drift | 1 / 2 | 0.500 | [0.095, 0.905] | 0.08 | 0.08 |
| stream_a | reset_at_joins | clock_skew | 0 / 1 | 0.000 | [0.000, 0.793] | n/a | n/a |
| stream_a | reset_at_joins | delay | 2 / 2 | 1.000 | [0.342, 1.000] | 15.258333333 | 15.371666666600001 |
| stream_a | reset_at_joins | drop | 1 / 1 | 1.000 | [0.207, 1.000] | 15.3 | 15.3 |
| stream_a | reset_at_joins | duplicate | 1 / 1 | 1.000 | [0.207, 1.000] | 0.716666667 | 0.716666667 |
| stream_a | reset_at_joins | false_contact | 0 / 1 | 0.000 | [0.000, 0.793] | n/a | n/a |
| stream_a | reset_at_joins | flood | 1 / 1 | 1.000 | [0.207, 1.000] | 0.566666666 | 0.566666666 |
| stream_a | reset_at_joins | freeze | 0 / 1 | 0.000 | [0.000, 0.793] | n/a | n/a |
| stream_a | reset_at_joins | replay | 0 / 1 | 0.000 | [0.000, 0.793] | n/a | n/a |
| stream_b_seed_1701 | continuous_state | bias_drift | 6 / 9 | 0.667 | [0.354, 0.879] | 0.02 | 0.04 |
| stream_b_seed_1701 | continuous_state | clock_skew | 1 / 9 | 0.111 | [0.020, 0.435] | 13.3 | 13.3 |
| stream_b_seed_1701 | continuous_state | delay | 9 / 9 | 1.000 | [0.701, 1.000] | 0.4 | 0.51 |
| stream_b_seed_1701 | continuous_state | drop | 9 / 9 | 1.000 | [0.701, 1.000] | 0.3 | 0.7299999998000001 |
| stream_b_seed_1701 | continuous_state | duplicate | 9 / 9 | 1.000 | [0.701, 1.000] | 0.4 | 0.74 |
| stream_b_seed_1701 | continuous_state | false_contact | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_1701 | continuous_state | flood | 9 / 9 | 1.000 | [0.701, 1.000] | 0.216666667 | 0.5133333332000001 |
| stream_b_seed_1701 | continuous_state | freeze | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_1701 | continuous_state | jump | 2 / 9 | 0.222 | [0.063, 0.547] | 11.231666666999999 | 20.1530000006 |
| stream_b_seed_1701 | continuous_state | missed_contact | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_1701 | continuous_state | noise | 9 / 9 | 1.000 | [0.701, 1.000] | 0.04 | 0.084 |
| stream_b_seed_1701 | continuous_state | param_tamper | 3 / 3 | 1.000 | [0.439, 1.000] | -0.966666667 | -0.8333333334 |
| stream_b_seed_1701 | continuous_state | replay | 1 / 3 | 0.333 | [0.061, 0.792] | 20.449999999 | 20.449999999 |
| stream_b_seed_1701 | continuous_state | service_abuse | 3 / 3 | 1.000 | [0.439, 1.000] | -0.85 | -0.85 |
| stream_b_seed_1701 | continuous_state | spoof | 3 / 3 | 1.000 | [0.439, 1.000] | -2.25 | -1.9566666663999999 |
| stream_b_seed_1701 | continuous_state | unauthorized_node | 3 / 3 | 1.000 | [0.439, 1.000] | -0.766666667 | -0.5399999998 |
| stream_b_seed_1701 | continuous_state | unauthorized_subscription | 3 / 3 | 1.000 | [0.439, 1.000] | -0.6 | -0.5733333336 |
| stream_b_seed_1701 | reset_at_joins | bias_drift | 6 / 9 | 0.667 | [0.354, 0.879] | 0.02 | 0.04 |
| stream_b_seed_1701 | reset_at_joins | clock_skew | 1 / 9 | 0.111 | [0.020, 0.435] | 13.3 | 13.3 |
| stream_b_seed_1701 | reset_at_joins | delay | 9 / 9 | 1.000 | [0.701, 1.000] | 0.4 | 0.51 |
| stream_b_seed_1701 | reset_at_joins | drop | 9 / 9 | 1.000 | [0.701, 1.000] | 0.3 | 0.7299999998000001 |
| stream_b_seed_1701 | reset_at_joins | duplicate | 9 / 9 | 1.000 | [0.701, 1.000] | 0.4 | 0.74 |
| stream_b_seed_1701 | reset_at_joins | false_contact | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_1701 | reset_at_joins | flood | 9 / 9 | 1.000 | [0.701, 1.000] | 0.216666667 | 0.5133333332000001 |
| stream_b_seed_1701 | reset_at_joins | freeze | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_1701 | reset_at_joins | jump | 2 / 9 | 0.222 | [0.063, 0.547] | 11.231666666999999 | 20.1530000006 |
| stream_b_seed_1701 | reset_at_joins | missed_contact | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_1701 | reset_at_joins | noise | 9 / 9 | 1.000 | [0.701, 1.000] | 0.04 | 0.084 |
| stream_b_seed_1701 | reset_at_joins | param_tamper | 3 / 3 | 1.000 | [0.439, 1.000] | -0.966666667 | -0.8333333334 |
| stream_b_seed_1701 | reset_at_joins | replay | 1 / 3 | 0.333 | [0.061, 0.792] | 20.449999999 | 20.449999999 |
| stream_b_seed_1701 | reset_at_joins | service_abuse | 3 / 3 | 1.000 | [0.439, 1.000] | -0.85 | -0.85 |
| stream_b_seed_1701 | reset_at_joins | spoof | 3 / 3 | 1.000 | [0.439, 1.000] | -2.25 | -1.9566666663999999 |
| stream_b_seed_1701 | reset_at_joins | unauthorized_node | 3 / 3 | 1.000 | [0.439, 1.000] | -0.766666667 | -0.5399999998 |
| stream_b_seed_1701 | reset_at_joins | unauthorized_subscription | 3 / 3 | 1.000 | [0.439, 1.000] | -0.6 | -0.5733333336 |
| stream_b_seed_2903 | continuous_state | bias_drift | 6 / 9 | 0.667 | [0.354, 0.879] | 0.02 | 0.04 |
| stream_b_seed_2903 | continuous_state | clock_skew | 1 / 9 | 0.111 | [0.020, 0.435] | 13.3 | 13.3 |
| stream_b_seed_2903 | continuous_state | delay | 9 / 9 | 1.000 | [0.701, 1.000] | 0.4 | 0.51 |
| stream_b_seed_2903 | continuous_state | drop | 9 / 9 | 1.000 | [0.701, 1.000] | 0.3 | 0.7299999998000001 |
| stream_b_seed_2903 | continuous_state | duplicate | 9 / 9 | 1.000 | [0.701, 1.000] | 0.4 | 0.74 |
| stream_b_seed_2903 | continuous_state | false_contact | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_2903 | continuous_state | flood | 9 / 9 | 1.000 | [0.701, 1.000] | 0.216666667 | 0.5133333332000001 |
| stream_b_seed_2903 | continuous_state | freeze | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_2903 | continuous_state | jump | 2 / 9 | 0.222 | [0.063, 0.547] | 11.231666666999999 | 20.1530000006 |
| stream_b_seed_2903 | continuous_state | missed_contact | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_2903 | continuous_state | noise | 9 / 9 | 1.000 | [0.701, 1.000] | 0.04 | 0.084 |
| stream_b_seed_2903 | continuous_state | param_tamper | 3 / 3 | 1.000 | [0.439, 1.000] | -0.966666667 | -0.8333333334 |
| stream_b_seed_2903 | continuous_state | replay | 1 / 3 | 0.333 | [0.061, 0.792] | 20.449999999 | 20.449999999 |
| stream_b_seed_2903 | continuous_state | service_abuse | 3 / 3 | 1.000 | [0.439, 1.000] | -0.85 | -0.85 |
| stream_b_seed_2903 | continuous_state | spoof | 3 / 3 | 1.000 | [0.439, 1.000] | -2.25 | -1.9566666663999999 |
| stream_b_seed_2903 | continuous_state | unauthorized_node | 3 / 3 | 1.000 | [0.439, 1.000] | -0.766666667 | -0.5399999998 |
| stream_b_seed_2903 | continuous_state | unauthorized_subscription | 3 / 3 | 1.000 | [0.439, 1.000] | -0.6 | -0.5733333336 |
| stream_b_seed_2903 | reset_at_joins | bias_drift | 6 / 9 | 0.667 | [0.354, 0.879] | 0.02 | 0.04 |
| stream_b_seed_2903 | reset_at_joins | clock_skew | 1 / 9 | 0.111 | [0.020, 0.435] | 13.3 | 13.3 |
| stream_b_seed_2903 | reset_at_joins | delay | 9 / 9 | 1.000 | [0.701, 1.000] | 0.4 | 0.51 |
| stream_b_seed_2903 | reset_at_joins | drop | 9 / 9 | 1.000 | [0.701, 1.000] | 0.3 | 0.7299999998000001 |
| stream_b_seed_2903 | reset_at_joins | duplicate | 9 / 9 | 1.000 | [0.701, 1.000] | 0.4 | 0.74 |
| stream_b_seed_2903 | reset_at_joins | false_contact | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_2903 | reset_at_joins | flood | 9 / 9 | 1.000 | [0.701, 1.000] | 0.216666667 | 0.5133333332000001 |
| stream_b_seed_2903 | reset_at_joins | freeze | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_2903 | reset_at_joins | jump | 2 / 9 | 0.222 | [0.063, 0.547] | 11.231666666999999 | 20.1530000006 |
| stream_b_seed_2903 | reset_at_joins | missed_contact | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_2903 | reset_at_joins | noise | 9 / 9 | 1.000 | [0.701, 1.000] | 0.04 | 0.084 |
| stream_b_seed_2903 | reset_at_joins | param_tamper | 3 / 3 | 1.000 | [0.439, 1.000] | -0.966666667 | -0.8333333334 |
| stream_b_seed_2903 | reset_at_joins | replay | 1 / 3 | 0.333 | [0.061, 0.792] | 20.449999999 | 20.449999999 |
| stream_b_seed_2903 | reset_at_joins | service_abuse | 3 / 3 | 1.000 | [0.439, 1.000] | -0.85 | -0.85 |
| stream_b_seed_2903 | reset_at_joins | spoof | 3 / 3 | 1.000 | [0.439, 1.000] | -2.25 | -1.9566666663999999 |
| stream_b_seed_2903 | reset_at_joins | unauthorized_node | 3 / 3 | 1.000 | [0.439, 1.000] | -0.766666667 | -0.5399999998 |
| stream_b_seed_2903 | reset_at_joins | unauthorized_subscription | 3 / 3 | 1.000 | [0.439, 1.000] | -0.6 | -0.5733333336 |
| stream_b_seed_4307 | continuous_state | bias_drift | 6 / 9 | 0.667 | [0.354, 0.879] | 0.02 | 0.04 |
| stream_b_seed_4307 | continuous_state | clock_skew | 1 / 9 | 0.111 | [0.020, 0.435] | 13.3 | 13.3 |
| stream_b_seed_4307 | continuous_state | delay | 9 / 9 | 1.000 | [0.701, 1.000] | 0.4 | 0.51 |
| stream_b_seed_4307 | continuous_state | drop | 9 / 9 | 1.000 | [0.701, 1.000] | 0.3 | 0.7299999998000001 |
| stream_b_seed_4307 | continuous_state | duplicate | 9 / 9 | 1.000 | [0.701, 1.000] | 0.4 | 0.74 |
| stream_b_seed_4307 | continuous_state | false_contact | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_4307 | continuous_state | flood | 9 / 9 | 1.000 | [0.701, 1.000] | 0.216666667 | 0.5133333332000001 |
| stream_b_seed_4307 | continuous_state | freeze | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_4307 | continuous_state | jump | 2 / 9 | 0.222 | [0.063, 0.547] | 11.231666666999999 | 20.1530000006 |
| stream_b_seed_4307 | continuous_state | missed_contact | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_4307 | continuous_state | noise | 9 / 9 | 1.000 | [0.701, 1.000] | 0.04 | 0.084 |
| stream_b_seed_4307 | continuous_state | param_tamper | 3 / 3 | 1.000 | [0.439, 1.000] | -0.966666667 | -0.8333333334 |
| stream_b_seed_4307 | continuous_state | replay | 1 / 3 | 0.333 | [0.061, 0.792] | 20.449999999 | 20.449999999 |
| stream_b_seed_4307 | continuous_state | service_abuse | 3 / 3 | 1.000 | [0.439, 1.000] | -0.85 | -0.85 |
| stream_b_seed_4307 | continuous_state | spoof | 3 / 3 | 1.000 | [0.439, 1.000] | -2.25 | -1.9566666663999999 |
| stream_b_seed_4307 | continuous_state | unauthorized_node | 3 / 3 | 1.000 | [0.439, 1.000] | -0.766666667 | -0.5399999998 |
| stream_b_seed_4307 | continuous_state | unauthorized_subscription | 3 / 3 | 1.000 | [0.439, 1.000] | -0.6 | -0.5733333336 |
| stream_b_seed_4307 | reset_at_joins | bias_drift | 6 / 9 | 0.667 | [0.354, 0.879] | 0.02 | 0.04 |
| stream_b_seed_4307 | reset_at_joins | clock_skew | 1 / 9 | 0.111 | [0.020, 0.435] | 13.3 | 13.3 |
| stream_b_seed_4307 | reset_at_joins | delay | 9 / 9 | 1.000 | [0.701, 1.000] | 0.4 | 0.51 |
| stream_b_seed_4307 | reset_at_joins | drop | 9 / 9 | 1.000 | [0.701, 1.000] | 0.3 | 0.7299999998000001 |
| stream_b_seed_4307 | reset_at_joins | duplicate | 9 / 9 | 1.000 | [0.701, 1.000] | 0.4 | 0.74 |
| stream_b_seed_4307 | reset_at_joins | false_contact | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_4307 | reset_at_joins | flood | 9 / 9 | 1.000 | [0.701, 1.000] | 0.216666667 | 0.5133333332000001 |
| stream_b_seed_4307 | reset_at_joins | freeze | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_4307 | reset_at_joins | jump | 2 / 9 | 0.222 | [0.063, 0.547] | 11.231666666999999 | 20.1530000006 |
| stream_b_seed_4307 | reset_at_joins | missed_contact | 0 / 3 | 0.000 | [0.000, 0.561] | n/a | n/a |
| stream_b_seed_4307 | reset_at_joins | noise | 9 / 9 | 1.000 | [0.701, 1.000] | 0.04 | 0.084 |
| stream_b_seed_4307 | reset_at_joins | param_tamper | 3 / 3 | 1.000 | [0.439, 1.000] | -0.966666667 | -0.8333333334 |
| stream_b_seed_4307 | reset_at_joins | replay | 1 / 3 | 0.333 | [0.061, 0.792] | 20.449999999 | 20.449999999 |
| stream_b_seed_4307 | reset_at_joins | service_abuse | 3 / 3 | 1.000 | [0.439, 1.000] | -0.85 | -0.85 |
| stream_b_seed_4307 | reset_at_joins | spoof | 3 / 3 | 1.000 | [0.439, 1.000] | -2.25 | -1.9566666663999999 |
| stream_b_seed_4307 | reset_at_joins | unauthorized_node | 3 / 3 | 1.000 | [0.439, 1.000] | -0.766666667 | -0.5399999998 |
| stream_b_seed_4307 | reset_at_joins | unauthorized_subscription | 3 / 3 | 1.000 | [0.439, 1.000] | -0.6 | -0.5733333336 |

## Stream B recall spread across shuffle seeds

This per-seed recall table uses continuous-state mode.

| Class | Seed 1701 | Seed 2903 | Seed 4307 | Min-max spread |
|---|---:|---:|---:|---:|
| bias_drift | 0.667 | 0.667 | 0.667 | 0.0 |
| clock_skew | 0.111 | 0.111 | 0.111 | 0.0 |
| delay | 1.000 | 1.000 | 1.000 | 0.0 |
| drop | 1.000 | 1.000 | 1.000 | 0.0 |
| duplicate | 1.000 | 1.000 | 1.000 | 0.0 |
| false_contact | 0.000 | 0.000 | 0.000 | 0.0 |
| flood | 1.000 | 1.000 | 1.000 | 0.0 |
| freeze | 0.000 | 0.000 | 0.000 | 0.0 |
| jump | 0.222 | 0.222 | 0.222 | 0.0 |
| missed_contact | 0.000 | 0.000 | 0.000 | 0.0 |
| noise | 1.000 | 1.000 | 1.000 | 0.0 |
| param_tamper | 1.000 | 1.000 | 1.000 | 0.0 |
| replay | 0.333 | 0.333 | 0.333 | 0.0 |
| service_abuse | 1.000 | 1.000 | 1.000 | 0.0 |
| spoof | 1.000 | 1.000 | 1.000 | 0.0 |
| unauthorized_node | 1.000 | 1.000 | 1.000 | 0.0 |
| unauthorized_subscription | 1.000 | 1.000 | 1.000 | 0.0 |

## Incident precision

| Stream | Mode | Incidents | Matching an event | Incident precision |
|---|---|---:|---:|---:|
| stream_a | continuous_state | 177 | 15 | 0.0847457627118644 |
| stream_a | reset_at_joins | 32 | 7 | 0.21875 |
| stream_b_seed_1701 | continuous_state | 182 | 75 | 0.41208791208791207 |
| stream_b_seed_1701 | reset_at_joins | 88 | 75 | 0.8522727272727273 |
| stream_b_seed_2903 | continuous_state | 179 | 75 | 0.41899441340782123 |
| stream_b_seed_2903 | reset_at_joins | 88 | 75 | 0.8522727272727273 |
| stream_b_seed_4307 | continuous_state | 187 | 75 | 0.40106951871657753 |
| stream_b_seed_4307 | reset_at_joins | 88 | 75 | 0.8522727272727273 |
| stream_c | continuous_state | 169 | 0 | 0.0 |
| stream_c | reset_at_joins | 25 | 0 | 0.0 |

Event and per-hour outcomes matter more than row-level metrics. All detectors remain advisory; no automatic action is taken.

## False alerts per normal-driving hour

Only nonzero detector/rule/category/location combinations are listed. The detailed CSV retains the full dimensions; `within_1.5s_of_label_boundary` is a symmetric diagnostic bucket, while event matching uses the asymmetric tolerance stated above. Location categories are non-exclusive, so an incident may be near a join and a label boundary. False-alert categories distinguish graph evidence continuing in a post-event source segment from unattributed alerts.

| Stream | Mode | Detector | Rule/model | Suspected category | False-alert category | Location | Components | Alerts/hour (95% Poisson CI) |
|---|---|---|---|---|---|---:|---:|---|
| stream_a | continuous_state | health | timestamp_jitter | flooding | unattributed_false_alert | at_join_point | 1 | 0.580 (0.015, 3.232) |
| stream_a | continuous_state | health | timestamp_jitter | graph/access anomaly | unattributed_false_alert | at_join_point | 3 | 1.740 (0.359, 5.086) |
| stream_a | continuous_state | health | timestamp_jitter | sensor-value anomaly | unattributed_false_alert | at_join_point | 13 | 7.541 (4.015, 12.896) |
| stream_a | continuous_state | health | timestamp_jitter | telemetry health | unattributed_false_alert | at_join_point | 66 | 38.286 (29.611, 48.709) |
| stream_a | continuous_state | health | timestamp_jitter | timing anomaly | unattributed_false_alert | at_join_point | 5 | 2.900 (0.942, 6.769) |
| stream_a | continuous_state | policy_rule:late_messages_observed | late_messages_observed | sensor-value anomaly | unattributed_false_alert | at_join_point | 1 | 0.580 (0.015, 3.232) |
| stream_a | continuous_state | policy_rule:late_messages_observed | late_messages_observed | timing anomaly | unattributed_false_alert | at_join_point | 8 | 4.641 (2.004, 9.144) |
| stream_a | continuous_state | policy_rule:late_messages_observed | late_messages_observed | timing anomaly | unattributed_false_alert | elsewhere | 20 | 11.602 (7.087, 17.918) |
| stream_a | continuous_state | policy_rule:parameter_event_outside_approved_window | parameter_event_outside_approved_window | timing anomaly | unattributed_false_alert | at_join_point | 3 | 1.740 (0.359, 5.086) |
| stream_a | continuous_state | policy_rule:service_call_rate_above_policy | service_call_rate_above_policy | graph/access anomaly | unattributed_false_alert | at_join_point | 3 | 1.740 (0.359, 5.086) |
| stream_a | continuous_state | policy_rule:topic_gap_above_policy | topic_gap_above_policy | timing anomaly | unattributed_false_alert | elsewhere | 7 | 4.061 (1.633, 8.367) |
| stream_a | continuous_state | policy_rule:topic_rate_out_of_band | topic_rate_out_of_band | flooding | unattributed_false_alert | at_join_point | 22 | 12.762 (7.998, 19.322) |
| stream_a | continuous_state | policy_rule:topic_rate_out_of_band | topic_rate_out_of_band | telemetry health | unattributed_false_alert | at_join_point | 2 | 1.160 (0.141, 4.191) |
| stream_a | continuous_state | policy_rule:topic_rate_out_of_band | topic_rate_out_of_band | timing anomaly | unattributed_false_alert | at_join_point | 17 | 9.862 (5.745, 15.789) |
| stream_a | continuous_state | policy_rule:topic_rate_out_of_band | topic_rate_out_of_band | timing anomaly | unattributed_false_alert | elsewhere | 8 | 4.641 (2.004, 9.144) |
| stream_a | continuous_state | policy_rule:topic_stamp_lag_above_policy | topic_stamp_lag_above_policy | flooding | unattributed_false_alert | at_join_point | 3 | 1.740 (0.359, 5.086) |
| stream_a | continuous_state | policy_rule:topic_stamp_lag_above_policy | topic_stamp_lag_above_policy | timing anomaly | unattributed_false_alert | at_join_point | 7 | 4.061 (1.633, 8.367) |
| stream_a | continuous_state | policy_rule:topic_stamp_lag_above_policy | topic_stamp_lag_above_policy | timing anomaly | unattributed_false_alert | elsewhere | 10 | 5.801 (2.782, 10.668) |
| stream_a | continuous_state | sensor_noise_model | sensor_random_forest | flooding | unattributed_false_alert | at_join_point | 5 | 2.900 (0.942, 6.769) |
| stream_a | continuous_state | sensor_noise_model | sensor_random_forest | graph/access anomaly | unattributed_false_alert | at_join_point | 1 | 0.580 (0.015, 3.232) |
| stream_a | continuous_state | sensor_noise_model | sensor_random_forest | sensor-value anomaly | unattributed_false_alert | at_join_point | 29 | 16.823 (11.266, 24.160) |
| stream_a | continuous_state | telemetry_model | telemetry_random_forest | flooding | unattributed_false_alert | at_join_point | 18 | 10.442 (6.188, 16.502) |
| stream_a | continuous_state | telemetry_model | telemetry_random_forest | telemetry health | unattributed_false_alert | at_join_point | 2 | 1.160 (0.141, 4.191) |
| stream_a | continuous_state | telemetry_model | telemetry_random_forest | timing anomaly | unattributed_false_alert | at_join_point | 5 | 2.900 (0.942, 6.769) |
| stream_a | reset_at_joins | policy_rule:late_messages_observed | late_messages_observed | timing anomaly | unattributed_false_alert | elsewhere | 8 | 4.641 (2.004, 9.144) |
| stream_a | reset_at_joins | policy_rule:topic_gap_above_policy | topic_gap_above_policy | timing anomaly | unattributed_false_alert | elsewhere | 4 | 2.320 (0.632, 5.941) |
| stream_a | reset_at_joins | policy_rule:topic_rate_out_of_band | topic_rate_out_of_band | timing anomaly | unattributed_false_alert | elsewhere | 3 | 1.740 (0.359, 5.086) |
| stream_a | reset_at_joins | policy_rule:topic_stamp_lag_above_policy | topic_stamp_lag_above_policy | timing anomaly | unattributed_false_alert | elsewhere | 6 | 3.481 (1.277, 7.576) |
| stream_a | reset_at_joins | telemetry_model | telemetry_random_forest | telemetry health | unattributed_false_alert | at_join_point | 15 | 8.701 (4.870, 14.352) |
| stream_c | continuous_state | health | timestamp_jitter | flooding | unattributed_false_alert | at_join_point | 2 | 1.160 (0.141, 4.191) |
| stream_c | continuous_state | health | timestamp_jitter | graph/access anomaly | unattributed_false_alert | at_join_point | 3 | 1.740 (0.359, 5.086) |
| stream_c | continuous_state | health | timestamp_jitter | sensor-value anomaly | unattributed_false_alert | at_join_point | 15 | 8.701 (4.870, 14.352) |
| stream_c | continuous_state | health | timestamp_jitter | telemetry health | unattributed_false_alert | at_join_point | 69 | 40.027 (31.143, 50.656) |
| stream_c | continuous_state | health | timestamp_jitter | timing anomaly | unattributed_false_alert | at_join_point | 5 | 2.900 (0.942, 6.769) |
| stream_c | continuous_state | policy_rule:late_messages_observed | late_messages_observed | sensor-value anomaly | unattributed_false_alert | at_join_point | 1 | 0.580 (0.015, 3.232) |
| stream_c | continuous_state | policy_rule:late_messages_observed | late_messages_observed | timing anomaly | unattributed_false_alert | at_join_point | 8 | 4.641 (2.004, 9.144) |
| stream_c | continuous_state | policy_rule:late_messages_observed | late_messages_observed | timing anomaly | unattributed_false_alert | elsewhere | 20 | 11.602 (7.087, 17.918) |
| stream_c | continuous_state | policy_rule:parameter_event_outside_approved_window | parameter_event_outside_approved_window | timing anomaly | unattributed_false_alert | at_join_point | 3 | 1.740 (0.359, 5.086) |
| stream_c | continuous_state | policy_rule:service_call_rate_above_policy | service_call_rate_above_policy | graph/access anomaly | unattributed_false_alert | at_join_point | 3 | 1.740 (0.359, 5.086) |
| stream_c | continuous_state | policy_rule:topic_gap_above_policy | topic_gap_above_policy | timing anomaly | unattributed_false_alert | elsewhere | 7 | 4.061 (1.633, 8.367) |
| stream_c | continuous_state | policy_rule:topic_rate_out_of_band | topic_rate_out_of_band | flooding | unattributed_false_alert | at_join_point | 23 | 13.342 (8.458, 20.020) |
| stream_c | continuous_state | policy_rule:topic_rate_out_of_band | topic_rate_out_of_band | telemetry health | unattributed_false_alert | at_join_point | 2 | 1.160 (0.141, 4.191) |
| stream_c | continuous_state | policy_rule:topic_rate_out_of_band | topic_rate_out_of_band | timing anomaly | unattributed_false_alert | at_join_point | 18 | 10.442 (6.188, 16.502) |
| stream_c | continuous_state | policy_rule:topic_rate_out_of_band | topic_rate_out_of_band | timing anomaly | unattributed_false_alert | elsewhere | 8 | 4.641 (2.004, 9.144) |
| stream_c | continuous_state | policy_rule:topic_stamp_lag_above_policy | topic_stamp_lag_above_policy | flooding | unattributed_false_alert | at_join_point | 3 | 1.740 (0.359, 5.086) |
| stream_c | continuous_state | policy_rule:topic_stamp_lag_above_policy | topic_stamp_lag_above_policy | timing anomaly | unattributed_false_alert | at_join_point | 7 | 4.061 (1.633, 8.367) |
| stream_c | continuous_state | policy_rule:topic_stamp_lag_above_policy | topic_stamp_lag_above_policy | timing anomaly | unattributed_false_alert | elsewhere | 10 | 5.801 (2.782, 10.668) |
| stream_c | continuous_state | sensor_noise_model | sensor_random_forest | flooding | unattributed_false_alert | at_join_point | 6 | 3.481 (1.277, 7.576) |
| stream_c | continuous_state | sensor_noise_model | sensor_random_forest | graph/access anomaly | unattributed_false_alert | at_join_point | 1 | 0.580 (0.015, 3.232) |
| stream_c | continuous_state | sensor_noise_model | sensor_random_forest | sensor-value anomaly | unattributed_false_alert | at_join_point | 31 | 17.983 (12.219, 25.525) |
| stream_c | continuous_state | telemetry_model | telemetry_random_forest | flooding | unattributed_false_alert | at_join_point | 18 | 10.442 (6.188, 16.502) |
| stream_c | continuous_state | telemetry_model | telemetry_random_forest | telemetry health | unattributed_false_alert | at_join_point | 2 | 1.160 (0.141, 4.191) |
| stream_c | continuous_state | telemetry_model | telemetry_random_forest | timing anomaly | unattributed_false_alert | at_join_point | 5 | 2.900 (0.942, 6.769) |
| stream_c | reset_at_joins | policy_rule:late_messages_observed | late_messages_observed | timing anomaly | unattributed_false_alert | elsewhere | 8 | 4.641 (2.004, 9.144) |
| stream_c | reset_at_joins | policy_rule:topic_gap_above_policy | topic_gap_above_policy | timing anomaly | unattributed_false_alert | elsewhere | 4 | 2.320 (0.632, 5.941) |
| stream_c | reset_at_joins | policy_rule:topic_rate_out_of_band | topic_rate_out_of_band | timing anomaly | unattributed_false_alert | elsewhere | 3 | 1.740 (0.359, 5.086) |
| stream_c | reset_at_joins | policy_rule:topic_stamp_lag_above_policy | topic_stamp_lag_above_policy | timing anomaly | unattributed_false_alert | elsewhere | 6 | 3.481 (1.277, 7.576) |
| stream_c | reset_at_joins | telemetry_model | telemetry_random_forest | telemetry health | unattributed_false_alert | at_join_point | 15 | 8.701 (4.870, 14.352) |

## False-alert attribution

| Stream | Mode | Original false incidents (count/rate) | Residual (count/rate) | Unattributed (count/rate) |
|---|---|---:|---:|---:|
| stream_a | continuous_state | 162 (93.975) | 0 (0.000) | 162 (93.975) |
| stream_a | reset_at_joins | 25 (14.502) | 0 (0.000) | 25 (14.502) |
| stream_c | continuous_state | 169 (98.036) | 0 (0.000) | 169 (98.036) |
| stream_c | reset_at_joins | 25 (14.502) | 0 (0.000) | 25 (14.502) |

## Ten longest Stream C reset-mode false incidents

Simulation-clock timestamps are shown as nanoseconds from stream start.

| Start sim ns | End sim ns | Duration (s) | Suspected category | Detectors | Source segments |
|---:|---:|---:|---|---|---|
| 202636666666 | 205636666666 | 3.000 | timing anomaly | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_stamp_lag_above_policy | noise_L2_npc10_seed3 [0.0, 30.0) |
| 408993333334 | 409993333334 | 1.000 | timing anomaly | policy_rule:late_messages_observed, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy | noise_L3_npc10_seed3 [60.0, 90.0) |
| 114043333334 | 114543333334 | 0.500 | timing anomaly | policy_rule:late_messages_observed, policy_rule:topic_stamp_lag_above_policy | noise_L1_npc20_seed3 [60.0, 90.0) |
| 1131373333332 | 1131873333332 | 0.500 | timing anomaly | policy_rule:late_messages_observed | jump_L1_npc10_seed3 [60.0, 90.0) |
| 1310393333332 | 1310893333332 | 0.500 | timing anomaly | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_stamp_lag_above_policy | jump_L2_npc10_seed3 [60.0, 90.0) |
| 2361959999999 | 2362459999999 | 0.500 | timing anomaly | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_stamp_lag_above_policy | delay_L1_npc10_seed3 [0.0, 30.0) |
| 2732219999999 | 2732719999999 | 0.500 | telemetry health | telemetry_model | delay_L3_npc10_seed3 [60.0, 90.0) |
| 3112376666666 | 3112876666666 | 0.500 | timing anomaly | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_stamp_lag_above_policy | drop_L2_npc10_seed3 [60.0, 90.0) |
| 4250503333332 | 4251003333332 | 0.500 | timing anomaly | policy_rule:late_messages_observed | clock_skew_L2_npc20_seed3 [60.0, 90.0) |
| 2240746666666 | 2240746666666 | 0.000 | timing anomaly | policy_rule:topic_rate_out_of_band | missed_contact_L1_npc20_seed3 [0.0, 30.0) |

## Detector-level event performance (all Stream B shuffles, continuous state)

Precision counts each detector's incidents that overlap the named class's event window under the -1.5/+0.5 s tolerance. Latency is measured from the event start to the first matching detector component.

| Stream | Class | Detector | Detected/events | Incident precision | Median latency (s) | P90 latency (s) |
|---|---|---|---:|---:|---:|---:|
| stream_b_seed_1701 | bias_drift | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | clock_skew | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | delay | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | drop | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | duplicate | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | false_contact | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | flood | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | freeze | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | jump | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | missed_contact | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | noise | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | param_tamper | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | replay | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | service_abuse | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | spoof | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | unauthorized_node | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | unauthorized_subscription | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | bias_drift | policy_rule:late_messages_observed | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | clock_skew | policy_rule:late_messages_observed | 1/9 | 0.02702702702702703 | 13.3 | 13.3 |
| stream_b_seed_1701 | delay | policy_rule:late_messages_observed | 8/9 | 0.21621621621621623 | 1.1916666660000002 | 9.52 |
| stream_b_seed_1701 | drop | policy_rule:late_messages_observed | 1/9 | 0.02702702702702703 | 8.3 | 8.3 |
| stream_b_seed_1701 | duplicate | policy_rule:late_messages_observed | 1/9 | 0.02702702702702703 | 18.4 | 18.4 |
| stream_b_seed_1701 | false_contact | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | flood | policy_rule:late_messages_observed | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | freeze | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | jump | policy_rule:late_messages_observed | 1/9 | 0.02702702702702703 | 22.883333334 | 22.883333334 |
| stream_b_seed_1701 | missed_contact | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | noise | policy_rule:late_messages_observed | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | param_tamper | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | replay | policy_rule:late_messages_observed | 1/3 | 0.02702702702702703 | 20.949999999 | 20.949999999 |
| stream_b_seed_1701 | service_abuse | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | spoof | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | unauthorized_node | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | unauthorized_subscription | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | bias_drift | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | clock_skew | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | delay | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | drop | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | duplicate | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | false_contact | policy_rule:node_set_hash_change | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | flood | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | freeze | policy_rule:node_set_hash_change | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | jump | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | missed_contact | policy_rule:node_set_hash_change | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | noise | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | param_tamper | policy_rule:node_set_hash_change | 3/3 | 0.2 | -0.966666667 | -0.8333333334 |
| stream_b_seed_1701 | replay | policy_rule:node_set_hash_change | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | service_abuse | policy_rule:node_set_hash_change | 3/3 | 0.2 | -0.85 | -0.85 |
| stream_b_seed_1701 | spoof | policy_rule:node_set_hash_change | 3/3 | 0.2 | -2.25 | -1.9566666663999999 |
| stream_b_seed_1701 | unauthorized_node | policy_rule:node_set_hash_change | 3/3 | 0.2 | -0.766666667 | -0.5399999998 |
| stream_b_seed_1701 | unauthorized_subscription | policy_rule:node_set_hash_change | 3/3 | 0.2 | -0.6 | -0.5733333336 |
| stream_b_seed_1701 | bias_drift | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | clock_skew | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | delay | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | drop | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | duplicate | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | false_contact | policy_rule:parameter_event_outside_approved_window | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | flood | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | freeze | policy_rule:parameter_event_outside_approved_window | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | jump | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | missed_contact | policy_rule:parameter_event_outside_approved_window | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | noise | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | param_tamper | policy_rule:parameter_event_outside_approved_window | 3/3 | 0.25 | -0.966666667 | -0.8333333334 |
| stream_b_seed_1701 | replay | policy_rule:parameter_event_outside_approved_window | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | service_abuse | policy_rule:parameter_event_outside_approved_window | 1/3 | 0.08333333333333333 | -0.85 | -0.85 |
| stream_b_seed_1701 | spoof | policy_rule:parameter_event_outside_approved_window | 3/3 | 0.25 | -2.25 | -1.9566666663999999 |
| stream_b_seed_1701 | unauthorized_node | policy_rule:parameter_event_outside_approved_window | 2/3 | 0.16666666666666666 | -0.783333333 | -0.543333333 |
| stream_b_seed_1701 | unauthorized_subscription | policy_rule:parameter_event_outside_approved_window | 3/3 | 0.25 | -0.6 | -0.5733333336 |
| stream_b_seed_1701 | bias_drift | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | clock_skew | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | delay | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | drop | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | duplicate | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | false_contact | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | flood | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | freeze | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | jump | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | missed_contact | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | noise | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | param_tamper | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | replay | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | service_abuse | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | spoof | policy_rule:publisher_count_above_policy | 3/3 | 1.0 | -0.383333333 | -0.2766666666 |
| stream_b_seed_1701 | unauthorized_node | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | unauthorized_subscription | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | bias_drift | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | clock_skew | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | delay | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | drop | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | duplicate | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | false_contact | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | flood | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | freeze | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | jump | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | missed_contact | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | noise | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | param_tamper | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | replay | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | service_abuse | policy_rule:service_call_rate_above_policy | 3/3 | 1.0 | -0.35 | -0.35 |
| stream_b_seed_1701 | spoof | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | unauthorized_node | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | unauthorized_subscription | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | bias_drift | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | clock_skew | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | delay | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | drop | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | duplicate | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | false_contact | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | flood | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | freeze | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | jump | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | missed_contact | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | noise | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | param_tamper | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | replay | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | service_abuse | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | spoof | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | unauthorized_node | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | unauthorized_subscription | policy_rule:subscriber_count_above_policy | 3/3 | 1.0 | -0.316666667 | -0.11666666699999999 |
| stream_b_seed_1701 | bias_drift | policy_rule:topic_gap_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | clock_skew | policy_rule:topic_gap_above_policy | 1/9 | 0.05263157894736842 | 13.3 | 13.3 |
| stream_b_seed_1701 | delay | policy_rule:topic_gap_above_policy | 6/9 | 0.3157894736842105 | 0.4 | 0.583333333 |
| stream_b_seed_1701 | drop | policy_rule:topic_gap_above_policy | 3/9 | 0.15789473684210525 | 10.766666667 | 10.793333333400001 |
| stream_b_seed_1701 | duplicate | policy_rule:topic_gap_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | false_contact | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | flood | policy_rule:topic_gap_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | freeze | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | jump | policy_rule:topic_gap_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | missed_contact | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | noise | policy_rule:topic_gap_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | param_tamper | policy_rule:topic_gap_above_policy | 1/3 | 0.05263157894736842 | 10.533333333 | 10.533333333 |
| stream_b_seed_1701 | replay | policy_rule:topic_gap_above_policy | 1/3 | 0.05263157894736842 | 20.949999999 | 20.949999999 |
| stream_b_seed_1701 | service_abuse | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | spoof | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | unauthorized_node | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | unauthorized_subscription | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | bias_drift | policy_rule:topic_rate_out_of_band | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | clock_skew | policy_rule:topic_rate_out_of_band | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | delay | policy_rule:topic_rate_out_of_band | 9/9 | 0.16981132075471697 | 0.4 | 0.51 |
| stream_b_seed_1701 | drop | policy_rule:topic_rate_out_of_band | 9/9 | 0.16981132075471697 | 0.3 | 0.7299999998000001 |
| stream_b_seed_1701 | duplicate | policy_rule:topic_rate_out_of_band | 9/9 | 0.16981132075471697 | 0.4 | 0.74 |
| stream_b_seed_1701 | false_contact | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | flood | policy_rule:topic_rate_out_of_band | 9/9 | 0.16981132075471697 | 0.216666667 | 0.5133333332000001 |
| stream_b_seed_1701 | freeze | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | jump | policy_rule:topic_rate_out_of_band | 1/9 | 0.018867924528301886 | 22.383333334 | 22.383333334 |
| stream_b_seed_1701 | missed_contact | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | noise | policy_rule:topic_rate_out_of_band | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | param_tamper | policy_rule:topic_rate_out_of_band | 3/3 | 0.05660377358490566 | -0.466666667 | -0.3333333334 |
| stream_b_seed_1701 | replay | policy_rule:topic_rate_out_of_band | 1/3 | 0.018867924528301886 | 20.449999999 | 20.449999999 |
| stream_b_seed_1701 | service_abuse | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | spoof | policy_rule:topic_rate_out_of_band | 3/3 | 0.05660377358490566 | -0.383333333 | -0.2766666666 |
| stream_b_seed_1701 | unauthorized_node | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | unauthorized_subscription | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | bias_drift | policy_rule:topic_stamp_lag_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | clock_skew | policy_rule:topic_stamp_lag_above_policy | 1/9 | 0.04 | 13.3 | 13.3 |
| stream_b_seed_1701 | delay | policy_rule:topic_stamp_lag_above_policy | 9/9 | 0.36 | 0.85 | 1.2933333328 |
| stream_b_seed_1701 | drop | policy_rule:topic_stamp_lag_above_policy | 1/9 | 0.04 | 8.3 | 8.3 |
| stream_b_seed_1701 | duplicate | policy_rule:topic_stamp_lag_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | false_contact | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | flood | policy_rule:topic_stamp_lag_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | freeze | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | jump | policy_rule:topic_stamp_lag_above_policy | 1/9 | 0.04 | 22.883333334 | 22.883333334 |
| stream_b_seed_1701 | missed_contact | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | noise | policy_rule:topic_stamp_lag_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | param_tamper | policy_rule:topic_stamp_lag_above_policy | 1/3 | 0.04 | 28.533333333 | 28.533333333 |
| stream_b_seed_1701 | replay | policy_rule:topic_stamp_lag_above_policy | 1/3 | 0.04 | 20.949999999 | 20.949999999 |
| stream_b_seed_1701 | service_abuse | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | spoof | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | unauthorized_node | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | unauthorized_subscription | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | bias_drift | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | clock_skew | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | delay | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | drop | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | duplicate | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | false_contact | policy_rule:unapproved_node | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | flood | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | freeze | policy_rule:unapproved_node | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | jump | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | missed_contact | policy_rule:unapproved_node | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | noise | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | param_tamper | policy_rule:unapproved_node | 3/3 | 0.2 | -0.966666667 | -0.8333333334 |
| stream_b_seed_1701 | replay | policy_rule:unapproved_node | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | service_abuse | policy_rule:unapproved_node | 3/3 | 0.2 | -0.85 | -0.85 |
| stream_b_seed_1701 | spoof | policy_rule:unapproved_node | 3/3 | 0.2 | -2.25 | -1.9566666663999999 |
| stream_b_seed_1701 | unauthorized_node | policy_rule:unapproved_node | 3/3 | 0.2 | -0.766666667 | -0.5399999998 |
| stream_b_seed_1701 | unauthorized_subscription | policy_rule:unapproved_node | 3/3 | 0.2 | -0.6 | -0.5733333336 |
| stream_b_seed_1701 | bias_drift | sensor_noise_model | 6/9 | 0.2972972972972973 | 0.02 | 0.04 |
| stream_b_seed_1701 | clock_skew | sensor_noise_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | delay | sensor_noise_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | drop | sensor_noise_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | duplicate | sensor_noise_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | false_contact | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | flood | sensor_noise_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | freeze | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | jump | sensor_noise_model | 1/9 | 0.02702702702702703 | 0.08 | 0.08 |
| stream_b_seed_1701 | missed_contact | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | noise | sensor_noise_model | 9/9 | 0.24324324324324326 | 0.04 | 0.084 |
| stream_b_seed_1701 | param_tamper | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | replay | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | service_abuse | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | spoof | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | unauthorized_node | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | unauthorized_subscription | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | bias_drift | telemetry_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | clock_skew | telemetry_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | delay | telemetry_model | 3/9 | 0.08333333333333333 | 30.266666666 | 30.373333333199998 |
| stream_b_seed_1701 | drop | telemetry_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | duplicate | telemetry_model | 9/9 | 0.25 | 0.55 | 12.260000000000002 |
| stream_b_seed_1701 | false_contact | telemetry_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | flood | telemetry_model | 9/9 | 0.25 | 0.216666667 | 0.5133333332000001 |
| stream_b_seed_1701 | freeze | telemetry_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | jump | telemetry_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | missed_contact | telemetry_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | noise | telemetry_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | param_tamper | telemetry_model | 3/3 | 0.08333333333333333 | 2.533333333 | 2.6666666666000003 |
| stream_b_seed_1701 | replay | telemetry_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_1701 | service_abuse | telemetry_model | 3/3 | 0.08333333333333333 | -0.35 | 0.05000000000000002 |
| stream_b_seed_1701 | spoof | telemetry_model | 3/3 | 0.08333333333333333 | -1.25 | -0.15666666639999993 |
| stream_b_seed_1701 | unauthorized_node | telemetry_model | 3/3 | 0.08333333333333333 | -0.083333333 | 0.796666667 |
| stream_b_seed_1701 | unauthorized_subscription | telemetry_model | 3/3 | 0.08333333333333333 | 0.4 | 0.4266666664 |
| stream_b_seed_2903 | bias_drift | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | clock_skew | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | delay | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | drop | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | duplicate | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | false_contact | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | flood | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | freeze | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | jump | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | missed_contact | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | noise | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | param_tamper | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | replay | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | service_abuse | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | spoof | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | unauthorized_node | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | unauthorized_subscription | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | bias_drift | policy_rule:late_messages_observed | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | clock_skew | policy_rule:late_messages_observed | 1/9 | 0.02702702702702703 | 13.3 | 13.3 |
| stream_b_seed_2903 | delay | policy_rule:late_messages_observed | 8/9 | 0.21621621621621623 | 1.1916666660000002 | 9.52 |
| stream_b_seed_2903 | drop | policy_rule:late_messages_observed | 1/9 | 0.02702702702702703 | 8.3 | 8.3 |
| stream_b_seed_2903 | duplicate | policy_rule:late_messages_observed | 1/9 | 0.02702702702702703 | 18.4 | 18.4 |
| stream_b_seed_2903 | false_contact | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | flood | policy_rule:late_messages_observed | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | freeze | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | jump | policy_rule:late_messages_observed | 1/9 | 0.02702702702702703 | 22.883333334 | 22.883333334 |
| stream_b_seed_2903 | missed_contact | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | noise | policy_rule:late_messages_observed | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | param_tamper | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | replay | policy_rule:late_messages_observed | 1/3 | 0.02702702702702703 | 20.949999999 | 20.949999999 |
| stream_b_seed_2903 | service_abuse | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | spoof | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | unauthorized_node | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | unauthorized_subscription | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | bias_drift | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | clock_skew | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | delay | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | drop | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | duplicate | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | false_contact | policy_rule:node_set_hash_change | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | flood | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | freeze | policy_rule:node_set_hash_change | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | jump | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | missed_contact | policy_rule:node_set_hash_change | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | noise | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | param_tamper | policy_rule:node_set_hash_change | 3/3 | 0.2 | -0.966666667 | -0.8333333334 |
| stream_b_seed_2903 | replay | policy_rule:node_set_hash_change | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | service_abuse | policy_rule:node_set_hash_change | 3/3 | 0.2 | -0.85 | -0.85 |
| stream_b_seed_2903 | spoof | policy_rule:node_set_hash_change | 3/3 | 0.2 | -2.25 | -1.9566666663999999 |
| stream_b_seed_2903 | unauthorized_node | policy_rule:node_set_hash_change | 3/3 | 0.2 | -0.766666667 | -0.5399999998 |
| stream_b_seed_2903 | unauthorized_subscription | policy_rule:node_set_hash_change | 3/3 | 0.2 | -0.6 | -0.5733333336 |
| stream_b_seed_2903 | bias_drift | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | clock_skew | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | delay | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | drop | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | duplicate | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | false_contact | policy_rule:parameter_event_outside_approved_window | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | flood | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | freeze | policy_rule:parameter_event_outside_approved_window | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | jump | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | missed_contact | policy_rule:parameter_event_outside_approved_window | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | noise | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | param_tamper | policy_rule:parameter_event_outside_approved_window | 3/3 | 0.25 | -0.966666667 | -0.8333333334 |
| stream_b_seed_2903 | replay | policy_rule:parameter_event_outside_approved_window | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | service_abuse | policy_rule:parameter_event_outside_approved_window | 1/3 | 0.08333333333333333 | -0.85 | -0.85 |
| stream_b_seed_2903 | spoof | policy_rule:parameter_event_outside_approved_window | 3/3 | 0.25 | -2.25 | -1.9566666663999999 |
| stream_b_seed_2903 | unauthorized_node | policy_rule:parameter_event_outside_approved_window | 2/3 | 0.16666666666666666 | -0.783333333 | -0.543333333 |
| stream_b_seed_2903 | unauthorized_subscription | policy_rule:parameter_event_outside_approved_window | 3/3 | 0.25 | -0.6 | -0.5733333336 |
| stream_b_seed_2903 | bias_drift | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | clock_skew | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | delay | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | drop | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | duplicate | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | false_contact | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | flood | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | freeze | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | jump | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | missed_contact | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | noise | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | param_tamper | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | replay | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | service_abuse | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | spoof | policy_rule:publisher_count_above_policy | 3/3 | 1.0 | -0.383333333 | -0.2766666666 |
| stream_b_seed_2903 | unauthorized_node | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | unauthorized_subscription | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | bias_drift | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | clock_skew | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | delay | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | drop | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | duplicate | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | false_contact | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | flood | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | freeze | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | jump | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | missed_contact | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | noise | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | param_tamper | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | replay | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | service_abuse | policy_rule:service_call_rate_above_policy | 3/3 | 1.0 | -0.35 | -0.35 |
| stream_b_seed_2903 | spoof | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | unauthorized_node | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | unauthorized_subscription | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | bias_drift | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | clock_skew | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | delay | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | drop | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | duplicate | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | false_contact | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | flood | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | freeze | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | jump | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | missed_contact | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | noise | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | param_tamper | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | replay | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | service_abuse | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | spoof | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | unauthorized_node | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | unauthorized_subscription | policy_rule:subscriber_count_above_policy | 3/3 | 1.0 | -0.316666667 | -0.11666666699999999 |
| stream_b_seed_2903 | bias_drift | policy_rule:topic_gap_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | clock_skew | policy_rule:topic_gap_above_policy | 1/9 | 0.05263157894736842 | 13.3 | 13.3 |
| stream_b_seed_2903 | delay | policy_rule:topic_gap_above_policy | 6/9 | 0.3157894736842105 | 0.4 | 0.583333333 |
| stream_b_seed_2903 | drop | policy_rule:topic_gap_above_policy | 3/9 | 0.15789473684210525 | 10.766666667 | 10.793333333400001 |
| stream_b_seed_2903 | duplicate | policy_rule:topic_gap_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | false_contact | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | flood | policy_rule:topic_gap_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | freeze | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | jump | policy_rule:topic_gap_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | missed_contact | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | noise | policy_rule:topic_gap_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | param_tamper | policy_rule:topic_gap_above_policy | 1/3 | 0.05263157894736842 | 10.533333333 | 10.533333333 |
| stream_b_seed_2903 | replay | policy_rule:topic_gap_above_policy | 1/3 | 0.05263157894736842 | 20.949999999 | 20.949999999 |
| stream_b_seed_2903 | service_abuse | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | spoof | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | unauthorized_node | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | unauthorized_subscription | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | bias_drift | policy_rule:topic_rate_out_of_band | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | clock_skew | policy_rule:topic_rate_out_of_band | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | delay | policy_rule:topic_rate_out_of_band | 9/9 | 0.16981132075471697 | 0.4 | 0.51 |
| stream_b_seed_2903 | drop | policy_rule:topic_rate_out_of_band | 9/9 | 0.16981132075471697 | 0.3 | 0.7299999998000001 |
| stream_b_seed_2903 | duplicate | policy_rule:topic_rate_out_of_band | 9/9 | 0.16981132075471697 | 0.4 | 0.74 |
| stream_b_seed_2903 | false_contact | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | flood | policy_rule:topic_rate_out_of_band | 9/9 | 0.16981132075471697 | 0.216666667 | 0.5133333332000001 |
| stream_b_seed_2903 | freeze | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | jump | policy_rule:topic_rate_out_of_band | 1/9 | 0.018867924528301886 | 22.383333334 | 22.383333334 |
| stream_b_seed_2903 | missed_contact | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | noise | policy_rule:topic_rate_out_of_band | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | param_tamper | policy_rule:topic_rate_out_of_band | 3/3 | 0.05660377358490566 | -0.466666667 | -0.3333333334 |
| stream_b_seed_2903 | replay | policy_rule:topic_rate_out_of_band | 1/3 | 0.018867924528301886 | 20.449999999 | 20.449999999 |
| stream_b_seed_2903 | service_abuse | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | spoof | policy_rule:topic_rate_out_of_band | 3/3 | 0.05660377358490566 | -0.383333333 | -0.2766666666 |
| stream_b_seed_2903 | unauthorized_node | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | unauthorized_subscription | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | bias_drift | policy_rule:topic_stamp_lag_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | clock_skew | policy_rule:topic_stamp_lag_above_policy | 1/9 | 0.04 | 13.3 | 13.3 |
| stream_b_seed_2903 | delay | policy_rule:topic_stamp_lag_above_policy | 9/9 | 0.36 | 0.85 | 1.2933333328 |
| stream_b_seed_2903 | drop | policy_rule:topic_stamp_lag_above_policy | 1/9 | 0.04 | 8.3 | 8.3 |
| stream_b_seed_2903 | duplicate | policy_rule:topic_stamp_lag_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | false_contact | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | flood | policy_rule:topic_stamp_lag_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | freeze | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | jump | policy_rule:topic_stamp_lag_above_policy | 1/9 | 0.04 | 22.883333334 | 22.883333334 |
| stream_b_seed_2903 | missed_contact | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | noise | policy_rule:topic_stamp_lag_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | param_tamper | policy_rule:topic_stamp_lag_above_policy | 1/3 | 0.04 | 28.533333333 | 28.533333333 |
| stream_b_seed_2903 | replay | policy_rule:topic_stamp_lag_above_policy | 1/3 | 0.04 | 20.949999999 | 20.949999999 |
| stream_b_seed_2903 | service_abuse | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | spoof | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | unauthorized_node | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | unauthorized_subscription | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | bias_drift | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | clock_skew | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | delay | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | drop | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | duplicate | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | false_contact | policy_rule:unapproved_node | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | flood | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | freeze | policy_rule:unapproved_node | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | jump | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | missed_contact | policy_rule:unapproved_node | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | noise | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | param_tamper | policy_rule:unapproved_node | 3/3 | 0.2 | -0.966666667 | -0.8333333334 |
| stream_b_seed_2903 | replay | policy_rule:unapproved_node | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | service_abuse | policy_rule:unapproved_node | 3/3 | 0.2 | -0.85 | -0.85 |
| stream_b_seed_2903 | spoof | policy_rule:unapproved_node | 3/3 | 0.2 | -2.25 | -1.9566666663999999 |
| stream_b_seed_2903 | unauthorized_node | policy_rule:unapproved_node | 3/3 | 0.2 | -0.766666667 | -0.5399999998 |
| stream_b_seed_2903 | unauthorized_subscription | policy_rule:unapproved_node | 3/3 | 0.2 | -0.6 | -0.5733333336 |
| stream_b_seed_2903 | bias_drift | sensor_noise_model | 6/9 | 0.3142857142857143 | 0.02 | 0.04 |
| stream_b_seed_2903 | clock_skew | sensor_noise_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | delay | sensor_noise_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | drop | sensor_noise_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | duplicate | sensor_noise_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | false_contact | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | flood | sensor_noise_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | freeze | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | jump | sensor_noise_model | 1/9 | 0.02857142857142857 | 0.08 | 0.08 |
| stream_b_seed_2903 | missed_contact | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | noise | sensor_noise_model | 9/9 | 0.2571428571428571 | 0.04 | 0.084 |
| stream_b_seed_2903 | param_tamper | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | replay | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | service_abuse | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | spoof | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | unauthorized_node | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | unauthorized_subscription | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | bias_drift | telemetry_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | clock_skew | telemetry_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | delay | telemetry_model | 3/9 | 0.08333333333333333 | 30.266666666 | 30.373333333199998 |
| stream_b_seed_2903 | drop | telemetry_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | duplicate | telemetry_model | 9/9 | 0.25 | 0.55 | 12.260000000000002 |
| stream_b_seed_2903 | false_contact | telemetry_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | flood | telemetry_model | 9/9 | 0.25 | 0.216666667 | 0.5133333332000001 |
| stream_b_seed_2903 | freeze | telemetry_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | jump | telemetry_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | missed_contact | telemetry_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | noise | telemetry_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | param_tamper | telemetry_model | 3/3 | 0.08333333333333333 | 2.533333333 | 2.6666666666000003 |
| stream_b_seed_2903 | replay | telemetry_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_2903 | service_abuse | telemetry_model | 3/3 | 0.08333333333333333 | -0.35 | 0.05000000000000002 |
| stream_b_seed_2903 | spoof | telemetry_model | 3/3 | 0.08333333333333333 | -1.25 | -0.15666666639999993 |
| stream_b_seed_2903 | unauthorized_node | telemetry_model | 3/3 | 0.08333333333333333 | -0.083333333 | 0.796666667 |
| stream_b_seed_2903 | unauthorized_subscription | telemetry_model | 3/3 | 0.08333333333333333 | 0.4 | 0.4266666664 |
| stream_b_seed_4307 | bias_drift | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | clock_skew | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | delay | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | drop | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | duplicate | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | false_contact | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | flood | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | freeze | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | jump | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | missed_contact | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | noise | health | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | param_tamper | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | replay | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | service_abuse | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | spoof | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | unauthorized_node | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | unauthorized_subscription | health | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | bias_drift | policy_rule:late_messages_observed | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | clock_skew | policy_rule:late_messages_observed | 1/9 | 0.02702702702702703 | 13.3 | 13.3 |
| stream_b_seed_4307 | delay | policy_rule:late_messages_observed | 8/9 | 0.21621621621621623 | 1.1916666660000002 | 9.52 |
| stream_b_seed_4307 | drop | policy_rule:late_messages_observed | 1/9 | 0.02702702702702703 | 8.3 | 8.3 |
| stream_b_seed_4307 | duplicate | policy_rule:late_messages_observed | 1/9 | 0.02702702702702703 | 18.4 | 18.4 |
| stream_b_seed_4307 | false_contact | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | flood | policy_rule:late_messages_observed | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | freeze | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | jump | policy_rule:late_messages_observed | 1/9 | 0.02702702702702703 | 22.883333334 | 22.883333334 |
| stream_b_seed_4307 | missed_contact | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | noise | policy_rule:late_messages_observed | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | param_tamper | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | replay | policy_rule:late_messages_observed | 1/3 | 0.02702702702702703 | 20.949999999 | 20.949999999 |
| stream_b_seed_4307 | service_abuse | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | spoof | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | unauthorized_node | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | unauthorized_subscription | policy_rule:late_messages_observed | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | bias_drift | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | clock_skew | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | delay | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | drop | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | duplicate | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | false_contact | policy_rule:node_set_hash_change | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | flood | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | freeze | policy_rule:node_set_hash_change | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | jump | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | missed_contact | policy_rule:node_set_hash_change | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | noise | policy_rule:node_set_hash_change | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | param_tamper | policy_rule:node_set_hash_change | 3/3 | 0.2 | -0.966666667 | -0.8333333334 |
| stream_b_seed_4307 | replay | policy_rule:node_set_hash_change | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | service_abuse | policy_rule:node_set_hash_change | 3/3 | 0.2 | -0.85 | -0.85 |
| stream_b_seed_4307 | spoof | policy_rule:node_set_hash_change | 3/3 | 0.2 | -2.25 | -1.9566666663999999 |
| stream_b_seed_4307 | unauthorized_node | policy_rule:node_set_hash_change | 3/3 | 0.2 | -0.766666667 | -0.5399999998 |
| stream_b_seed_4307 | unauthorized_subscription | policy_rule:node_set_hash_change | 3/3 | 0.2 | -0.6 | -0.5733333336 |
| stream_b_seed_4307 | bias_drift | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | clock_skew | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | delay | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | drop | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | duplicate | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | false_contact | policy_rule:parameter_event_outside_approved_window | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | flood | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | freeze | policy_rule:parameter_event_outside_approved_window | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | jump | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | missed_contact | policy_rule:parameter_event_outside_approved_window | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | noise | policy_rule:parameter_event_outside_approved_window | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | param_tamper | policy_rule:parameter_event_outside_approved_window | 3/3 | 0.25 | -0.966666667 | -0.8333333334 |
| stream_b_seed_4307 | replay | policy_rule:parameter_event_outside_approved_window | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | service_abuse | policy_rule:parameter_event_outside_approved_window | 1/3 | 0.08333333333333333 | -0.85 | -0.85 |
| stream_b_seed_4307 | spoof | policy_rule:parameter_event_outside_approved_window | 3/3 | 0.25 | -2.25 | -1.9566666663999999 |
| stream_b_seed_4307 | unauthorized_node | policy_rule:parameter_event_outside_approved_window | 2/3 | 0.16666666666666666 | -0.783333333 | -0.543333333 |
| stream_b_seed_4307 | unauthorized_subscription | policy_rule:parameter_event_outside_approved_window | 3/3 | 0.25 | -0.6 | -0.5733333336 |
| stream_b_seed_4307 | bias_drift | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | clock_skew | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | delay | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | drop | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | duplicate | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | false_contact | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | flood | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | freeze | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | jump | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | missed_contact | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | noise | policy_rule:publisher_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | param_tamper | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | replay | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | service_abuse | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | spoof | policy_rule:publisher_count_above_policy | 3/3 | 1.0 | -0.383333333 | -0.2766666666 |
| stream_b_seed_4307 | unauthorized_node | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | unauthorized_subscription | policy_rule:publisher_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | bias_drift | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | clock_skew | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | delay | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | drop | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | duplicate | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | false_contact | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | flood | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | freeze | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | jump | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | missed_contact | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | noise | policy_rule:service_call_rate_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | param_tamper | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | replay | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | service_abuse | policy_rule:service_call_rate_above_policy | 3/3 | 1.0 | -0.35 | -0.35 |
| stream_b_seed_4307 | spoof | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | unauthorized_node | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | unauthorized_subscription | policy_rule:service_call_rate_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | bias_drift | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | clock_skew | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | delay | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | drop | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | duplicate | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | false_contact | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | flood | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | freeze | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | jump | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | missed_contact | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | noise | policy_rule:subscriber_count_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | param_tamper | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | replay | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | service_abuse | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | spoof | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | unauthorized_node | policy_rule:subscriber_count_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | unauthorized_subscription | policy_rule:subscriber_count_above_policy | 3/3 | 1.0 | -0.316666667 | -0.11666666699999999 |
| stream_b_seed_4307 | bias_drift | policy_rule:topic_gap_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | clock_skew | policy_rule:topic_gap_above_policy | 1/9 | 0.05263157894736842 | 13.3 | 13.3 |
| stream_b_seed_4307 | delay | policy_rule:topic_gap_above_policy | 6/9 | 0.3157894736842105 | 0.4 | 0.583333333 |
| stream_b_seed_4307 | drop | policy_rule:topic_gap_above_policy | 3/9 | 0.15789473684210525 | 10.766666667 | 10.793333333400001 |
| stream_b_seed_4307 | duplicate | policy_rule:topic_gap_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | false_contact | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | flood | policy_rule:topic_gap_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | freeze | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | jump | policy_rule:topic_gap_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | missed_contact | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | noise | policy_rule:topic_gap_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | param_tamper | policy_rule:topic_gap_above_policy | 1/3 | 0.05263157894736842 | 10.533333333 | 10.533333333 |
| stream_b_seed_4307 | replay | policy_rule:topic_gap_above_policy | 1/3 | 0.05263157894736842 | 20.949999999 | 20.949999999 |
| stream_b_seed_4307 | service_abuse | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | spoof | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | unauthorized_node | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | unauthorized_subscription | policy_rule:topic_gap_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | bias_drift | policy_rule:topic_rate_out_of_band | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | clock_skew | policy_rule:topic_rate_out_of_band | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | delay | policy_rule:topic_rate_out_of_band | 9/9 | 0.16981132075471697 | 0.4 | 0.51 |
| stream_b_seed_4307 | drop | policy_rule:topic_rate_out_of_band | 9/9 | 0.16981132075471697 | 0.3 | 0.7299999998000001 |
| stream_b_seed_4307 | duplicate | policy_rule:topic_rate_out_of_band | 9/9 | 0.16981132075471697 | 0.4 | 0.74 |
| stream_b_seed_4307 | false_contact | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | flood | policy_rule:topic_rate_out_of_band | 9/9 | 0.16981132075471697 | 0.216666667 | 0.5133333332000001 |
| stream_b_seed_4307 | freeze | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | jump | policy_rule:topic_rate_out_of_band | 1/9 | 0.018867924528301886 | 22.383333334 | 22.383333334 |
| stream_b_seed_4307 | missed_contact | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | noise | policy_rule:topic_rate_out_of_band | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | param_tamper | policy_rule:topic_rate_out_of_band | 3/3 | 0.05660377358490566 | -0.466666667 | -0.3333333334 |
| stream_b_seed_4307 | replay | policy_rule:topic_rate_out_of_band | 1/3 | 0.018867924528301886 | 20.449999999 | 20.449999999 |
| stream_b_seed_4307 | service_abuse | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | spoof | policy_rule:topic_rate_out_of_band | 3/3 | 0.05660377358490566 | -0.383333333 | -0.2766666666 |
| stream_b_seed_4307 | unauthorized_node | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | unauthorized_subscription | policy_rule:topic_rate_out_of_band | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | bias_drift | policy_rule:topic_stamp_lag_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | clock_skew | policy_rule:topic_stamp_lag_above_policy | 1/9 | 0.04 | 13.3 | 13.3 |
| stream_b_seed_4307 | delay | policy_rule:topic_stamp_lag_above_policy | 9/9 | 0.36 | 0.85 | 1.2933333328 |
| stream_b_seed_4307 | drop | policy_rule:topic_stamp_lag_above_policy | 1/9 | 0.04 | 8.3 | 8.3 |
| stream_b_seed_4307 | duplicate | policy_rule:topic_stamp_lag_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | false_contact | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | flood | policy_rule:topic_stamp_lag_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | freeze | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | jump | policy_rule:topic_stamp_lag_above_policy | 1/9 | 0.04 | 22.883333334 | 22.883333334 |
| stream_b_seed_4307 | missed_contact | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | noise | policy_rule:topic_stamp_lag_above_policy | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | param_tamper | policy_rule:topic_stamp_lag_above_policy | 1/3 | 0.04 | 28.533333333 | 28.533333333 |
| stream_b_seed_4307 | replay | policy_rule:topic_stamp_lag_above_policy | 1/3 | 0.04 | 20.949999999 | 20.949999999 |
| stream_b_seed_4307 | service_abuse | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | spoof | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | unauthorized_node | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | unauthorized_subscription | policy_rule:topic_stamp_lag_above_policy | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | bias_drift | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | clock_skew | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | delay | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | drop | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | duplicate | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | false_contact | policy_rule:unapproved_node | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | flood | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | freeze | policy_rule:unapproved_node | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | jump | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | missed_contact | policy_rule:unapproved_node | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | noise | policy_rule:unapproved_node | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | param_tamper | policy_rule:unapproved_node | 3/3 | 0.2 | -0.966666667 | -0.8333333334 |
| stream_b_seed_4307 | replay | policy_rule:unapproved_node | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | service_abuse | policy_rule:unapproved_node | 3/3 | 0.2 | -0.85 | -0.85 |
| stream_b_seed_4307 | spoof | policy_rule:unapproved_node | 3/3 | 0.2 | -2.25 | -1.9566666663999999 |
| stream_b_seed_4307 | unauthorized_node | policy_rule:unapproved_node | 3/3 | 0.2 | -0.766666667 | -0.5399999998 |
| stream_b_seed_4307 | unauthorized_subscription | policy_rule:unapproved_node | 3/3 | 0.2 | -0.6 | -0.5733333336 |
| stream_b_seed_4307 | bias_drift | sensor_noise_model | 6/9 | 0.3055555555555556 | 0.02 | 0.04 |
| stream_b_seed_4307 | clock_skew | sensor_noise_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | delay | sensor_noise_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | drop | sensor_noise_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | duplicate | sensor_noise_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | false_contact | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | flood | sensor_noise_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | freeze | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | jump | sensor_noise_model | 1/9 | 0.027777777777777776 | 0.08 | 0.08 |
| stream_b_seed_4307 | missed_contact | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | noise | sensor_noise_model | 9/9 | 0.25 | 0.04 | 0.084 |
| stream_b_seed_4307 | param_tamper | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | replay | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | service_abuse | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | spoof | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | unauthorized_node | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | unauthorized_subscription | sensor_noise_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | bias_drift | telemetry_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | clock_skew | telemetry_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | delay | telemetry_model | 3/9 | 0.08333333333333333 | 30.266666666 | 30.373333333199998 |
| stream_b_seed_4307 | drop | telemetry_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | duplicate | telemetry_model | 9/9 | 0.25 | 0.55 | 12.260000000000002 |
| stream_b_seed_4307 | false_contact | telemetry_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | flood | telemetry_model | 9/9 | 0.25 | 0.216666667 | 0.5133333332000001 |
| stream_b_seed_4307 | freeze | telemetry_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | jump | telemetry_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | missed_contact | telemetry_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | noise | telemetry_model | 0/9 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | param_tamper | telemetry_model | 3/3 | 0.08333333333333333 | 2.533333333 | 2.6666666666000003 |
| stream_b_seed_4307 | replay | telemetry_model | 0/3 | 0.0 | n/a | n/a |
| stream_b_seed_4307 | service_abuse | telemetry_model | 3/3 | 0.08333333333333333 | -0.35 | 0.05000000000000002 |
| stream_b_seed_4307 | spoof | telemetry_model | 3/3 | 0.08333333333333333 | -1.25 | -0.15666666639999993 |
| stream_b_seed_4307 | unauthorized_node | telemetry_model | 3/3 | 0.08333333333333333 | -0.083333333 | 0.796666667 |
| stream_b_seed_4307 | unauthorized_subscription | telemetry_model | 3/3 | 0.08333333333333333 | 0.4 | 0.4266666664 |

## Row-level metrics

| Stream | Mode | Precision | Recall | F1 | FPR |
|---|---|---:|---:|---:|---:|
| stream_a | continuous_state | 0.3560 | 0.0200 | 0.0379 | 0.0019 |
| stream_a | reset_at_joins | 0.8526 | 0.0130 | 0.0256 | 0.0001 |
| stream_b_seed_1701 | continuous_state | 0.9687 | 0.1123 | 0.2013 | 0.0017 |
| stream_b_seed_1701 | reset_at_joins | 0.9874 | 0.1123 | 0.2017 | 0.0007 |
| stream_b_seed_2903 | continuous_state | 0.9695 | 0.1123 | 0.2013 | 0.0017 |
| stream_b_seed_2903 | reset_at_joins | 0.9874 | 0.1123 | 0.2017 | 0.0007 |
| stream_b_seed_4307 | continuous_state | 0.9707 | 0.1123 | 0.2014 | 0.0016 |
| stream_b_seed_4307 | reset_at_joins | 0.9874 | 0.1123 | 0.2017 | 0.0007 |
| stream_c | continuous_state | 0.0000 | 0.0000 | 0.0000 | 0.0019 |
| stream_c | reset_at_joins | 0.0000 | 0.0000 | 0.0000 | 0.0001 |

## Class coverage (all Stream B shuffles)

| Stream | Class | Events | Detected | Detector(s) | Multi-detector | Expected miss |
|---|---|---:|---|---|---|---|
| stream_b_seed_1701 | bias_drift | 9 | True | sensor_noise_model | False | False |
| stream_b_seed_1701 | clock_skew | 9 | True | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_stamp_lag_above_policy | True | False |
| stream_b_seed_1701 | delay | 9 | True | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy, telemetry_model | True | False |
| stream_b_seed_1701 | drop | 9 | True | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy | True | False |
| stream_b_seed_1701 | duplicate | 9 | True | policy_rule:late_messages_observed, policy_rule:topic_rate_out_of_band, telemetry_model | True | False |
| stream_b_seed_1701 | false_contact | 3 | False | none | False | False |
| stream_b_seed_1701 | flood | 9 | True | policy_rule:topic_rate_out_of_band, telemetry_model | True | False |
| stream_b_seed_1701 | freeze | 3 | False | none | False | False |
| stream_b_seed_1701 | jump | 9 | True | policy_rule:late_messages_observed, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy, sensor_noise_model | True | False |
| stream_b_seed_1701 | missed_contact | 3 | False | none | False | True |
| stream_b_seed_1701 | noise | 9 | True | sensor_noise_model | False | False |
| stream_b_seed_1701 | param_tamper | 3 | True | policy_rule:node_set_hash_change, policy_rule:parameter_event_outside_approved_window, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy, policy_rule:unapproved_node, telemetry_model | True | False |
| stream_b_seed_1701 | replay | 3 | True | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy | True | False |
| stream_b_seed_1701 | service_abuse | 3 | True | policy_rule:node_set_hash_change, policy_rule:parameter_event_outside_approved_window, policy_rule:service_call_rate_above_policy, policy_rule:unapproved_node, telemetry_model | True | False |
| stream_b_seed_1701 | spoof | 3 | True | policy_rule:node_set_hash_change, policy_rule:parameter_event_outside_approved_window, policy_rule:publisher_count_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:unapproved_node, telemetry_model | True | False |
| stream_b_seed_1701 | unauthorized_node | 3 | True | policy_rule:node_set_hash_change, policy_rule:parameter_event_outside_approved_window, policy_rule:unapproved_node, telemetry_model | True | False |
| stream_b_seed_1701 | unauthorized_subscription | 3 | True | policy_rule:node_set_hash_change, policy_rule:parameter_event_outside_approved_window, policy_rule:subscriber_count_above_policy, policy_rule:unapproved_node, telemetry_model | True | False |
| stream_b_seed_2903 | bias_drift | 9 | True | sensor_noise_model | False | False |
| stream_b_seed_2903 | clock_skew | 9 | True | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_stamp_lag_above_policy | True | False |
| stream_b_seed_2903 | delay | 9 | True | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy, telemetry_model | True | False |
| stream_b_seed_2903 | drop | 9 | True | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy | True | False |
| stream_b_seed_2903 | duplicate | 9 | True | policy_rule:late_messages_observed, policy_rule:topic_rate_out_of_band, telemetry_model | True | False |
| stream_b_seed_2903 | false_contact | 3 | False | none | False | False |
| stream_b_seed_2903 | flood | 9 | True | policy_rule:topic_rate_out_of_band, telemetry_model | True | False |
| stream_b_seed_2903 | freeze | 3 | False | none | False | False |
| stream_b_seed_2903 | jump | 9 | True | policy_rule:late_messages_observed, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy, sensor_noise_model | True | False |
| stream_b_seed_2903 | missed_contact | 3 | False | none | False | True |
| stream_b_seed_2903 | noise | 9 | True | sensor_noise_model | False | False |
| stream_b_seed_2903 | param_tamper | 3 | True | policy_rule:node_set_hash_change, policy_rule:parameter_event_outside_approved_window, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy, policy_rule:unapproved_node, telemetry_model | True | False |
| stream_b_seed_2903 | replay | 3 | True | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy | True | False |
| stream_b_seed_2903 | service_abuse | 3 | True | policy_rule:node_set_hash_change, policy_rule:parameter_event_outside_approved_window, policy_rule:service_call_rate_above_policy, policy_rule:unapproved_node, telemetry_model | True | False |
| stream_b_seed_2903 | spoof | 3 | True | policy_rule:node_set_hash_change, policy_rule:parameter_event_outside_approved_window, policy_rule:publisher_count_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:unapproved_node, telemetry_model | True | False |
| stream_b_seed_2903 | unauthorized_node | 3 | True | policy_rule:node_set_hash_change, policy_rule:parameter_event_outside_approved_window, policy_rule:unapproved_node, telemetry_model | True | False |
| stream_b_seed_2903 | unauthorized_subscription | 3 | True | policy_rule:node_set_hash_change, policy_rule:parameter_event_outside_approved_window, policy_rule:subscriber_count_above_policy, policy_rule:unapproved_node, telemetry_model | True | False |
| stream_b_seed_4307 | bias_drift | 9 | True | sensor_noise_model | False | False |
| stream_b_seed_4307 | clock_skew | 9 | True | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_stamp_lag_above_policy | True | False |
| stream_b_seed_4307 | delay | 9 | True | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy, telemetry_model | True | False |
| stream_b_seed_4307 | drop | 9 | True | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy | True | False |
| stream_b_seed_4307 | duplicate | 9 | True | policy_rule:late_messages_observed, policy_rule:topic_rate_out_of_band, telemetry_model | True | False |
| stream_b_seed_4307 | false_contact | 3 | False | none | False | False |
| stream_b_seed_4307 | flood | 9 | True | policy_rule:topic_rate_out_of_band, telemetry_model | True | False |
| stream_b_seed_4307 | freeze | 3 | False | none | False | False |
| stream_b_seed_4307 | jump | 9 | True | policy_rule:late_messages_observed, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy, sensor_noise_model | True | False |
| stream_b_seed_4307 | missed_contact | 3 | False | none | False | True |
| stream_b_seed_4307 | noise | 9 | True | sensor_noise_model | False | False |
| stream_b_seed_4307 | param_tamper | 3 | True | policy_rule:node_set_hash_change, policy_rule:parameter_event_outside_approved_window, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy, policy_rule:unapproved_node, telemetry_model | True | False |
| stream_b_seed_4307 | replay | 3 | True | policy_rule:late_messages_observed, policy_rule:topic_gap_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:topic_stamp_lag_above_policy | True | False |
| stream_b_seed_4307 | service_abuse | 3 | True | policy_rule:node_set_hash_change, policy_rule:parameter_event_outside_approved_window, policy_rule:service_call_rate_above_policy, policy_rule:unapproved_node, telemetry_model | True | False |
| stream_b_seed_4307 | spoof | 3 | True | policy_rule:node_set_hash_change, policy_rule:parameter_event_outside_approved_window, policy_rule:publisher_count_above_policy, policy_rule:topic_rate_out_of_band, policy_rule:unapproved_node, telemetry_model | True | False |
| stream_b_seed_4307 | unauthorized_node | 3 | True | policy_rule:node_set_hash_change, policy_rule:parameter_event_outside_approved_window, policy_rule:unapproved_node, telemetry_model | True | False |
| stream_b_seed_4307 | unauthorized_subscription | 3 | True | policy_rule:node_set_hash_change, policy_rule:parameter_event_outside_approved_window, policy_rule:subscriber_count_above_policy, policy_rule:unapproved_node, telemetry_model | True | False |

Freeze and false_contact each have 0/3 detected events in these runs. They are not documented expected misses: only missed_contact is known to be indistinguishable from normal with the available channels. These results therefore identify current blind spots, not evidence that the classes are inherently unobservable.

## Category agreement and join comparison

| Stream | Mode | Category agreements / detected events | Agreement rate | Incidents near joins / joins |
|---|---|---:|---:|---:|
| stream_a | continuous_state | 6 / 11 | 0.5454545454545454 | 154 / 211 |
| stream_a | reset_at_joins | 5 / 6 | 0.8333333333333334 | 22 / 211 |
| stream_b_seed_1701 | continuous_state | 58 / 70 | 0.8285714285714286 | 83 / 101 |
| stream_b_seed_1701 | reset_at_joins | 58 / 70 | 0.8285714285714286 | 0 / 101 |
| stream_b_seed_2903 | continuous_state | 58 / 70 | 0.8285714285714286 | 80 / 101 |
| stream_b_seed_2903 | reset_at_joins | 58 / 70 | 0.8285714285714286 | 0 / 101 |
| stream_b_seed_4307 | continuous_state | 58 / 70 | 0.8285714285714286 | 88 / 101 |
| stream_b_seed_4307 | reset_at_joins | 58 / 70 | 0.8285714285714286 | 0 / 101 |
| stream_c | continuous_state | 0 / 0 | n/a | 146 / 200 |
| stream_c | reset_at_joins | 0 / 0 | n/a | 15 / 200 |

Category agreement is diagnostic only and does not attribute attacks. Continuous-state and reset-at-joins results are both shown because artificial joins do not occur in a live monitor.
