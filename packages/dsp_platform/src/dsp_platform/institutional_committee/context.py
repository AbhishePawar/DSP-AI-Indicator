"""Context distribution for committee agents (EPIC-A005)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.institutional_committee.models import (
    UNAVAILABLE_MESSAGE,
    CommitteeContext,
    freeze_mapping,
)

__all__ = [
    "distribute_committee_context",
    "section_available",
]


def _as_mapping_list(
    value: Mapping[str, Any] | list[Any] | None,
) -> tuple[Mapping[str, Any], ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        return tuple(v for v in value.values() if isinstance(v, Mapping))
    if isinstance(value, list):
        return tuple(v for v in value if isinstance(v, Mapping))
    return ()


def _ro_section(research_object: Mapping[str, Any] | None, name: str) -> Mapping[str, Any]:
    if research_object is None:
        return {
            "name": name,
            "available": False,
            "status": "unavailable",
            "message": UNAVAILABLE_MESSAGE,
            "payload": None,
        }
    section = research_object.get(name)
    if isinstance(section, Mapping):
        available = bool(section.get("available", section.get("status") == "ok"))
        return {
            "name": name,
            "available": available,
            "status": section.get("status") or ("ok" if available else "unavailable"),
            "message": section.get("message"),
            "payload": section.get("payload"),
            "source": section.get("source"),
        }
    # Flat payload fallback
    if name in research_object and research_object.get(name) is not None:
        return {
            "name": name,
            "available": True,
            "status": "ok",
            "message": None,
            "payload": research_object.get(name),
            "source": "research_object",
        }
    return {
        "name": name,
        "available": False,
        "status": "unavailable",
        "message": UNAVAILABLE_MESSAGE,
        "payload": None,
    }


def section_available(section_index: Mapping[str, Any], name: str) -> bool:
    row = section_index.get(name)
    return isinstance(row, Mapping) and bool(row.get("available"))


def distribute_committee_context(
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
) -> CommitteeContext:
    """Build a shared immutable context for all agents (no provider/engine calls)."""
    snap_list = _as_mapping_list(snapshots)
    diff_list = _as_mapping_list(diffs)

    focus_names = (
        "identity",
        "market_data",
        "financial_statements",
        "valuation",
        "margin_of_safety",
        "business_quality",
        "risk",
        "recommendation",
        "explainability",
        "audit",
        "corporate_actions",
        "historical_series",
        "scenarios",
    )
    section_index: dict[str, Any] = {
        name: _ro_section(research_object, name) for name in focus_names
    }

    # Report-level index (availability only)
    if report is not None:
        section_index["institutional_report"] = {
            "name": "institutional_report",
            "available": True,
            "status": "ok",
            "message": None,
            "payload": {
                "report_id": report.get("report_id"),
                "generated_at": report.get("generated_at") or report.get("created_at"),
            },
            "source": "institutional_report",
        }
    else:
        section_index["institutional_report"] = {
            "name": "institutional_report",
            "available": False,
            "status": "unavailable",
            "message": UNAVAILABLE_MESSAGE,
            "payload": None,
            "source": "institutional_report",
        }

    source_flags = {
        "research_object": research_object is not None,
        "institutional_report": report is not None,
        "research_archive": bool(snap_list),
        "research_diff": bool(diff_list),
        "research_copilot": copilot_response is not None,
        "portfolio_intelligence": portfolio_intelligence is not None,
        "research_monitoring": monitoring_result is not None,
        "decision_workspace": workspace is not None,
    }

    return CommitteeContext(
        subject=str(subject).strip().upper(),
        research_object=freeze_mapping(dict(research_object))
        if isinstance(research_object, Mapping)
        else None,
        report=freeze_mapping(dict(report)) if isinstance(report, Mapping) else None,
        snapshots=tuple(freeze_mapping(dict(s)) or freeze_mapping({}) for s in snap_list),
        diffs=tuple(freeze_mapping(dict(d)) or freeze_mapping({}) for d in diff_list),
        copilot_response=freeze_mapping(dict(copilot_response))
        if isinstance(copilot_response, Mapping)
        else None,
        portfolio_intelligence=freeze_mapping(dict(portfolio_intelligence))
        if isinstance(portfolio_intelligence, Mapping)
        else None,
        monitoring_result=freeze_mapping(dict(monitoring_result))
        if isinstance(monitoring_result, Mapping)
        else None,
        workspace=freeze_mapping(dict(workspace))
        if isinstance(workspace, Mapping)
        else None,
        section_index=freeze_mapping(section_index) or freeze_mapping({}),
        source_flags=freeze_mapping(source_flags) or freeze_mapping({}),
    )
