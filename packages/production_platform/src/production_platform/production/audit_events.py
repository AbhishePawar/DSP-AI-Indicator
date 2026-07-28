"""Operational audit event pipeline (PEP-003)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from production_platform.production.correlation import get_correlation_id
from production_platform.production.interfaces import AuditEventPort, LoggingPort

__all__ = [
    "AuditEvent",
    "FanoutAuditEventPort",
    "InMemoryAuditEventPort",
    "LoggingAuditEventPort",
]


@dataclass(frozen=True, slots=True)
class AuditEvent:
    action: str
    subject: str
    success: bool
    detail: str = ""
    correlation_id: str | None = None
    fields: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


class InMemoryAuditEventPort:
    """Process-local audit ring — reference adapter."""

    def __init__(self, *, max_events: int = 5000) -> None:
        self._max = max(1, max_events)
        self._events: list[AuditEvent] = []
        self._lock = Lock()

    def emit(
        self,
        *,
        action: str,
        subject: str,
        success: bool,
        detail: str = "",
        correlation_id: str | None = None,
        fields: dict[str, Any] | None = None,
    ) -> None:
        cid = correlation_id if correlation_id is not None else get_correlation_id()
        event = AuditEvent(
            action=action.strip(),
            subject=subject,
            success=success,
            detail=detail,
            correlation_id=cid,
            fields=dict(fields or {}),
        )
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max:
                self._events = self._events[-self._max :]

    def list_events(self, *, limit: int = 100) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(self._events[-max(1, limit) :])


class LoggingAuditEventPort:
    """Mirror audit events into structured LoggingPort."""

    def __init__(self, logging: LoggingPort) -> None:
        self._logging = logging
        self._inner = InMemoryAuditEventPort()

    def emit(
        self,
        *,
        action: str,
        subject: str,
        success: bool,
        detail: str = "",
        correlation_id: str | None = None,
        fields: dict[str, Any] | None = None,
    ) -> None:
        self._inner.emit(
            action=action,
            subject=subject,
            success=success,
            detail=detail,
            correlation_id=correlation_id,
            fields=fields,
        )
        self._logging.log(
            "INFO" if success else "WARNING",
            f"audit:{action}",
            correlation_id=correlation_id,
            fields={
                "audit": True,
                "action": action,
                "subject": subject,
                "success": success,
                "detail": detail,
                **(fields or {}),
            },
        )

    def list_events(self, *, limit: int = 100) -> tuple[AuditEvent, ...]:
        return self._inner.list_events(limit=limit)


class FanoutAuditEventPort:
    """Fan-out AuditEventPort to multiple sinks."""

    def __init__(self, *ports: AuditEventPort) -> None:
        self._ports = ports

    def emit(
        self,
        *,
        action: str,
        subject: str,
        success: bool,
        detail: str = "",
        correlation_id: str | None = None,
        fields: dict[str, Any] | None = None,
    ) -> None:
        for port in self._ports:
            port.emit(
                action=action,
                subject=subject,
                success=success,
                detail=detail,
                correlation_id=correlation_id,
                fields=fields,
            )

    def list_events(self, *, limit: int = 100) -> tuple[Any, ...]:
        if not self._ports:
            return ()
        return self._ports[0].list_events(limit=limit)
