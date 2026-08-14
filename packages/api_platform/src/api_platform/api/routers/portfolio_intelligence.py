"""Additive Portfolio Intelligence routes (EPIC-A002)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["portfolio-intelligence"])


class PortfolioIntelligenceRequest(BaseModel):
    portfolio: dict[str, Any] | None = None
    watchlist: dict[str, Any] | None = None
    research_objects: dict[str, Any] | list[Any] | None = None
    reports: dict[str, Any] | list[Any] | None = None
    snapshots: dict[str, Any] | list[Any] | None = None
    snapshot_ids: dict[str, str] | None = None
    result_id: str | None = Field(None, max_length=128)
    created_at: str | None = Field(None, max_length=64)


@router.get("/portfolio/intelligence/schema")
def portfolio_intelligence_schema(
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    return {"ok": True, "schema": state.platform.portfolio_intelligence_schema()}


@router.post("/portfolio/intelligence")
def portfolio_intelligence(
    body: PortfolioIntelligenceRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Summarize portfolio/watchlist using linked Research Objects only."""
    try:
        result = state.platform.evaluate_portfolio_intelligence(
            portfolio=body.portfolio,
            watchlist=body.watchlist,
            research_objects=body.research_objects,
            reports=body.reports,
            snapshots=body.snapshots,
            snapshot_ids=body.snapshot_ids,
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
