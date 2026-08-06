"""Authenticated historical time-series façade for DSPPlatform (EPIC-D004).

Thin wrapper over ``data_engine.historical_series``. No indicators, TA,
valuation, or scoring.
"""

from __future__ import annotations

from datetime import date
from threading import Lock
from typing import Any

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine import (
    HistoricalSeriesQuery,
    HistoricalSeriesService,
    build_default_historical_adapter_from_env,
)

__all__ = [
    "get_authenticated_historical_series",
    "historical_series_health",
    "historical_series_metrics",
    "reset_historical_series_service_for_tests",
]

_LOCK = Lock()
_SERVICE: HistoricalSeriesService | None = None


def _service() -> HistoricalSeriesService:
    global _SERVICE
    with _LOCK:
        if _SERVICE is None:
            adapter = build_default_historical_adapter_from_env()
            _SERVICE = HistoricalSeriesService(adapter)
        return _SERVICE


def reset_historical_series_service_for_tests(
    service: HistoricalSeriesService | None = None,
) -> None:
    """Replace or clear the process-local historical series service (tests only)."""
    global _SERVICE
    with _LOCK:
        _SERVICE = service


def _d(value: date | str | None) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def get_authenticated_historical_series(
    symbol: str,
    *,
    series_kind: str,
    exchange: str | None = None,
    currency: str = "USD",
    frequency: str | None = "daily",
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    limit: int = 500,
) -> dict[str, Any] | None:
    """Fetch authenticated historical series as a public dict, or ``None``."""
    instrument = Instrument(
        symbol=symbol.strip().upper(),
        asset_class=AssetClass.EQUITY,
        currency=currency,
        exchange=exchange,
    )
    query = HistoricalSeriesQuery(
        instrument=instrument,
        series_kind=series_kind,
        frequency=frequency,
        start_date=_d(start_date),
        end_date=_d(end_date),
        limit=limit,
    )
    bundle = _service().get_series(query)
    if bundle is None:
        return None
    return bundle.to_public_dict()


def historical_series_health() -> dict[str, Any]:
    return _service().health().to_dict()


def historical_series_metrics() -> dict[str, int]:
    return _service().metrics.snapshot()
