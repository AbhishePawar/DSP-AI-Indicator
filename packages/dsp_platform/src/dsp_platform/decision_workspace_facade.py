"""Platform façade helpers for Decision Workspace (EPIC-A004)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.decision_workspace import (
    WORKSPACE_SCHEMA_VERSION,
    WORKSPACE_SERVICE_VERSION,
    build_decision_workspace,
)

__all__ = [
    "build_canonical_decision_workspace",
    "decision_workspace_schema",
]


def decision_workspace_schema() -> dict[str, Any]:
    return {
        "schema_version": WORKSPACE_SCHEMA_VERSION,
        "service_version": WORKSPACE_SERVICE_VERSION,
        "read_only": True,
        "kinds": ["company", "portfolio", "watchlist"],
        "sources": [
            "research_object",
            "institutional_report",
            "research_archive",
            "research_diff",
            "research_copilot",
            "portfolio_intelligence",
            "research_monitoring",
        ],
        "panels": [
            "research",
            "report",
            "timeline",
            "active_alerts",
            "report_history",
            "snapshot_history",
            "diff_history",
            "copilot",
            "portfolio",
            "monitoring",
            "audit",
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
        ],
    }


def build_canonical_decision_workspace(
    *,
    kind: str,
    subject: str,
    research_object: Mapping[str, Any] | None = None,
    report: Mapping[str, Any] | None = None,
    reports: Mapping[str, Any] | list[Any] | None = None,
    snapshots: Mapping[str, Any] | list[Any] | None = None,
    diffs: Mapping[str, Any] | list[Any] | None = None,
    copilot_response: Mapping[str, Any] | None = None,
    portfolio_intelligence: Mapping[str, Any] | None = None,
    monitoring_result: Mapping[str, Any] | None = None,
    workspace_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    return build_decision_workspace(
        kind=kind,
        subject=subject,
        research_object=research_object,
        report=report,
        reports=reports,
        snapshots=snapshots,
        diffs=diffs,
        copilot_response=copilot_response,
        portfolio_intelligence=portfolio_intelligence,
        monitoring_result=monitoring_result,
        workspace_id=workspace_id,
        created_at=created_at,
    )
