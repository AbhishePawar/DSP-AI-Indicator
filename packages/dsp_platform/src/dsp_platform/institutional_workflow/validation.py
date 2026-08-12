"""Validate workflow results (EPIC-A007)."""

from __future__ import annotations

from dsp_platform.institutional_workflow.models import (
    WORKFLOW_SCHEMA_VERSION,
    WORKFLOW_STAGES,
    WorkflowResult,
)

__all__ = [
    "InstitutionalWorkflowValidationError",
    "validate_workflow_result",
]


class InstitutionalWorkflowValidationError(ValueError):
    """Workflow result failed validation."""


def validate_workflow_result(result: WorkflowResult) -> None:
    if result.schema_version != WORKFLOW_SCHEMA_VERSION:
        raise InstitutionalWorkflowValidationError(
            f"unsupported schema_version {result.schema_version!r}"
        )
    if not result.result_id.strip():
        raise InstitutionalWorkflowValidationError("missing result_id")
    if not result.created_at:
        raise InstitutionalWorkflowValidationError("missing created_at")
    wf = result.workflow
    stage = str(wf.get("stage") or "")
    if stage not in WORKFLOW_STAGES:
        raise InstitutionalWorkflowValidationError(f"invalid stage {stage!r}")
    if not result.citations:
        raise InstitutionalWorkflowValidationError("citations required")
    for c in result.citations:
        if not c.get("path") or not c.get("section"):
            raise InstitutionalWorkflowValidationError(
                "citation missing path/section"
            )
    if result.provenance is None or result.audit is None:
        raise InstitutionalWorkflowValidationError("missing provenance/audit")
