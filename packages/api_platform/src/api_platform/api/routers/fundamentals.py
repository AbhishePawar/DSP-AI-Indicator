"""Additive authenticated financial statement routes (EPIC-D002)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["fundamentals"])


@router.get("/fundamentals/statements")
def financial_statements(
    symbol: str = Query(..., min_length=1, max_length=32),
    exchange: str | None = Query(None, max_length=32),
    period_type: str | None = Query(
        None, description="annual | quarterly | ttm (omit for all)"
    ),
    limit: int = Query(8, ge=1, le=40),
    include_restated: bool = Query(True),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Return authenticated financial statements (RS-003).

    Additive endpoint — does not alter ``/analyse``. Missing authenticated
    data returns HTTP 200 with ``available: false`` (never fabricated fields).
    Retrieval and validation only — no calculations.
    """
    try:
        payload = state.platform.get_authenticated_financial_statements(
            symbol,
            exchange=exchange,
            period_type=period_type,
            limit=limit,
            include_restated=include_restated,
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
                "periods": None,
                "identity": None,
                "provenance": None,
                "message": "Data unavailable.",
            }
        )

    return JSONResponse(
        {
            "ok": True,
            "available": True,
            "authenticated": True,
            "symbol": payload.get("identity", {}).get("symbol")
            if isinstance(payload.get("identity"), dict)
            else symbol.strip().upper(),
            "identity": payload.get("identity"),
            "reporting_currency": payload.get("reporting_currency"),
            "periods": payload.get("periods"),
            "provenance": payload.get("provenance"),
            "message": None,
        }
    )


@router.get("/fundamentals/resolve")
def resolve_company(
    symbol: str = Query(..., min_length=1, max_length=32),
    exchange: str | None = Query(None, max_length=32),
    select_listing: bool = Query(
        False,
        description=(
            "When true, run BSE-first/NSE-fallback before identity resolve. "
            "Default false preserves ticker-only U1 AMBIGUOUS behavior."
        ),
    ),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Resolve company identifiers via authenticated statement provider."""
    selected_exchange = exchange
    listing_payload = None
    if select_listing:
        try:
            listing_payload = state.platform.select_indian_listing(
                symbol, explicit_exchange=exchange
            )
        except Exception as exc:  # noqa: BLE001
            return JSONResponse(
                status_code=503,
                content={
                    "ok": False,
                    "available": False,
                    "symbol": symbol.strip().upper(),
                    "status": "UNAVAILABLE",
                    "error": str(exc),
                    "message": "Data unavailable.",
                },
            )
        listing_status = str(listing_payload.get("status") or "")
        if listing_status == "UNAVAILABLE":
            return JSONResponse(
                status_code=503,
                content={
                    "ok": False,
                    "available": False,
                    "symbol": listing_payload.get("symbol") or symbol.strip().upper(),
                    "status": listing_status,
                    "exchange": listing_payload.get("exchange"),
                    "isin": listing_payload.get("isin"),
                    "detail": listing_payload.get("detail"),
                    "identity": None,
                    "message": "Data unavailable.",
                },
            )
        if listing_status == "SELECTED":
            raw_exchange = listing_payload.get("exchange")
            selected_exchange = (
                str(raw_exchange).strip().upper()
                if isinstance(raw_exchange, str) and raw_exchange.strip()
                else None
            )
        elif listing_status in {"NOT_FOUND", "AMBIGUOUS"}:
            return JSONResponse(
                {
                    "ok": True,
                    "available": False,
                    "symbol": listing_payload.get("symbol") or symbol.strip().upper(),
                    "status": listing_status,
                    "exchange": listing_payload.get("exchange"),
                    "isin": listing_payload.get("isin"),
                    "detail": listing_payload.get("detail"),
                    "identity": None,
                    "message": "Data unavailable.",
                }
            )
        # NOT_APPLICABLE: do not remap US/other venues; keep caller exchange.
    try:
        identity = state.platform.resolve_company_identity(
            symbol, exchange=selected_exchange
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
    listing_fields = {}
    if listing_payload is not None:
        listing_fields = {
            "status": str(listing_payload.get("status") or ""),
            "exchange": selected_exchange
            if selected_exchange is not None
            else listing_payload.get("exchange"),
            "isin": listing_payload.get("isin"),
            "detail": listing_payload.get("detail"),
        }
    if identity is None:
        body = {
            "ok": True,
            "available": False,
            "symbol": symbol.strip().upper(),
            "identity": None,
            "message": "Data unavailable.",
        }
        body.update(listing_fields)
        return JSONResponse(body)
    body = {
        "ok": True,
        "available": True,
        "symbol": identity.get("symbol"),
        "identity": identity,
        "message": None,
    }
    body.update(listing_fields)
    return JSONResponse(body)


@router.get("/fundamentals/health")
def fundamentals_health(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Authenticated financial statement provider health."""
    return {
        "ok": True,
        "provider": state.platform.financial_statement_health(),
    }
