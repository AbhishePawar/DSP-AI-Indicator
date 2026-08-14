"""Serialize Decision Workspace results (EPIC-A004)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.decision_workspace.models import (
    WORKSPACE_SCHEMA_VERSION,
    WORKSPACE_SERVICE_VERSION,
    TimelineEvent,
    WorkspacePanel,
    WorkspaceResult,
    freeze_mapping,
)
from dsp_platform.decision_workspace.validation import (
    DecisionWorkspaceValidationError,
    validate_workspace_result,
)

__all__ = [
    "workspace_result_from_dict",
    "workspace_result_to_dict",
]


def workspace_result_to_dict(result: WorkspaceResult) -> dict[str, Any]:
    validate_workspace_result(result)
    return result.to_dict()


def workspace_result_from_dict(data: Mapping[str, Any]) -> WorkspaceResult:
    if not isinstance(data, Mapping):
        raise DecisionWorkspaceValidationError("result must be a mapping")

    panels: list[WorkspacePanel] = []
    for row in data.get("panels") or []:
        if not isinstance(row, Mapping):
            continue
        citations = tuple(
            freeze_mapping(dict(c)) or freeze_mapping({})
            for c in (row.get("citations") or [])
            if isinstance(c, Mapping)
        )
        panels.append(
            WorkspacePanel(
                name=str(row.get("name") or ""),
                available=bool(row.get("available")),
                status=str(row.get("status") or ""),
                source_kind=str(row.get("source_kind") or ""),
                summary=freeze_mapping(dict(row.get("summary") or {}))
                or freeze_mapping({}),
                citations=citations,
                payload=(
                    freeze_mapping(dict(row["payload"]))
                    if isinstance(row.get("payload"), Mapping)
                    else None
                ),
                message=row.get("message"),
            )
        )

    timeline: list[TimelineEvent] = []
    for row in data.get("timeline") or []:
        if not isinstance(row, Mapping):
            continue
        timeline.append(
            TimelineEvent(
                event_id=str(row.get("event_id") or ""),
                event_type=str(row.get("event_type") or ""),
                timestamp=str(row.get("timestamp") or ""),
                label=str(row.get("label") or ""),
                source_kind=str(row.get("source_kind") or ""),
                available=bool(row.get("available")),
                ref_id=row.get("ref_id"),
                message=row.get("message"),
                metadata=freeze_mapping(dict(row.get("metadata") or {}))
                or freeze_mapping({}),
            )
        )

    citations = tuple(
        freeze_mapping(dict(c)) or freeze_mapping({})
        for c in (data.get("citations") or [])
        if isinstance(c, Mapping)
    )
    limitations = data.get("limitations") or ()
    result = WorkspaceResult(
        workspace_id=str(data.get("workspace_id") or ""),
        schema_version=str(data.get("schema_version") or WORKSPACE_SCHEMA_VERSION),
        service_version=str(
            data.get("service_version") or WORKSPACE_SERVICE_VERSION
        ),
        created_at=str(data.get("created_at") or ""),
        kind=str(data.get("kind") or ""),
        subject=str(data.get("subject") or ""),
        panels=tuple(panels),
        timeline=tuple(timeline),
        citations=citations,
        provenance=freeze_mapping(dict(data.get("provenance") or {}))
        or freeze_mapping({}),
        audit=freeze_mapping(dict(data.get("audit") or {})) or freeze_mapping({}),
        limitations=tuple(limitations)
        if isinstance(limitations, (list, tuple))
        else (),
    )
    validate_workspace_result(result)
    return result
