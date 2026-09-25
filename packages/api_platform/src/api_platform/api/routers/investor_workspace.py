"""Investor workspace routes — Figma Dashboard · Portfolio · Research Hub ·
Research Canvas · Client Profile.

All routes are per-user (P0-05: identity from server-validated JWT only).
Values returned are user records joined with authenticated quotes and the
coverage registry; all arithmetic lives in ``dsp_platform.investor_workspace``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from api_platform.api.dependencies import (
    ApiState,
    get_api_state,
    require_authenticated_actor,
)

router = APIRouter(tags=["investor-workspace"])


def _validation_error(exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"ok": False, "error": str(exc), "message": "Unable to save."},
    )


def _is_validation_error(exc: Exception) -> bool:
    return type(exc).__name__ == "WorkspaceValidationError" or isinstance(exc, ValueError)


# -- Watchlist ----------------------------------------------------------------


class WatchlistAddRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    exchange: str | None = Field(None, max_length=32)


@router.get("/workspace/watchlist")
def get_watchlist(
    request: Request, state: ApiState = Depends(get_api_state)
) -> dict[str, Any]:
    actor = require_authenticated_actor(request)
    return state.platform.investor_workspace().watchlist_view(actor["user_id"])


@router.post("/workspace/watchlist")
def add_watchlist(
    body: WatchlistAddRequest,
    request: Request,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    actor = require_authenticated_actor(request)
    ws = state.platform.investor_workspace()
    try:
        ws.store.add_watchlist(actor["user_id"], body.symbol, exchange=body.exchange)
    except Exception as exc:  # noqa: BLE001
        if _is_validation_error(exc):
            return _validation_error(exc)
        raise
    return JSONResponse(ws.watchlist_view(actor["user_id"]))


@router.delete("/workspace/watchlist/{symbol}")
def remove_watchlist(
    symbol: str, request: Request, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    actor = require_authenticated_actor(request)
    ws = state.platform.investor_workspace()
    try:
        removed = ws.store.remove_watchlist(actor["user_id"], symbol)
    except Exception as exc:  # noqa: BLE001
        if _is_validation_error(exc):
            return _validation_error(exc)
        raise
    view = ws.watchlist_view(actor["user_id"])
    view["removed"] = removed
    return JSONResponse(view)


# -- Portfolio holdings -------------------------------------------------------


class HoldingUpsertRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    quantity: float = Field(..., gt=0)
    average_cost: float = Field(..., gt=0)
    exchange: str | None = Field(None, max_length=32)
    sector: str | None = Field(None, max_length=120)


@router.get("/workspace/portfolio")
def get_portfolio(
    request: Request, state: ApiState = Depends(get_api_state)
) -> dict[str, Any]:
    actor = require_authenticated_actor(request)
    return state.platform.investor_workspace().portfolio_view(actor["user_id"])


@router.post("/workspace/portfolio/holdings")
def upsert_holding(
    body: HoldingUpsertRequest,
    request: Request,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    actor = require_authenticated_actor(request)
    ws = state.platform.investor_workspace()
    try:
        ws.store.upsert_holding(
            actor["user_id"],
            symbol=body.symbol,
            quantity=body.quantity,
            average_cost=body.average_cost,
            exchange=body.exchange,
            sector=body.sector,
        )
    except Exception as exc:  # noqa: BLE001
        if _is_validation_error(exc):
            return _validation_error(exc)
        raise
    return JSONResponse(ws.portfolio_view(actor["user_id"]))


@router.delete("/workspace/portfolio/holdings/{symbol}")
def remove_holding(
    symbol: str, request: Request, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    actor = require_authenticated_actor(request)
    ws = state.platform.investor_workspace()
    try:
        removed = ws.store.remove_holding(actor["user_id"], symbol)
    except Exception as exc:  # noqa: BLE001
        if _is_validation_error(exc):
            return _validation_error(exc)
        raise
    view = ws.portfolio_view(actor["user_id"])
    view["removed"] = removed
    return JSONResponse(view)


@router.delete("/workspace/portfolio/holdings")
def clear_holdings(
    request: Request, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    actor = require_authenticated_actor(request)
    ws = state.platform.investor_workspace()
    cleared = ws.store.clear_holdings(actor["user_id"])
    view = ws.portfolio_view(actor["user_id"])
    view["cleared"] = cleared
    return JSONResponse(view)


# -- Dashboard overview -------------------------------------------------------


@router.get("/workspace/dashboard")
def dashboard_overview(
    request: Request, state: ApiState = Depends(get_api_state)
) -> dict[str, Any]:
    actor = require_authenticated_actor(request)
    return state.platform.investor_workspace().dashboard_overview(actor["user_id"])


# -- Saved research (Research Hub) --------------------------------------------


class SavedResearchRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    title: str = Field(..., min_length=1, max_length=200)
    tags: list[str] = Field(default_factory=list)
    turns: int | None = Field(None, ge=0)
    research_id: str | None = Field(None, max_length=128)
    saved_id: str | None = Field(None, max_length=128)


@router.get("/workspace/research/saved")
def list_saved_research(
    request: Request, state: ApiState = Depends(get_api_state)
) -> dict[str, Any]:
    actor = require_authenticated_actor(request)
    items = state.platform.investor_workspace().store.list_saved_research(actor["user_id"])
    return {"ok": True, "items": items, "count": len(items)}


@router.post("/workspace/research/saved")
def save_research(
    body: SavedResearchRequest,
    request: Request,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    actor = require_authenticated_actor(request)
    store = state.platform.investor_workspace().store
    try:
        record = store.save_research(
            actor["user_id"],
            symbol=body.symbol,
            title=body.title,
            tags=body.tags,
            turns=body.turns,
            research_id=body.research_id,
            saved_id=body.saved_id,
        )
    except Exception as exc:  # noqa: BLE001
        if _is_validation_error(exc):
            return _validation_error(exc)
        raise
    return JSONResponse({"ok": True, "item": record})


@router.delete("/workspace/research/saved/{saved_id}")
def delete_saved_research(
    saved_id: str, request: Request, state: ApiState = Depends(get_api_state)
) -> dict[str, Any]:
    actor = require_authenticated_actor(request)
    store = state.platform.investor_workspace().store
    return {"ok": True, "removed": store.delete_saved_research(actor["user_id"], saved_id)}


# -- Research canvas ----------------------------------------------------------


class CanvasSaveRequest(BaseModel):
    title: str = Field("Untitled canvas", max_length=200)
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    canvas_id: str | None = Field(None, max_length=128)


@router.get("/workspace/research/canvas")
def list_canvases(
    request: Request, state: ApiState = Depends(get_api_state)
) -> dict[str, Any]:
    actor = require_authenticated_actor(request)
    items = state.platform.investor_workspace().store.list_canvases(actor["user_id"])
    return {"ok": True, "items": items, "count": len(items)}


@router.get("/workspace/research/canvas/{canvas_id}")
def get_canvas(
    canvas_id: str, request: Request, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    actor = require_authenticated_actor(request)
    item = state.platform.investor_workspace().store.get_canvas(actor["user_id"], canvas_id)
    if item is None:
        return JSONResponse(status_code=404, content={"ok": False, "error": "canvas not found"})
    return JSONResponse({"ok": True, "item": item})


@router.post("/workspace/research/canvas")
def save_canvas(
    body: CanvasSaveRequest,
    request: Request,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    actor = require_authenticated_actor(request)
    store = state.platform.investor_workspace().store
    try:
        record = store.save_canvas(
            actor["user_id"], title=body.title, blocks=body.blocks, canvas_id=body.canvas_id
        )
    except Exception as exc:  # noqa: BLE001
        if _is_validation_error(exc):
            return _validation_error(exc)
        raise
    return JSONResponse({"ok": True, "item": record})


@router.delete("/workspace/research/canvas/{canvas_id}")
def delete_canvas(
    canvas_id: str, request: Request, state: ApiState = Depends(get_api_state)
) -> dict[str, Any]:
    actor = require_authenticated_actor(request)
    store = state.platform.investor_workspace().store
    return {"ok": True, "removed": store.delete_canvas(actor["user_id"], canvas_id)}


# -- Client financial profile + Financial Health Score ------------------------


def _account_fields(actor: dict[str, Any]) -> dict[str, Any]:
    user = actor.get("user") if isinstance(actor.get("user"), dict) else {}
    return {
        "name": user.get("name") or user.get("full_name") or user.get("display_name"),
        "email": user.get("email"),
        "mobile": user.get("mobile") or user.get("phone"),
    }


@router.get("/workspace/profile")
def get_profile(
    request: Request, state: ApiState = Depends(get_api_state)
) -> dict[str, Any]:
    actor = require_authenticated_actor(request)
    return state.platform.investor_workspace().profile_view(
        actor["user_id"], account=_account_fields(actor)
    )


class ProfileSaveRequest(BaseModel):
    """Figma Client Profile fields. Extra keys are ignored, not invented."""

    model_config = ConfigDict(extra="ignore")

    full_name: str | None = Field(None, max_length=200)
    email: str | None = Field(None, max_length=200)
    mobile: str | None = Field(None, max_length=200)
    age: int | None = Field(None, ge=0, le=3000)
    city: str | None = Field(None, max_length=200)
    occupation: str | None = Field(None, max_length=200)
    dependents: int | None = Field(None, ge=0, le=3000)
    monthly_income: float | None = Field(None, ge=0)
    monthly_expenses: float | None = Field(None, ge=0)
    monthly_emi: float | None = Field(None, ge=0)
    other_monthly_income: float | None = Field(None, ge=0)
    total_savings: float | None = Field(None, ge=0)
    total_investments: float | None = Field(None, ge=0)
    emergency_fund: float | None = Field(None, ge=0)
    outstanding_loans: float | None = Field(None, ge=0)
    credit_card_outstanding: float | None = Field(None, ge=0)
    health_insurance: float | None = Field(None, ge=0)
    life_insurance: float | None = Field(None, ge=0)
    no_outstanding_debt: bool | None = None
    primary_goal: str | None = Field(None, max_length=64)
    target_amount: float | None = Field(None, ge=0)
    target_year: int | None = Field(None, ge=0, le=3000)
    investments: list[dict[str, Any]] | None = None


@router.put("/workspace/profile")
def put_profile(
    body: ProfileSaveRequest,
    request: Request,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    actor = require_authenticated_actor(request)
    ws = state.platform.investor_workspace()
    try:
        view = ws.save_profile(
            actor["user_id"], body.model_dump(), account=_account_fields(actor)
        )
    except Exception as exc:  # noqa: BLE001
        if _is_validation_error(exc):
            return _validation_error(exc)
        raise
    return JSONResponse(view)


@router.post("/workspace/profile/score")
def calculate_score(
    request: Request,
    state: ApiState = Depends(get_api_state),
    persist: bool = Query(False),
) -> dict[str, Any]:
    """Explicit 'Calculate My Financial Health Score' action (idempotent)."""
    actor = require_authenticated_actor(request)
    _ = persist  # score is pure; nothing further to persist server-side
    return state.platform.investor_workspace().profile_view(
        actor["user_id"], account=_account_fields(actor)
    )
