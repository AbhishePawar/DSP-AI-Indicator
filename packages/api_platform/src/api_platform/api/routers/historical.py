"""Additive authenticated historical time-series routes (EPIC-D004)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["historical"])


@router.get("/historical/series")
def historical_series(
    symbol: str = Query(..., min_length=1, max_length=32),
    series_kind: str = Query(
        ...,
        description=(
            "ohlcv|market_cap|volume|enterprise_value|fundamentals|ratios"
        ),
    ),
    exchange: str | None = Query(None, max_length=32),
    frequency: str | None = Query(
        "daily", description="daily|weekly|monthly (ohlcv)"
    ),
    start_date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    end_date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    limit: int = Query(500, ge=1, le=5000),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Return authenticated historical time-series.

    Additive endpoint — does not alter ``/analyse``. Missing authenticated
    data returns HTTP 200 with ``available: false``. Retrieval/validation only
    — no indicators or adjusted series.
    """
    try:
        payload = state.platform.get_authenticated_historical_series(
            symbol,
            series_kind=series_kind,
            exchange=exchange,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "available": False,
                "symbol": symbol.strip().upper(),
                "series_kind": series_kind,
                "error": str(exc),
                "message": "Data unavailable.",
            },
        )

    if payload is None:
        return JSONResponse(
            {
                "ok": True,
                "available": False,
                "authenticated": False,
                "symbol": symbol.strip().upper(),
                "series_kind": series_kind,
                "bars": None,
                "points": None,
                "snapshots": None,
                "identity": None,
                "provenance": None,
                "message": "Data unavailable.",
            }
        )

    identity = payload.get("identity")
    return JSONResponse(
        {
            "ok": True,
            "available": True,
            "authenticated": True,
            "symbol": identity.get("symbol")
            if isinstance(identity, dict)
            else symbol.strip().upper(),
            "identity": identity,
            "series_kind": payload.get("series_kind"),
            "frequency": payload.get("frequency"),
            "start_date": payload.get("start_date"),
            "end_date": payload.get("end_date"),
            "currency": payload.get("currency"),
            "bars": payload.get("bars"),
            "points": payload.get("points"),
            "snapshots": payload.get("snapshots"),
            "provenance": payload.get("provenance"),
            "message": None,
        }
    )


@router.get("/historical/health")
def historical_health(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Authenticated historical series provider health."""
    return {
        "ok": True,
        "provider": state.platform.historical_series_health(),
    }
