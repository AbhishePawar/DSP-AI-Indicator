"""Additive authenticated company news routes (Data Connector Framework)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["news"])


@router.get("/news")
def news(
    symbol: str = Query(..., min_length=1, max_length=32),
    exchange: str | None = Query(None, max_length=32),
    limit: int = Query(20, ge=1, le=100),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Return authenticated company news, trying every configured provider in
    priority order (automatic failover).

    Additive endpoint — does not alter ``/analyse``. Missing authenticated
    data returns HTTP 200 with ``available: false`` (never fabricated).
    """
    try:
        payload = state.platform.get_authenticated_news(
            symbol, exchange=exchange, limit=limit
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
        return JSONResponse(
            {
                "ok": True,
                "available": False,
                "authenticated": False,
                "symbol": symbol.strip().upper(),
                "exchange": exchange,
                "articles": None,
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
            "articles": payload.get("articles"),
            "provenance": payload.get("provenance"),
            "attempted_provider_ids": payload.get("attempted_provider_ids"),
            "message": None,
        }
    )


@router.get("/news/health")
def news_health(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Authenticated news provider group health."""
    return {
        "ok": True,
        "providers": state.platform.news_health(),
    }
