"""Additive Research Intelligence routes (EPIC-011B).

Measurement & validation only — does not alter analytical APIs.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["research-intelligence"])

_DB_BOUND = False


def _maybe_bind_database_store(state: ApiState) -> None:
    """Prefer EPIC-011A DatabasePort when available; else keep InMemory."""
    global _DB_BOUND
    if _DB_BOUND:
        return
    _DB_BOUND = True
    infra = getattr(state, "infrastructure", None)
    database = getattr(infra, "database", None) if infra is not None else None
    if database is None:
        return
    adapter = type(database).__name__
    if adapter == "InMemoryDatabasePort" and os.getenv(
        "DSP_RI_FORCE_MEMORY", "0"
    ) not in {"1", "true", "yes"}:
        # Still usable for tests; leave default memory registry unless Postgres.
        if "Postgres" not in adapter:
            return
    if "Postgres" not in adapter and os.getenv("DSP_RI_USE_DATABASE", "0") not in {
        "1",
        "true",
        "yes",
    }:
        return
    try:
        from dsp_platform.research_intelligence import (
            DatabaseResearchSnapshotStore,
            ResearchIntelligenceService,
            reset_research_intelligence_for_tests,
        )

        store = DatabaseResearchSnapshotStore(database)
        reset_research_intelligence_for_tests(ResearchIntelligenceService(store=store))
    except Exception:  # noqa: BLE001
        # Honest degrade — keep InMemory registry
        return


class CaptureSnapshotRequest(BaseModel):
    payload: dict[str, Any]
    research_id: str | None = Field(None, max_length=128)
    timestamp: str | None = Field(None, max_length=64)
    ticker: str | None = Field(None, max_length=32)
    company: str | None = Field(None, max_length=256)
    exchange: str | None = Field(None, max_length=32)
    research_version: str | None = Field(None, max_length=64)
    model_version: str | None = Field(None, max_length=64)
    allow_duplicate: bool = False


class MeasureRequest(BaseModel):
    research_id: str = Field(..., max_length=128)
    window_months: int = Field(..., ge=1, le=36)
    price_at_horizon: float | None = None
    iv_at_horizon: float | None = None
    measured_at: str | None = Field(None, max_length=64)


class MeasureBatchRequest(BaseModel):
    window_months: int = Field(..., ge=1, le=36)
    horizon_prices: dict[str, float | None] | None = None
    measured_at: str | None = Field(None, max_length=64)


class WindowedRequest(BaseModel):
    window_months: int = Field(12, ge=1, le=36)
    horizon_prices: dict[str, float | None] | None = None
    result_id: str | None = Field(None, max_length=128)
    created_at: str | None = Field(None, max_length=64)
    measured_at: str | None = Field(None, max_length=64)
    top_n: int = Field(5, ge=1, le=50)


@router.get("/research/intelligence/schema")
def research_intelligence_schema(
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    _maybe_bind_database_store(state)
    return {"ok": True, "schema": state.platform.research_intelligence_schema()}


@router.post("/research/intelligence/snapshots")
def capture_snapshot(
    body: CaptureSnapshotRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Explicit immutable snapshot capture — does not run analysis engines."""
    _maybe_bind_database_store(state)
    try:
        result = state.platform.capture_research_intelligence_snapshot(
            body.payload,
            research_id=body.research_id,
            timestamp=body.timestamp,
            ticker=body.ticker,
            company=body.company,
            exchange=body.exchange,
            research_version=body.research_version,
            model_version=body.model_version,
            allow_duplicate=body.allow_duplicate,
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
    return JSONResponse({**result, "message": None})


@router.get("/research/intelligence/snapshots")
def list_snapshots(
    symbol: str | None = Query(None),
    company: str | None = Query(None),
    limit: int | None = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    _maybe_bind_database_store(state)
    return state.platform.research_intelligence_list_snapshots(
        symbol=symbol, company=company, limit=limit, offset=offset
    )


@router.get("/research/intelligence/timeline")
def timeline(
    symbol: str | None = Query(None),
    company: str | None = Query(None),
    limit: int | None = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    _maybe_bind_database_store(state)
    return state.platform.research_intelligence_timeline(
        symbol=symbol, company=company, limit=limit, offset=offset
    )


@router.post("/research/intelligence/outcomes")
def measure_outcome(
    body: MeasureRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    _maybe_bind_database_store(state)
    try:
        result = state.platform.research_intelligence_measure(
            research_id=body.research_id,
            window_months=body.window_months,
            price_at_horizon=body.price_at_horizon,
            iv_at_horizon=body.iv_at_horizon,
            measured_at=body.measured_at,
        )
    except KeyError as exc:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Unable to calculate."},
        )
    return JSONResponse({**result, "message": None})


@router.post("/research/intelligence/outcomes/batch")
def measure_batch(
    body: MeasureBatchRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    _maybe_bind_database_store(state)
    try:
        result = state.platform.research_intelligence_measure_batch(
            window_months=body.window_months,
            horizon_prices=body.horizon_prices,
            measured_at=body.measured_at,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Unable to calculate."},
        )
    return JSONResponse({**result, "message": None})


@router.post("/research/intelligence/calibration")
def calibration(
    body: WindowedRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    _maybe_bind_database_store(state)
    try:
        result = state.platform.research_intelligence_calibration(
            window_months=body.window_months,
            horizon_prices=body.horizon_prices,
            result_id=body.result_id,
            created_at=body.created_at,
            measured_at=body.measured_at,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Unable to calculate."},
        )
    return JSONResponse({**result, "message": None})


@router.post("/research/intelligence/performance")
def performance(
    body: WindowedRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    _maybe_bind_database_store(state)
    try:
        result = state.platform.research_intelligence_performance(
            window_months=body.window_months,
            horizon_prices=body.horizon_prices,
            result_id=body.result_id,
            created_at=body.created_at,
            measured_at=body.measured_at,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Unable to calculate."},
        )
    return JSONResponse({**result, "message": None})


@router.get("/research/intelligence/performance")
def performance_get(
    window_months: int = Query(12, ge=1, le=36),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """GET convenience — outcomes without horizon prices remain Data unavailable."""
    _maybe_bind_database_store(state)
    try:
        result = state.platform.research_intelligence_performance(
            window_months=window_months,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Unable to calculate."},
        )
    return JSONResponse({**result, "message": None})


@router.post("/research/intelligence/insights")
def insights(
    body: WindowedRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    _maybe_bind_database_store(state)
    try:
        result = state.platform.research_intelligence_insights(
            window_months=body.window_months,
            horizon_prices=body.horizon_prices,
            result_id=body.result_id,
            created_at=body.created_at,
            measured_at=body.measured_at,
            top_n=body.top_n,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Unable to calculate."},
        )
    return JSONResponse({**result, "message": None})


@router.get("/research/intelligence/insights")
def insights_get(
    window_months: int = Query(12, ge=1, le=36),
    top_n: int = Query(5, ge=1, le=50),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    _maybe_bind_database_store(state)
    try:
        result = state.platform.research_intelligence_insights(
            window_months=window_months,
            top_n=top_n,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Unable to calculate."},
        )
    return JSONResponse({**result, "message": None})
