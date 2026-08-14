"""Validate Decision Workspace results (EPIC-A004)."""

from __future__ import annotations

from dsp_platform.decision_workspace.models import (
    PANEL_NAMES,
    WORKSPACE_KINDS,
    WORKSPACE_SCHEMA_VERSION,
    WorkspaceResult,
)

__all__ = [
    "DecisionWorkspaceValidationError",
    "validate_workspace_result",
]


class DecisionWorkspaceValidationError(ValueError):
    """Workspace result failed validation."""


def validate_workspace_result(result: WorkspaceResult) -> None:
    if result.schema_version != WORKSPACE_SCHEMA_VERSION:
        raise DecisionWorkspaceValidationError(
            f"unsupported schema_version {result.schema_version!r}"
        )
    if result.kind not in WORKSPACE_KINDS:
        raise DecisionWorkspaceValidationError(f"invalid kind {result.kind!r}")
    if not result.workspace_id.strip():
        raise DecisionWorkspaceValidationError("missing workspace_id")
    if not result.subject.strip():
        raise DecisionWorkspaceValidationError("missing subject")
    if not result.created_at:
        raise DecisionWorkspaceValidationError("missing created_at")
    names = [p.name for p in result.panels]
    if names != list(PANEL_NAMES):
        raise DecisionWorkspaceValidationError(
            f"panels must match PANEL_NAMES order, got {names!r}"
        )
    for panel in result.panels:
        if not panel.citations:
            raise DecisionWorkspaceValidationError(
                f"panel {panel.name} missing citations"
            )
        for c in panel.citations:
            if not c.get("path") or not c.get("section"):
                raise DecisionWorkspaceValidationError(
                    f"panel {panel.name} citation missing path/section"
                )
    if not result.citations:
        raise DecisionWorkspaceValidationError("workspace citations required")
    if result.provenance is None or result.audit is None:
        raise DecisionWorkspaceValidationError("missing provenance/audit")
