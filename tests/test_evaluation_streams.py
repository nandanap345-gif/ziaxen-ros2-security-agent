import numpy as np
import pandas as pd

from ziaxen_agent.evaluation_streams import _Run, _segment, _stitch


def _run(name, event_intervals=(), counter_start=0):
    aligned_rel = np.arange(0.0, 60.0, 0.02)
    telemetry_rel = np.arange(0.0, 60.0, 0.5)
    aligned = pd.DataFrame(
        {
            "sim_time_s": aligned_rel + 100.0,
            "sim_time_ns": ((aligned_rel + 100.0) * 1e9).astype(np.int64),
            "t_rel_s": aligned_rel,
            "imu.linear_acceleration.x": np.sin(aligned_rel),
            "is_attack": np.zeros(len(aligned_rel), dtype=np.int8),
            "attack_type": ["noise"] * len(aligned_rel),
            "run_id": [name] * len(aligned_rel),
        }
    )
    telemetry = pd.DataFrame(
        {
            "sim_time_s": telemetry_rel + 100.0,
            "sim_time_ns": ((telemetry_rel + 100.0) * 1e9).astype(np.int64),
            "node_count": np.ones(len(telemetry_rel), dtype=int),
            "collector_queue_drops": (
                np.arange(len(telemetry_rel), dtype=int) + counter_start
            ),
            "is_attack": np.zeros(len(telemetry_rel), dtype=np.int8),
            "attack_type": ["noise"] * len(telemetry_rel),
            "run_id": [name] * len(telemetry_rel),
        }
    )
    return _Run(
        relative_path=f"abnormal_data\\{name}",
        run_id=name,
        class_name="noise",
        run_type="attack" if event_intervals else "normal",
        t0_sim_s=100.0,
        duration_s=60.0,
        aligned=aligned,
        telemetry=telemetry,
        event_intervals=list(event_intervals),
    )


def test_stitch_rebases_time_strips_labels_preserves_gt_and_counters(tmp_path):
    first = _run("first")
    second = _run("second", event_intervals=[(30.0, 60.0)], counter_start=50)
    segments = [
        _segment(first, 0.0, 30.0),
        _segment(second, 30.0, 60.0, attack=True),
    ]
    manifest = _stitch("synthetic", segments, tmp_path, rng_seeds={"test": 1})
    aligned = pd.read_csv(tmp_path / "synthetic_aligned.csv.gz")
    telemetry = pd.read_csv(tmp_path / "synthetic_telemetry.csv.gz")

    assert aligned.sim_time_ns.is_monotonic_increasing
    assert telemetry.sim_time_ns.is_monotonic_increasing
    assert not any(
        column in {"is_attack", "run_id"} or column.startswith("attack_")
        for column in aligned.columns
    )
    assert not any(
        column in {"is_attack", "run_id"} or column.startswith("attack_")
        for column in telemetry.columns
    )
    assert manifest["ground_truth"] == [
        {
            "class_name": "noise",
            "source_run": "second",
            "start_sim_ns": 30_020_000_000,
            "stop_sim_ns": 60_020_000_000,
        }
    ]
    assert telemetry.collector_queue_drops.is_monotonic_increasing
    assert telemetry.collector_queue_drops.iloc[60] == telemetry.collector_queue_drops.iloc[59]
