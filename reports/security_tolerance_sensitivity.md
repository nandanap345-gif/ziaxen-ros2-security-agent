# Security event stop-tolerance sensitivity

- **Seeds:** [1, 2] only; 204 runs.
- **Pre-start tolerance:** 1.5 s.
- **scikit-learn:** 1.9.1.
- **Security model SHA-256:** `8bcc4c491cca4d1f31f3ec657d2ef6733a371147db751643ad9f3bca44fff88e`.
- **Thresholds changed:** False.
- **Interpretation:** The shipped model was trained on seeds 1-2, so these results are in-sample diagnostics for label-window sensitivity, not independent performance estimates. Seed 3 was not accessed.

| Post-stop tolerance (s) | Method | Detected/events | Event recall | False incidents | Normal hours | False alerts/hour |
|---:|---|---:|---:|---:|---:|---:|
| 0.0 | policy_rules | 111/198 | 0.5606 | 149 | 2.832 | 52.619 |
| 0.0 | selected_telemetry_model | 65/198 | 0.3283 | 12 | 2.832 | 4.238 |
| 0.0 | rules_plus_selected_model | 111/198 | 0.5606 | 149 | 2.832 | 52.619 |
| 0.5 | policy_rules | 111/198 | 0.5606 | 135 | 2.804 | 48.143 |
| 0.5 | selected_telemetry_model | 71/198 | 0.3586 | 1 | 2.804 | 0.357 |
| 0.5 | rules_plus_selected_model | 111/198 | 0.5606 | 135 | 2.804 | 48.143 |
| 1.0 | policy_rules | 111/198 | 0.5606 | 71 | 2.777 | 25.570 |
| 1.0 | selected_telemetry_model | 71/198 | 0.3586 | 1 | 2.777 | 0.360 |
| 1.0 | rules_plus_selected_model | 111/198 | 0.5606 | 71 | 2.777 | 25.570 |
| 1.5 | policy_rules | 111/198 | 0.5606 | 71 | 2.749 | 25.826 |
| 1.5 | selected_telemetry_model | 71/198 | 0.3586 | 1 | 2.749 | 0.364 |
| 1.5 | rules_plus_selected_model | 111/198 | 0.5606 | 71 | 2.749 | 25.826 |
| 2.0 | policy_rules | 111/198 | 0.5606 | 71 | 2.722 | 26.087 |
| 2.0 | selected_telemetry_model | 71/198 | 0.3586 | 1 | 2.722 | 0.367 |
| 2.0 | rules_plus_selected_model | 111/198 | 0.5606 | 71 | 2.722 | 26.087 |
