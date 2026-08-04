"""Deterministic rule evaluator (EPIC-A006).

Structural presence / equality checks only — no calculations, valuation,
scoring, or recommendations.
"""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.investment_policy.citations import citation
from dsp_platform.investment_policy.models import (
    UNAVAILABLE_MESSAGE,
    PolicyRule,
    RuleResult,
    freeze_mapping,
)
from dsp_platform.investment_policy.registry import ExceptionRegistry

__all__ = ["PolicyArtifacts", "evaluate_rule"]


class PolicyArtifacts:
    """Caller-supplied artifacts for compliance evaluation."""

    def __init__(
        self,
        *,
        subject: str,
        research_object: Mapping[str, Any] | None = None,
        report: Mapping[str, Any] | None = None,
        snapshots: list[Mapping[str, Any]] | None = None,
        diffs: list[Mapping[str, Any]] | None = None,
        portfolio_intelligence: Mapping[str, Any] | None = None,
        monitoring_result: Mapping[str, Any] | None = None,
        workspace: Mapping[str, Any] | None = None,
        committee_report: Mapping[str, Any] | None = None,
    ) -> None:
        self.subject = subject
        self.research_object = research_object
        self.report = report
        self.snapshots = snapshots or []
        self.diffs = diffs or []
        self.portfolio_intelligence = portfolio_intelligence
        self.monitoring_result = monitoring_result
        self.workspace = workspace
        self.committee_report = committee_report

    def source_present(self, source: str) -> bool:
        mapping = {
            "research_object": self.research_object is not None,
            "institutional_report": self.report is not None,
            "research_archive": bool(self.snapshots),
            "research_diff": bool(self.diffs),
            "portfolio_intelligence": self.portfolio_intelligence is not None,
            "research_monitoring": self.monitoring_result is not None,
            "decision_workspace": self.workspace is not None,
            "institutional_committee": self.committee_report is not None,
        }
        return bool(mapping.get(source, False))


def _section_available(research_object: Mapping[str, Any] | None, section: str) -> bool:
    if research_object is None:
        return False
    row = research_object.get(section)
    if isinstance(row, Mapping):
        if "available" in row:
            return bool(row.get("available"))
        return str(row.get("status") or "") == "ok"
    return research_object.get(section) is not None


def _fail_outcome(rule: PolicyRule) -> str:
    return "violation" if rule.severity == "violation" else "warning"


def evaluate_rule(
    rule: PolicyRule,
    artifacts: PolicyArtifacts,
    exceptions: ExceptionRegistry,
) -> RuleResult:
    waived = exceptions.is_waived(rule.rule_id)
    if waived is not None:
        return RuleResult(
            rule_id=rule.rule_id,
            kind=rule.kind,
            outcome="waived",
            severity=rule.severity,
            message=f"Waived: {waived.reason}",
            citations=(
                citation(
                    source_kind="investment_policy",
                    section="exception",
                    path=f"policy.exceptions.{waived.exception_id}",
                    available=True,
                    rule_id=rule.rule_id,
                    ref_id=waived.exception_id,
                    label="policy/exception",
                ),
            ),
            evidence=freeze_mapping(
                {
                    "exception_id": waived.exception_id,
                    "reason": waived.reason,
                }
            )
            or freeze_mapping({}),
        )

    kind = rule.kind
    params = rule.params if isinstance(rule.params, Mapping) else {}

    if kind == "require_source_present":
        source = str(params.get("source") or "")
        present = artifacts.source_present(source)
        cites = (
            citation(
                source_kind=source or "unknown",
                section="presence",
                path=source or "unknown",
                available=present,
                rule_id=rule.rule_id,
                symbol=artifacts.subject,
            ),
        )
        if present:
            return RuleResult(
                rule_id=rule.rule_id,
                kind=kind,
                outcome="pass",
                severity=rule.severity,
                message=f"Source {source} present.",
                citations=cites,
                evidence=freeze_mapping({"source": source, "present": True})
                or freeze_mapping({}),
            )
        return RuleResult(
            rule_id=rule.rule_id,
            kind=kind,
            outcome=_fail_outcome(rule),
            severity=rule.severity,
            message=UNAVAILABLE_MESSAGE if not source else f"Source {source} missing.",
            citations=cites,
            evidence=freeze_mapping({"source": source, "present": False})
            or freeze_mapping({}),
        )

    if kind == "require_section_available":
        section = str(params.get("section") or "")
        if artifacts.research_object is None:
            cites = (
                citation(
                    source_kind="research_object",
                    section=section or "research_object",
                    path=f"research_object.{section}" if section else "research_object",
                    available=False,
                    rule_id=rule.rule_id,
                    symbol=artifacts.subject,
                ),
            )
            return RuleResult(
                rule_id=rule.rule_id,
                kind=kind,
                outcome="unavailable",
                severity=rule.severity,
                message=UNAVAILABLE_MESSAGE,
                citations=cites,
                evidence=freeze_mapping({"section": section, "available": False})
                or freeze_mapping({}),
            )
        available = _section_available(artifacts.research_object, section)
        cites = (
            citation(
                source_kind="research_object",
                section=section,
                path=f"research_object.{section}",
                available=available,
                rule_id=rule.rule_id,
                symbol=artifacts.subject,
            ),
        )
        if available:
            return RuleResult(
                rule_id=rule.rule_id,
                kind=kind,
                outcome="pass",
                severity=rule.severity,
                message=f"Section {section} available.",
                citations=cites,
                evidence=freeze_mapping({"section": section, "available": True})
                or freeze_mapping({}),
            )
        return RuleResult(
            rule_id=rule.rule_id,
            kind=kind,
            outcome=_fail_outcome(rule),
            severity=rule.severity,
            message=f"Section {section}: {UNAVAILABLE_MESSAGE}",
            citations=cites,
            evidence=freeze_mapping({"section": section, "available": False})
            or freeze_mapping({}),
        )

    if kind == "require_report_present":
        present = artifacts.report is not None
        cites = (
            citation(
                source_kind="institutional_report",
                section="report",
                path="institutional_report",
                available=present,
                rule_id=rule.rule_id,
                ref_id=str((artifacts.report or {}).get("report_id") or "") or None,
            ),
        )
        if present:
            return RuleResult(
                rule_id=rule.rule_id,
                kind=kind,
                outcome="pass",
                severity=rule.severity,
                message="Institutional report present.",
                citations=cites,
                evidence=freeze_mapping({"present": True}) or freeze_mapping({}),
            )
        return RuleResult(
            rule_id=rule.rule_id,
            kind=kind,
            outcome=_fail_outcome(rule),
            severity=rule.severity,
            message=UNAVAILABLE_MESSAGE,
            citations=cites,
            evidence=freeze_mapping({"present": False}) or freeze_mapping({}),
        )

    if kind in {"require_committee_stance", "forbid_committee_stance"}:
        if artifacts.committee_report is None:
            cites = (
                citation(
                    source_kind="institutional_committee",
                    section="consensus",
                    path="institutional_committee.consensus",
                    available=False,
                    rule_id=rule.rule_id,
                ),
            )
            return RuleResult(
                rule_id=rule.rule_id,
                kind=kind,
                outcome="unavailable",
                severity=rule.severity,
                message=UNAVAILABLE_MESSAGE,
                citations=cites,
                evidence=freeze_mapping({"committee_present": False})
                or freeze_mapping({}),
            )
        consensus = artifacts.committee_report.get("consensus")
        stance = (
            str(consensus.get("stance") or "")
            if isinstance(consensus, Mapping)
            else ""
        )
        allowed = params.get("stances") or []
        if not isinstance(allowed, (list, tuple)):
            allowed = [allowed]
        allowed_set = {str(s) for s in allowed}
        cites = (
            citation(
                source_kind="institutional_committee",
                section="consensus",
                path="institutional_committee.consensus.stance",
                available=True,
                rule_id=rule.rule_id,
                ref_id=str(artifacts.committee_report.get("report_id") or "") or None,
            ),
        )
        if kind == "require_committee_stance":
            ok = stance in allowed_set
        else:
            ok = stance not in allowed_set
        if ok:
            return RuleResult(
                rule_id=rule.rule_id,
                kind=kind,
                outcome="pass",
                severity=rule.severity,
                message=f"Committee stance {stance!r} complies.",
                citations=cites,
                evidence=freeze_mapping({"stance": stance, "params": list(allowed_set)})
                or freeze_mapping({}),
            )
        return RuleResult(
            rule_id=rule.rule_id,
            kind=kind,
            outcome=_fail_outcome(rule),
            severity=rule.severity,
            message=f"Committee stance {stance!r} does not comply.",
            citations=cites,
            evidence=freeze_mapping({"stance": stance, "params": list(allowed_set)})
            or freeze_mapping({}),
        )

    if kind == "forbid_missing_research":
        if artifacts.portfolio_intelligence is None:
            cites = (
                citation(
                    source_kind="portfolio_intelligence",
                    section="missing_research",
                    path="portfolio_intelligence.missing_research",
                    available=False,
                    rule_id=rule.rule_id,
                ),
            )
            return RuleResult(
                rule_id=rule.rule_id,
                kind=kind,
                outcome="unavailable",
                severity=rule.severity,
                message=UNAVAILABLE_MESSAGE,
                citations=cites,
                evidence=freeze_mapping({"portfolio_present": False})
                or freeze_mapping({}),
            )
        missing = artifacts.portfolio_intelligence.get("missing_research") or []
        symbols = [
            str(m.get("symbol"))
            for m in missing
            if isinstance(m, Mapping) and m.get("symbol")
        ]
        cites = (
            citation(
                source_kind="portfolio_intelligence",
                section="missing_research",
                path="portfolio_intelligence.missing_research",
                available=True,
                rule_id=rule.rule_id,
                ref_id=str(artifacts.portfolio_intelligence.get("result_id") or "")
                or None,
            ),
        )
        if not symbols:
            return RuleResult(
                rule_id=rule.rule_id,
                kind=kind,
                outcome="pass",
                severity=rule.severity,
                message="No missing research links.",
                citations=cites,
                evidence=freeze_mapping({"missing_symbols": []}) or freeze_mapping({}),
            )
        return RuleResult(
            rule_id=rule.rule_id,
            kind=kind,
            outcome=_fail_outcome(rule),
            severity=rule.severity,
            message=f"Missing research for: {', '.join(sorted(symbols))}.",
            citations=cites,
            evidence=freeze_mapping({"missing_symbols": sorted(symbols)})
            or freeze_mapping({}),
        )

    if kind == "forbid_alert_severity":
        if artifacts.monitoring_result is None:
            cites = (
                citation(
                    source_kind="research_monitoring",
                    section="alerts",
                    path="research_monitoring.alerts",
                    available=False,
                    rule_id=rule.rule_id,
                ),
            )
            return RuleResult(
                rule_id=rule.rule_id,
                kind=kind,
                outcome="unavailable",
                severity=rule.severity,
                message=UNAVAILABLE_MESSAGE,
                citations=cites,
                evidence=freeze_mapping({"monitoring_present": False})
                or freeze_mapping({}),
            )
        severities = params.get("severities") or []
        if not isinstance(severities, (list, tuple)):
            severities = [severities]
        banned = {str(s) for s in severities}
        alerts = artifacts.monitoring_result.get("alerts") or []
        hits = [
            a
            for a in alerts
            if isinstance(a, Mapping) and str(a.get("severity") or "") in banned
        ]
        cites = (
            citation(
                source_kind="research_monitoring",
                section="alerts",
                path="research_monitoring.alerts",
                available=True,
                rule_id=rule.rule_id,
                ref_id=str(artifacts.monitoring_result.get("result_id") or "") or None,
            ),
        )
        if not hits:
            return RuleResult(
                rule_id=rule.rule_id,
                kind=kind,
                outcome="pass",
                severity=rule.severity,
                message="No forbidden alert severities.",
                citations=cites,
                evidence=freeze_mapping({"hit_count": 0}) or freeze_mapping({}),
            )
        return RuleResult(
            rule_id=rule.rule_id,
            kind=kind,
            outcome=_fail_outcome(rule),
            severity=rule.severity,
            message=f"Forbidden alert severity present ({len(hits)} alert(s)).",
            citations=cites,
            evidence=freeze_mapping(
                {
                    "hit_count": len(hits),
                    "severities": sorted(
                        {str(a.get("severity")) for a in hits}
                    ),
                }
            )
            or freeze_mapping({}),
        )

    if kind == "require_diff_identical":
        if not artifacts.diffs:
            cites = (
                citation(
                    source_kind="research_diff",
                    section="change_summary",
                    path="research_diff.change_summary",
                    available=False,
                    rule_id=rule.rule_id,
                ),
            )
            return RuleResult(
                rule_id=rule.rule_id,
                kind=kind,
                outcome="unavailable",
                severity=rule.severity,
                message=UNAVAILABLE_MESSAGE,
                citations=cites,
                evidence=freeze_mapping({"diff_count": 0}) or freeze_mapping({}),
            )
        non_identical = []
        for d in artifacts.diffs:
            summary = (
                d.get("change_summary")
                if isinstance(d.get("change_summary"), Mapping)
                else {}
            )
            if summary.get("identical_content") is False:
                non_identical.append(str(d.get("diff_id") or "diff"))
        cites = tuple(
            citation(
                source_kind="research_diff",
                section="change_summary",
                path="research_diff.change_summary",
                available=True,
                rule_id=rule.rule_id,
                ref_id=str(d.get("diff_id") or "") or None,
            )
            for d in artifacts.diffs
            if isinstance(d, Mapping)
        ) or (
            citation(
                source_kind="research_diff",
                section="change_summary",
                path="research_diff.change_summary",
                available=True,
                rule_id=rule.rule_id,
            ),
        )
        if not non_identical:
            return RuleResult(
                rule_id=rule.rule_id,
                kind=kind,
                outcome="pass",
                severity=rule.severity,
                message="All supplied diffs report identical_content.",
                citations=cites,
                evidence=freeze_mapping({"non_identical": []}) or freeze_mapping({}),
            )
        return RuleResult(
            rule_id=rule.rule_id,
            kind=kind,
            outcome=_fail_outcome(rule),
            severity=rule.severity,
            message=f"Non-identical diffs: {', '.join(sorted(non_identical))}.",
            citations=cites,
            evidence=freeze_mapping({"non_identical": sorted(non_identical)})
            or freeze_mapping({}),
        )

    return RuleResult(
        rule_id=rule.rule_id,
        kind=kind,
        outcome="unavailable",
        severity=rule.severity,
        message=UNAVAILABLE_MESSAGE,
        citations=(
            citation(
                source_kind="investment_policy",
                section="rule",
                path=f"policy.rules.{rule.rule_id}",
                available=False,
                rule_id=rule.rule_id,
            ),
        ),
        evidence=freeze_mapping({"unsupported_kind": kind}) or freeze_mapping({}),
    )
