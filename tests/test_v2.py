import numpy as np
import pandas as pd

from ziaxen_agent.v2 import detect_v2, fit_v2_config


def _frame(values, contact=None):
    n = len(values)
    return pd.DataFrame({
        "sim_time_ns": np.arange(n, dtype=np.int64) * 20_000_000,
        "odom.twist.linear.x": values,
        "contact.is_contact": [0] * n if contact is None else contact,
        "is_attack": [0] * n,
        "attack_type": ["none"] * n,
        "run_id": ["secret"] * n,
    })


def test_v2_rules_fire_on_synthetic_positive_and_ignore_normal():
    normal = _frame(np.sin(np.arange(160) / 10.0))
    config = fit_v2_config([normal], [normal])
    config["limits"]["jump_abs_diff"] = 0.5
    config["limits"]["freeze_samples"] = 8
    positive = _frame([0.0] * 40 + [10.0] + [10.0] * 40 + list(np.sin(np.arange(79) / 10.0)))
    rules = {finding.rule_id for finding in detect_v2(positive, config)}
    assert "v2_jump" in rules
    assert "v2_freeze" in rules
    assert not detect_v2(normal, config)


def test_v2_strips_labels_and_identity_before_rules():
    frame = _frame(np.zeros(40))
    config = {"limits": {"freeze_samples": 8}, "columns": {"flatline": ["odom.twist.linear.x"], "numeric": []}}
    findings = detect_v2(frame, config)
    assert findings
    assert all("attack" not in str(item.evidence).lower() for item in findings)
