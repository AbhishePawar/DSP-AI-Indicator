"""Authentication audit trail — immutable, append-only event log.

Reuses the platform's existing generic persistence primitive (the
``audit_record`` entity kind already defined in
:mod:`persistence.models`) instead of introducing a parallel storage
mechanism. Every entry is written with ``allow_update=False`` so history
can never be silently mutated or overwritten — only appended.

This module is intentionally provider-agnostic: any port exposing the
``put`` / ``get`` / ``list_ids`` surface already used across the ``auth``
package (see :class:`persistence.service.PersistenceService`) can serve as
the backing store.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "AuditEvent",
    "AuditLogger",
]

_AUDIT_PREFIX = "auth-audit-"


@runtime_checkable
class _PersistencePort(Protocol):
    def put(
        self,
        *,
        kind: str,
        entity_id: str,
        payload: dict[str, Any],
        refs: dict[str, Any],
        created_at: str,
        allow_update: bool,
    ) -> Any: ...

    def get(self, kind: str, entity_id: str) -> dict[str, Any] | None: ...

    def list_ids(self, kind: str) -> list[str]: ...


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """A single immutable authentication audit entry."""

    event_id: str
    event_type: str
    created_at: str
    user_id: str | None = None
    organization_id: str | None = None
    ip_hint: str | None = None
    user_agent_hint: str | None = None
    detail: str | None = None
    metadata: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "created_at": self.created_at,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "ip_hint": self.ip_hint,
            "user_agent_hint": self.user_agent_hint,
            "detail": self.detail,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


class AuditLogger:
    """Append-only authentication audit trail over the shared persistence port.

    Every authentication-relevant event — login, logout, failed login,
    OAuth, OTP, magic link, password reset, MFA changes, passkey
    registration, invite acceptance, admin provisioning, single-use token
    lifecycle, etc. — should be recorded through this single object so
    there is exactly one audit code path for the whole platform.
    """

    def __init__(self, persistence: _PersistencePort) -> None:
        self._persistence = persistence

    def record(
        self,
        event_type: str,
        *,
        user_id: str | None = None,
        organization_id: str | None = None,
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
        detail: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
            user_id=user_id,
            organization_id=organization_id,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
            detail=detail,
            metadata=metadata or {},
        )
        payload = event.to_dict()
        refs: dict[str, Any] = {"auth_entity": "audit_event", "event_type": event_type}
        if user_id:
            refs["user_id"] = user_id
        if organization_id:
            refs["organization_id"] = organization_id
        self._persistence.put(
            kind="audit_record",
            entity_id=f"{_AUDIT_PREFIX}{event.event_id}",
            payload=payload,
            refs=refs,
            created_at=event.created_at,
            allow_update=False,
        )
        return payload

    def list_events(
        self,
        *,
        user_id: str | None = None,
        event_type: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for entity_id in self._persistence.list_ids("audit_record"):
            if not str(entity_id).startswith(_AUDIT_PREFIX):
                continue
            row = self._persistence.get("audit_record", entity_id)
            if not row:
                continue
            payload = row.get("payload") or {}
            if user_id and payload.get("user_id") != user_id:
                continue
            if event_type and payload.get("event_type") != event_type:
                continue
            out.append(payload)
        out.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
        return out[:limit]
