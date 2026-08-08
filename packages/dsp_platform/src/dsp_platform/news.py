"""Authenticated company news façade for DSPPlatform (Data Connector Framework).

Thin wrapper over ``data_engine.news``. Builds the default multi-provider
registry from environment configuration, wraps every registered provider in
a resilient ``NewsService`` (cache/rate-limit/retry/circuit-breaker), and
orchestrates automatic failover across them via ``FailoverGroup``. No
scoring, summarization, or business logic lives here.
"""

from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Any

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine import (
    FailoverGroup,
    NewsQuery,
    NewsService,
    build_default_news_registry_from_env,
)

__all__ = [
    "get_authenticated_news",
    "news_health",
    "news_metrics",
    "reset_news_service_for_tests",
]

_LOCK = Lock()
_GROUP: FailoverGroup[NewsService, NewsQuery, Any] | None = None
_SERVICES: tuple[NewsService, ...] = ()


def _build_group() -> tuple[FailoverGroup[NewsService, NewsQuery, Any], tuple[NewsService, ...]]:
    registry = build_default_news_registry_from_env()
    services = tuple(NewsService(provider) for provider in registry.ordered())
    group: FailoverGroup[NewsService, NewsQuery, Any] = FailoverGroup(
        services,
        call=lambda service, query: service.get_news(query),
        domain="news",
        operation="get_news",
    )
    return group, services


def _group() -> FailoverGroup[NewsService, NewsQuery, Any]:
    global _GROUP, _SERVICES
    with _LOCK:
        if _GROUP is None:
            _GROUP, _SERVICES = _build_group()
        return _GROUP


def reset_news_service_for_tests(
    services: tuple[NewsService, ...] | None = None,
) -> None:
    """Replace or clear the process-local news failover group (tests only)."""
    global _GROUP, _SERVICES
    with _LOCK:
        if services is None:
            _GROUP = None
            _SERVICES = ()
        else:
            _SERVICES = services
            _GROUP = FailoverGroup(
                services,
                call=lambda service, query: service.get_news(query),
                domain="news",
                operation="get_news",
            )


def get_authenticated_news(
    symbol: str,
    *,
    exchange: str | None = None,
    currency: str = "USD",
    limit: int = 20,
    since: datetime | None = None,
) -> dict[str, Any] | None:
    """Fetch authenticated company news as a public dict, or ``None``."""
    instrument = Instrument(
        symbol=symbol.strip().upper(),
        asset_class=AssetClass.EQUITY,
        currency=currency,
        exchange=exchange,
    )
    query = NewsQuery(instrument=instrument, limit=limit, since=since)
    outcome = _group().call(query, symbol=instrument.symbol)
    if outcome is None:
        return None
    payload = outcome.result.to_public_dict()
    payload["attempted_provider_ids"] = list(outcome.attempted_provider_ids)
    return payload


def news_health() -> dict[str, Any]:
    healths = _group().health()
    return {
        "providers": [h.to_dict() for h in healths],
        "healthy": any(h.healthy for h in healths) if healths else False,
    }


def news_metrics() -> dict[str, Any]:
    _group()
    with _LOCK:
        services = _SERVICES
    return {service.provider_id: service.metrics.snapshot() for service in services}
