"""Citation helpers for Institutional Workflow (EPIC-A007)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.institutional_workflow.models import UNAVAILABLE_MESSAGE, freeze_mapping

__all__ = ["build_workflow_citations", "citation"]


def citation(
    *,
    source_kind: str,
    section: str,
    path: str,
    available: bool,
    workflow_id: str | None = None,
    label: str | None = None,
    ref_id: str | None = None,
) -> Mapping[str, Any]:
    row: dict[str, Any] = {
        "source_kind": source_kind,
        "section": section,
        "path": path,
        "available": available,
        "label": label or f"{source_kind}/{section}",
    }
    if workflow_id:
        row["workflow_id"] = workflow_id
    if ref_id:
        row["ref_id"] = ref_id
    if not available:
        row["message"] = UNAVAILABLE_MESSAGE
    return freeze_mapping(row) or freeze_mapping({})


def build_workflow_citations(
    artifact_refs: Mapping[str, Any],
    *,
    workflow_id: str,
) -> tuple[Mapping[str, Any], ...]:
    """Cite referenced artifacts by id only — never mutate them."""
    key_to_kind = {
        "research_object_id": ("research_object", "object_id"),
        "report_id": ("institutional_report", "report_id"),
        "snapshot_id": ("research_archive", "snapshot_id"),
        "diff_id": ("research_diff", "diff_id"),
        "workspace_id": ("decision_workspace", "workspace_id"),
        "committee_report_id": ("institutional_committee", "report_id"),
        "compliance_result_id": ("investment_policy", "result_id"),
    }
    cites: list[Mapping[str, Any]] = []
    for key, (source_kind, section) in sorted(key_to_kind.items()):
        value = artifact_refs.get(key)
        available = value is not None and str(value).strip() != ""
        cites.append(
            citation(
                source_kind=source_kind,
                section=section,
                path=f"workflow.artifact_refs.{key}",
                available=available,
                workflow_id=workflow_id,
                ref_id=str(value) if available else None,
                label=f"{source_kind}/{key}",
            )
        )
    cites.append(
        citation(
            source_kind="institutional_workflow",
            section="workflow",
            path="workflow",
            available=True,
            workflow_id=workflow_id,
            ref_id=workflow_id,
            label="workflow",
        )
    )
    return tuple(cites)
