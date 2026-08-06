"""Refresh-token rotation + reuse detection (OAuth 2.0 Security BCP).

Covers both layers that share one ``AuthenticationService``/``SessionManager``:

* the bare A009 :class:`~auth.service.AuthService` (also what backs the
  pre-existing ``/auth/rbac/refresh`` endpoint), and
* :class:`~auth.enterprise_platform.EnterpriseAuthPlatform`, which wires the
  shared :class:`~auth.audit.AuditLogger` onto the same
  ``AuthenticationService`` instance so refresh-rotation events are audited
  for free with zero duplicate logic or storage.
"""

from __future__ import annotations

import threading

import pytest

from auth import (
    AuthenticationError,
    AuthService,
    InvalidTokenError,
    RefreshTokenReuseError,
    RoleRegistry,
    reset_auth_service_for_tests,
    reset_enterprise_auth_platform_for_tests,
    reset_role_registry_for_tests,
)
from auth.enterprise_platform import EnterpriseAuthPlatform
from auth.otp import OtpService
from auth.sms import DevSmsAdapter
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
)


@pytest.fixture()
def auth_service() -> AuthService:
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    svc = AuthService(ps, jwt_secret="test-secret")
    reset_auth_service_for_tests(svc)
    yield svc
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


@pytest.fixture()
def platform(
    auth_service: AuthService, monkeypatch: pytest.MonkeyPatch
) -> EnterpriseAuthPlatform:
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    plat = EnterpriseAuthPlatform(auth_service, otp=OtpService(DevSmsAdapter()))
    reset_enterprise_auth_platform_for_tests(plat)
    yield plat
    reset_enterprise_auth_platform_for_tests(None)


def _register_and_login(plat: EnterpriseAuthPlatform, *, email: str = "trader@example.com"):
    reg = plat.register_email(
        name="Trader",
        email=email,
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    plat.verify_email(reg["verification_token"])
    return plat.login_password(identifier=email, password="StrongPass12!")


# --------------------------------------------------------------------------
# Bare AuthService (A009) — core rotation semantics, no audit dependency.
# --------------------------------------------------------------------------


def test_refresh_rotates_both_tokens(auth_service: AuthService) -> None:
    auth_service.create_user(
        username="analyst1",
        email="a1@example.com",
        password="Secret123!",
        user_id="u-1",
    )
    login = auth_service.login(username="analyst1", password="Secret123!")
    refreshed = auth_service.refresh(refresh_token=login["tokens"]["refresh_token"])

    assert refreshed["tokens"]["access_token"] != login["tokens"]["access_token"]
    assert refreshed["tokens"]["refresh_token"] != login["tokens"]["refresh_token"]
    assert refreshed["session"]["session_id"] == login["session"]["session_id"]
    # The public session view never echoes the internal security digest.
    assert "refresh_token_hash" not in refreshed["session"]


def test_rotated_away_token_cannot_be_reused(auth_service: AuthService) -> None:
    auth_service.create_user(
        username="analyst1", email="a1@example.com", password="Secret123!", user_id="u-1"
    )
    login = auth_service.login(username="analyst1", password="Secret123!")
    old_refresh = login["tokens"]["refresh_token"]

    first = auth_service.refresh(refresh_token=old_refresh)
    new_refresh = first["tokens"]["refresh_token"]

    # Replaying the already-rotated-away token is a reuse/replay attack.
    with pytest.raises(RefreshTokenReuseError):
        auth_service.refresh(refresh_token=old_refresh)

    # The whole family (session) is revoked — even the *legitimately* rotated
    # token from the successful call above is now dead.
    with pytest.raises(InvalidTokenError):
        auth_service.refresh(refresh_token=new_refresh)


def test_family_wide_revocation_kills_every_lineage_member(auth_service: AuthService) -> None:
    """Reuse of ANY prior token in the chain kills the entire lineage, not just its child."""
    auth_service.create_user(
        username="analyst1", email="a1@example.com", password="Secret123!", user_id="u-1"
    )
    login = auth_service.login(username="analyst1", password="Secret123!")
    v1 = login["tokens"]["refresh_token"]
    r1 = auth_service.refresh(refresh_token=v1)
    v2 = r1["tokens"]["refresh_token"]
    r2 = auth_service.refresh(refresh_token=v2)
    v3 = r2["tokens"]["refresh_token"]

    # v3 is the only currently-valid token. Replay the very first one (v1).
    with pytest.raises(RefreshTokenReuseError):
        auth_service.refresh(refresh_token=v1)

    # v3, though never itself replayed, is now dead too (family revoked).
    with pytest.raises(InvalidTokenError):
        auth_service.refresh(refresh_token=v3)


def test_expired_refresh_token_rejected(auth_service: AuthService) -> None:
    from datetime import datetime, timedelta, timezone

    auth_service.create_user(
        username="analyst1", email="a1@example.com", password="Secret123!", user_id="u-1"
    )
    login = auth_service.login(username="analyst1", password="Secret123!")
    far_future = datetime.now(tz=timezone.utc) + timedelta(days=30)
    with pytest.raises(InvalidTokenError):
        auth_service.refresh(refresh_token=login["tokens"]["refresh_token"], now=far_future)


def test_revoked_session_refresh_rejected(auth_service: AuthService) -> None:
    auth_service.create_user(
        username="analyst1", email="a1@example.com", password="Secret123!", user_id="u-1"
    )
    login = auth_service.login(username="analyst1", password="Secret123!")
    auth_service.logout(session_id=login["session"]["session_id"])
    with pytest.raises(InvalidTokenError):
        auth_service.refresh(refresh_token=login["tokens"]["refresh_token"])


def test_malformed_or_wrong_token_use_rejected(auth_service: AuthService) -> None:
    auth_service.create_user(
        username="analyst1", email="a1@example.com", password="Secret123!", user_id="u-1"
    )
    login = auth_service.login(username="analyst1", password="Secret123!")
    with pytest.raises(InvalidTokenError):
        auth_service.refresh(refresh_token=login["tokens"]["access_token"])
    with pytest.raises(InvalidTokenError):
        auth_service.refresh(refresh_token="not-a-jwt")


def test_parallel_refresh_requests_only_one_wins(auth_service: AuthService) -> None:
    """Two concurrent requests presenting the same still-valid refresh token.

    Only one may succeed; the loser is treated as reuse (its token was
    rotated away by the winner microseconds earlier) and the whole session
    is revoked — including the winner's brand-new tokens. This is the
    intentionally strict, spec-compliant interpretation of "concurrent
    refresh protection": the system never allows two token pairs to be
    minted from a single refresh token, under any timing.
    """
    auth_service.create_user(
        username="analyst1", email="a1@example.com", password="Secret123!", user_id="u-1"
    )
    login = auth_service.login(username="analyst1", password="Secret123!")
    token = login["tokens"]["refresh_token"]

    results: list[tuple[str, object]] = []
    barrier = threading.Barrier(2)

    def _attempt() -> None:
        barrier.wait(timeout=5)
        try:
            out = auth_service.refresh(refresh_token=token)
            results.append(("ok", out))
        except Exception as exc:  # noqa: BLE001
            results.append(("error", exc))

    threads = [threading.Thread(target=_attempt) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    oks = [r for kind, r in results if kind == "ok"]
    errors = [r for kind, r in results if kind == "error"]
    assert len(oks) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], RefreshTokenReuseError)

    # Session is dead afterwards, regardless of which side "won".
    session_id = login["session"]["session_id"]
    with pytest.raises(Exception):  # noqa: PT011 - SessionError/InvalidTokenError
        auth_service.authentication.sessions.require_active(session_id)


def test_session_specific_revocation_does_not_affect_other_sessions(
    auth_service: AuthService,
) -> None:
    auth_service.create_user(
        username="analyst1", email="a1@example.com", password="Secret123!", user_id="u-1"
    )
    session_a = auth_service.login(
        username="analyst1", password="Secret123!", session_id="sess-a"
    )
    session_b = auth_service.login(
        username="analyst1", password="Secret123!", session_id="sess-b"
    )

    auth_service.logout(session_id="sess-a")

    with pytest.raises(InvalidTokenError):
        auth_service.refresh(refresh_token=session_a["tokens"]["refresh_token"])

    # Session B is untouched and rotates normally.
    refreshed_b = auth_service.refresh(refresh_token=session_b["tokens"]["refresh_token"])
    assert refreshed_b["tokens"]["refresh_token"] != session_b["tokens"]["refresh_token"]


# --------------------------------------------------------------------------
# EnterpriseAuthPlatform — audit wiring + platform-level entry point.
# --------------------------------------------------------------------------


def test_refresh_session_wrapper_matches_bare_authservice(
    platform: EnterpriseAuthPlatform,
) -> None:
    login = _register_and_login(platform)
    out = platform.refresh_session(refresh_token=login["tokens"]["refresh_token"])
    assert out["tokens"]["refresh_token"] != login["tokens"]["refresh_token"]
    assert out["session"]["session_id"] == login["session"]["session_id"]


def test_refresh_audit_trail_issued_and_rotated(platform: EnterpriseAuthPlatform) -> None:
    login = _register_and_login(platform)
    user_id = login["user"]["user_id"]
    platform.refresh_session(refresh_token=login["tokens"]["refresh_token"])

    events = platform.audit.list_events(user_id=user_id)
    types = [e["event_type"] for e in events]
    assert "refresh.issued" in types
    assert "refresh.rotated" in types


def test_refresh_reuse_audit_trail(platform: EnterpriseAuthPlatform) -> None:
    login = _register_and_login(platform)
    user_id = login["user"]["user_id"]
    old_refresh = login["tokens"]["refresh_token"]
    platform.refresh_session(refresh_token=old_refresh)

    with pytest.raises(RefreshTokenReuseError):
        platform.refresh_session(refresh_token=old_refresh)

    events = platform.audit.list_events(user_id=user_id)
    types = [e["event_type"] for e in events]
    assert "refresh.reused" in types
    assert "refresh.revoked" in types
    assert "session.revoked" in types


def test_admin_revoke_sessions_emits_session_revoked_audit(
    platform: EnterpriseAuthPlatform,
) -> None:
    login = _register_and_login(platform)
    user_id = login["user"]["user_id"]
    result = platform.revoke_sessions_for_user(user_id)
    assert result["sessions_revoked"] >= 1

    events = platform.audit.list_events(user_id=user_id, event_type="session.revoked")
    assert len(events) >= 1

    with pytest.raises(InvalidTokenError):
        platform.refresh_session(refresh_token=login["tokens"]["refresh_token"])


def test_password_reset_revokes_sessions_with_audit(platform: EnterpriseAuthPlatform) -> None:
    login = _register_and_login(platform)
    user_id = login["user"]["user_id"]

    req = platform.request_password_reset("trader@example.com")
    token = req["reset_token"]
    platform.confirm_password_reset(token, "EvenStrongerPass1!")

    events = platform.audit.list_events(user_id=user_id, event_type="session.revoked")
    assert len(events) >= 1
    with pytest.raises(InvalidTokenError):
        platform.refresh_session(refresh_token=login["tokens"]["refresh_token"])
