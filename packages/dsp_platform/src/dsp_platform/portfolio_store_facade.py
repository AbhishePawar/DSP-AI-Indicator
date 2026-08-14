"""Portfolio Store façade for DSPPlatform (RC1 Milestone 3).

Thin wrapper over ``portfolio_store`` — server-side, user-owned persistence
for Portfolio/Holdings/Transactions/Watchlist, replacing browser-only
``localStorage``. No analytics/valuation/scoring lives here — that remains
exclusively ``dsp_platform.portfolio_analytics`` /
``dsp_platform.portfolio_intelligence``. Named ``*_facade`` (not
``dsp_platform.portfolio_store``) to avoid any name confusion with the
``portfolio_store`` package itself, matching the existing
``dsp_platform.auth_facade`` convention.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from portfolio_store import get_portfolio_service, reset_portfolio_service_for_tests

__all__ = [
    "add_portfolio_watchlist_symbol",
    "configure_portfolio_store",
    "create_portfolio",
    "delete_portfolio",
    "get_default_portfolio",
    "get_portfolio",
    "list_portfolio_holdings",
    "list_portfolio_transactions",
    "list_portfolio_watchlist",
    "list_portfolios",
    "migrate_local_portfolio",
    "portfolio_store_schema",
    "record_portfolio_transaction",
    "remove_portfolio_holding",
    "remove_portfolio_watchlist_symbol",
    "reset_portfolio_store_for_tests",
    "set_portfolio_benchmark",
    "update_portfolio",
    "upsert_portfolio_holding",
]


def configure_portfolio_store(*, database: Any | None = None) -> None:
    """Wire a durable ``DatabasePort`` into the process-local singleton.

    Safe to call multiple times / with ``database=None`` — the underlying
    singleton factory only honors the first call, mirroring
    ``enterprise.get_enterprise_service``.
    """
    get_portfolio_service(database=database)


def portfolio_store_schema() -> dict[str, Any]:
    return get_portfolio_service().schema()


def create_portfolio(
    *,
    user_id: str,
    name: str,
    is_default: bool | None = None,
    benchmark_symbol: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    portfolio_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    return get_portfolio_service().create_portfolio(
        user_id=user_id,
        name=name,
        is_default=is_default,
        benchmark_symbol=benchmark_symbol,
        metadata=metadata,
        portfolio_id=portfolio_id,
        created_at=created_at,
    )


def list_portfolios(*, user_id: str) -> list[dict[str, Any]]:
    return get_portfolio_service().list_portfolios(user_id=user_id)


def get_portfolio(portfolio_id: str, *, user_id: str) -> dict[str, Any]:
    return get_portfolio_service().get_portfolio(portfolio_id, user_id=user_id)


def get_default_portfolio(*, user_id: str) -> dict[str, Any] | None:
    return get_portfolio_service().get_default_portfolio(user_id=user_id)


def update_portfolio(
    portfolio_id: str,
    *,
    user_id: str,
    name: str | None = None,
    is_default: bool | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """General portfolio metadata update. Benchmark changes are a dedicated
    concern — use ``set_portfolio_benchmark`` so "omitted" vs. "explicitly
    cleared to None" is never ambiguous."""
    return get_portfolio_service().update_portfolio(
        portfolio_id,
        user_id=user_id,
        name=name,
        is_default=is_default,
        metadata=metadata,
    )


def delete_portfolio(portfolio_id: str, *, user_id: str) -> bool:
    return get_portfolio_service().delete_portfolio(portfolio_id, user_id=user_id)


def set_portfolio_benchmark(
    portfolio_id: str, *, user_id: str, benchmark_symbol: str | None
) -> dict[str, Any]:
    return get_portfolio_service().set_benchmark(
        portfolio_id, user_id=user_id, benchmark_symbol=benchmark_symbol
    )


def list_portfolio_holdings(portfolio_id: str, *, user_id: str) -> list[dict[str, Any]]:
    return get_portfolio_service().list_holdings(portfolio_id, user_id=user_id)


def upsert_portfolio_holding(
    portfolio_id: str,
    *,
    user_id: str,
    symbol: str,
    weight: float,
    units: float | None = None,
    cost_basis_per_unit: float | None = None,
    purchase_date: str | None = None,
    sector: str | None = None,
    country: str | None = None,
    exchange: str | None = None,
    value_score: float | None = None,
    quality_score: float | None = None,
    momentum_score: float | None = None,
    size_score: float | None = None,
    volatility_score: float | None = None,
) -> dict[str, Any]:
    return get_portfolio_service().upsert_holding(
        portfolio_id,
        user_id=user_id,
        symbol=symbol,
        weight=weight,
        units=units,
        cost_basis_per_unit=cost_basis_per_unit,
        purchase_date=purchase_date,
        sector=sector,
        country=country,
        exchange=exchange,
        value_score=value_score,
        quality_score=quality_score,
        momentum_score=momentum_score,
        size_score=size_score,
        volatility_score=volatility_score,
    )


def remove_portfolio_holding(portfolio_id: str, *, user_id: str, symbol: str) -> bool:
    return get_portfolio_service().remove_holding(portfolio_id, user_id=user_id, symbol=symbol)


def record_portfolio_transaction(
    portfolio_id: str,
    *,
    user_id: str,
    transaction_type: str,
    transaction_date: str,
    symbol: str | None = None,
    quantity: float | None = None,
    price: float | None = None,
    amount: float | None = None,
    currency: str = "USD",
    notes: str | None = None,
) -> dict[str, Any]:
    return get_portfolio_service().record_transaction(
        portfolio_id,
        user_id=user_id,
        transaction_type=transaction_type,
        transaction_date=transaction_date,
        symbol=symbol,
        quantity=quantity,
        price=price,
        amount=amount,
        currency=currency,
        notes=notes,
    )


def list_portfolio_transactions(
    portfolio_id: str, *, user_id: str, symbol: str | None = None, limit: int = 200
) -> list[dict[str, Any]]:
    return get_portfolio_service().list_transactions(
        portfolio_id, user_id=user_id, symbol=symbol, limit=limit
    )


def list_portfolio_watchlist(portfolio_id: str, *, user_id: str) -> list[dict[str, Any]]:
    return get_portfolio_service().list_watchlist(portfolio_id, user_id=user_id)


def add_portfolio_watchlist_symbol(
    portfolio_id: str, *, user_id: str, symbol: str, label: str | None = None
) -> dict[str, Any]:
    return get_portfolio_service().add_watchlist_symbol(
        portfolio_id, user_id=user_id, symbol=symbol, label=label
    )


def remove_portfolio_watchlist_symbol(
    portfolio_id: str, *, user_id: str, symbol: str
) -> bool:
    return get_portfolio_service().remove_watchlist_symbol(
        portfolio_id, user_id=user_id, symbol=symbol
    )


def migrate_local_portfolio(
    *,
    user_id: str,
    name: str = "My Portfolio",
    holdings: list[Mapping[str, Any]] | None = None,
    watchlist: list[Mapping[str, Any]] | None = None,
    benchmark_symbol: str | None = None,
) -> dict[str, Any]:
    return get_portfolio_service().migrate_local_portfolio(
        user_id=user_id,
        name=name,
        holdings=holdings,
        watchlist=watchlist,
        benchmark_symbol=benchmark_symbol,
    )


def reset_portfolio_store_for_tests(service: Any | None = None) -> None:
    reset_portfolio_service_for_tests(service)
