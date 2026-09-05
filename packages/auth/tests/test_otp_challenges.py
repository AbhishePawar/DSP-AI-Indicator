"""Stage 0L: durable OTP challenge store across processes."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import pytest

from auth.exceptions import AuthenticationError
from auth.otp import OtpService
from auth.otp_challenges import OtpChallengeStore, default_otp_store
from auth.sms import DevSmsAdapter
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
)


def _shared_store() -> OtpChallengeStore:
    return OtpChallengeStore(
        PersistenceService(RepositoryRegistry(storage=InMemoryStorageProvider()))
    )


def _svc(store: OtpChallengeStore | None = None, sms: DevSmsAdapter | None = None) -> OtpService:
    return OtpService(sms or DevSmsAdapter(), store=store)


def test_isolated_services_cannot_verify_each_others_challenges() -> None:
    """Process-local stores (two Cloud Run instances without shared A008) fail."""
    sms_a = DevSmsAdapter()
    a = _svc(sms=sms_a)
    b = _svc()
    issued = a.request_otp("+919876543210")
    code = (issued.get("sms") or {}).get("debug_code")
    assert code
    with pytest.raises(AuthenticationError, match="Invalid or expired OTP challenge"):
        b.verify_otp(challenge_id=issued["challenge_id"], code=code)


def test_shared_store_cross_process_verify() -> None:
    store = _shared_store()
    sms = DevSmsAdapter()
    issuer = _svc(store, sms)
    verifier = _svc(store)
    issued = issuer.request_otp("+919876543210")
    code = (issued.get("sms") or {}).get("debug_code")
    dest = verifier.verify_otp(challenge_id=issued["challenge_id"], code=code)
    assert dest == "+919876543210"


def test_correct_otp_succeeds_and_is_single_use() -> None:
    sms = DevSmsAdapter()
    svc = _svc(sms=sms)
    issued = svc.request_otp("+919812345678")
    code = issued["sms"]["debug_code"]
    assert svc.verify_otp(challenge_id=issued["challenge_id"], code=code) == "+919812345678"
    with pytest.raises(AuthenticationError, match="OTP already used"):
        svc.verify_otp(challenge_id=issued["challenge_id"], code=code)


def test_incorrect_otp_fails() -> None:
    sms = DevSmsAdapter()
    svc = _svc(sms=sms)
    issued = svc.request_otp("+919812345679")
    with pytest.raises(AuthenticationError, match="Invalid OTP code"):
        svc.verify_otp(challenge_id=issued["challenge_id"], code="000000")


def test_expired_otp_fails() -> None:
    sms = DevSmsAdapter()
    svc = _svc(sms=sms)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    issued = svc.request_otp("+919800000001", now=now)
    code = issued["sms"]["debug_code"]
    with pytest.raises(AuthenticationError, match="OTP expired"):
        svc.verify_otp(
            challenge_id=issued["challenge_id"],
            code=code,
            now=now + timedelta(minutes=6),
        )


def test_unknown_challenge_fails() -> None:
    svc = _svc()
    with pytest.raises(AuthenticationError, match="Invalid or expired OTP challenge"):
        svc.verify_otp(challenge_id="00000000-0000-0000-0000-000000000000", code="123456")


def test_attempt_limit_shared_across_services() -> None:
    store = _shared_store()
    sms = DevSmsAdapter()
    a = _svc(store, sms)
    b = _svc(store)
    issued = a.request_otp("+919800000002")
    code = issued["sms"]["debug_code"]
    for _ in range(3):
        with pytest.raises(AuthenticationError, match="Invalid OTP code"):
            a.verify_otp(challenge_id=issued["challenge_id"], code="111111")
    for _ in range(2):
        with pytest.raises(AuthenticationError, match="Invalid OTP code"):
            b.verify_otp(challenge_id=issued["challenge_id"], code="222222")
    with pytest.raises(AuthenticationError, match="Too many invalid OTP attempts"):
        a.verify_otp(challenge_id=issued["challenge_id"], code=code)


def test_concurrent_verification_one_success() -> None:
    store = _shared_store()
    sms = DevSmsAdapter()
    issuer = _svc(store, sms)
    issued = issuer.request_otp("+919800000003")
    code = issued["sms"]["debug_code"]
    barrier = threading.Barrier(2)

    def attempt() -> str:
        svc = _svc(store)
        barrier.wait()
        try:
            svc.verify_otp(challenge_id=issued["challenge_id"], code=code)
            return "success"
        except AuthenticationError:
            return "failure"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = [pool.submit(attempt), pool.submit(attempt)]
        results = [fut.result() for fut in as_completed(futs)]
    assert results.count("success") == 1
    assert results.count("failure") == 1


def test_resend_cooldown_shared() -> None:
    store = _shared_store()
    sms = DevSmsAdapter()
    a = _svc(store, sms)
    b = _svc(store, DevSmsAdapter())
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    a.request_otp("+919800000004", now=now)
    with pytest.raises(AuthenticationError, match="Resend available after"):
        b.request_otp("+919800000004", now=now + timedelta(seconds=10))
    later = a.request_otp("+919800000004", now=now + timedelta(seconds=31))
    assert later["challenge_id"]


def test_hourly_send_cap_shared() -> None:
    store = _shared_store()
    mobile = "+919800000005"
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(5):
        _svc(store, DevSmsAdapter()).request_otp(
            mobile, now=now + timedelta(seconds=31 * i)
        )
    with pytest.raises(AuthenticationError, match="OTP rate limit exceeded"):
        _svc(store, DevSmsAdapter()).request_otp(
            mobile, now=now + timedelta(seconds=31 * 5)
        )


def test_plaintext_otp_not_persisted_or_logged(caplog: pytest.LogCaptureFixture) -> None:
    store = _shared_store()
    sms = DevSmsAdapter()
    svc = _svc(store, sms)
    caplog.set_level(logging.INFO)
    issued = svc.request_otp("+919800000006")
    code = issued["sms"]["debug_code"]
    assert code
    assert "debug_code" in issued["sms"]
    record = store.get_challenge(issued["challenge_id"])
    assert record is not None
    blob = str(record.challenge)
    assert code not in blob
    assert record.challenge.code_hash.startswith("sha256$")
    assert code not in record.challenge.code_hash
    joined = " ".join(record.message for record in caplog.records)
    assert code not in joined
    public = {k: v for k, v in issued.items() if k != "sms"}
    assert code not in str(public)


def test_destination_is_not_database_key() -> None:
    store = _shared_store()
    sms = DevSmsAdapter()
    svc = _svc(store, sms)
    mobile = "+919800000007"
    issued = svc.request_otp(mobile)
    ids = store._persistence.list_ids("metadata")
    assert mobile not in ids
    assert not any(mobile in item for item in ids)


def test_stale_consumed_challenge_pruned_after_keep_window() -> None:
    store = _shared_store()
    sms = DevSmsAdapter()
    svc = _svc(store, sms)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    issued = svc.request_otp("+919800000008", now=now)
    code = issued["sms"]["debug_code"]
    svc.verify_otp(challenge_id=issued["challenge_id"], code=code, now=now)
    still = store.get_challenge(issued["challenge_id"], now=now + timedelta(minutes=10))
    assert still is not None
    assert still.challenge.consumed
    gone = store.get_challenge(issued["challenge_id"], now=now + timedelta(hours=2))
    assert gone is None


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
    store = default_otp_store()
    assert store._persistence.registry.storage.provider_id == "postgres"
