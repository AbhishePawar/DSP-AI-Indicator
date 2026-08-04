"""Compliance checker / orchestrator (EPIC-A006)."""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from dsp_platform.investment_policy.citations import build_policy_citations
from dsp_platform.investment_policy.evaluator import PolicyArtifacts, evaluate_rule
from dsp_platform.investment_policy.loader import load_investment_policy
from dsp_platform.investment_policy.models import (
    POLICY_SCHEMA_VERSION,
    POLICY_SERVICE_VERSION,
    ComplianceResult,
    freeze_mapping,
    utc_now,
)
from dsp_platform.investment_policy.registry import ExceptionRegistry, RuleRegistry
from dsp_platform.investment_policy.serde import compliance_result_to_dict
from dsp_platform.investment_policy.validation import validate_compliance_result

__all__ = [
    "POLICY_SERVICE_VERSION",
    "ComplianceChecker",
    "evaluate_investment_policy",
]


def _as_mapping_list(
    value: Mapping[str, Any] | list[Any] | None,
) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        return [v for v in value.values() if isinstance(v, Mapping)]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, Mapping)]
    return []


class ComplianceChecker:
    """Evaluate artifacts against a loaded investment policy."""

    def evaluate(
        self,
        *,
        subject: str,
        policy: Mapping[str, Any] | None = None,
        exceptions: list[Mapping[str, Any]] | None = None,
        research_object: Mapping[str, Any] | None = None,
        report: Mapping[str, Any] | None = None,
        snapshots: Mapping[str, Any] | list[Any] | None = None,
        diffs: Mapping[str, Any] | list[Any] | None = None,
        portfolio_intelligence: Mapping[str, Any] | None = None,
        monitoring_result: Mapping[str, Any] | None = None,
        workspace: Mapping[str, Any] | None = None,
        committee_report: Mapping[str, Any] | None = None,
        result_id: str | None = None,
        created_at: str | None = None,
    ) -> ComplianceResult:
        subject_norm = str(subject or "").strip()
        if not subject_norm:
            raise ValueError("subject is required")
        subject_norm = subject_norm.upper()

        loaded = load_investment_policy(policy, exceptions=exceptions)
        rules = RuleRegistry(loaded.rules)
        exc_reg = ExceptionRegistry(loaded.exceptions)

        artifacts = PolicyArtifacts(
            subject=subject_norm,
            research_object=research_object,
            report=report,
            snapshots=_as_mapping_list(snapshots),
            diffs=_as_mapping_list(diffs),
            portfolio_intelligence=portfolio_intelligence,
            monitoring_result=monitoring_result,
            workspace=workspace,
            committee_report=committee_report,
        )

        rule_results = tuple(
            evaluate_rule(rule, artifacts, exc_reg) for rule in rules.enabled_rules()
        )

        violations = tuple(
            freeze_mapping(r.to_dict()) or freeze_mapping({})
            for r in rule_results
            if r.outcome == "violation"
        )
        warnings = tuple(
            freeze_mapping(r.to_dict()) or freeze_mapping({})
            for r in rule_results
            if r.outcome == "warning"
        )

        counts = {
            "pass": sum(1 for r in rule_results if r.outcome == "pass"),
            "warning": sum(1 for r in rule_results if r.outcome == "warning"),
            "violation": sum(1 for r in rule_results if r.outcome == "violation"),
            "unavailable": sum(1 for r in rule_results if r.outcome == "unavailable"),
            "waived": sum(1 for r in rule_results if r.outcome == "waived"),
        }
        if counts["violation"] > 0:
            status = "non_compliant"
        elif counts["warning"] > 0 or counts["unavailable"] > 0:
            status = "compliant_with_warnings"
        else:
            status = "compliant"

        summary = freeze_mapping(
            {
                "status": status,
                "counts": counts,
                "policy_id": loaded.policy_id,
                "policy_version": loaded.version,
                "rule_count": len(rule_results),
                "violation_count": counts["violation"],
                "warning_count": counts["warning"],
            }
        ) or freeze_mapping({})

        audit_trail = tuple(
            freeze_mapping(
                {
                    "event": "rule_evaluated",
                    "rule_id": r.rule_id,
                    "outcome": r.outcome,
                    "severity": r.severity,
                    "message": r.message,
                }
            )
            or freeze_mapping({})
            for r in rule_results
        )

        citations = build_policy_citations(
            [c for r in rule_results for c in r.citations]
        )

        created = created_at or utc_now().isoformat()
        rid = result_id or str(uuid.uuid4())

        provenance = {
            "source": "investment_policy",
            "service_version": POLICY_SERVICE_VERSION,
            "providers_called": False,
            "engines_called": False,
            "calculations_performed": False,
            "scoring_performed": False,
            "policy_id": loaded.policy_id,
            "sources_present": {
                "research_object": research_object is not None,
                "institutional_report": report is not None,
                "research_archive": bool(artifacts.snapshots),
                "research_diff": bool(artifacts.diffs),
                "portfolio_intelligence": portfolio_intelligence is not None,
                "research_monitoring": monitoring_result is not None,
                "decision_workspace": workspace is not None,
                "institutional_committee": committee_report is not None,
            },
        }
        audit = {
            "result_id": rid,
            "created_at": created,
            "subject": subject_norm,
            "status": status,
            "rule_count": len(rule_results),
            "citation_count": len(citations),
            "exception_count": len(loaded.exceptions),
        }
        limitations = (
            "Validates compliance against configured policy only.",
            "No valuation, scoring, optimisation, or recommendations.",
            "No providers or engines executed.",
            "Unavailable source for a rule yields outcome unavailable.",
        )

        result = ComplianceResult(
            result_id=rid,
            schema_version=POLICY_SCHEMA_VERSION,
            service_version=POLICY_SERVICE_VERSION,
            created_at=created,
            subject=subject_norm,
            policy=freeze_mapping(loaded.to_dict()) or freeze_mapping({}),
            rule_results=rule_results,
            summary=summary,
            violations=violations,
            warnings=warnings,
            audit_trail=audit_trail,
            citations=citations,
            provenance=freeze_mapping(provenance) or freeze_mapping({}),
            audit=freeze_mapping(audit) or freeze_mapping({}),
            limitations=limitations,
        )
        validate_compliance_result(result)
        return result


def evaluate_investment_policy(**kwargs: Any) -> dict[str, Any]:
    result = ComplianceChecker().evaluate(**kwargs)
    return compliance_result_to_dict(result)
