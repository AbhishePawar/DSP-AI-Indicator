"""Historical series provider registry (EPIC-D004)."""

from __future__ import annotations

from threading import Lock
from typing import Iterable

from data_engine.exceptions import DataEngineError
from data_engine.historical_series.service import HistoricalSeriesPort

__all__ = ["HistoricalSeriesProviderRegistry"]


class HistoricalSeriesProviderRegistry:
    """Thread-safe registry of authenticated historical series providers."""

    def __init__(self) -> None:
        self._providers: dict[str, HistoricalSeriesPort] = {}
        self._default: str | None = None
        self._lock = Lock()

    def register(
        self, provider: HistoricalSeriesPort, *, default: bool = False
    ) -> None:
        with self._lock:
            self._providers[provider.provider_id] = provider
            if default or self._default is None:
                self._default = provider.provider_id

    def get(self, provider_id: str | None = None) -> HistoricalSeriesPort:
        with self._lock:
            key = provider_id or self._default
            if key is None:
                raise DataEngineError("no historical series provider registered")
            try:
                return self._providers[key]
            except KeyError as exc:
                raise DataEngineError(
                    f"historical series provider not registered: {key}"
                ) from exc

    def list_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._providers))

    def all(self) -> Iterable[HistoricalSeriesPort]:
        with self._lock:
            return tuple(self._providers.values())
