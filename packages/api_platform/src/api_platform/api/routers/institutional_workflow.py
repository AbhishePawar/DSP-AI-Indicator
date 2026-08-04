"""Additive Institutional Workflow & Approval routes (EPIC-A007)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["institutional-workflow"])


class WorkflowActionRequest(BaseModel):
    action: str = Field(..., min_length=1, max_length=32)
    subject: str | None = Field(None, max_length=128)
    workflow_id: str | None = Field(None, max_length=128)
    template_id: str | None = Field(None, max_length=128)
    artifact_refs: dict[str, Any] | None = None
    reviewers: list[dict[str, Any]] | None = None
    to_stage: str | None = Field(None, max_length=64)
    actor_id: str | None = Field(None, max_length=128)
    author_id: str | None = Field(None, max_length=128)
    body: str | None = Field(None, max_length=4000)
    reason: str | None = Field(None, max_length=1000)
    note: str | None = Field(None, max_length=1000)
    comment_id: str | None = Field(None, max_length=128)
    approval_id: str | None = Field(None, max_length=128)
    event_id: str | None = Field(None, max_length=128)
    reviewer_id: str | None = Field(None, max_length=128)
    role: str | None = Field(None, max_length=64)
    display_name: str | None = Field(None, max_length=256)
    metadata: dict[str, Any] | None = None
    result_id: str | None = Field(None, max_length=128)
    created_at: str | None = Field(None, max_length=64)


@router.get("/workflow/schema")
def workflow_schema(
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    return {"ok": True, "schema": state.platform.institutional_workflow_schema()}


@router.get("/workflow/templates")
def workflow_templates(
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    return {"ok": True, "templates": state.platform.list_workflow_templates()}


@router.post("/workflow/action")
def workflow_action(
    body: WorkflowActionRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Apply a workflow action (create / transition / comment / get / assign / history)."""
    try:
        result = state.platform.apply_institutional_workflow(
            action=body.action,
            subject=body.subject,
            workflow_id=body.workflow_id,
            template_id=body.template_id,
            artifact_refs=body.artifact_refs,
            reviewers=body.reviewers,
            to_stage=body.to_stage,
            actor_id=body.actor_id,
            author_id=body.author_id,
            body=body.body,
            reason=body.reason,
            note=body.note,
            comment_id=body.comment_id,
            approval_id=body.approval_id,
            event_id=body.event_id,
            reviewer_id=body.reviewer_id,
            role=body.role,
            display_name=body.display_name,
            metadata=body.metadata,
            result_id=body.result_id,
            created_at=body.created_at,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    except KeyError as exc:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    return JSONResponse({"ok": True, "result": result, "message": None})
