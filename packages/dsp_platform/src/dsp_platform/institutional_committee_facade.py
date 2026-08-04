"""Platform façade helpers for Institutional Committee (EPIC-A005)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.institutional_committee import (
    AGENT_IDS,
    COMMITTEE_SCHEMA_VERSION,
    COMMITTEE_SERVICE_VERSION,
    get_agent_registry,
    run_institutional_committee,
)

__all__ = [
    "institutional_committee_schema",
    "list_committee_agents",
    "run_canonical_institutional_committee",
]


def institutional_committee_schema() -> dict[str, Any]:
    return {
        "schema_version": COMMITTEE_SCHEMA_VERSION,
        "service_version": COMMITTEE_SERVICE_VERSION,
        "read_only": True,
        "agents": list(AGENT_IDS),
        "stances": ["supportive", "cautionary", "unavailable"],
        "confidence_levels": ["high", "medium", "low", "unavailable"],
        "sources": [
            "research_object",
            "institutional_report",
            "research_archive",
            "research_diff",
            "research_copilot",
            "portfolio_intelligence",
            "research_monitoring",
            "decision_workspace",
        ],
        "rules": [
            "existing_artifacts_only",
            "no_provider_calls",
            "no_engine_execution",
            "no_calculations",
            "no_valuation",
            "no_scoring",
            "no_optimisation",
            "no_fabricated_conclusions",
            "no_data_mutation",
            "missing_is_data_unavailable",
            "deterministic_orchestration",
        ],
    }


def list_committee_agents() -> list[dict[str, str]]:
    return get_agent_registry().list_agents()


def run_canonical_institutional_committee(
    *,
    subject: str,
    research_object: Mapping[str, Any] | None = None,
    report: Mapping[str, Any] | None = None,
    snapshots: Mapping[str, Any] | list[Any] | None = None,
    diffs: Mapping[str, Any] | list[Any] | None = None,
    copilot_response: Mapping[str, Any] | None = None,
    portfolio_intelligence: Mapping[str, Any] | None = None,
    monitoring_result: Mapping[str, Any] | None = None,
    workspace: Mapping[str, Any] | None = None,
    report_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    return run_institutional_committee(
        subject=subject,
        research_object=research_object,
        report=report,
        snapshots=snapshots,
        diffs=diffs,
        copilot_response=copilot_response,
        portfolio_intelligence=portfolio_intelligence,
        monitoring_result=monitoring_result,
        workspace=workspace,
        report_id=report_id,
        created_at=created_at,
    )
