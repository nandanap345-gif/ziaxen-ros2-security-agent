# Held-out evaluation report

- **Task:** normal_vs_sensor_noise
- **Selected model:** random_forest
- **Test split:** all normal/noise runs with seed 3 (run-grouped; no row shuffle)
- **Test runs:** 12 (3 normal, 9 noise)
- **Final model fit:** seeds [1, 2]
- **Model/threshold selection:** seed [2] (using candidate models initially fit on seed [1])
- **Labels:** derived from `events.csv` start/stop intervals

## Candidate comparison

| Model | Accuracy | Precision | Recall | F1 | False-positive rate | Threshold |
|---|---:|---:|---:|---:|---:|---:|
| isolation_forest | 0.9181 | 0.7643 | 0.9656 | 0.8532 | 0.0974 | -0.0134342 |
| random_forest | 0.9985 | 0.9961 | 0.9979 | 0.9970 | 0.0013 | 0.693775 |

## Selected-model metrics

- Confusion matrix (rows=actual [normal, noise], columns=predicted): `[[41194, 53], [29, 13471]]`
- Accuracy: 99.8502%
- Average precision: 0.9984
- False positives: 53
- False negatives: 29
- Detected noise runs: 9/9
- Missed noise runs: 0
- Median detection latency on detected runs: 0.0400 s

## Performance by noise level and NPC count

| Level | NPCs | Precision | Recall | F1 | False-positive rate | Rows |
|---:|---:|---:|---:|---:|---:|---:|
| L1 | 10 | 0.9927 | 0.9967 | 0.9947 | 0.0036 | 4575 |
| L1 | 20 | 0.9987 | 0.9973 | 0.9980 | 0.0007 | 4572 |
| L1 | 30 | 0.9987 | 0.9953 | 0.9970 | 0.0007 | 4552 |
| L2 | 10 | 0.9987 | 0.9993 | 0.9990 | 0.0007 | 4576 |
| L2 | 20 | 0.9973 | 0.9980 | 0.9977 | 0.0013 | 4556 |
| L2 | 30 | 0.9973 | 0.9980 | 0.9977 | 0.0013 | 4557 |
| L3 | 10 | 0.9855 | 0.9987 | 0.9921 | 0.0072 | 4574 |
| L3 | 20 | 0.9973 | 0.9993 | 0.9983 | 0.0013 | 4559 |
| L3 | 30 | 0.9987 | 0.9980 | 0.9983 | 0.0007 | 4552 |

## Caveats

- Results apply only to normal-versus-simulated-sensor-noise detection.
- The detector has not been validated on real vehicle data.
- The supplied simulator sensors are documented as idealized and noise-free.
- The ego vehicle is driven by an in-simulation callback, not ROS/CAN.

The output `confusion_matrix.png`, `predictions.csv`, `scenario_metrics.csv`, and `noise_level_metrics.csv` accompany this report.
