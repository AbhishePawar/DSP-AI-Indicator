"""Generic, priority-aware provider registry.

Extends the existing "named lookup with one default" pattern (e.g.
``CorporateActionProviderRegistry``) with two capabilities every new
connector domain needs: **provider priority** (which provider is tried
first) and **enable/disable** (temporarily remove a misbehaving
provider from rotation without unregistering it). Combined with
:class:`~data_engine.connector_framework.failover.FailoverGroup`, this
is what gives each domain automatic failover.

Generic over the provider's Port type so it is written once and reused
by all six new domains — each domain still gets its own named registry
class (e.g. ``NewsProviderRegistry``) for API clarity, but they are all
thin subclasses of this one implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Generic, TypeVar

from data_engine.exceptions import DataEngineError

__all__ = ["PriorityProviderRegistry", "ProviderRegistration"]

P = TypeVar("P")


@dataclass(frozen=True, slots=True)
class ProviderRegistration(Generic[P]):
    """One registered provider plus its ordering/availability metadata."""

    provider: P
    provider_id: str
    priority: int
    enabled: bool
    sequence: int
    """Registration order — the tie-breaker when priorities are equal."""


class PriorityProviderRegistry(Generic[P]):
    """Thread-safe registry with provider priority and enable/disable.

    Lower ``priority`` values are tried first. Ties are broken by
    registration order, so behavior is deterministic even when every
    provider shares the same priority.
    """

    def __init__(self) -> None:
        self._entries: dict[str, ProviderRegistration[P]] = {}
        self._lock = Lock()
        self._sequence = 0

    def register(
        self,
        provider: P,
        *,
        provider_id: str,
        priority: int = 100,
        enabled: bool = True,
    ) -> None:
        """Register (or replace) a provider under ``provider_id``."""
        with self._lock:
            self._sequence += 1
            self._entries[provider_id] = ProviderRegistration(
                provider=provider,
                provider_id=provider_id,
                priority=priority,
                enabled=enabled,
                sequence=self._sequence,
            )

    def set_enabled(self, provider_id: str, enabled: bool) -> None:
        """Enable or disable a provider without unregistering it."""
        with self._lock:
            entry = self._entries.get(provider_id)
            if entry is None:
                raise DataEngineError(f"provider not registered: {provider_id}")
            self._entries[provider_id] = ProviderRegistration(
                provider=entry.provider,
                provider_id=entry.provider_id,
                priority=entry.priority,
                enabled=enabled,
                sequence=entry.sequence,
            )

    def get(self, provider_id: str) -> P:
        """Return a specific provider by id, ignoring enable/disable state."""
        with self._lock:
            entry = self._entries.get(provider_id)
            if entry is None:
                raise DataEngineError(f"provider not registered: {provider_id}")
            return entry.provider

    def ordered(self, *, include_disabled: bool = False) -> tuple[P, ...]:
        """Providers in failover order: lowest priority first, then registration order."""
        with self._lock:
            entries = list(self._entries.values())
        if not include_disabled:
            entries = [e for e in entries if e.enabled]
        entries.sort(key=lambda e: (e.priority, e.sequence))
        return tuple(e.provider for e in entries)

    def ordered_ids(self, *, include_disabled: bool = False) -> tuple[str, ...]:
        with self._lock:
            entries = list(self._entries.values())
        if not include_disabled:
            entries = [e for e in entries if e.enabled]
        entries.sort(key=lambda e: (e.priority, e.sequence))
        return tuple(e.provider_id for e in entries)

    def all_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._entries))

    def all(self) -> tuple[P, ...]:
        with self._lock:
            return tuple(e.provider for e in self._entries.values())

    def is_empty(self) -> bool:
        with self._lock:
            return not self._entries

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
