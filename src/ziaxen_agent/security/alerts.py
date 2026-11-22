"""Structured, evidence-backed advisory alert records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Finding:
    rule_id: str
    timestamp_sim_ns: int
    run_id: str
    evidence: dict[str, Any]
    severity: str
    source: str = "policy"
    affected: dict[str, str] | None = None
    score: float | None = None
    threshold: float | None = None
    what_this_does_not_prove: str = "An observed anomaly does not by itself establish malicious intent."
    recommended_next_step: str = "Review the evidence and verify the approved system configuration."
    confidence_notes: str = "Based only on recorded telemetry and the supplied inventory."


@dataclass(frozen=True)
class SecurityAlert:
    alert_id: str
    timestamp_sim_ns: int
    run_id: str
    source: str
    rule_or_model: str
    affected: dict[str, str] | None
    evidence: dict[str, Any]
    what_this_does_not_prove: str
    severity: str
    score: float | None
    threshold: float | None
    confidence_notes: str
    recommended_next_step: str
    requires_human_approval: bool = True
    automatic_action_taken: bool = False
    incident_start_sim_ns: int | None = None
    incident_end_sim_ns: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def finding_to_alert(finding: Finding) -> SecurityAlert:
    identity = json.dumps(
        [
            finding.run_id,
            finding.rule_id,
            finding.timestamp_sim_ns,
            finding.affected,
            finding.evidence,
        ],
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    alert_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    return SecurityAlert(
        alert_id=alert_id,
        timestamp_sim_ns=int(finding.timestamp_sim_ns),
        run_id=finding.run_id,
        source=finding.source,
        rule_or_model=finding.rule_id,
        affected=finding.affected,
        evidence=finding.evidence,
        what_this_does_not_prove=finding.what_this_does_not_prove,
        severity=finding.severity,
        score=finding.score,
        threshold=finding.threshold,
        confidence_notes=finding.confidence_notes,
        recommended_next_step=finding.recommended_next_step,
        incident_start_sim_ns=int(finding.timestamp_sim_ns),
        incident_end_sim_ns=int(finding.timestamp_sim_ns),
    )


def merge_alerts(
    findings: list[Finding], *, merge_gap_ns: int = 2_000_000_000
) -> list[SecurityAlert]:
    """Merge adjacent findings of the same rule and affected entity into incidents."""
    ordered = sorted(
        findings,
        key=lambda item: (
            item.run_id,
            item.rule_id,
            str(item.affected),
            item.timestamp_sim_ns,
        ),
    )
    groups: list[list[Finding]] = []
    for finding in ordered:
        key = (finding.run_id, finding.rule_id, str(finding.affected))
        if groups:
            previous = groups[-1][-1]
            previous_key = (
                previous.run_id,
                previous.rule_id,
                str(previous.affected),
            )
            if (
                key == previous_key
                and finding.timestamp_sim_ns - previous.timestamp_sim_ns <= merge_gap_ns
            ):
                groups[-1].append(finding)
                continue
        groups.append([finding])

    alerts: list[SecurityAlert] = []
    for group in groups:
        first = group[0]
        evidence = dict(first.evidence)
        if len(group) > 1:
            evidence["merged_finding_count"] = len(group)
            evidence["sample_evidence"] = [item.evidence for item in group[:5]]
        base = finding_to_alert(
            Finding(
                rule_id=first.rule_id,
                timestamp_sim_ns=first.timestamp_sim_ns,
                run_id=first.run_id,
                evidence=evidence,
                severity=max(
                    (item.severity for item in group),
                    key=("info", "low", "medium", "high", "critical").index,
                ),
                source=first.source,
                affected=first.affected,
                score=first.score,
                threshold=first.threshold,
                what_this_does_not_prove=first.what_this_does_not_prove,
                recommended_next_step=first.recommended_next_step,
                confidence_notes=first.confidence_notes,
            )
        )
        alerts.append(
            SecurityAlert(
                **{
                    **base.to_dict(),
                    "incident_start_sim_ns": group[0].timestamp_sim_ns,
                    "incident_end_sim_ns": group[-1].timestamp_sim_ns,
                }
            )
        )
    return alerts
