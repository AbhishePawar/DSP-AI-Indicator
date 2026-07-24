"""Compliance audit event ports — architecture only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

__all__ = ["AuditEvent", "AuditPort"]


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_id: str
    action: str
    actor: str
    occurred_at: datetime
    resource_ref: str | None = None
    detail: str | None = None


@runtime_checkable
class AuditPort(Protocol):
    def record(self, event: AuditEvent) -> None: ...

    def list_for_resource(self, resource_ref: str) -> tuple[AuditEvent, ...]: ...
