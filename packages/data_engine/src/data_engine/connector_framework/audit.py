"""Provider-call audit logging for the Data Connector Framework.

``data_engine`` may only depend on ``contracts`` and ``core``
(enforced by ``test_architecture.py``), so it cannot import the richer
audit facilities in ``auth`` or ``production_platform``. Instead this
module defines a small local :class:`ProviderAuditPort` Protocol —
every attempt, success, failure, and failover decision made while
resolving a connector request is recorded through it.

The default implementation (:class:`LoggingProviderAuditPort`) writes
structured log records via stdlib ``logging``, matching how every
existing D001–D004 service already reports outcomes (e.g.
``market_quote_ok`` / ``market_quote_failure``). A composition root
that wants a durable/queryable audit trail (e.g. bridging into
``auth.AuditLogger`` or ``production_platform``'s
``AuditEventPort``) can supply its own :class:`ProviderAuditPort`
implementation at the ``dsp_platform`` wiring layer — this is the
dependency-injection seam requested by the framework's audit-logging
requirement.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Mapping, Protocol, runtime_checkable

from data_engine.connector_framework.models import utc_now

__all__ = [
    "InMemoryProviderAuditLog",
    "LoggingProviderAuditPort",
    "NullProviderAuditPort",
    "ProviderAuditEvent",
    "ProviderAuditPort",
]

_LOG = logging.getLogger("data_engine.connector_framework.audit")


@dataclass(frozen=True, slots=True)
class ProviderAuditEvent:
    """One immutable audit record for a single provider-call attempt."""

    event_type: str
    """One of: attempt, success, unavailable, failure, circuit_open,
    rate_limited, rejected_invalid, all_providers_exhausted."""
    domain: str
    """Connector domain, e.g. ``"news"``, ``"filings"``, ``"ownership"``."""
    provider_id: str
    operation: str
    symbol: str | None = None
    detail: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    recorded_at: Any = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "domain": self.domain,
            "provider_id": self.provider_id,
            "operation": self.operation,
            "symbol": self.symbol,
            "detail": self.detail,
            "metadata": dict(self.metadata),
            "recorded_at": self.recorded_at.isoformat(),
        }


@runtime_checkable
class ProviderAuditPort(Protocol):
    """Dependency-inversion boundary for provider-call audit sinks."""

    def record(
        self,
        event_type: str,
        *,
        domain: str,
        provider_id: str,
        operation: str,
        symbol: str | None = None,
        detail: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Record one audit event. Must never raise — audit failures must
        not break the request they are observing."""
        ...


class LoggingProviderAuditPort:
    """Default audit sink: one structured log line per event."""

    def record(
        self,
        event_type: str,
        *,
        domain: str,
        provider_id: str,
        operation: str,
        symbol: str | None = None,
        detail: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        try:
            _LOG.info(
                "connector_audit_%s",
                event_type,
                extra={
                    "domain": domain,
                    "provider": provider_id,
                    "operation": operation,
                    "symbol": symbol,
                    "detail": detail,
                    "metadata": dict(metadata or {}),
                },
            )
        except Exception:  # noqa: BLE001 — audit must never break the call path
            pass


class NullProviderAuditPort:
    """No-op audit sink — for tests that want to ignore audit entirely."""

    def record(
        self,
        event_type: str,
        *,
        domain: str,
        provider_id: str,
        operation: str,
        symbol: str | None = None,
        detail: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        return None


class InMemoryProviderAuditLog:
    """Thread-safe in-memory audit sink — for tests that assert on the trail."""

    def __init__(self) -> None:
        self._events: list[ProviderAuditEvent] = []
        self._lock = Lock()

    def record(
        self,
        event_type: str,
        *,
        domain: str,
        provider_id: str,
        operation: str,
        symbol: str | None = None,
        detail: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        event = ProviderAuditEvent(
            event_type=event_type,
            domain=domain,
            provider_id=provider_id,
            operation=operation,
            symbol=symbol,
            detail=detail,
            metadata=dict(metadata or {}),
        )
        with self._lock:
            self._events.append(event)

    def events(self) -> tuple[ProviderAuditEvent, ...]:
        with self._lock:
            return tuple(self._events)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
