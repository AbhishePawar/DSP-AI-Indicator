"""Additive authenticated corporate actions routes (EPIC-D003)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["corporate-actions"])


@router.get("/corporate-actions")
def corporate_actions(
    symbol: str = Query(..., min_length=1, max_length=32),
    exchange: str | None = Query(None, max_length=32),
    action_type: str | None = Query(
        None,
        description=(
            "stock_split|bonus_issue|dividend|rights_issue|buyback|"
            "merger|demerger|symbol_change|share_capital_change"
        ),
    ),
    start_date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    end_date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=200),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Return authenticated corporate actions.

    Additive endpoint — does not alter ``/analyse``. Missing authenticated
    data returns HTTP 200 with ``available: false``. Retrieval/validation only.
    """
    try:
        payload = state.platform.get_authenticated_corporate_actions(
            symbol,
            exchange=exchange,
            action_type=action_type,
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
                "events": None,
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
            "events": payload.get("events"),
            "provenance": payload.get("provenance"),
            "message": None,
        }
    )


@router.get("/corporate-actions/health")
def corporate_actions_health(
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    """Authenticated corporate actions provider health."""
    return {
        "ok": True,
        "provider": state.platform.corporate_actions_health(),
    }
