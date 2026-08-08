"""Additive Continuous Research Monitoring routes (EPIC-A003)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["research-monitoring"])


class WatchlistRegisterRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)


class PortfolioRegisterRequest(BaseModel):
    portfolio_id: str = Field(..., min_length=1, max_length=128)
    metadata: dict[str, Any] | None = None


class SnapshotTrackRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=64)
    subject_kind: str = Field("symbol", max_length=32)
    baseline_snapshot_id: str | None = Field(None, max_length=128)
    current_snapshot_id: str | None = Field(None, max_length=128)
    tracked_at: str | None = Field(None, max_length=64)


class MonitoringEvaluateRequest(BaseModel):
    snapshot_pairs: dict[str, dict[str, str]] | None = None
    portfolio_intelligence_baseline: dict[str, Any] | None = None
    portfolio_intelligence_current: dict[str, Any] | None = None
    portfolio_id: str | None = Field(None, max_length=128)
    result_id: str | None = Field(None, max_length=128)
    created_at: str | None = Field(None, max_length=64)
    register_watchlist_symbols: list[str] | None = None


@router.get("/research/monitoring/schema")
def research_monitoring_schema(
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    return {"ok": True, "schema": state.platform.research_monitoring_schema()}


@router.post("/research/monitoring/watchlist")
def register_watchlist(
    body: WatchlistRegisterRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        symbols = state.platform.register_monitoring_watchlist(body.symbols)
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    return JSONResponse({"ok": True, "symbols": symbols, "message": None})


@router.post("/research/monitoring/portfolio")
def register_portfolio(
    body: PortfolioRegisterRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        entry = state.platform.register_monitoring_portfolio(
            body.portfolio_id, metadata=body.metadata
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    return JSONResponse({"ok": True, "portfolio": entry, "message": None})


@router.post("/research/monitoring/track")
def track_snapshot(
    body: SnapshotTrackRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        track = state.platform.track_monitoring_snapshot(
            body.subject,
            subject_kind=body.subject_kind,
            baseline_snapshot_id=body.baseline_snapshot_id,
            current_snapshot_id=body.current_snapshot_id,
            tracked_at=body.tracked_at,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    return JSONResponse({"ok": True, "track": track, "message": None})


@router.post("/research/monitoring/evaluate")
def evaluate_monitoring(
    body: MonitoringEvaluateRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Detect research/portfolio changes via immutable artifacts only."""
    try:
        result = state.platform.evaluate_research_monitoring(
            snapshot_pairs=body.snapshot_pairs,
            portfolio_intelligence_baseline=body.portfolio_intelligence_baseline,
            portfolio_intelligence_current=body.portfolio_intelligence_current,
            portfolio_id=body.portfolio_id,
            result_id=body.result_id,
            created_at=body.created_at,
            register_watchlist_symbols=body.register_watchlist_symbols,
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
