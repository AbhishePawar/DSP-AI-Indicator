"""Authenticated insider trading façade for DSPPlatform (Data Connector Framework).

Thin wrapper over ``data_engine.insider_trading``. Builds the default
multi-provider registry from environment configuration, wraps every
registered provider in a resilient ``InsiderTradingService``, and
orchestrates automatic failover across them via ``FailoverGroup``. No
scoring or business logic (e.g. "cluster buying" signals) lives here.
"""

from __future__ import annotations

from datetime import date
from threading import Lock
from typing import Any

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine import (
    FailoverGroup,
    InsiderTradingQuery,
    InsiderTradingService,
    build_default_insider_trading_registry_from_env,
)

__all__ = [
    "get_authenticated_insider_activity",
    "insider_trading_health",
    "insider_trading_metrics",
    "reset_insider_trading_service_for_tests",
]

_LOCK = Lock()
_GROUP: FailoverGroup[InsiderTradingService, InsiderTradingQuery, Any] | None = None
_SERVICES: tuple[InsiderTradingService, ...] = ()


def _make_group(
    services: tuple[InsiderTradingService, ...],
) -> FailoverGroup[InsiderTradingService, InsiderTradingQuery, Any]:
    return FailoverGroup(
        services,
        call=lambda service, query: service.get_insider_activity(query),
        domain="insider_trading",
        operation="get_insider_activity",
    )


def _group() -> FailoverGroup[InsiderTradingService, InsiderTradingQuery, Any]:
    global _GROUP, _SERVICES
    with _LOCK:
        if _GROUP is None:
            registry = build_default_insider_trading_registry_from_env()
            _SERVICES = tuple(InsiderTradingService(provider) for provider in registry.ordered())
            _GROUP = _make_group(_SERVICES)
        return _GROUP


def reset_insider_trading_service_for_tests(
    services: tuple[InsiderTradingService, ...] | None = None,
) -> None:
    """Replace or clear the process-local insider trading failover group (tests only)."""
    global _GROUP, _SERVICES
    with _LOCK:
        if services is None:
            _GROUP = None
            _SERVICES = ()
        else:
            _SERVICES = services
            _GROUP = _make_group(services)


def get_authenticated_insider_activity(
    symbol: str,
    *,
    exchange: str | None = None,
    currency: str = "USD",
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    limit: int = 50,
) -> dict[str, Any] | None:
    """Fetch authenticated insider trading activity as a public dict, or ``None``."""
    instrument = Instrument(
        symbol=symbol.strip().upper(),
        asset_class=AssetClass.EQUITY,
        currency=currency,
        exchange=exchange,
    )

    def _d(value: date | str | None) -> date | None:
        if value is None or value == "":
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value)[:10])

    query = InsiderTradingQuery(
        instrument=instrument,
        start_date=_d(start_date),
        end_date=_d(end_date),
        limit=limit,
    )
    outcome = _group().call(query, symbol=instrument.symbol)
    if outcome is None:
        return None
    payload = outcome.result.to_public_dict()
    payload["attempted_provider_ids"] = list(outcome.attempted_provider_ids)
    return payload


def insider_trading_health() -> dict[str, Any]:
    healths = _group().health()
    return {
        "providers": [h.to_dict() for h in healths],
        "healthy": any(h.healthy for h in healths) if healths else False,
    }


def insider_trading_metrics() -> dict[str, Any]:
    _group()
    with _LOCK:
        services = _SERVICES
    return {service.provider_id: service.metrics.snapshot() for service in services}
