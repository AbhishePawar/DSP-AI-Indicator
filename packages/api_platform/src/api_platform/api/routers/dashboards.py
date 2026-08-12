"""RC1 Milestone 6 — thin enterprise role dashboard routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["enterprise-dashboards"])


def _parse_csv(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _dashboard_response(
    state: ApiState,
    role: str,
    *,
    portfolio_id: str | None,
    symbols: str | None,
    watchlist_id: str | None,
    client_portfolio_ids: str | None,
    workflow_id: str | None,
) -> JSONResponse:
    try:
        result = state.platform.get_enterprise_dashboard(
            role,
            portfolio_id=portfolio_id,
            symbols=_parse_csv(symbols),
            watchlist_id=watchlist_id,
            client_portfolio_ids=_parse_csv(client_portfolio_ids),
            workflow_id=workflow_id,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/dashboards/schema")
def dashboards_schema(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "schema": state.platform.enterprise_dashboard_schema()}


@router.get("/dashboards/research")
def dashboard_research(
    portfolio_id: str | None = Query(None, max_length=128),
    symbols: str | None = Query(None, max_length=512),
    watchlist_id: str | None = Query(None, max_length=128),
    workflow_id: str | None = Query(None, max_length=128),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    return _dashboard_response(
        state,
        "research",
        portfolio_id=portfolio_id,
        symbols=symbols,
        watchlist_id=watchlist_id,
        client_portfolio_ids=None,
        workflow_id=workflow_id,
    )


@router.get("/dashboards/portfolio-manager")
def dashboard_portfolio_manager(
    portfolio_id: str | None = Query(None, max_length=128),
    symbols: str | None = Query(None, max_length=512),
    watchlist_id: str | None = Query(None, max_length=128),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    return _dashboard_response(
        state,
        "portfolio-manager",
        portfolio_id=portfolio_id,
        symbols=symbols,
        watchlist_id=watchlist_id,
        client_portfolio_ids=None,
        workflow_id=None,
    )


@router.get("/dashboards/wealth-advisor")
def dashboard_wealth_advisor(
    portfolio_id: str | None = Query(None, max_length=128),
    symbols: str | None = Query(None, max_length=512),
    client_portfolio_ids: str | None = Query(None, max_length=1024),
    workflow_id: str | None = Query(None, max_length=128),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    return _dashboard_response(
        state,
        "wealth-advisor",
        portfolio_id=portfolio_id,
        symbols=symbols,
        watchlist_id=None,
        client_portfolio_ids=client_portfolio_ids,
        workflow_id=workflow_id,
    )


@router.get("/dashboards/family-office")
def dashboard_family_office(
    portfolio_id: str | None = Query(None, max_length=128),
    symbols: str | None = Query(None, max_length=512),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    return _dashboard_response(
        state,
        "family-office",
        portfolio_id=portfolio_id,
        symbols=symbols,
        watchlist_id=None,
        client_portfolio_ids=None,
        workflow_id=None,
    )


@router.get("/dashboards/executive")
def dashboard_executive(
    workflow_id: str | None = Query(None, max_length=128),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    return _dashboard_response(
        state,
        "executive",
        portfolio_id=None,
        symbols=None,
        watchlist_id=None,
        client_portfolio_ids=None,
        workflow_id=workflow_id,
    )
