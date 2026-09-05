"""Stage 0M: durable DeviceRegistry across processes."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta

import pytest

from auth.device_store import DeviceStore, default_device_store
from auth.devices import DeviceRegistry
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
)


def _shared_store() -> DeviceStore:
    return DeviceStore(
        PersistenceService(RepositoryRegistry(storage=InMemoryStorageProvider()))
    )


def test_isolated_registries_cannot_see_each_others_devices() -> None:
    """Process-local stores (two Cloud Run instances without shared A008) fail."""
    a = DeviceRegistry()
    b = DeviceRegistry()
    device = a.register(user_id="u1", ip_hint="1.1.1.1", user_agent_hint="agent-a")
    a.set_trusted(device.device_id, user_id="u1", trusted=True)
    assert a.is_trusted("u1", ip_hint="1.1.1.1", user_agent_hint="agent-a") is True
    assert b.is_trusted("u1", ip_hint="1.1.1.1", user_agent_hint="agent-a") is False
    assert b.get(device.device_id) is None


def test_shared_store_cross_process_register_and_lookup() -> None:
    store = _shared_store()
    a = DeviceRegistry(store=store)
    b = DeviceRegistry(store=store)
    created = a.register(user_id="u-cross", ip_hint="2.2.2.2", user_agent_hint="agent-b")
    found = b.get(created.device_id)
    assert found is not None
    assert found.user_id == "u-cross"
    assert found.device_id == created.device_id


def test_register_and_retrieve() -> None:
    devices = DeviceRegistry()
    device = devices.register(user_id="u1", ip_hint="10.0.0.1", user_agent_hint="pytest")
    got = devices.get(device.device_id)
    assert got is not None
    assert got.user_id == "u1"
    listed = devices.list_for_user("u1")
    assert listed[0]["device_id"] == device.device_id


def test_duplicate_register_same_fingerprint_reuses_device() -> None:
    devices = DeviceRegistry()
    first = devices.register(user_id="u1", ip_hint="8.8.8.8", user_agent_hint="same")
    second = devices.register(user_id="u1", ip_hint="8.8.8.8", user_agent_hint="same")
    assert first.device_id == second.device_id


def test_cross_process_trust_and_revoke() -> None:
    store = _shared_store()
    a = DeviceRegistry(store=store)
    b = DeviceRegistry(store=store)
    device = a.register(user_id="u-rev", ip_hint="3.3.3.3", user_agent_hint="agent")
    a.set_trusted(device.device_id, user_id="u-rev", trusted=True)
    assert b.is_trusted("u-rev", ip_hint="3.3.3.3", user_agent_hint="agent") is True
    b.revoke(device.device_id, user_id="u-rev")
    assert a.is_trusted("u-rev", ip_hint="3.3.3.3", user_agent_hint="agent") is False
    with pytest.raises(KeyError, match="device not found"):
        a.set_trusted(device.device_id, user_id="u-rev", trusted=True)


def test_expired_trust_rejected() -> None:
    devices = DeviceRegistry()
    device = devices.register(user_id="u-exp", ip_hint="4.4.4.4", user_agent_hint="agent")
    devices.set_trusted(device.device_id, user_id="u-exp", trusted=True)
    record = devices.get(device.device_id)
    assert record is not None
    record.trusted_until = (datetime.now(tz=UTC) - timedelta(days=1)).isoformat()
    devices._store.put_device(record.to_store_payload())  # noqa: SLF001
    assert devices.is_trusted("u-exp", ip_hint="4.4.4.4", user_agent_hint="agent") is False


def test_user_isolation() -> None:
    store = _shared_store()
    devices = DeviceRegistry(store=store)
    device = devices.register(user_id="owner", ip_hint="5.5.5.5", user_agent_hint="agent")
    devices.set_trusted(device.device_id, user_id="owner", trusted=True)
    other = DeviceRegistry(store=store)
    assert other.is_trusted("intruder", ip_hint="5.5.5.5", user_agent_hint="agent") is False
    with pytest.raises(KeyError, match="device not found"):
        other.set_trusted(device.device_id, user_id="intruder", trusted=True)
    with pytest.raises(KeyError, match="device not found"):
        other.revoke(device.device_id, user_id="intruder")
    assert other.list_for_user("intruder") == []
    assert devices.list_for_user("owner")[0]["device_id"] == device.device_id


def test_concurrent_registration_one_device_id() -> None:
    store = _shared_store()
    barrier = threading.Barrier(2)

    def register() -> str:
        registry = DeviceRegistry(store=store)
        barrier.wait()
        device = registry.register(
            user_id="u-race",
            ip_hint="6.6.6.6",
            user_agent_hint="same-agent",
        )
        return device.device_id

    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = [pool.submit(register), pool.submit(register)]
        ids = [fut.result() for fut in as_completed(futs)]
    assert ids[0] == ids[1]
    listed = DeviceRegistry(store=store).list_for_user("u-race")
    assert len(listed) == 1


def test_revoke_all_propagates_across_processes() -> None:
    store = _shared_store()
    a = DeviceRegistry(store=store)
    b = DeviceRegistry(store=store)
    first = a.register(user_id="u-all", ip_hint="7.7.7.7", user_agent_hint="one")
    second = a.register(user_id="u-all", ip_hint="7.7.7.8", user_agent_hint="two")
    a.set_trusted(first.device_id, user_id="u-all", trusted=True)
    a.set_trusted(second.device_id, user_id="u-all", trusted=True)
    assert b.revoke_all("u-all") == 2
    assert a.is_trusted("u-all", ip_hint="7.7.7.7", user_agent_hint="one") is False
    assert a.list_for_user("u-all") == []


def test_fingerprint_entity_id_is_hmac_not_raw_user() -> None:
    store = _shared_store()
    devices = DeviceRegistry(store=store)
    devices.register(user_id="user-visible-id", ip_hint="9.9.9.9", user_agent_hint="agent")
    ids = store._persistence.list_ids("metadata")  # noqa: SLF001
    assert any(item.startswith("auth-device-fp-") for item in ids)
    joined = " ".join(ids)
    assert "user-visible-id" not in joined


def test_logs_do_not_include_ip_or_user_agent(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    devices = DeviceRegistry()
    devices.register(
        user_id="u-log",
        ip_hint="203.0.113.9",
        user_agent_hint="SecretAgent/1.0",
    )
    text = caplog.text
    assert "203.0.113.9" not in text
    assert "SecretAgent/1.0" not in text


def test_payload_has_no_plaintext_device_secret() -> None:
    store = _shared_store()
    devices = DeviceRegistry(store=store)
    device = devices.register(user_id="u-sec", ip_hint="10.10.10.10", user_agent_hint="ua")
    payload = store.get_device(device.device_id)
    assert payload is not None
    assert "otp" not in payload
    assert "secret" not in payload
    assert payload["fingerprint_hash"] != "10.10.10.10|ua"
    assert len(str(payload["fingerprint_hash"])) == 32


def test_production_default_store_uses_process_a008(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakePostgres(InMemoryStorageProvider):
        provider_id = "postgres"

    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_DATABASE_URL", "postgresql://dsp:secret@localhost/dsp")
    from persistence.registry import reset_repository_registry_for_tests
    from persistence.service import reset_persistence_service_for_tests

    reset_repository_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    monkeypatch.setattr(
        "persistence.postgres_storage.build_postgres_storage",
        lambda dsn, **kwargs: _FakePostgres(),
    )
    try:
        store = default_device_store()
        assert store._persistence.registry.storage.provider_id == "postgres"
    finally:
        reset_repository_registry_for_tests(None)
        reset_persistence_service_for_tests(None)


def test_production_missing_database_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.delenv("DSP_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from persistence.exceptions import PersistenceError
    from persistence.registry import reset_repository_registry_for_tests
    from persistence.service import reset_persistence_service_for_tests

    reset_repository_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    try:
        with pytest.raises(PersistenceError, match="DSP_DATABASE_URL"):
            default_device_store()
    finally:
        reset_repository_registry_for_tests(None)
        reset_persistence_service_for_tests(None)
