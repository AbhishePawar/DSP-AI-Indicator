"""Authenticated regulatory filings façade for DSPPlatform (Data Connector Framework).

Thin wrapper over ``data_engine.filings``. Builds the default multi-provider
registry from environment configuration, wraps every registered provider in
a resilient ``FilingsService``, and orchestrates automatic failover across
them via ``FailoverGroup``. No scoring or business logic lives here.
"""

from __future__ import annotations

from datetime import date
from threading import Lock
from typing import Any

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine import (
    FailoverGroup,
    FilingsQuery,
    FilingsService,
    build_default_filings_registry_from_env,
)

__all__ = [
    "get_authenticated_filings",
    "filings_health",
    "filings_metrics",
    "reset_filings_service_for_tests",
]

_LOCK = Lock()
_GROUP: FailoverGroup[FilingsService, FilingsQuery, Any] | None = None
_SERVICES: tuple[FilingsService, ...] = ()


def _make_group(
    services: tuple[FilingsService, ...],
) -> FailoverGroup[FilingsService, FilingsQuery, Any]:
    return FailoverGroup(
        services,
        call=lambda service, query: service.get_filings(query),
        domain="filings",
        operation="get_filings",
    )


def _group() -> FailoverGroup[FilingsService, FilingsQuery, Any]:
    global _GROUP, _SERVICES
    with _LOCK:
        if _GROUP is None:
            registry = build_default_filings_registry_from_env()
            _SERVICES = tuple(FilingsService(provider) for provider in registry.ordered())
            _GROUP = _make_group(_SERVICES)
        return _GROUP


def reset_filings_service_for_tests(
    services: tuple[FilingsService, ...] | None = None,
) -> None:
    """Replace or clear the process-local filings failover group (tests only)."""
    global _GROUP, _SERVICES
    with _LOCK:
        if services is None:
            _GROUP = None
            _SERVICES = ()
        else:
            _SERVICES = services
            _GROUP = _make_group(services)


def get_authenticated_filings(
    symbol: str,
    *,
    exchange: str | None = None,
    currency: str = "USD",
    filing_types: tuple[str, ...] = (),
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    limit: int = 50,
) -> dict[str, Any] | None:
    """Fetch authenticated regulatory filings as a public dict, or ``None``."""
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

    query = FilingsQuery(
        instrument=instrument,
        filing_types=tuple(filing_types),
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


def filings_health() -> dict[str, Any]:
    healths = _group().health()
    return {
        "providers": [h.to_dict() for h in healths],
        "healthy": any(h.healthy for h in healths) if healths else False,
    }


def filings_metrics() -> dict[str, Any]:
    _group()
    with _LOCK:
        services = _SERVICES
    return {service.provider_id: service.metrics.snapshot() for service in services}
