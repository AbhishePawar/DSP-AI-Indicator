"""Additive authenticated earnings call transcript routes (Data Connector Framework)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["transcripts"])


@router.get("/transcripts")
def transcripts(
    symbol: str = Query(..., min_length=1, max_length=32),
    exchange: str | None = Query(None, max_length=32),
    year: int | None = Query(None, ge=1990, le=2100),
    quarter: int | None = Query(None, ge=1, le=4),
    limit: int = Query(8, ge=1, le=50),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Return authenticated earnings call transcripts, trying every
    configured provider in priority order (automatic failover).

    Additive endpoint — does not alter ``/analyse``. Missing authenticated
    data returns HTTP 200 with ``available: false`` (never fabricated).
    """
    try:
        payload = state.platform.get_authenticated_transcripts(
            symbol, exchange=exchange, year=year, quarter=quarter, limit=limit
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
                "transcripts": None,
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
            "transcripts": payload.get("transcripts"),
            "provenance": payload.get("provenance"),
            "attempted_provider_ids": payload.get("attempted_provider_ids"),
            "message": None,
        }
    )


@router.get("/transcripts/health")
def transcripts_health(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Authenticated transcripts provider group health."""
    return {
        "ok": True,
        "providers": state.platform.transcripts_health(),
    }
