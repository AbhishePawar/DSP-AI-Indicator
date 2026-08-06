"""Additive Investment Policy & Compliance routes (EPIC-A006)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["investment-policy"])


class PolicyEvaluateRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=128)
    policy: dict[str, Any] | None = None
    exceptions: list[dict[str, Any]] | None = None
    research_object: dict[str, Any] | None = None
    report: dict[str, Any] | None = None
    snapshots: dict[str, Any] | list[Any] | None = None
    diffs: dict[str, Any] | list[Any] | None = None
    portfolio_intelligence: dict[str, Any] | None = None
    monitoring_result: dict[str, Any] | None = None
    workspace: dict[str, Any] | None = None
    committee_report: dict[str, Any] | None = None
    result_id: str | None = Field(None, max_length=128)
    created_at: str | None = Field(None, max_length=64)


@router.get("/policy/schema")
def policy_schema(
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    return {"ok": True, "schema": state.platform.investment_policy_schema()}


@router.get("/policy/default")
def policy_default(
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    return {"ok": True, "policy": state.platform.default_investment_policy()}


@router.post("/policy/evaluate")
def policy_evaluate(
    body: PolicyEvaluateRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Evaluate supplied artifacts against an investment policy."""
    try:
        result = state.platform.evaluate_investment_policy(
            subject=body.subject,
            policy=body.policy,
            exceptions=body.exceptions,
            research_object=body.research_object,
            report=body.report,
            snapshots=body.snapshots,
            diffs=body.diffs,
            portfolio_intelligence=body.portfolio_intelligence,
            monitoring_result=body.monitoring_result,
            workspace=body.workspace,
            committee_report=body.committee_report,
            result_id=body.result_id,
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
