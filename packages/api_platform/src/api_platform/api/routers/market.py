"""Additive authenticated market quote routes (EPIC-D001)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["market"])


@router.get("/market/quote")
def market_quote(
    symbol: str = Query(..., min_length=1, max_length=32),
    exchange: str | None = Query(None, max_length=32),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Return an authenticated market quote snapshot (RS-002).

    Additive endpoint — does not alter ``/analyse``. Missing authenticated
    data returns HTTP 200 with ``available: false`` (never fabricated fields).
    """
    try:
        payload = state.platform.get_authenticated_market_quote(
            symbol, exchange=exchange
        )
    except Exception as exc:  # noqa: BLE001 — map provider failures honestly
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "available": False,
                "symbol": symbol.strip().upper(),
                "error": str(exc),
                "message": "Data unavailable.",
            },
        )

    if payload is None:
        from data_engine.investment_data_provider import (
            INVESTMENT_DATA_UNAVAILABLE,
            investment_data_is_unavailable,
        )

        body: dict[str, Any] = {
            "ok": True,
            "available": False,
            "authenticated": False,
            "symbol": symbol.strip().upper(),
            "exchange": exchange,
            "fields": None,
            "provenance": None,
            "message": "Data unavailable.",
        }
        if investment_data_is_unavailable():
            body["capability"] = INVESTMENT_DATA_UNAVAILABLE
        return JSONResponse(body)

    return JSONResponse(
        {
            "ok": True,
            "available": True,
            "authenticated": True,
            "symbol": payload.get("symbol"),
            "exchange": payload.get("exchange"),
            "currency": payload.get("currency"),
            "fields": payload.get("fields"),
            "provenance": payload.get("provenance"),
            "message": None,
        }
    )


@router.get("/market/health")
def market_health(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Authenticated market quote provider health."""
    try:
        provider = state.platform.market_quote_health()
    except Exception as exc:  # noqa: BLE001 — capability must not 500
        return {
            "ok": False,
            "available": False,
            "capability": "INVESTMENT_DATA_UNAVAILABLE",
            "provider": {"healthy": False, "authenticated": False, "detail": str(exc)},
        }
    from data_engine.investment_data_provider import (
        INVESTMENT_DATA_UNAVAILABLE,
        investment_data_is_unavailable,
    )

    payload: dict[str, Any] = {"ok": True, "provider": provider}
    if investment_data_is_unavailable():
        payload["ok"] = False
        payload["available"] = False
        payload["capability"] = INVESTMENT_DATA_UNAVAILABLE
    return payload
