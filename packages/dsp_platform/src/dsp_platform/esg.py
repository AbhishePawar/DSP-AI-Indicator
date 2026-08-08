"""Authenticated ESG score façade for DSPPlatform (Data Connector Framework).

Thin wrapper over ``data_engine.esg``. Builds the default multi-provider
registry from environment configuration, wraps every registered provider in
a resilient ``EsgService``, and orchestrates automatic failover across them
via ``FailoverGroup``. No aggregation, re-weighting, or scoring lives here.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine import (
    EsgQuery,
    EsgService,
    FailoverGroup,
    build_default_esg_registry_from_env,
)

__all__ = [
    "get_authenticated_esg_score",
    "esg_health",
    "esg_metrics",
    "reset_esg_service_for_tests",
]

_LOCK = Lock()
_GROUP: FailoverGroup[EsgService, EsgQuery, Any] | None = None
_SERVICES: tuple[EsgService, ...] = ()


def _make_group(services: tuple[EsgService, ...]) -> FailoverGroup[EsgService, EsgQuery, Any]:
    return FailoverGroup(
        services,
        call=lambda service, query: service.get_esg_score(query),
        domain="esg",
        operation="get_esg_score",
    )


def _group() -> FailoverGroup[EsgService, EsgQuery, Any]:
    global _GROUP, _SERVICES
    with _LOCK:
        if _GROUP is None:
            registry = build_default_esg_registry_from_env()
            _SERVICES = tuple(EsgService(provider) for provider in registry.ordered())
            _GROUP = _make_group(_SERVICES)
        return _GROUP


def reset_esg_service_for_tests(
    services: tuple[EsgService, ...] | None = None,
) -> None:
    """Replace or clear the process-local ESG failover group (tests only)."""
    global _GROUP, _SERVICES
    with _LOCK:
        if services is None:
            _GROUP = None
            _SERVICES = ()
        else:
            _SERVICES = services
            _GROUP = _make_group(services)


def get_authenticated_esg_score(
    symbol: str,
    *,
    exchange: str | None = None,
    currency: str = "USD",
) -> dict[str, Any] | None:
    """Fetch an authenticated ESG score as a public dict, or ``None``."""
    instrument = Instrument(
        symbol=symbol.strip().upper(),
        asset_class=AssetClass.EQUITY,
        currency=currency,
        exchange=exchange,
    )
    query = EsgQuery(instrument=instrument)
    outcome = _group().call(query, symbol=instrument.symbol)
    if outcome is None:
        return None
    payload = outcome.result.to_public_dict()
    payload["attempted_provider_ids"] = list(outcome.attempted_provider_ids)
    return payload


def esg_health() -> dict[str, Any]:
    healths = _group().health()
    return {
        "providers": [h.to_dict() for h in healths],
        "healthy": any(h.healthy for h in healths) if healths else False,
    }


def esg_metrics() -> dict[str, Any]:
    _group()
    with _LOCK:
        services = _SERVICES
    return {service.provider_id: service.metrics.snapshot() for service in services}
