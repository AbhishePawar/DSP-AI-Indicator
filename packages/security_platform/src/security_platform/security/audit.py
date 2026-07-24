"""In-memory audit logger — no persistence backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock

__all__ = ["AuditEvent", "AuditLogger"]


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Immutable security audit event."""

    action: str
    subject: str
    success: bool
    detail: str = ""
    permission: str | None = None
    path: str | None = None
    request_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


class AuditLogger:
    """Process-local audit ring — adapters may mirror externally."""

    def __init__(self, *, max_events: int = 1000) -> None:
        self._max = max(1, max_events)
        self._events: list[AuditEvent] = []
        self._lock = Lock()

    def log(
        self,
        *,
        action: str,
        subject: str,
        success: bool,
        detail: str = "",
        permission: str | None = None,
        path: str | None = None,
        request_id: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            action=action,
            subject=subject,
            success=success,
            detail=detail,
            permission=permission,
            path=path,
            request_id=request_id,
        )
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max:
                self._events = self._events[-self._max :]
        return event

    def list_events(self) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(self._events)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)
