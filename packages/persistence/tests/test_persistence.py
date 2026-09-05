"""EPIC-A008 Institutional Persistence Layer unit tests."""

from __future__ import annotations

import pytest

from persistence import (
    PERSISTENCE_SCHEMA_VERSION,
    DuplicateIdError,
    InMemoryStorageProvider,
    PersistenceError,
    PersistenceService,
    RepositoryRegistry,
    SnapshotError,
    TransactionError,
    ValidationError,
    canonical_dumps,
    content_hash,
    get_persistence_service,
    get_repository_registry,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
)
from persistence.registry import build_default_storage

FIXED = "2026-07-28T12:00:00+00:00"


@pytest.fixture(autouse=True)
def _reset() -> None:
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    reset_persistence_service_for_tests(PersistenceService(registry))
    yield
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


def test_repository_crud() -> None:
    svc = get_persistence_service()
    saved = svc.put(
        kind="metadata",
        entity_id="meta-1",
        payload={"label": "core"},
        refs={"workspace_id": "ws-1"},
        created_at=FIXED,
    )
    assert saved["entity_id"] == "meta-1"
    assert saved["version"] == 1
    got = svc.get("metadata", "meta-1")
    assert got == saved
    updated = svc.put(
        kind="metadata",
        entity_id="meta-1",
        payload={"label": "core-2"},
        refs={"workspace_id": "ws-1"},
        created_at=FIXED,
    )
    assert updated["version"] == 2
    assert updated["created_at"] == FIXED
    assert "meta-1" in svc.list_ids("metadata")
    assert svc.delete("metadata", "meta-1") is True
    assert svc.get("metadata", "meta-1") is None


def test_duplicate_id_when_update_forbidden() -> None:
    svc = get_persistence_service()
    svc.put(kind="citation", entity_id="c1", payload={"path": "a", "section": "b"}, created_at=FIXED)
    with pytest.raises(DuplicateIdError):
        svc.registry.repository("citation").put(
            svc.registry.repository("citation").require("c1"),
            allow_update=False,
        )


def test_transactions_commit_and_rollback() -> None:
    svc = get_persistence_service()
    svc.begin()
    svc.put(kind="audit_record", entity_id="audit-1", payload={"event": "x"}, created_at=FIXED)
    svc.commit()
    assert svc.get("audit_record", "audit-1") is not None

    svc.begin()
    svc.put(kind="audit_record", entity_id="audit-2", payload={"event": "y"}, created_at=FIXED)
    assert svc.get("audit_record", "audit-2") is not None
    svc.rollback()
    assert svc.get("audit_record", "audit-2") is None
    assert svc.get("audit_record", "audit-1") is not None


def test_nested_transaction_rejected() -> None:
    svc = get_persistence_service()
    svc.begin()
    with pytest.raises(TransactionError, match="already active"):
        svc.begin()
    svc.rollback()


def test_serialization_determinism() -> None:
    a = {"b": 1, "a": [2, 1], "z": {"y": True}}
    b = {"z": {"y": True}, "a": [2, 1], "b": 1}
    assert canonical_dumps(a) == canonical_dumps(b)
    assert content_hash(a) == content_hash(b)


def test_validation_rejects_research_payload_keys() -> None:
    svc = get_persistence_service()
    with pytest.raises(ValidationError, match="forbidden"):
        svc.put(
            kind="research_ref",
            entity_id="bad",
            payload={"research_object": {"symbol": "AAPL"}},
            created_at=FIXED,
        )


def test_broken_reference_validation() -> None:
    svc = get_persistence_service()
    with pytest.raises(ValidationError, match="broken reference"):
        svc.put(
            kind="metadata",
            entity_id="m-bad",
            refs={"workflow_id": ""},
            created_at=FIXED,
        )


def test_snapshot_immutable() -> None:
    svc = get_persistence_service()
    snap = svc.create_snapshot(
        kind="workflow",
        source_entity_id="wf-1",
        payload={"stage": "draft"},
        snapshot_id="snap-1",
        created_at=FIXED,
    )
    assert snap["read_only"] is True
    assert snap["content_hash"]
    with pytest.raises(SnapshotError, match="immutable"):
        svc.create_snapshot(
            kind="workflow",
            source_entity_id="wf-1",
            payload={"stage": "review"},
            snapshot_id="snap-1",
            created_at=FIXED,
        )


def test_workflow_persistence_strips_to_metadata() -> None:
    svc = get_persistence_service()
    record = svc.persist_workflow_record(
        {
            "workflow_id": "wf-p1",
            "template_id": "institutional_research_v1",
            "subject": "AAPL",
            "stage": "review",
            "created_at": FIXED,
            "updated_at": FIXED,
            "artifact_refs": {"research_object_id": "ro-1"},
            "reviewers": [{"reviewer_id": "u1", "role": "analyst"}],
            "approvals": [],
            "decision_history": [],
            "audit_trail": [{"event": "workflow_created"}],
            "comments": [{"comment_id": "c1", "body": "ok"}],
        },
        created_at=FIXED,
    )
    assert record["kind"] == "workflow_record"
    assert record["payload"]["stage"] == "review"
    assert record["refs"]["research_object_id"] == "ro-1"
    assert "research_object" not in record["payload"]
    assert record["provenance"]["research_mutated"] is False


def test_audit_citation_provenance_persistence() -> None:
    svc = get_persistence_service()
    audit = svc.persist_audit_record(
        {"event_id": "e1", "event": "stage_transition", "workflow_id": "wf-1", "created_at": FIXED},
        created_at=FIXED,
    )
    cite = svc.persist_citation(
        {"path": "research_object.risk", "section": "risk", "source_kind": "research_object"},
        created_at=FIXED,
    )
    prov = svc.persist_provenance(
        {"source": "institutional_workflow", "workflow_id": "wf-1"},
        created_at=FIXED,
    )
    assert audit["kind"] == "audit_record"
    assert cite["kind"] == "citation"
    assert prov["kind"] == "provenance"


def test_schema_version() -> None:
    schema = get_persistence_service().schema()
    assert schema["schema_version"] == PERSISTENCE_SCHEMA_VERSION
    assert "no_research_mutation" in schema["rules"]
    assert schema["provider"] == "in_memory"


def test_determinism_of_put() -> None:
    svc = get_persistence_service()
    a = svc.put(
        kind="metadata",
        entity_id="det-1",
        payload={"x": 1, "y": 2},
        refs={"a": "1"},
        created_at=FIXED,
    )
    listed = svc.list_entities("metadata")
    assert listed[0]["payload"] == {"x": 1, "y": 2}
    assert canonical_dumps(a["payload"]) == canonical_dumps({"y": 2, "x": 1})


def test_atomic_consume_unexpired_once() -> None:
    svc = get_persistence_service()
    svc.put(
        kind="metadata",
        entity_id="consume-1",
        payload={"expires_at": "2099-01-01T00:00:00+00:00", "consumed_at": None},
        created_at=FIXED,
    )
    first = svc.atomic_consume_unexpired(
        "metadata",
        "consume-1",
        now_iso="2026-07-28T12:00:00+00:00",
        consumed_at="2026-07-28T12:00:01+00:00",
    )
    assert first is not None
    assert first["payload"]["consumed_at"] == "2026-07-28T12:00:01+00:00"
    second = svc.atomic_consume_unexpired(
        "metadata",
        "consume-1",
        now_iso="2026-07-28T12:00:02+00:00",
        consumed_at="2026-07-28T12:00:02+00:00",
    )
    assert second is None


def test_atomic_increment_unexpired_caps_and_skips_consumed() -> None:
    svc = get_persistence_service()
    svc.put(
        kind="metadata",
        entity_id="inc-1",
        payload={"expires_at": "2099-01-01T00:00:00+00:00", "consumed_at": None, "attempts": 0},
        created_at=FIXED,
    )
    first = svc.atomic_increment_unexpired(
        "metadata",
        "inc-1",
        now_iso="2026-07-28T12:00:00+00:00",
        max_value=2,
    )
    assert first is not None
    assert first["payload"]["attempts"] == 1
    second = svc.atomic_increment_unexpired(
        "metadata",
        "inc-1",
        now_iso="2026-07-28T12:00:01+00:00",
        max_value=2,
    )
    assert second is not None
    assert second["payload"]["attempts"] == 2
    third = svc.atomic_increment_unexpired(
        "metadata",
        "inc-1",
        now_iso="2026-07-28T12:00:02+00:00",
        max_value=2,
    )
    assert third is None
    consumed = svc.atomic_consume_unexpired(
        "metadata",
        "inc-1",
        now_iso="2026-07-28T12:00:03+00:00",
        consumed_at="2026-07-28T12:00:03+00:00",
        attempts_field=("payload", "attempts"),
        max_attempts=2,
    )
    assert consumed is None


def test_atomic_put_if_absent_returns_winner() -> None:
    svc = get_persistence_service()
    first = svc.atomic_put_if_absent(
        kind="metadata",
        entity_id="absent-1",
        payload={"device_id": "a"},
        created_at=FIXED,
    )
    second = svc.atomic_put_if_absent(
        kind="metadata",
        entity_id="absent-1",
        payload={"device_id": "b"},
        created_at=FIXED,
    )
    assert first["payload"]["device_id"] == "a"
    assert second["payload"]["device_id"] == "a"
    assert svc.get("metadata", "absent-1")["payload"]["device_id"] == "a"


def test_atomic_merge_payload_preserves_sibling_fields() -> None:
    svc = get_persistence_service()
    svc.put(
        kind="metadata",
        entity_id="merge-1",
        payload={"trusted": True, "revoked": False, "last_seen_at": "t0"},
        created_at=FIXED,
    )
    merged = svc.atomic_merge_payload(
        "metadata",
        "merge-1",
        fields={"last_seen_at": "t1", "ip_hint": "1.2.3.4"},
        updated_at="2026-07-28T12:00:01+00:00",
        match={"revoked": False},
    )
    assert merged is not None
    assert merged["payload"]["trusted"] is True
    assert merged["payload"]["revoked"] is False
    assert merged["payload"]["last_seen_at"] == "t1"
    assert merged["payload"]["ip_hint"] == "1.2.3.4"
    skipped = svc.atomic_merge_payload(
        "metadata",
        "merge-1",
        fields={"revoked": True},
        updated_at="2026-07-28T12:00:02+00:00",
        match={"user_id": "other"},
    )
    assert skipped is None
    still = svc.get("metadata", "merge-1")
    assert still is not None
    assert still["payload"]["revoked"] is False


def test_atomic_consume_rejects_expired_and_missing() -> None:
    svc = get_persistence_service()
    svc.put(
        kind="metadata",
        entity_id="consume-expired",
        payload={"expires_at": "2000-01-01T00:00:00+00:00", "consumed_at": None},
        created_at=FIXED,
    )
    assert (
        svc.atomic_consume_unexpired(
            "metadata",
            "consume-expired",
            now_iso="2026-07-28T12:00:00+00:00",
            consumed_at="2026-07-28T12:00:00+00:00",
        )
        is None
    )
    assert (
        svc.atomic_consume_unexpired(
            "metadata",
            "missing",
            now_iso="2026-07-28T12:00:00+00:00",
            consumed_at="2026-07-28T12:00:00+00:00",
        )
        is None
    )


def test_production_missing_database_url_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.delenv("DSP_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reset_repository_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    with pytest.raises(PersistenceError, match="DSP_DATABASE_URL"):
        build_default_storage()
    with pytest.raises(PersistenceError, match="DSP_DATABASE_URL"):
        get_repository_registry()
    with pytest.raises(PersistenceError, match="DSP_DATABASE_URL"):
        get_persistence_service()


def test_development_storage_is_in_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    reset_repository_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    storage = build_default_storage()
    assert storage.provider_id == "in_memory"
