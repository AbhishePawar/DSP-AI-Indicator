"""Market quote provider registry (EPIC-D001)."""

from __future__ import annotations

from threading import Lock
from typing import Iterable

from data_engine.exceptions import DataEngineError
from data_engine.market_quote.service import MarketQuotePort

__all__ = ["MarketQuoteProviderRegistry"]


class MarketQuoteProviderRegistry:
    """Thread-safe registry of authenticated quote providers."""

    def __init__(self) -> None:
        self._providers: dict[str, MarketQuotePort] = {}
        self._default: str | None = None
        self._lock = Lock()

    def register(
        self, provider: MarketQuotePort, *, default: bool = False
    ) -> None:
        with self._lock:
            self._providers[provider.provider_id] = provider
            if default or self._default is None:
                self._default = provider.provider_id

    def get(self, provider_id: str | None = None) -> MarketQuotePort:
        with self._lock:
            key = provider_id or self._default
            if key is None:
                raise DataEngineError("no market quote provider registered")
            try:
                return self._providers[key]
            except KeyError as exc:
                raise DataEngineError(
                    f"market quote provider not registered: {key}"
                ) from exc

    def list_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._providers))

    def all(self) -> Iterable[MarketQuotePort]:
        with self._lock:
            return tuple(self._providers.values())
