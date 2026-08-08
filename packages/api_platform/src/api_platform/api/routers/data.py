"""Additive unified authenticated data gateway routes (EPIC-D005)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["data"])


@router.get("/data/bundle")
def unified_data_bundle(
    symbol: str = Query(..., min_length=1, max_length=32),
    exchange: str | None = Query(None, max_length=32),
    include_market_quote: bool = Query(True),
    include_financial_statements: bool = Query(True),
    include_corporate_actions: bool = Query(True),
    include_historical_series: bool = Query(True),
    historical_series_kind: str = Query("ohlcv"),
    historical_frequency: str | None = Query("daily"),
    historical_limit: int = Query(30, ge=1, le=5000),
    statement_limit: int = Query(8, ge=1, le=40),
    corporate_actions_limit: int = Query(50, ge=1, le=200),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Aggregate authenticated market / statements / actions / history.

    Additive endpoint — does not alter ``/analyse``. Partial provider failure
    returns HTTP 200 with per-section status (never fabricates missing data).
    """
    try:
        payload = state.platform.get_unified_data_bundle(
            symbol,
            exchange=exchange,
            include_market_quote=include_market_quote,
            include_financial_statements=include_financial_statements,
            include_corporate_actions=include_corporate_actions,
            include_historical_series=include_historical_series,
            historical_series_kind=historical_series_kind,
            historical_frequency=historical_frequency,
            historical_limit=historical_limit,
            statement_limit=statement_limit,
            corporate_actions_limit=corporate_actions_limit,
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "symbol": symbol.strip().upper(),
                "error": str(exc),
                "message": "Data unavailable.",
            },
        )

    return JSONResponse(
        {
            "ok": True,
            "symbol": payload.get("identity", {}).get("symbol")
            if isinstance(payload.get("identity"), dict)
            else symbol.strip().upper(),
            "bundle": payload,
            "message": None,
        }
    )


@router.get("/data/health")
def unified_data_health(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Aggregated authenticated data provider health."""
    return {
        "ok": True,
        "health": state.platform.unified_data_health(),
    }
