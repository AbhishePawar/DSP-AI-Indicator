"""Panel builders for Decision Workspace (EPIC-A004)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.decision_workspace.citations import citation
from dsp_platform.decision_workspace.models import (
    UNAVAILABLE_MESSAGE,
    WorkspacePanel,
    freeze_mapping,
)
__all__ = [
    "build_active_alerts_panel",
    "build_audit_panel",
    "build_copilot_panel",
    "build_diff_history_panel",
    "build_monitoring_panel",
    "build_portfolio_panel",
    "build_report_history_panel",
    "build_report_panel",
    "build_research_panel",
    "build_snapshot_history_panel",
    "build_timeline_panel",
]


def _unavailable_panel(name: str, source_kind: str) -> WorkspacePanel:
    return WorkspacePanel(
        name=name,
        available=False,
        status="unavailable",
        source_kind=source_kind,
        summary=freeze_mapping({"available": False}) or freeze_mapping({}),
        citations=(
            citation(
                source_kind=source_kind,
                section=name,
                path=f"workspace.{name}",
                available=False,
                label=f"{source_kind}/{name}",
            ),
        ),
        payload=None,
        message=UNAVAILABLE_MESSAGE,
    )


def build_research_panel(
    research_object: Mapping[str, Any] | None,
    *,
    symbol: str | None = None,
) -> WorkspacePanel:
    if research_object is None:
        return _unavailable_panel("research", "research_object")
    oid = str(
        research_object.get("object_id")
        or research_object.get("research_object_id")
        or ""
    )
    return WorkspacePanel(
        name="research",
        available=True,
        status="ok",
        source_kind="research_object",
        summary=freeze_mapping(
            {
                "object_id": oid or None,
                "symbol": research_object.get("symbol") or symbol,
                "schema_version": research_object.get("schema_version"),
                "created_at": research_object.get("created_at"),
            }
        )
        or freeze_mapping({}),
        citations=(
            citation(
                source_kind="research_object",
                section="research_object",
                path="research_object",
                available=True,
                symbol=str(research_object.get("symbol") or symbol or ""),
                ref_id=oid or None,
                label="research_object",
            ),
        ),
        payload=freeze_mapping(dict(research_object)),
        message=None,
    )


def build_report_panel(report: Mapping[str, Any] | None) -> WorkspacePanel:
    if report is None:
        return _unavailable_panel("report", "institutional_report")
    rid = str(report.get("report_id") or "")
    return WorkspacePanel(
        name="report",
        available=True,
        status="ok",
        source_kind="institutional_report",
        summary=freeze_mapping(
            {
                "report_id": rid or None,
                "schema_version": report.get("schema_version"),
                "generated_at": report.get("generated_at")
                or report.get("created_at"),
            }
        )
        or freeze_mapping({}),
        citations=(
            citation(
                source_kind="institutional_report",
                section="report",
                path="institutional_report",
                available=True,
                ref_id=rid or None,
                label="institutional_report",
            ),
        ),
        payload=freeze_mapping(dict(report)),
        message=None,
    )


def build_timeline_panel(
    timeline_events: tuple[Any, ...],
) -> WorkspacePanel:
    available = bool(timeline_events) and not (
        len(timeline_events) == 1
        and getattr(timeline_events[0], "available", True) is False
    )
    events = [e.to_dict() for e in timeline_events]
    return WorkspacePanel(
        name="timeline",
        available=available,
        status="ok" if available else "unavailable",
        source_kind="decision_workspace",
        summary=freeze_mapping({"event_count": len(events), "available": available})
        or freeze_mapping({}),
        citations=(
            citation(
                source_kind="decision_workspace",
                section="timeline",
                path="workspace.timeline",
                available=available,
                label="timeline",
            ),
        ),
        payload=freeze_mapping({"events": events}),
        message=None if available else UNAVAILABLE_MESSAGE,
    )


def build_active_alerts_panel(
    monitoring_result: Mapping[str, Any] | None,
) -> WorkspacePanel:
    if monitoring_result is None:
        return _unavailable_panel("active_alerts", "research_monitoring")
    alerts = monitoring_result.get("alerts") or []
    if not isinstance(alerts, list):
        alerts = []
    # Surface non-info alerts as "active"
    active = [
        a
        for a in alerts
        if isinstance(a, Mapping) and a.get("severity") not in {"info", None}
    ]
    return WorkspacePanel(
        name="active_alerts",
        available=True,
        status="ok",
        source_kind="research_monitoring",
        summary=freeze_mapping(
            {
                "alert_count": len(alerts),
                "active_count": len(active),
                "result_id": monitoring_result.get("result_id"),
            }
        )
        or freeze_mapping({}),
        citations=(
            citation(
                source_kind="research_monitoring",
                section="alerts",
                path="research_monitoring.alerts",
                available=True,
                ref_id=str(monitoring_result.get("result_id") or "") or None,
                label="monitoring/alerts",
            ),
        ),
        payload=freeze_mapping({"alerts": active, "all_alerts": alerts}),
        message=None,
    )


def build_report_history_panel(
    reports: list[Mapping[str, Any]] | None,
) -> WorkspacePanel:
    rows = [r for r in (reports or []) if isinstance(r, Mapping)]
    if not rows:
        return _unavailable_panel("report_history", "institutional_report")
    history = [
        {
            "report_id": r.get("report_id"),
            "generated_at": r.get("generated_at") or r.get("created_at"),
            "schema_version": r.get("schema_version"),
        }
        for r in rows
    ]
    history.sort(key=lambda x: str(x.get("generated_at") or ""))
    return WorkspacePanel(
        name="report_history",
        available=True,
        status="ok",
        source_kind="institutional_report",
        summary=freeze_mapping({"count": len(history)}) or freeze_mapping({}),
        citations=(
            citation(
                source_kind="institutional_report",
                section="report_history",
                path="workspace.report_history",
                available=True,
                label="report_history",
            ),
        ),
        payload=freeze_mapping({"reports": history}),
        message=None,
    )


def build_snapshot_history_panel(
    snapshots: list[Mapping[str, Any]] | None,
) -> WorkspacePanel:
    rows = [s for s in (snapshots or []) if isinstance(s, Mapping)]
    if not rows:
        return _unavailable_panel("snapshot_history", "research_archive")
    history = []
    for s in rows:
        version = s.get("version") if isinstance(s.get("version"), Mapping) else {}
        history.append(
            {
                "snapshot_id": s.get("snapshot_id"),
                "kind": s.get("kind"),
                "archived_at": s.get("archived_at"),
                "lineage_id": version.get("lineage_id"),
                "content_hash": s.get("content_hash"),
            }
        )
    history.sort(key=lambda x: str(x.get("archived_at") or ""))
    return WorkspacePanel(
        name="snapshot_history",
        available=True,
        status="ok",
        source_kind="research_archive",
        summary=freeze_mapping({"count": len(history)}) or freeze_mapping({}),
        citations=(
            citation(
                source_kind="research_archive",
                section="snapshot_history",
                path="workspace.snapshot_history",
                available=True,
                label="snapshot_history",
            ),
        ),
        payload=freeze_mapping({"snapshots": history}),
        message=None,
    )


def build_diff_history_panel(
    diffs: list[Mapping[str, Any]] | None,
) -> WorkspacePanel:
    rows = [d for d in (diffs or []) if isinstance(d, Mapping)]
    if not rows:
        return _unavailable_panel("diff_history", "research_diff")
    history = []
    for d in rows:
        summary = (
            d.get("change_summary")
            if isinstance(d.get("change_summary"), Mapping)
            else {}
        )
        history.append(
            {
                "diff_id": d.get("diff_id"),
                "created_at": d.get("created_at"),
                "left_snapshot_id": d.get("left_snapshot_id"),
                "right_snapshot_id": d.get("right_snapshot_id"),
                "identical_content": summary.get("identical_content"),
                "fields_changed": summary.get("fields_changed"),
            }
        )
    history.sort(key=lambda x: str(x.get("created_at") or ""))
    return WorkspacePanel(
        name="diff_history",
        available=True,
        status="ok",
        source_kind="research_diff",
        summary=freeze_mapping({"count": len(history)}) or freeze_mapping({}),
        citations=(
            citation(
                source_kind="research_diff",
                section="diff_history",
                path="workspace.diff_history",
                available=True,
                label="diff_history",
            ),
        ),
        payload=freeze_mapping({"diffs": history}),
        message=None,
    )


def build_copilot_panel(
    copilot_response: Mapping[str, Any] | None,
) -> WorkspacePanel:
    if copilot_response is None:
        return _unavailable_panel("copilot", "research_copilot")
    return WorkspacePanel(
        name="copilot",
        available=True,
        status="ok",
        source_kind="research_copilot",
        summary=freeze_mapping(
            {
                "response_id": copilot_response.get("response_id"),
                "unavailable": copilot_response.get("unavailable"),
                "citation_count": len(copilot_response.get("citations") or []),
            }
        )
        or freeze_mapping({}),
        citations=(
            citation(
                source_kind="research_copilot",
                section="answer",
                path="research_copilot.answer",
                available=not bool(copilot_response.get("unavailable")),
                ref_id=str(copilot_response.get("response_id") or "") or None,
                label="copilot/answer",
            ),
        ),
        payload=freeze_mapping(dict(copilot_response)),
        message=None,
    )


def build_portfolio_panel(
    portfolio_intelligence: Mapping[str, Any] | None,
) -> WorkspacePanel:
    if portfolio_intelligence is None:
        return _unavailable_panel("portfolio", "portfolio_intelligence")
    summary_src = portfolio_intelligence.get("portfolio_summary")
    if not isinstance(summary_src, Mapping):
        summary_src = {}
    return WorkspacePanel(
        name="portfolio",
        available=True,
        status="ok",
        source_kind="portfolio_intelligence",
        summary=freeze_mapping(
            {
                "result_id": portfolio_intelligence.get("result_id"),
                "holding_count": summary_src.get("holding_count"),
                "linked_research_count": summary_src.get("linked_research_count"),
                "missing_research_count": summary_src.get("missing_research_count"),
            }
        )
        or freeze_mapping({}),
        citations=(
            citation(
                source_kind="portfolio_intelligence",
                section="portfolio_summary",
                path="portfolio_intelligence.portfolio_summary",
                available=True,
                ref_id=str(portfolio_intelligence.get("result_id") or "") or None,
                label="portfolio_intelligence",
            ),
        ),
        payload=freeze_mapping(dict(portfolio_intelligence)),
        message=None,
    )


def build_monitoring_panel(
    monitoring_result: Mapping[str, Any] | None,
) -> WorkspacePanel:
    if monitoring_result is None:
        return _unavailable_panel("monitoring", "research_monitoring")
    audit = (
        monitoring_result.get("audit")
        if isinstance(monitoring_result.get("audit"), Mapping)
        else {}
    )
    return WorkspacePanel(
        name="monitoring",
        available=True,
        status="ok",
        source_kind="research_monitoring",
        summary=freeze_mapping(
            {
                "result_id": monitoring_result.get("result_id"),
                "alert_count": audit.get("alert_count")
                or len(monitoring_result.get("alerts") or []),
                "track_count": audit.get("track_count"),
            }
        )
        or freeze_mapping({}),
        citations=(
            citation(
                source_kind="research_monitoring",
                section="result",
                path="research_monitoring",
                available=True,
                ref_id=str(monitoring_result.get("result_id") or "") or None,
                label="research_monitoring",
            ),
        ),
        payload=freeze_mapping(dict(monitoring_result)),
        message=None,
    )


def build_audit_panel(
    *,
    workspace_id: str,
    kind: str,
    subject: str,
    created_at: str,
    panel_names: list[str],
    available_panels: list[str],
    source_flags: Mapping[str, bool],
) -> WorkspacePanel:
    summary = {
        "workspace_id": workspace_id,
        "kind": kind,
        "subject": subject,
        "created_at": created_at,
        "panel_count": len(panel_names),
        "available_panel_count": len(available_panels),
        "sources_present": dict(source_flags),
    }
    return WorkspacePanel(
        name="audit",
        available=True,
        status="ok",
        source_kind="decision_workspace",
        summary=freeze_mapping(summary) or freeze_mapping({}),
        citations=(
            citation(
                source_kind="decision_workspace",
                section="audit",
                path="workspace.audit",
                available=True,
                label="workspace/audit",
            ),
        ),
        payload=freeze_mapping(
            {
                "panels": panel_names,
                "available_panels": available_panels,
                "sources_present": dict(source_flags),
            }
        ),
        message=None,
    )
