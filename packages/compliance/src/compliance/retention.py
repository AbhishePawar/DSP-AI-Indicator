"""Audit retention policies and immutable audit references (PEP-004)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any, Protocol, Sequence, runtime_checkable

from compliance.audit import AuditEvent, AuditPort

__all__ = [
    "AuditRetentionPolicy",
    "AuditRetentionPort",
    "ImmutableAuditReference",
    "InMemoryAuditPort",
    "InMemoryAuditRetentionPort",
]


@dataclass(frozen=True, slots=True)
class AuditRetentionPolicy:
    """CERT-In–aligned retention posture for compliance audit events."""

    policy_id: str = "cert_in_default"
    retention_days: int = 180
    timezone: str = "Asia/Kolkata"
    immutable: bool = True
    worm_optional: bool = True

    def __post_init__(self) -> None:
        if self.retention_days < 180:
            raise ValueError("CERT-In posture requires retention_days >= 180")


@dataclass(frozen=True, slots=True)
class ImmutableAuditReference:
    """Content-addressed reference to an audit event (evidence preservation)."""

    reference_id: str
    event_id: str
    content_hash: str
    created_at: datetime
    retention_until: datetime
    policy_id: str


@runtime_checkable
class AuditRetentionPort(Protocol):
    """Retention + immutable references for compliance audit events."""

    def policy(self) -> AuditRetentionPolicy:
        """Return active retention policy."""

    def preserve(self, event: AuditEvent) -> ImmutableAuditReference:
        """Create an immutable reference for evidence preservation."""

    def get_reference(self, reference_id: str) -> ImmutableAuditReference | None:
        """Lookup a reference."""

    def list_references(self, *, limit: int = 100) -> Sequence[ImmutableAuditReference]:
        """List recent immutable references."""

    def is_expired(self, reference: ImmutableAuditReference, *, now: datetime | None = None) -> bool:
        """Return True when retention window has elapsed."""


class InMemoryAuditPort:
    """Reference AuditPort implementation."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._lock = Lock()

    def record(self, event: AuditEvent) -> None:
        with self._lock:
            self._events.append(event)

    def list_for_resource(self, resource_ref: str) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(
                e for e in self._events if e.resource_ref == resource_ref
            )

    def list_all(self, *, limit: int = 100) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(self._events[-max(1, limit) :])


class InMemoryAuditRetentionPort:
    """Reference retention + hash-chained audit references."""

    def __init__(self, policy: AuditRetentionPolicy | None = None) -> None:
        self._policy = policy or AuditRetentionPolicy()
        self._refs: dict[str, ImmutableAuditReference] = {}
        self._lock = Lock()

    def policy(self) -> AuditRetentionPolicy:
        return self._policy

    def preserve(self, event: AuditEvent) -> ImmutableAuditReference:
        payload = {
            "event_id": event.event_id,
            "action": event.action,
            "actor": event.actor,
            "occurred_at": event.occurred_at.isoformat(),
            "resource_ref": event.resource_ref,
            "detail": event.detail,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        now = datetime.now(tz=UTC)
        ref = ImmutableAuditReference(
            reference_id=f"aref_{uuid.uuid4().hex[:12]}",
            event_id=event.event_id,
            content_hash=digest,
            created_at=now,
            retention_until=now + timedelta(days=self._policy.retention_days),
            policy_id=self._policy.policy_id,
        )
        with self._lock:
            self._refs[ref.reference_id] = ref
        return ref

    def get_reference(self, reference_id: str) -> ImmutableAuditReference | None:
        with self._lock:
            return self._refs.get(reference_id)

    def list_references(self, *, limit: int = 100) -> tuple[ImmutableAuditReference, ...]:
        with self._lock:
            items = list(self._refs.values())
        return tuple(items[-max(1, limit) :])

    def is_expired(
        self, reference: ImmutableAuditReference, *, now: datetime | None = None
    ) -> bool:
        clock = now or datetime.now(tz=UTC)
        return clock >= reference.retention_until
