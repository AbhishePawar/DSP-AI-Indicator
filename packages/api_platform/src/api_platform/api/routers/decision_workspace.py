"""Additive Institutional Decision Workspace routes (EPIC-A004)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["decision-workspace"])


class DecisionWorkspaceRequest(BaseModel):
    kind: str = Field(..., min_length=1, max_length=32)
    subject: str = Field(..., min_length=1, max_length=128)
    research_object: dict[str, Any] | None = None
    report: dict[str, Any] | None = None
    reports: dict[str, Any] | list[Any] | None = None
    snapshots: dict[str, Any] | list[Any] | None = None
    diffs: dict[str, Any] | list[Any] | None = None
    copilot_response: dict[str, Any] | None = None
    portfolio_intelligence: dict[str, Any] | None = None
    monitoring_result: dict[str, Any] | None = None
    workspace_id: str | None = Field(None, max_length=128)
    created_at: str | None = Field(None, max_length=64)


@router.get("/decision/workspace/schema")
def decision_workspace_schema(
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    return {"ok": True, "schema": state.platform.decision_workspace_schema()}


@router.post("/decision/workspace")
def decision_workspace(
    body: DecisionWorkspaceRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Aggregate supplied research artifacts into a read-only workspace."""
    try:
        result = state.platform.build_decision_workspace(
            kind=body.kind,
            subject=body.subject,
            research_object=body.research_object,
            report=body.report,
            reports=body.reports,
            snapshots=body.snapshots,
            diffs=body.diffs,
            copilot_response=body.copilot_response,
            portfolio_intelligence=body.portfolio_intelligence,
            monitoring_result=body.monitoring_result,
            workspace_id=body.workspace_id,
            created_at=body.created_at,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    return JSONResponse({"ok": True, "result": result, "message": None})
