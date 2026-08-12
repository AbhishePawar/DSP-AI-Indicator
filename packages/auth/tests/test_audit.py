"""Unit tests for the append-only authentication audit logger."""

from __future__ import annotations

import pytest

from auth.audit import AuditLogger
from persistence import InMemoryStorageProvider, PersistenceService, RepositoryRegistry
from persistence.exceptions import PersistenceError


@pytest.fixture
def audit() -> AuditLogger:
    persistence = PersistenceService(RepositoryRegistry(storage=InMemoryStorageProvider()))
    return AuditLogger(persistence)


def test_record_returns_payload_with_event_type(audit: AuditLogger) -> None:
    entry = audit.record("login.success", user_id="u1", ip_hint="1.2.3.4")
    assert entry["event_type"] == "login.success"
    assert entry["user_id"] == "u1"
    assert entry["ip_hint"] == "1.2.3.4"
    assert entry["event_id"]
    assert entry["created_at"]


def test_list_events_filters_by_user(audit: AuditLogger) -> None:
    audit.record("login.success", user_id="u1")
    audit.record("login.success", user_id="u2")
    audit.record("logout", user_id="u1")

    events = audit.list_events(user_id="u1")
    assert len(events) == 2
    assert all(e["user_id"] == "u1" for e in events)


def test_list_events_filters_by_event_type(audit: AuditLogger) -> None:
    audit.record("login.failed", user_id="u1")
    audit.record("login.success", user_id="u1")

    events = audit.list_events(event_type="login.failed")
    assert len(events) == 1
    assert events[0]["event_type"] == "login.failed"


def test_list_events_sorted_newest_first(audit: AuditLogger) -> None:
    audit.record("event.one", user_id="u1")
    audit.record("event.two", user_id="u1")
    audit.record("event.three", user_id="u1")

    events = audit.list_events(user_id="u1")
    timestamps = [e["created_at"] for e in events]
    assert timestamps == sorted(timestamps, reverse=True)


def test_list_events_respects_limit(audit: AuditLogger) -> None:
    for i in range(5):
        audit.record(f"event.{i}", user_id="u1")
    events = audit.list_events(user_id="u1", limit=2)
    assert len(events) == 2


def test_events_are_immutable_append_only(audit: AuditLogger) -> None:
    entry = audit.record("mfa.enabled", user_id="u1")
    event_id = entry["event_id"]

    # Directly attempting to overwrite the same entity_id must fail because
    # the audit trail is written with allow_update=False.
    with pytest.raises(PersistenceError):
        audit._persistence.put(
            kind="audit_record",
            entity_id=f"auth-audit-{event_id}",
            payload={"tampered": True},
            refs={"auth_entity": "audit_event"},
            created_at=entry["created_at"],
            allow_update=False,
        )


def test_record_without_user_id_has_no_broken_refs(audit: AuditLogger) -> None:
    # Anonymous/system events (e.g. provider discovery) must not include
    # empty-string refs, which the persistence layer rejects.
    entry = audit.record("provider.discovered", detail="google")
    assert entry["user_id"] is None
