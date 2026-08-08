"""Additive Institutional Multi-Agent Committee routes (EPIC-A005)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["institutional-committee"])


class CommitteeRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=128)
    research_object: dict[str, Any] | None = None
    report: dict[str, Any] | None = None
    snapshots: dict[str, Any] | list[Any] | None = None
    diffs: dict[str, Any] | list[Any] | None = None
    copilot_response: dict[str, Any] | None = None
    portfolio_intelligence: dict[str, Any] | None = None
    monitoring_result: dict[str, Any] | None = None
    workspace: dict[str, Any] | None = None
    report_id: str | None = Field(None, max_length=128)
    created_at: str | None = Field(None, max_length=64)


@router.get("/committee/schema")
def committee_schema(
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    return {"ok": True, "schema": state.platform.institutional_committee_schema()}


@router.get("/committee/agents")
def committee_agents(
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    return {"ok": True, "agents": state.platform.list_committee_agents()}


@router.post("/committee/run")
def committee_run(
    body: CommitteeRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Run deterministic multi-agent review over supplied artifacts."""
    try:
        result = state.platform.run_institutional_committee(
            subject=body.subject,
            research_object=body.research_object,
            report=body.report,
            snapshots=body.snapshots,
            diffs=body.diffs,
            copilot_response=body.copilot_response,
            portfolio_intelligence=body.portfolio_intelligence,
            monitoring_result=body.monitoring_result,
            workspace=body.workspace,
            report_id=body.report_id,
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
