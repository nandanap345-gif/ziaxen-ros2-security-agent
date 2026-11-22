# Leave-one-class-out telemetry experiment

- **Training seeds:** [1, 2]; threshold chosen on seed 2.
- **Test seed:** 3.
- **Model storage:** experiment-only bundles; shipped models were not modified.
- **Scope:** All outcomes are under simulated conditions with idealized sensors and an in-sim driver, not a ROS-driven vehicle.

| Omitted class | Model detected / events | Model recall | 95% Wilson CI | Rules detected / events | Rules recall | 95% Wilson CI | Threshold |
|---|---:|---:|---|---:|---:|---|---:|
| flood | 0 / 9 | 0.000 | [0.000, 0.299] | 9 / 9 | 1.000 | [0.701, 1.000] | 0.486421 |
| spoof | 3 / 3 | 1.000 | [0.439, 1.000] | 3 / 3 | 1.000 | [0.439, 1.000] | 0.389043 |
| unauthorized_node | 3 / 3 | 1.000 | [0.439, 1.000] | 3 / 3 | 1.000 | [0.439, 1.000] | 0.477992 |
| unauthorized_subscription | 3 / 3 | 1.000 | [0.439, 1.000] | 3 / 3 | 1.000 | [0.439, 1.000] | 0.377877 |

> Each held-out class has only three seed-3 events; recall intervals are imprecise and do not establish reliability.

> WARNING: DRAFT INVENTORY OVERRIDE ENABLED — rules results are offline evaluation only.
