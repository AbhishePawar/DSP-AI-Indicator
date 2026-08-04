"""Serialize workflow results (EPIC-A007)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.institutional_workflow.models import (
    WORKFLOW_SCHEMA_VERSION,
    WORKFLOW_SERVICE_VERSION,
    WorkflowResult,
    freeze_mapping,
)
from dsp_platform.institutional_workflow.validation import (
    InstitutionalWorkflowValidationError,
    validate_workflow_result,
)

__all__ = [
    "workflow_result_from_dict",
    "workflow_result_to_dict",
]


def workflow_result_to_dict(result: WorkflowResult) -> dict[str, Any]:
    validate_workflow_result(result)
    return result.to_dict()


def workflow_result_from_dict(data: Mapping[str, Any]) -> WorkflowResult:
    if not isinstance(data, Mapping):
        raise InstitutionalWorkflowValidationError("result must be a mapping")
    citations = tuple(
        freeze_mapping(dict(c)) or freeze_mapping({})
        for c in (data.get("citations") or [])
        if isinstance(c, Mapping)
    )
    limitations = data.get("limitations") or ()
    result = WorkflowResult(
        result_id=str(data.get("result_id") or ""),
        schema_version=str(data.get("schema_version") or WORKFLOW_SCHEMA_VERSION),
        service_version=str(
            data.get("service_version") or WORKFLOW_SERVICE_VERSION
        ),
        created_at=str(data.get("created_at") or ""),
        action=str(data.get("action") or ""),
        workflow=freeze_mapping(dict(data.get("workflow") or {}))
        or freeze_mapping({}),
        citations=citations,
        provenance=freeze_mapping(dict(data.get("provenance") or {}))
        or freeze_mapping({}),
        audit=freeze_mapping(dict(data.get("audit") or {})) or freeze_mapping({}),
        limitations=tuple(limitations)
        if isinstance(limitations, (list, tuple))
        else (),
    )
    validate_workflow_result(result)
    return result
