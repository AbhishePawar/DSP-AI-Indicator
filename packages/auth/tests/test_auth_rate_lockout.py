"""Stage 0O: durable rate limits, lockout, and remaining auth races."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from auth.exceptions import AuthenticationError, RefreshTokenReuseError, SessionError
from auth.lockout import AuthLockoutStore
from auth.mfa_totp import TotpAdapter, totp_at
from auth.rate_limit import AuthRateLimiter
from auth.sessions import SessionManager
from auth.single_use_tokens import SingleUseTokenError, SingleUseTokenService
from datetime import timedelta
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
)


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_AUTH_JWT_SECRET", "test-secret")
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")


def _persistence() -> PersistenceService:
    return PersistenceService(RepositoryRegistry(storage=InMemoryStorageProvider()))


# -- Rate limiter ------------------------------------------------------------


def test_isolated_rate_limiters_do_not_share_counters() -> None:
    a = AuthRateLimiter(_persistence())
    b = AuthRateLimiter(_persistence())
    for _ in range(3):
        a.check("login:attacker", limit=3, window_sec=300)
    b.check("login:attacker", limit=3, window_sec=300)
    with pytest.raises(AuthenticationError, match="Rate limit exceeded"):
        a.check("login:attacker", limit=3, window_sec=300)


def test_shared_rate_limiters_enforce_across_instances() -> None:
    persistence = _persistence()
    a = AuthRateLimiter(persistence)
    b = AuthRateLimiter(persistence)
    for _ in range(3):
        a.check("login:shared", limit=3, window_sec=300)
    with pytest.raises(AuthenticationError, match="Rate limit exceeded"):
        b.check("login:shared", limit=3, window_sec=300)


def test_rate_keys_are_isolated() -> None:
    limiter = AuthRateLimiter(_persistence())
    for _ in range(2):
        limiter.check("login:user-a", limit=2, window_sec=300)
    limiter.check("login:user-b", limit=2, window_sec=300)
    with pytest.raises(AuthenticationError, match="Rate limit exceeded"):
        limiter.check("login:user-a", limit=2, window_sec=300)


def test_rate_entity_ids_are_hmac() -> None:
    persistence = _persistence()
    limiter = AuthRateLimiter(persistence)
    limiter.check("login:203.0.113.9", limit=5, window_sec=60)
    ids = persistence.list_ids("metadata")
    assert "203.0.113.9" not in ids
    assert not any("203.0.113.9" in item for item in ids)
    assert any(item.startswith("auth-rate-") for item in ids)


def test_concurrent_rate_increments_cap_exactly() -> None:
    persistence = _persistence()
    barrier = threading.Barrier(8)

    def attempt() -> str:
        limiter = AuthRateLimiter(persistence)
        barrier.wait()
        try:
            limiter.check("login:burst", limit=3, window_sec=300)
            return "ok"
        except AuthenticationError:
            return "limited"

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = [fut.result() for fut in as_completed([pool.submit(attempt) for _ in range(8)])]
    assert results.count("ok") == 3
    assert results.count("limited") == 5


# -- Lockout -----------------------------------------------------------------


def _user_and_store():
    from auth.users import UserStore

    persistence = _persistence()
    users = UserStore(persistence)
    user = users.create(
        username="lockuser",
        email="lock@example.com",
        password="StrongPass1!",
    )
    return user, AuthLockoutStore(persistence), users, persistence


def test_lockout_threshold_is_atomic_and_shared() -> None:
    user, store, users, persistence = _user_and_store()
    other = AuthLockoutStore(persistence)
    for _ in range(2):
        store.record_failure(user, threshold=3, lockout_seconds=900)
        user = users.get(user.user_id)
        assert user is not None
    other.record_failure(user, threshold=3, lockout_seconds=900)
    locked = users.get(user.user_id)
    assert locked is not None
    assert locked.status == "locked"
    assert other.is_locked(user.user_id, threshold=3) is True


def test_isolated_lockout_stores_do_not_share_counters() -> None:
    user, store, users, _ = _user_and_store()
    other_ps = _persistence()
    from auth.users import UserStore

    other_users = UserStore(other_ps)
    clone = other_users.create(
        username="lockuser",
        email="lock@example.com",
        password="StrongPass1!",
        user_id=user.user_id,
    )
    other = AuthLockoutStore(other_ps)
    for _ in range(3):
        store.record_failure(user, threshold=3, lockout_seconds=900)
        user = users.get(user.user_id)
        assert user is not None
    assert store.is_locked(user.user_id, threshold=3) is True
    assert other.is_locked(clone.user_id, threshold=3) is False


def test_concurrent_lockout_increments_reach_threshold_once() -> None:
    user, store, users, persistence = _user_and_store()
    barrier = threading.Barrier(6)

    def attempt() -> int:
        live = AuthLockoutStore(persistence)
        current = users.get(user.user_id)
        assert current is not None
        barrier.wait()
        return live.record_failure(current, threshold=5, lockout_seconds=900)

    with ThreadPoolExecutor(max_workers=6) as pool:
        counts = [fut.result() for fut in as_completed([pool.submit(attempt) for _ in range(6)])]
    assert max(counts) >= 5
    assert store.is_locked(user.user_id, threshold=5) is True
    locked = users.get(user.user_id)
    assert locked is not None
    assert locked.status == "locked"


def test_lockout_reset_clears_counter() -> None:
    user, store, users, _ = _user_and_store()
    for _ in range(3):
        store.record_failure(user, threshold=3, lockout_seconds=900)
        user = users.get(user.user_id)
        assert user is not None
    store.reset(user.user_id)
    assert store.is_locked(user.user_id, threshold=3) is False


# -- Single-use tokens across process replicas --------------------------------


def test_isolated_token_services_cannot_consume_each_others_tokens() -> None:
    a = SingleUseTokenService(_persistence())
    b = SingleUseTokenService(_persistence())
    token = a.issue(purpose="magic_link", ttl=timedelta(minutes=15))
    with pytest.raises(SingleUseTokenError):
        b.consume(purpose="magic_link", token=token)


def test_shared_token_services_consume_once_across_instances() -> None:
    persistence = _persistence()
    a = SingleUseTokenService(persistence)
    b = SingleUseTokenService(persistence)
    token = a.issue(purpose="password_reset", ttl=timedelta(hours=1), user_id="u-1")
    record = b.consume(purpose="password_reset", token=token)
    assert record.user_id == "u-1"
    with pytest.raises(SingleUseTokenError):
        a.consume(purpose="password_reset", token=token)


def test_cross_instance_concurrent_token_consume_one_success() -> None:
    persistence = _persistence()
    token = SingleUseTokenService(persistence).issue(
        purpose="magic_link", ttl=timedelta(minutes=15)
    )
    barrier = threading.Barrier(2)

    def attempt() -> str:
        svc = SingleUseTokenService(persistence)
        barrier.wait()
        try:
            svc.consume(purpose="magic_link", token=token)
            return "ok"
        except SingleUseTokenError:
            return "fail"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [fut.result() for fut in as_completed([pool.submit(attempt), pool.submit(attempt)])]
    assert results.count("ok") == 1
    assert results.count("fail") == 1


# -- Refresh rotation across process replicas --------------------------------


def test_cross_instance_refresh_rotation_one_success() -> None:
    persistence = _persistence()
    a = SessionManager(persistence)
    b = SessionManager(persistence)
    session = a.create(user_id="u-rot", refresh_token_id="rid-1")
    a.attach_refresh_material(session.session_id, token_id="rid-1", token_hash="hash-1")
    barrier = threading.Barrier(2)

    def attempt(mgr: SessionManager, new_id: str) -> str:
        barrier.wait()
        try:
            mgr.rotate_refresh_token(
                session.session_id,
                expected_token_id="rid-1",
                expected_token_hash="hash-1",
                new_token_id=new_id,
                new_token_hash=f"hash-{new_id}",
            )
            return "ok"
        except RefreshTokenReuseError:
            return "reuse"
        except SessionError:
            return "revoked"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            fut.result()
            for fut in as_completed(
                [
                    pool.submit(attempt, a, "rid-2"),
                    pool.submit(attempt, b, "rid-3"),
                ]
            )
        ]
    assert results.count("ok") == 1
    assert "reuse" in results or "revoked" in results
    live = a.get(session.session_id)
    assert live is not None
    assert live.revoked is True or live.refresh_token_id in {"rid-2", "rid-3"}


# -- TOTP last-used counter / recovery atomicity -----------------------------


def test_totp_replay_and_concurrent_same_counter() -> None:
    persistence = _persistence()
    adapter = TotpAdapter(persistence)
    begin = adapter.begin_enroll("user-totp-race")
    confirmed = adapter.confirm_enroll("user-totp-race", {"code": totp_at(begin["secret"])})
    assert confirmed["ok"] is True
    later = totp_at(begin["secret"], for_time=__import__("time").time() + 31)
    barrier = threading.Barrier(2)

    def attempt() -> bool:
        replica = TotpAdapter(persistence)
        barrier.wait()
        return replica.verify_challenge("user-totp-race", {"code": later})

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [fut.result() for fut in as_completed([pool.submit(attempt), pool.submit(attempt)])]
    assert results.count(True) == 1
    assert results.count(False) == 1
    assert adapter.verify_challenge("user-totp-race", {"code": later}) is False


def test_recovery_code_concurrent_consume_one_success() -> None:
    persistence = _persistence()
    adapter = TotpAdapter(persistence)
    begin = adapter.begin_enroll("user-rec-race")
    confirmed = adapter.confirm_enroll("user-rec-race", {"code": totp_at(begin["secret"])})
    code = confirmed["recovery_codes"][0]
    barrier = threading.Barrier(2)

    def attempt() -> bool:
        replica = TotpAdapter(persistence)
        barrier.wait()
        return replica.verify_challenge("user-rec-race", {"recovery_code": code})

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [fut.result() for fut in as_completed([pool.submit(attempt), pool.submit(attempt)])]
    assert results.count(True) == 1
    assert results.count(False) == 1
    assert adapter.verify_challenge("user-rec-race", {"recovery_code": code}) is False
