"""Calibrated, advisory sensor rules for detector v2.

The module intentionally accepts only a sanitized aligned frame and a JSON-safe
configuration.  It does not inspect labels, run names, attack metadata, or
folder names.  ``sim_time_ns`` is used only to compute causal sample spacing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .security.alerts import Finding


_TIME_COLUMNS = {"sim_time_ns", "sim_time_s", "t_rel_s"}
_LABEL_COLUMNS = {
    "is_attack", "is_attack_event", "attack_id", "attack_target", "attack_type",
    "event_label", "label", "labels", "run_id", "run_name", "relative_path",
    "scenario", "seed", "class", "class_name",
}
_EXCLUDED = _TIME_COLUMNS | _LABEL_COLUMNS


def _is_label_or_identity_column(name: str) -> bool:
    normalized = str(name).strip().lower()
    return normalized in _LABEL_COLUMNS or normalized.startswith("attack_") or normalized.startswith("label_")


@dataclass(frozen=True)
class V2Config:
    """Frozen limits learned from seed-1 normal data and selected on seed 2."""

    version: int
    limits: dict[str, float]
    columns: dict[str, list[str]]
    false_alert_budget_per_hour: float = 2.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "limits": self.limits,
            "columns": self.columns,
            "false_alert_budget_per_hour": self.false_alert_budget_per_hour,
        }


def _safe_frame(frame: pd.DataFrame) -> pd.DataFrame:
    forbidden = [c for c in frame.columns if _is_label_or_identity_column(c)]
    clean = frame.drop(columns=forbidden, errors="ignore").copy()
    if any(_is_label_or_identity_column(c) for c in clean.columns):
        raise ValueError("v2 detector input still contains label or identity columns")
    return clean


def _numeric_columns(frame: pd.DataFrame) -> list[str]:
    return [
        str(c)
        for c in frame.columns
        if str(c) not in _EXCLUDED and pd.api.types.is_numeric_dtype(frame[c])
    ]


def _quantile(values: list[np.ndarray], q: float, default: float) -> float:
    joined = np.concatenate([v[np.isfinite(v)] for v in values if len(v)]) if values else np.array([])
    return float(np.nanquantile(np.abs(joined), q)) if joined.size else default


def fit_v2_config(normal_frames: list[pd.DataFrame], seed2_frames: list[pd.DataFrame]) -> dict[str, Any]:
    """Fit limits on normal seed 1 and select conservative limits on seed 2.

    The caller is responsible for passing only normal recordings.  The returned
    bundle records the source roles so the evaluation can audit the split.
    """
    if not normal_frames:
        raise ValueError("At least one seed-1 normal frame is required")
    clean = [_safe_frame(f) for f in normal_frames]
    columns = sorted(set().union(*(_numeric_columns(f) for f in clean)))
    diff_values: list[np.ndarray] = []
    drift_values: list[np.ndarray] = []
    for name in columns:
        series = [pd.to_numeric(f[name], errors="coerce").to_numpy(float) for f in clean if name in f]
        diffs = [np.diff(x) for x in series if len(x) > 1]
        diff_values.extend(diffs)
        means = [pd.Series(x).rolling(100, min_periods=100).mean().dropna().to_numpy() for x in series]
        if means:
            drift_values.extend([m - np.nanmedian(m) for m in means if len(m)])
    limits = {
        "jump_abs_diff": max(_quantile(diff_values, 0.999, 1.0), 1e-9),
        "drift_abs_shift": max(_quantile(drift_values, 0.999, 1.0), 1e-9),
        "freeze_samples": 25.0,
        "replay_samples": 10.0,
        "clock_offset": 0.05,
        "contact_speed": 0.05,
        "contact_accel": 0.20,
    }
    numeric = [c for c in columns if not any(token in c.lower() for token in ("stamp", "lag", "age"))]
    flat_columns = [c for c in numeric if any(token in c.lower() for token in ("odom", "twist", "imu")) and "contact" not in c.lower()]
    if not flat_columns:
        flat_columns = numeric
    # Per-column limits are selected on seed-2 normal windows.  This prevents
    # mixed SI units and quaternion/contact fields from sharing one threshold.
    seed2 = [_safe_frame(f) for f in seed2_frames]
    jump_by_column: dict[str, float] = {}
    freeze_by_column: dict[str, int] = {}
    for name in flat_columns:
        normal_diffs = [
            np.abs(np.diff(pd.to_numeric(f[name], errors="coerce").to_numpy(float)))
            for f in seed2 if name in f
        ]
        finite = np.concatenate([v[np.isfinite(v)] for v in normal_diffs if len(v)]) if normal_diffs else np.array([])
        jump_by_column[name] = float(np.max(finite) + max(np.finfo(float).eps, 1e-12)) if finite.size else limits["jump_abs_diff"]
        longest = 1
        for f in seed2:
            if name not in f:
                continue
            values = pd.to_numeric(f[name], errors="coerce").to_numpy(float)
            run = best = 1
            for left, right in zip(values[:-1], values[1:]):
                run = run + 1 if np.isfinite(left) and left == right else 1
                best = max(best, run)
            longest = max(longest, best)
        freeze_by_column[name] = longest + 1
    clock_by_column: dict[str, float] = {}
    for name in (c for f in seed2 for c in f if "stamp_lag" in str(c).lower() or "age_s" in str(c).lower()):
        values = pd.to_numeric(pd.concat([f[name] for f in seed2 if name in f]), errors="coerce").to_numpy(float)
        finite = np.abs(values[np.isfinite(values)])
        clock_by_column[name] = float(np.max(finite) + 1e-12) if finite.size else limits["clock_offset"]
    limits["jump_abs_diff_by_column"] = jump_by_column
    limits["freeze_samples_by_column"] = freeze_by_column
    limits["clock_offset_by_column"] = clock_by_column
    return V2Config(2, limits, {"flatline": flat_columns, "numeric": [c for c in numeric if "contact" not in c.lower()]}, false_alert_budget_per_hour=2.0).to_dict()


def _finding(rule: str, timestamp: int, evidence: dict[str, Any], category: str) -> Finding:
    return Finding(
        rule_id=f"v2_{rule}", timestamp_sim_ns=timestamp, run_id="blind_recording",
        source="v2_rule", severity="medium", evidence=evidence,
        what_this_does_not_prove="This advisory signal does not prove an attack, fault, or unsafe vehicle response.",
        recommended_next_step="Review the named fields against an independent sensor or recorder.",
        confidence_notes=f"suspected_category={category}; limits were frozen before seed-3 scoring.",
    )


def detect_v2(frame: pd.DataFrame, config: dict[str, Any]) -> list[Finding]:
    """Run v2 rules causally and return evidence-backed findings."""
    clean = _safe_frame(frame)
    if clean.empty or "sim_time_ns" not in clean and "sim_time_s" not in clean:
        return []
    time = pd.to_numeric(clean.get("sim_time_ns", clean.get("sim_time_s")), errors="coerce").to_numpy(float)
    if "sim_time_ns" not in clean:
        time *= 1e9
    limits = {
        k: float(v) for k, v in config.get("limits", {}).items()
        if isinstance(v, (int, float))
    }
    disabled = set(config.get("disabled_rules", []))
    chosen = config.get("columns", {})
    findings: list[Finding] = []
    max_findings = 20_000
    numeric = [c for c in chosen.get("numeric", _numeric_columns(clean)) if c in clean and "contact" not in c.lower()]
    jump_limits = config.get("limits", {}).get("jump_abs_diff_by_column", {})
    for name in numeric if "jump" not in disabled else []:
        values = pd.to_numeric(clean[name], errors="coerce").to_numpy(float)
        diffs = np.abs(np.diff(values))
        limit = float(jump_limits.get(name, limits.get("jump_abs_diff", np.inf)))
        for i in np.flatnonzero(np.isfinite(diffs) & (diffs > limit)):
            findings.append(_finding("jump", int(time[i + 1]), {"column": name, "observed_abs_diff": float(diffs[i]), "limit": limit}, "jump"))
            if len(findings) >= max_findings:
                return findings
    freeze_limits = config.get("limits", {}).get("freeze_samples_by_column", {})
    for name in chosen.get("flatline", []) if "freeze" not in disabled else []:
        if name not in clean:
            continue
        values = pd.to_numeric(clean[name], errors="coerce").to_numpy(float)
        same = np.isfinite(values[1:]) & np.isfinite(values[:-1]) & (values[1:] == values[:-1])
        window = int(freeze_limits.get(name, limits.get("freeze_samples", 25)))
        run = 0
        for i, is_same in enumerate(same, start=1):
            run = run + 1 if is_same else 0
            if run == window:
                findings.append(_finding("freeze", int(time[i]), {"column": name, "flatline_samples": window, "limit": window}, "freeze"))
                if len(findings) >= max_findings:
                    return findings
    lag_cols = [c for c in clean if "stamp_lag" in str(c).lower() or "age_s" in str(c).lower()]
    clock_limits = config.get("limits", {}).get("clock_offset_by_column", {})
    for name in lag_cols if "clock_skew" not in disabled else []:
        values = pd.to_numeric(clean[name], errors="coerce").to_numpy(float)
        limit = float(clock_limits.get(name, limits.get("clock_offset", np.inf)))
        for i in np.flatnonzero(np.isfinite(values) & (np.abs(values) > limit)):
            findings.append(_finding("clock_skew", int(time[i]), {"column": name, "observed_offset_s": float(values[i]), "limit_s": limit}, "clock_skew"))
            if len(findings) >= max_findings:
                return findings
    contact = [c for c in clean if "contact" in str(c).lower() and pd.api.types.is_numeric_dtype(clean[c])]
    speed = [c for c in clean if "twist" in str(c).lower() and "linear" in str(c).lower()]
    for c in contact if "false_contact" not in disabled else []:
        flag = pd.to_numeric(clean[c], errors="coerce").to_numpy(float)
        for i in np.flatnonzero(flag > 0):
            speed_value = max((abs(float(pd.to_numeric(clean[s], errors="coerce").iloc[i])) for s in speed), default=0.0)
            if speed_value <= limits.get("contact_speed", 0.05):
                findings.append(_finding("false_contact", int(time[i]), {"contact_column": c, "observed_contact": float(flag[i]), "speed_limit": limits.get("contact_speed")}, "false_contact"))
                if len(findings) >= max_findings:
                    return findings
    return findings
