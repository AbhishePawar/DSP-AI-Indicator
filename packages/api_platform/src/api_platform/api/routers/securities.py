"""Provider-neutral Security Master routes (SIMPLE-WEB-04)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["securities"])


@router.get("/securities/search")
def securities_search(
    q: str = Query(..., min_length=1, max_length=128),
    exchange: str | None = Query(None, max_length=32),
    limit: int = Query(25, ge=1, le=50),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Search the official Security Master by ticker, name, or alias.

    Returns official listings (ISIN + MIC). Never guesses a listing.
    Vendor-shaped keys such as ``NSE_EQ|…`` are rejected.
    """
    payload = state.platform.search_securities(
        q, exchange=exchange, limit=limit
    )
    return JSONResponse(payload)


@router.get("/securities/resolve")
def securities_resolve(
    q: str = Query(..., min_length=1, max_length=128),
    exchange: str | None = Query(None, max_length=32),
    isin: str | None = Query(None, max_length=16),
    mic: str | None = Query(None, max_length=8),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Resolve a query to exactly one Security Master identity or fail explicitly."""
    payload = state.platform.resolve_security_identity(
        q, exchange=exchange, isin=isin, mic=mic
    )
    return JSONResponse(payload)


@router.get("/securities/health")
def securities_health(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    from dsp_platform.security_master import security_master_authority

    return {
        "ok": True,
        "authority": security_master_authority(),
        "provider": "official_exchange_master",
    }
