"""Generic automatic-failover orchestration across prioritized providers.

Each connector domain already gets per-provider resilience for free by
wrapping its Port in that domain's ``Service`` (cache, rate limit,
retry, circuit breaker, timeout — see ``market_quote.service`` and its
siblings). :class:`FailoverGroup` adds the next layer up: given several
*already-resilient* per-provider services for the same domain, ordered
by priority, it tries them in order and returns the first success,
auditing every attempt along the way. Only when every provider in the
group has failed or reported unavailable does the group itself report
unavailable — this is what "automatic failover" and "provider
priorities" mean operationally in this framework.

Generic over the per-provider service type, its query type, and its
result type, so it is implemented once and reused identically by News,
Filings, Ownership, Insider Trading, ESG, and Transcripts.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from data_engine.connector_framework.audit import (
    LoggingProviderAuditPort,
    ProviderAuditPort,
)
from data_engine.connector_framework.models import ProviderHealth
from data_engine.market_quote.service import CircuitOpenError

__all__ = ["FailoverGroup", "FailoverOutcome"]

_LOG = logging.getLogger("data_engine.connector_framework.failover")

TService = TypeVar("TService")
TQuery = TypeVar("TQuery")
TResult = TypeVar("TResult")


@dataclass(frozen=True, slots=True)
class FailoverOutcome(Generic[TResult]):
    """A successful failover result plus which provider actually served it."""

    result: TResult
    provider_id: str
    attempted_provider_ids: tuple[str, ...]
    """Every provider tried before (and including) the one that succeeded."""


class FailoverGroup(Generic[TService, TQuery, TResult]):
    """Tries an ordered sequence of per-provider services until one succeeds.

    ``services`` must already be ordered by priority (lowest first) —
    typically via ``PriorityProviderRegistry.ordered()``. Each element
    must expose ``provider_id: str``, ``health() -> ProviderHealth``,
    and be callable through the ``call`` function supplied here.
    """

    def __init__(
        self,
        services: Sequence[TService],
        *,
        call: Callable[[TService, TQuery], TResult | None],
        domain: str,
        operation: str,
        audit: ProviderAuditPort | None = None,
    ) -> None:
        self._services = tuple(services)
        self._call = call
        self._domain = domain
        self._operation = operation
        self._audit = audit or LoggingProviderAuditPort()

    @property
    def provider_ids(self) -> tuple[str, ...]:
        return tuple(getattr(s, "provider_id") for s in self._services)

    def is_empty(self) -> bool:
        return not self._services

    def call(
        self, query: TQuery, *, symbol: str | None = None
    ) -> FailoverOutcome[TResult] | None:
        """Try every provider in priority order; return the first success.

        Returns ``None`` (never raises) once every provider has either
        raised, timed out, tripped its circuit breaker, or reported
        unavailable — callers should treat that exactly like a single
        provider reporting "Data unavailable.".
        """
        attempted: list[str] = []
        for service in self._services:
            provider_id = getattr(service, "provider_id")
            attempted.append(provider_id)
            self._audit.record(
                "attempt",
                domain=self._domain,
                provider_id=provider_id,
                operation=self._operation,
                symbol=symbol,
            )
            try:
                result = self._call(service, query)
            except CircuitOpenError as exc:
                self._audit.record(
                    "circuit_open",
                    domain=self._domain,
                    provider_id=provider_id,
                    operation=self._operation,
                    symbol=symbol,
                    detail=str(exc),
                )
                _LOG.warning(
                    "connector_failover_circuit_open",
                    extra={
                        "domain": self._domain,
                        "provider": provider_id,
                        "operation": self._operation,
                    },
                )
                continue
            except Exception as exc:  # noqa: BLE001 — bounded failover surface
                self._audit.record(
                    "failure",
                    domain=self._domain,
                    provider_id=provider_id,
                    operation=self._operation,
                    symbol=symbol,
                    detail=str(exc),
                )
                _LOG.warning(
                    "connector_failover_provider_failed",
                    extra={
                        "domain": self._domain,
                        "provider": provider_id,
                        "operation": self._operation,
                        "error": str(exc),
                    },
                )
                continue

            if result is None:
                self._audit.record(
                    "unavailable",
                    domain=self._domain,
                    provider_id=provider_id,
                    operation=self._operation,
                    symbol=symbol,
                )
                continue

            self._audit.record(
                "success",
                domain=self._domain,
                provider_id=provider_id,
                operation=self._operation,
                symbol=symbol,
            )
            return FailoverOutcome(
                result=result,
                provider_id=provider_id,
                attempted_provider_ids=tuple(attempted),
            )

        self._audit.record(
            "all_providers_exhausted",
            domain=self._domain,
            provider_id="none",
            operation=self._operation,
            symbol=symbol,
            metadata={"attempted": attempted},
        )
        _LOG.info(
            "connector_failover_exhausted",
            extra={
                "domain": self._domain,
                "operation": self._operation,
                "attempted": attempted,
            },
        )
        return None

    def health(self) -> tuple[ProviderHealth, ...]:
        """Health of every provider in the group, in priority order."""
        return tuple(getattr(s, "health")() for s in self._services)
