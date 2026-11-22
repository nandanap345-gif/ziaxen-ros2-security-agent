# External-data evaluation

## Dataset status

| Dataset | Status | Mapping | Metrics |
|---|---|---|---|
| None supplied | **Skipped** | No mapping file created because `external_data/` is absent. The adapter can write `reports/external/<dataset>_mapping.json` when a CSV is provided. | No metrics reported. |

No data was downloaded or fabricated. The adapter is available at `src/ziaxen_agent/external_adapter.py`; it converts supported units, resamples to 50 Hz, records mapped/derived/missing columns, and returns **not applicable** when over half of the frozen model's raw sensor inputs are missing. It fills absent inputs with saved training medians, but this does not repair coordinate-frame mismatch or vehicle-specific calibration.

## Security telemetry model

The telemetry model **cannot be tested** on external sensor-only datasets. They do not provide the Ziaxen ROS graph telemetry (node hashes, publisher/subscriber counts, and late/gap counters), and no proxy mapping is invented.

## Transfer limitations and required real-world test

External evaluations are transfer estimates, not proof of real-world performance. A meaningful test requires recordings from an owned ROS 2 robot or vehicle with written approval, real sensor noise, a ROS-driven controller, and the same telemetry collector.
