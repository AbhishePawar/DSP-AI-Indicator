"""Additive authenticated shareholding/ownership routes (Data Connector Framework)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["ownership"])


@router.get("/ownership")
def ownership(
    symbol: str = Query(..., min_length=1, max_length=32),
    exchange: str | None = Query(None, max_length=32),
    as_of: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Return an authenticated shareholding pattern, trying every configured
    provider in priority order (automatic failover).

    Additive endpoint — does not alter ``/analyse``. Missing authenticated
    data returns HTTP 200 with ``available: false`` (never fabricated).
    """
    try:
        payload = state.platform.get_authenticated_ownership(
            symbol, exchange=exchange, as_of=as_of
        )
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
                "stakes": None,
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
            "stakes": payload.get("stakes"),
            "promoter_holding_percent": payload.get("promoter_holding_percent"),
            "institutional_holding_percent": payload.get("institutional_holding_percent"),
            "public_holding_percent": payload.get("public_holding_percent"),
            "provenance": payload.get("provenance"),
            "attempted_provider_ids": payload.get("attempted_provider_ids"),
            "message": None,
        }
    )


@router.get("/ownership/health")
def ownership_health(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Authenticated ownership provider group health."""
    return {
        "ok": True,
        "providers": state.platform.ownership_health(),
    }
