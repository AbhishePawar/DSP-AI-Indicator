"""Additive authenticated ESG score routes (Data Connector Framework)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["esg"])


@router.get("/esg")
def esg(
    symbol: str = Query(..., min_length=1, max_length=32),
    exchange: str | None = Query(None, max_length=32),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Return an authenticated ESG score, trying every configured provider in
    priority order (automatic failover).

    Additive endpoint — does not alter ``/analyse``. Missing authenticated
    data returns HTTP 200 with ``available: false`` (never fabricated).
    """
    try:
        payload = state.platform.get_authenticated_esg_score(symbol, exchange=exchange)
    except Exception as exc:  # noqa: BLE001
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
            "as_of": payload.get("as_of"),
            "environmental_score": payload.get("environmental_score"),
            "social_score": payload.get("social_score"),
            "governance_score": payload.get("governance_score"),
            "total_score": payload.get("total_score"),
            "controversy_level": payload.get("controversy_level"),
            "provenance": payload.get("provenance"),
            "attempted_provider_ids": payload.get("attempted_provider_ids"),
            "message": None,
        }
    )


@router.get("/esg/health")
def esg_health(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Authenticated ESG provider group health."""
    return {
        "ok": True,
        "providers": state.platform.esg_health(),
    }
