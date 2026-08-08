"""Authenticated earnings call transcript façade for DSPPlatform (Data Connector Framework).

Thin wrapper over ``data_engine.transcripts``. Builds the default
multi-provider registry from environment configuration, wraps every
registered provider in a resilient ``TranscriptService``, and orchestrates
automatic failover across them via ``FailoverGroup``. No summarization or
business logic lives here.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine import (
    FailoverGroup,
    TranscriptQuery,
    TranscriptService,
    build_default_transcript_registry_from_env,
)

__all__ = [
    "get_authenticated_transcripts",
    "transcripts_health",
    "transcripts_metrics",
    "reset_transcripts_service_for_tests",
]

_LOCK = Lock()
_GROUP: FailoverGroup[TranscriptService, TranscriptQuery, Any] | None = None
_SERVICES: tuple[TranscriptService, ...] = ()


def _make_group(
    services: tuple[TranscriptService, ...],
) -> FailoverGroup[TranscriptService, TranscriptQuery, Any]:
    return FailoverGroup(
        services,
        call=lambda service, query: service.get_transcripts(query),
        domain="transcripts",
        operation="get_transcripts",
    )


def _group() -> FailoverGroup[TranscriptService, TranscriptQuery, Any]:
    global _GROUP, _SERVICES
    with _LOCK:
        if _GROUP is None:
            registry = build_default_transcript_registry_from_env()
            _SERVICES = tuple(TranscriptService(provider) for provider in registry.ordered())
            _GROUP = _make_group(_SERVICES)
        return _GROUP


def reset_transcripts_service_for_tests(
    services: tuple[TranscriptService, ...] | None = None,
) -> None:
    """Replace or clear the process-local transcripts failover group (tests only)."""
    global _GROUP, _SERVICES
    with _LOCK:
        if services is None:
            _GROUP = None
            _SERVICES = ()
        else:
            _SERVICES = services
            _GROUP = _make_group(services)


def get_authenticated_transcripts(
    symbol: str,
    *,
    exchange: str | None = None,
    currency: str = "USD",
    year: int | None = None,
    quarter: int | None = None,
    limit: int = 8,
) -> dict[str, Any] | None:
    """Fetch authenticated earnings call transcripts as a public dict, or ``None``."""
    instrument = Instrument(
        symbol=symbol.strip().upper(),
        asset_class=AssetClass.EQUITY,
        currency=currency,
        exchange=exchange,
    )
    query = TranscriptQuery(instrument=instrument, year=year, quarter=quarter, limit=limit)
    outcome = _group().call(query, symbol=instrument.symbol)
    if outcome is None:
        return None
    payload = outcome.result.to_public_dict()
    payload["attempted_provider_ids"] = list(outcome.attempted_provider_ids)
    return payload


def transcripts_health() -> dict[str, Any]:
    healths = _group().health()
    return {
        "providers": [h.to_dict() for h in healths],
        "healthy": any(h.healthy for h in healths) if healths else False,
    }


def transcripts_metrics() -> dict[str, Any]:
    _group()
    with _LOCK:
        services = _SERVICES
    return {service.provider_id: service.metrics.snapshot() for service in services}
