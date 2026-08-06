"""Additive authenticated regulatory filings routes (Data Connector Framework)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["filings"])


@router.get("/filings")
def filings(
    symbol: str = Query(..., min_length=1, max_length=32),
    exchange: str | None = Query(None, max_length=32),
    filing_types: str | None = Query(
        None, description="Comma-separated: 10-K,10-Q,8-K,annual_report,..."
    ),
    start_date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    end_date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=200),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Return authenticated regulatory/corporate filings, trying every
    configured provider in priority order (automatic failover).

    Additive endpoint — does not alter ``/analyse``. Missing authenticated
    data returns HTTP 200 with ``available: false`` (never fabricated).
    """
    parsed_types = (
        tuple(t.strip() for t in filing_types.split(",") if t.strip())
        if filing_types
        else ()
    )
    try:
        payload = state.platform.get_authenticated_filings(
            symbol,
            exchange=exchange,
            filing_types=parsed_types,
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
                "filings": None,
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
            "filings": payload.get("filings"),
            "provenance": payload.get("provenance"),
            "attempted_provider_ids": payload.get("attempted_provider_ids"),
            "message": None,
        }
    )


@router.get("/filings/health")
def filings_health(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Authenticated filings provider group health."""
    return {
        "ok": True,
        "providers": state.platform.filings_health(),
    }
