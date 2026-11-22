# Ziaxen ROS 2 Security & Sensor-Anomaly Agent
Offline advisory monitor for ROS 2 robots: sensor-noise anomaly detection plus ROS graph/telemetry security checks. Alerts only, no automatic action.

## What was inspected

The `ai-team-data` branch of
[FireMax-Bot/zaixen-isaac-sim](https://github.com/FireMax-Bot/zaixen-isaac-sim/tree/ai-team-data/AI_team_data)
contains `AI_team_data/dataset_index.csv`, dataset guides, 9 normal runs, and
297 attack runs across 17 documented attack types. All 306 index entries were
marked `completed`. The `noise` category has exactly 27 runs: levels L1/L2/L3,
NPC counts 10/20/30, and seeds 1/2/3. Each inspected run has `aligned.csv.gz`,
`telemetry.csv.gz`, `events.csv`, and `manifest.json`.

The inspected normal and L1 noise aligned files had 36 columns and about 4,560
rows each. The columns include `sim_time_ns`, `sim_time_s`, `t_rel_s`, IMU
orientation/angular velocity/linear acceleration, odometry pose/twist,
`*.age_s`, `*.stamp_lag_s`, contact data, and label/metadata columns
(`is_attack`, `attack_type`, `attack_target`, `attack_id`). Aligned sampling is
50 Hz. The noise sample had 1,500 active rows and matching `start` and `stop`
rows in `events.csv`; the implementation re-derives labels from those events
and checks them against the stored `is_attack` values.

The inspected noise manifest configures IMU `accel`, `gyro`, and
`orientation`, plus odometry `position`, `pose_orientation`, and `twist`.
The per-level settings are:

| Level | `k` for acceleration/gyro/speed | Odometry position | Yaw |
|---|---:|---:|---:|
| L1 | 0.5 x standard deviation | 0.10 m | 5 degrees |
| L2 | 1.0 x standard deviation | 0.30 m | 10 degrees |
| L3 | 3.0 x standard deviation | 0.50 m | 20 degrees |

Noise events start at 30 seconds and stop at 60 seconds of run elapsed time in
the inspected noise scenarios. Event timestamps are absolute simulation
nanoseconds; the inspection command also reports elapsed seconds from the
first aligned row for each run.

Telemetry is a 31-column 2 Hz table. It contains per-topic rates, publishers,
subscribers, gaps and stamp lag, graph/node counts, parameter/service events,
and collector counters. In the inspected normal run, `new_nodes` and the
contact stamp-lag mean were entirely missing; these are expected/understandable
for fields without a value and are not model inputs. Telemetry is retained and
profiled by dataset inspection, but is not fused into this 50 Hz
sensor-noise-specific model. It would be relevant to separate network-attack
detectors, especially for attacks 12–17.

The dataset guide says the sensors are idealized and noise-free outside the
simulated attack. It also says the ego vehicle is driven by an in-simulation
callback, not by ROS; this project is a recorded-data Python detector, not a
real-time ROS/CAN integration.

## Project map

- `config/dataset.json` — verified dataset layout, expected counts, run
  dimensions, and documented sampling rates.
- `src/ziaxen_agent/data.py` — indexed run discovery, metadata/events loading,
  event-derived labels, label validation, and sampling/schema inspection.
- `src/ziaxen_agent/features.py` — numeric IMU/odometry/contact features,
  per-second changes, and causal trailing variability.
- `src/ziaxen_agent/models.py` — Isolation Forest baseline, Random Forest
  comparator, threshold selection, metrics, and ranked feature context.
- `src/ziaxen_agent/training.py` — training and validation with whole seeds.
- `src/ziaxen_agent/evaluation.py` — untouched held-out seed evaluation,
  confusion matrix, per-run and per-level reports, and latency measurement.
- `src/ziaxen_agent/agent.py` — saved-model loading and row-wise inference.
- `src/ziaxen_agent/cli.py` — beginner-friendly commands.
- `tests/` — focused checks for event labels, temporal features, and input
  validation.
- `models/` and `reports/` — generated model bundle, reports, predictions, and
  confusion matrix (created by the commands below).

## Model and evaluation design

The baseline is an Isolation Forest trained using only event-confirmed normal
rows. The supervised comparator is a class-weighted Random Forest trained on
the normal/noise labels derived from `events.csv`. Both receive raw numeric
sensor values, first changes divided by actual simulation-time differences, and
trailing standard deviations over 25 aligned rows (0.5 seconds at 50 Hz).
Features are causal and do not look into future rows. Missing feature values
are median-imputed using training data. Time, IDs, labels, and scenario metadata
are never model inputs.

Whole runs are separated by the dataset seed: candidate models are initially
fit on seed 1, and seed 2 selects the model and its operating threshold. After
that selection, the saved final candidates are refit on both seed 1 and seed 2
(24 runs total); seed 3 (12 runs) remains held out for final evaluation. The
saved threshold is the one selected on seed 2 using the initial seed-1 models.
No row-wise random split is used. Because there are only three seeds, this is
a single fixed run-group split, not a broad external validation.
The evaluation reports precision, recall, F1, false-positive rate, confusion
matrix, average precision, missed/detected noise runs, and detection latency
from the event start to the first alert. Latency averages exclude missed runs
and are labelled accordingly.

The selected model is whichever candidate has the better seed-2 validation F1
(then lower FPR). Inference scores are not probabilities for Isolation Forest.
Each alert includes the score, threshold, timestamp, original non-sensor
metadata, and the strongest deviations from the training normal feature
reference. These ranked features are diagnostic context, not causal proof.

## Setup in VS Code (Windows PowerShell)

1. Download/clone the dataset repository branch. For example, from a parent
   folder:

   ```powershell
   git clone --branch ai-team-data --single-branch https://github.com/FireMax-Bot/zaixen-isaac-sim.git
   ```

   The data root is the resulting `zaixen-isaac-sim\AI_team_data` folder. This
   project does not copy the full dataset into its source tree.

2. Open `ziaxen_ai_agent` in VS Code, select a Python 3.10+ interpreter, and
   open the integrated PowerShell terminal.

3. Create and activate an environment, then install dependencies:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

   If PowerShell blocks activation, use
   `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and prefix
   the commands below with `.\.venv\Scripts\python.exe`.

4. Add this project’s `src` directory to `PYTHONPATH`, then inspect the dataset
   before training (replace the example path):

   ```powershell
   $env:PYTHONPATH = "$PWD\src"
   python -m ziaxen_agent.cli inspect --data-root "C:\path\to\zaixen-isaac-sim\AI_team_data"
   ```

5. Train, evaluate, and run inference:

   ```powershell
   python -m ziaxen_agent.cli train --data-root "C:\path\to\zaixen-isaac-sim\AI_team_data"
   python -m ziaxen_agent.cli evaluate --data-root "C:\path\to\zaixen-isaac-sim\AI_team_data"
   python -m ziaxen_agent.cli infer --input "C:\path\to\recording.csv.gz"
   ```

   Training writes `models/noise_detector.joblib` and
   `reports/training_validation.json`. Evaluation writes
   `reports/evaluation_report.md`, `reports/evaluation_report.json`,
   `reports/confusion_matrix.png`, `reports/predictions.csv`,
   `reports/scenario_metrics.csv`, and `reports/noise_level_metrics.csv`.
   Inference prints one JSON object per input row; use `--output alerts.jsonl`
   to save those objects. Override the operating threshold with
   `--threshold 0.5` (the value is model-score-specific).

6. Run focused tests:

   ```powershell
   $env:PYTHONPATH = "$PWD\src"
   python -m pytest
   ```

Alternatively, run `pip install -e .` once and use the `ziaxen-agent` command
without setting `PYTHONPATH`.

## Quick presentation demo

The demo loads the saved Random Forest and compares one normal seed-3 recording
with one L1 noise seed-3 recording. It uses the existing inference pipeline and
does not retrain the model:

```powershell
python scripts\demo.py --data-root "$env:TEMP\ziaxen_noise_dataset\AI_team_data"
```

By default, it reads `normal_data/normal_npc10_seed3/aligned.csv.gz` and
`abnormal_data/01_noise/noise_L1_npc10_seed3/aligned.csv.gz` under the supplied
data root. It shows each file’s predicted class, peak per-row anomaly score,
saved threshold, and number of rows flagged, then prints a comparison. The
threshold is read from the model bundle and displayed to four decimal places;
it is not separately hardcoded.

## Missing files, assumptions, and limitations

- The inspected branch index lists 306 completed runs, and the checked normal
  and noise run folders contain all four expected files. The loader reports
  missing indexed files and does not silently skip them.
- Across the 36 loaded normal/noise runs, inspection covered 164,235 aligned
  rows and 6,869 telemetry rows. The aligned table had no missing values. In
  telemetry, `contact_mon.stamp_lag_mean_s` and `new_nodes` were fully empty;
  IMU/odometry stamp-lag means had 0.75702% missing values.
- File-by-file validation in this project covers the 9 normal and 27 noise runs
  used here. Other attack folders are inventoried in the index but are not
  loaded or file-validated by this noise-focused pipeline.
- `raw_clean.csv` is not present in this branch and, per its data guide, must
  never be used for training. No clean-truth stream is assumed.
- This project uses only the 9 normal runs and 27 `noise` runs; it does not
  train on or claim coverage of bias/drift, timing, contact, network, or other
  attack classes.
- Scenario labels come from `events.csv` using start-inclusive, stop-exclusive
  `sim_time_ns` intervals. Stored `is_attack` is checked for agreement but is
  not the training label source.
- Initial missing feature values (for example, causal differences at the first
  row) are imputed from training medians. Input columns absent from a recording
  are surfaced in each prediction’s `input_warnings`; unexpected sensor fields
  are ignored by the trained feature schema and surfaced there as well.
- Contact stamp lag and some telemetry values can be entirely empty because
  those data do not have a message timestamp/value. They are preserved in
  loaded inputs but not used as features for this task.
- Simulation results on idealized data can substantially overstate real-world
  performance. No safety-critical, real vehicle, ROS, or CAN claims are made.
