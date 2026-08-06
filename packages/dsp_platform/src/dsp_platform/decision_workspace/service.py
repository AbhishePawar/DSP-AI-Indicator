"""Institutional Decision Workspace service (EPIC-A004)."""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from dsp_platform.decision_workspace.citations import build_workspace_citations
from dsp_platform.decision_workspace.models import (
    PANEL_NAMES,
    WORKSPACE_KINDS,
    WORKSPACE_SCHEMA_VERSION,
    WORKSPACE_SERVICE_VERSION,
    WorkspaceResult,
    freeze_mapping,
    utc_now,
)
from dsp_platform.decision_workspace.panels import (
    build_active_alerts_panel,
    build_audit_panel,
    build_copilot_panel,
    build_diff_history_panel,
    build_monitoring_panel,
    build_portfolio_panel,
    build_report_history_panel,
    build_report_panel,
    build_research_panel,
    build_snapshot_history_panel,
    build_timeline_panel,
)
from dsp_platform.decision_workspace.serde import workspace_result_to_dict
from dsp_platform.decision_workspace.timeline import build_research_timeline
from dsp_platform.decision_workspace.validation import (
    DecisionWorkspaceValidationError,
    validate_workspace_result,
)

__all__ = [
    "WORKSPACE_SERVICE_VERSION",
    "DecisionWorkspaceService",
    "build_decision_workspace",
]


def _as_mapping_list(
    value: Mapping[str, Any] | list[Any] | None,
) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        # Allow {id: payload} maps
        out: list[Mapping[str, Any]] = []
        for item in value.values():
            if isinstance(item, Mapping):
                out.append(item)
        return out
    if isinstance(value, list):
        return [item for item in value if isinstance(item, Mapping)]
    return []


class DecisionWorkspaceService:
    """Aggregate supplied research artifacts into a read-only workspace."""

    def build(
        self,
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
    ) -> WorkspaceResult:
        kind_norm = str(kind or "").strip().lower()
        if kind_norm not in WORKSPACE_KINDS:
            raise DecisionWorkspaceValidationError(
                f"kind must be one of {WORKSPACE_KINDS}"
            )
        subject_norm = str(subject or "").strip()
        if not subject_norm:
            raise DecisionWorkspaceValidationError("subject is required")
        if kind_norm == "company":
            subject_norm = subject_norm.upper()

        snap_list = _as_mapping_list(snapshots)
        diff_list = _as_mapping_list(diffs)
        report_list = _as_mapping_list(reports)
        if report is not None and not any(
            r.get("report_id") == report.get("report_id") for r in report_list
        ):
            report_list = [dict(report), *report_list]

        created = created_at or utc_now().isoformat()
        wid = workspace_id or str(uuid.uuid4())

        timeline = build_research_timeline(
            research_object=research_object,
            report=report,
            snapshots=snap_list,
            diffs=diff_list,
            monitoring_result=monitoring_result,
            created_at=created,
        )

        panels = [
            build_research_panel(research_object, symbol=subject_norm),
            build_report_panel(report),
            build_timeline_panel(timeline),
            build_active_alerts_panel(monitoring_result),
            build_report_history_panel(report_list),
            build_snapshot_history_panel(snap_list),
            build_diff_history_panel(diff_list),
            build_copilot_panel(copilot_response),
            build_portfolio_panel(portfolio_intelligence),
            build_monitoring_panel(monitoring_result),
        ]
        available = [p.name for p in panels if p.available]
        source_flags = {
            "research_object": research_object is not None,
            "institutional_report": report is not None or bool(report_list),
            "research_archive": bool(snap_list),
            "research_diff": bool(diff_list),
            "research_copilot": copilot_response is not None,
            "portfolio_intelligence": portfolio_intelligence is not None,
            "research_monitoring": monitoring_result is not None,
        }
        audit_panel = build_audit_panel(
            workspace_id=wid,
            kind=kind_norm,
            subject=subject_norm,
            created_at=created,
            panel_names=list(PANEL_NAMES),
            available_panels=available + ["audit"],
            source_flags=source_flags,
        )
        panels.append(audit_panel)

        # Kind-specific availability notes (no calculations — flags only)
        if kind_norm == "company" and research_object is None and report is None:
            # still valid empty aggregation
            pass
        if kind_norm == "portfolio" and portfolio_intelligence is None:
            pass
        if kind_norm == "watchlist" and portfolio_intelligence is None:
            pass

        panel_citations = [c for p in panels for c in p.citations]
        citations = build_workspace_citations(panel_citations)

        provenance = {
            "source": "decision_workspace",
            "service_version": WORKSPACE_SERVICE_VERSION,
            "providers_called": False,
            "engines_called": False,
            "calculations_performed": False,
            "sources_present": source_flags,
            "kind": kind_norm,
            "subject": subject_norm,
        }
        audit = {
            "workspace_id": wid,
            "created_at": created,
            "kind": kind_norm,
            "subject": subject_norm,
            "panel_count": len(panels),
            "available_panel_count": sum(1 for p in panels if p.available),
            "timeline_event_count": len(timeline),
            "citation_count": len(citations),
        }
        limitations = (
            "Aggregates supplied artifacts only — no new research.",
            "No valuation, scoring, optimisation, or recommendations.",
            "No providers or engines executed.",
        )
        result = WorkspaceResult(
            workspace_id=wid,
            schema_version=WORKSPACE_SCHEMA_VERSION,
            service_version=WORKSPACE_SERVICE_VERSION,
            created_at=created,
            kind=kind_norm,
            subject=subject_norm,
            panels=tuple(panels),
            timeline=timeline,
            citations=citations,
            provenance=freeze_mapping(provenance) or freeze_mapping({}),
            audit=freeze_mapping(audit) or freeze_mapping({}),
            limitations=limitations,
        )
        validate_workspace_result(result)
        return result


def build_decision_workspace(**kwargs: Any) -> dict[str, Any]:
    result = DecisionWorkspaceService().build(**kwargs)
    return workspace_result_to_dict(result)
