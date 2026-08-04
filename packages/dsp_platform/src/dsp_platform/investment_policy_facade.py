"""Platform façade helpers for Investment Policy (EPIC-A006)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.investment_policy import (
    POLICY_SCHEMA_VERSION,
    POLICY_SERVICE_VERSION,
    RULE_KINDS,
    default_institutional_policy,
    evaluate_investment_policy,
    load_investment_policy,
)

__all__ = [
    "default_investment_policy_dict",
    "evaluate_canonical_investment_policy",
    "investment_policy_schema",
    "load_canonical_investment_policy",
]


def investment_policy_schema() -> dict[str, Any]:
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "service_version": POLICY_SERVICE_VERSION,
        "read_only": True,
        "rule_kinds": list(RULE_KINDS),
        "outcomes": ["pass", "warning", "violation", "unavailable", "waived"],
        "sources": [
            "research_object",
            "institutional_report",
            "research_archive",
            "research_diff",
            "portfolio_intelligence",
            "research_monitoring",
            "decision_workspace",
            "institutional_committee",
        ],
        "rules": [
            "existing_artifacts_only",
            "no_provider_calls",
            "no_engine_execution",
            "no_calculations",
            "no_valuation",
            "no_scoring",
            "no_optimisation",
            "no_recommendations",
            "no_data_mutation",
            "missing_is_data_unavailable",
            "deterministic_evaluation",
        ],
    }


def default_investment_policy_dict() -> dict[str, Any]:
    return default_institutional_policy().to_dict()


def load_canonical_investment_policy(
    policy: Mapping[str, Any] | None = None,
    *,
    exceptions: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    return load_investment_policy(policy, exceptions=exceptions).to_dict()


def evaluate_canonical_investment_policy(
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
) -> dict[str, Any]:
    return evaluate_investment_policy(
        subject=subject,
        policy=policy,
        exceptions=exceptions,
        research_object=research_object,
        report=report,
        snapshots=snapshots,
        diffs=diffs,
        portfolio_intelligence=portfolio_intelligence,
        monitoring_result=monitoring_result,
        workspace=workspace,
        committee_report=committee_report,
        result_id=result_id,
        created_at=created_at,
    )
