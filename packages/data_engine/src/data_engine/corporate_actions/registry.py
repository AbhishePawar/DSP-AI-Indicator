"""Corporate actions provider registry (EPIC-D003)."""

from __future__ import annotations

from threading import Lock
from typing import Iterable

from data_engine.corporate_actions.service import CorporateActionPort
from data_engine.exceptions import DataEngineError

__all__ = ["CorporateActionProviderRegistry"]


class CorporateActionProviderRegistry:
    """Thread-safe registry of authenticated corporate action providers."""

    def __init__(self) -> None:
        self._providers: dict[str, CorporateActionPort] = {}
        self._default: str | None = None
        self._lock = Lock()

    def register(
        self, provider: CorporateActionPort, *, default: bool = False
    ) -> None:
        with self._lock:
            self._providers[provider.provider_id] = provider
            if default or self._default is None:
                self._default = provider.provider_id

    def get(self, provider_id: str | None = None) -> CorporateActionPort:
        with self._lock:
            key = provider_id or self._default
            if key is None:
                raise DataEngineError("no corporate action provider registered")
            try:
                return self._providers[key]
            except KeyError as exc:
                raise DataEngineError(
                    f"corporate action provider not registered: {key}"
                ) from exc

    def list_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._providers))

    def all(self) -> Iterable[CorporateActionPort]:
        with self._lock:
            return tuple(self._providers.values())
