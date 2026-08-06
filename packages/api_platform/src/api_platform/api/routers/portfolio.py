"""Portfolio persistence routes (RC1 Milestone 3).

Thin, additive, authenticated routes over ``dsp_platform``'s Portfolio
Store façade — server-side replacement for browser-only ``localStorage``
Portfolio/Holdings/Transactions/Watchlist. Every route requires the
existing institutional auth (``get_current_user_id`` — EPIC-A009, no new
auth scheme) and enforces ownership via ``user_id``. No business logic,
analytics, or valuation here — see ``/portfolio/analytics/*`` for that.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import ApiState, get_api_state, get_current_user_id
from portfolio_store import ForbiddenError, NotFoundError, ValidationError

router = APIRouter(tags=["portfolio-store"])


def _error_response(exc: Exception) -> JSONResponse:
    if isinstance(exc, NotFoundError):
        status = 404
    elif isinstance(exc, ForbiddenError):
        status = 403
    elif isinstance(exc, ValidationError):
        status = 400
    else:
        status = 503
    return JSONResponse(
        status_code=status,
        content={"ok": False, "error": str(exc), "message": "Data unavailable."},
    )


class CreatePortfolioRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    is_default: bool | None = None
    benchmark_symbol: str | None = Field(None, max_length=32)
    metadata: dict[str, Any] | None = None


class UpdatePortfolioRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    is_default: bool | None = None
    metadata: dict[str, Any] | None = None


class SetBenchmarkRequest(BaseModel):
    benchmark_symbol: str | None = Field(None, max_length=32)


class UpsertHoldingRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    weight: float = Field(..., ge=0)
    units: float | None = None
    cost_basis_per_unit: float | None = None
    purchase_date: str | None = None
    sector: str | None = None
    country: str | None = None
    exchange: str | None = None
    value_score: float | None = None
    quality_score: float | None = None
    momentum_score: float | None = None
    size_score: float | None = None
    volatility_score: float | None = None


class RecordTransactionRequest(BaseModel):
    transaction_type: str = Field(..., min_length=1, max_length=32)
    transaction_date: str = Field(..., min_length=1, max_length=32)
    symbol: str | None = Field(None, max_length=32)
    quantity: float | None = None
    price: float | None = None
    amount: float | None = None
    currency: str = Field("USD", max_length=8)
    notes: str | None = Field(None, max_length=2000)


class AddWatchlistSymbolRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    label: str | None = Field(None, max_length=128)


class MigrateLocalPortfolioRequest(BaseModel):
    name: str = Field("My Portfolio", min_length=1, max_length=200)
    holdings: list[dict[str, Any]] | None = None
    watchlist: list[dict[str, Any]] | None = None
    benchmark_symbol: str | None = Field(None, max_length=32)


# -- Schema / discovery (registered before /{portfolio_id} for routing) -----


@router.get("/portfolio/schema")
def portfolio_schema(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "schema": state.platform.portfolio_store_schema()}


@router.post("/portfolio/migrate")
def migrate_local_portfolio(
    body: MigrateLocalPortfolioRequest,
    state: ApiState = Depends(get_api_state),
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    """Server-side half of the local -> server migration strategy.

    Idempotent: if the user already has a default portfolio, the supplied
    local snapshot is ignored and ``migrated: false`` is returned — the
    server is the source of truth once it has data, and the caller's local
    copy is never assumed stale. Never deletes anything client-side; the
    frontend keeps its local copy until this call reports success.
    """
    try:
        result = state.platform.migrate_local_portfolio(
            user_id=user_id,
            name=body.name,
            holdings=body.holdings,
            watchlist=body.watchlist,
            benchmark_symbol=body.benchmark_symbol,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


# -- Portfolio CRUD -----------------------------------------------------------


@router.get("/portfolio")
def list_portfolios(
    state: ApiState = Depends(get_api_state),
    user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    return {"ok": True, "result": state.platform.list_portfolios(user_id=user_id)}


@router.post("/portfolio")
def create_portfolio(
    body: CreatePortfolioRequest,
    state: ApiState = Depends(get_api_state),
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    try:
        result = state.platform.create_portfolio(
            user_id=user_id,
            name=body.name,
            is_default=body.is_default,
            benchmark_symbol=body.benchmark_symbol,
            metadata=body.metadata,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/portfolio/{portfolio_id}")
def get_portfolio(
    portfolio_id: str,
    state: ApiState = Depends(get_api_state),
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    try:
        result = state.platform.get_portfolio(portfolio_id, user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.put("/portfolio/{portfolio_id}")
def update_portfolio(
    portfolio_id: str,
    body: UpdatePortfolioRequest,
    state: ApiState = Depends(get_api_state),
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    try:
        result = state.platform.update_portfolio(
            portfolio_id,
            user_id=user_id,
            name=body.name,
            is_default=body.is_default,
            metadata=body.metadata,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.delete("/portfolio/{portfolio_id}")
def delete_portfolio(
    portfolio_id: str,
    state: ApiState = Depends(get_api_state),
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    try:
        deleted = state.platform.delete_portfolio(portfolio_id, user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "result": {"deleted": deleted}, "message": None})


@router.put("/portfolio/{portfolio_id}/benchmark")
def set_portfolio_benchmark(
    portfolio_id: str,
    body: SetBenchmarkRequest,
    state: ApiState = Depends(get_api_state),
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    try:
        result = state.platform.set_portfolio_benchmark(
            portfolio_id, user_id=user_id, benchmark_symbol=body.benchmark_symbol
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


# -- Holdings ------------------------------------------------------------------


@router.get("/portfolio/{portfolio_id}/holdings")
def list_portfolio_holdings(
    portfolio_id: str,
    state: ApiState = Depends(get_api_state),
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    try:
        result = state.platform.list_portfolio_holdings(portfolio_id, user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.post("/portfolio/{portfolio_id}/holdings")
def upsert_portfolio_holding(
    portfolio_id: str,
    body: UpsertHoldingRequest,
    state: ApiState = Depends(get_api_state),
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    try:
        result = state.platform.upsert_portfolio_holding(
            portfolio_id,
            user_id=user_id,
            symbol=body.symbol,
            weight=body.weight,
            units=body.units,
            cost_basis_per_unit=body.cost_basis_per_unit,
            purchase_date=body.purchase_date,
            sector=body.sector,
            country=body.country,
            exchange=body.exchange,
            value_score=body.value_score,
            quality_score=body.quality_score,
            momentum_score=body.momentum_score,
            size_score=body.size_score,
            volatility_score=body.volatility_score,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.delete("/portfolio/{portfolio_id}/holdings/{symbol}")
def remove_portfolio_holding(
    portfolio_id: str,
    symbol: str,
    state: ApiState = Depends(get_api_state),
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    try:
        removed = state.platform.remove_portfolio_holding(
            portfolio_id, user_id=user_id, symbol=symbol
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "result": {"removed": removed}, "message": None})


# -- Transactions ---------------------------------------------------------------


@router.get("/portfolio/{portfolio_id}/transactions")
def list_portfolio_transactions(
    portfolio_id: str,
    symbol: str | None = None,
    limit: int = 200,
    state: ApiState = Depends(get_api_state),
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    try:
        result = state.platform.list_portfolio_transactions(
            portfolio_id, user_id=user_id, symbol=symbol, limit=limit
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.post("/portfolio/{portfolio_id}/transactions")
def record_portfolio_transaction(
    portfolio_id: str,
    body: RecordTransactionRequest,
    state: ApiState = Depends(get_api_state),
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    try:
        result = state.platform.record_portfolio_transaction(
            portfolio_id,
            user_id=user_id,
            transaction_type=body.transaction_type,
            transaction_date=body.transaction_date,
            symbol=body.symbol,
            quantity=body.quantity,
            price=body.price,
            amount=body.amount,
            currency=body.currency,
            notes=body.notes,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


# -- Watchlist ------------------------------------------------------------------


@router.get("/portfolio/{portfolio_id}/watchlist")
def list_portfolio_watchlist(
    portfolio_id: str,
    state: ApiState = Depends(get_api_state),
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    try:
        result = state.platform.list_portfolio_watchlist(portfolio_id, user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.post("/portfolio/{portfolio_id}/watchlist")
def add_portfolio_watchlist_symbol(
    portfolio_id: str,
    body: AddWatchlistSymbolRequest,
    state: ApiState = Depends(get_api_state),
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    try:
        result = state.platform.add_portfolio_watchlist_symbol(
            portfolio_id, user_id=user_id, symbol=body.symbol, label=body.label
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.delete("/portfolio/{portfolio_id}/watchlist/{symbol}")
def remove_portfolio_watchlist_symbol(
    portfolio_id: str,
    symbol: str,
    state: ApiState = Depends(get_api_state),
    user_id: str = Depends(get_current_user_id),
) -> JSONResponse:
    try:
        removed = state.platform.remove_portfolio_watchlist_symbol(
            portfolio_id, user_id=user_id, symbol=symbol
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, "result": {"removed": removed}, "message": None})
