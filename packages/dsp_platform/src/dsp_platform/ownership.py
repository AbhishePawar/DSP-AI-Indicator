"""Authenticated shareholding/ownership façade for DSPPlatform (Data Connector Framework).

Thin wrapper over ``data_engine.ownership``. Builds the default multi-provider
registry from environment configuration, wraps every registered provider in
a resilient ``OwnershipService``, and orchestrates automatic failover across
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
    OwnershipQuery,
    OwnershipService,
    build_default_ownership_registry_from_env,
)

__all__ = [
    "get_authenticated_ownership",
    "ownership_health",
    "ownership_metrics",
    "reset_ownership_service_for_tests",
]

_LOCK = Lock()
_GROUP: FailoverGroup[OwnershipService, OwnershipQuery, Any] | None = None
_SERVICES: tuple[OwnershipService, ...] = ()


def _make_group(
    services: tuple[OwnershipService, ...],
) -> FailoverGroup[OwnershipService, OwnershipQuery, Any]:
    return FailoverGroup(
        services,
        call=lambda service, query: service.get_ownership(query),
        domain="ownership",
        operation="get_ownership",
    )


def _group() -> FailoverGroup[OwnershipService, OwnershipQuery, Any]:
    global _GROUP, _SERVICES
    with _LOCK:
        if _GROUP is None:
            registry = build_default_ownership_registry_from_env()
            _SERVICES = tuple(OwnershipService(provider) for provider in registry.ordered())
            _GROUP = _make_group(_SERVICES)
        return _GROUP


def reset_ownership_service_for_tests(
    services: tuple[OwnershipService, ...] | None = None,
) -> None:
    """Replace or clear the process-local ownership failover group (tests only)."""
    global _GROUP, _SERVICES
    with _LOCK:
        if services is None:
            _GROUP = None
            _SERVICES = ()
        else:
            _SERVICES = services
            _GROUP = _make_group(services)


def get_authenticated_ownership(
    symbol: str,
    *,
    exchange: str | None = None,
    currency: str = "USD",
    as_of: date | str | None = None,
) -> dict[str, Any] | None:
    """Fetch authenticated shareholding pattern as a public dict, or ``None``."""
    instrument = Instrument(
        symbol=symbol.strip().upper(),
        asset_class=AssetClass.EQUITY,
        currency=currency,
        exchange=exchange,
    )
    resolved_as_of: date | None
    if as_of is None or as_of == "":
        resolved_as_of = None
    elif isinstance(as_of, date):
        resolved_as_of = as_of
    else:
        resolved_as_of = date.fromisoformat(str(as_of)[:10])

    query = OwnershipQuery(instrument=instrument, as_of=resolved_as_of)
    outcome = _group().call(query, symbol=instrument.symbol)
    if outcome is None:
        return None
    payload = outcome.result.to_public_dict()
    payload["attempted_provider_ids"] = list(outcome.attempted_provider_ids)
    return payload


def ownership_health() -> dict[str, Any]:
    healths = _group().health()
    return {
        "providers": [h.to_dict() for h in healths],
        "healthy": any(h.healthy for h in healths) if healths else False,
    }


def ownership_metrics() -> dict[str, Any]:
    _group()
    with _LOCK:
        services = _SERVICES
    return {service.provider_id: service.metrics.snapshot() for service in services}
