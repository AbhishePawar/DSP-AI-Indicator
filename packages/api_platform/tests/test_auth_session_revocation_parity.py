"""Comprehensive parity and regression tests for session revocation across dsp-security and dsp-auth."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from api_platform.api.app import create_app
from auth import (
    AuthService,
    RoleRegistry,
    reset_auth_service_for_tests,
    reset_role_registry_for_tests,
)
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
    reset_repository_registry_for_tests,
)
from security_platform import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    CSRF_HEADER,
    REFRESH_COOKIE,
    SESSION_COOKIE,
    Role,
    SecurityBundle,
    SecuritySettings,
)
from security_platform.security.identity.ports import SessionRecord


@pytest.fixture
def sec_bundle():
    bundle = SecurityBundle.create(
        SecuritySettings(jwt_secret="unit-test-secret-parity-016"),
        seed_admin=False,
    )
    bundle.identity.provision(
        username="parityuser",
        role=Role.RESEARCHER,
        password="StrongPass1234!",
    )
    bundle.identity.provision(
        username="otheruser",
        role=Role.ADVISOR,
        password="StrongPass1234!",
    )
    return bundle


@pytest.fixture
def sec_client(sec_bundle):
    prior = {
        k: os.environ.get(k)
        for k in (
            "DSP_COOKIE_AUTH",
            "DSP_COOKIE_SECURE",
            "DSP_CSRF_ENABLED",
            "DSP_ENABLE_SECURITY",
        )
    }
    os.environ["DSP_COOKIE_AUTH"] = "true"
    os.environ["DSP_COOKIE_SECURE"] = "false"
    os.environ["DSP_CSRF_ENABLED"] = "true"
    os.environ.pop("DSP_ENABLE_SECURITY", None)

    app = create_app(security=sec_bundle, enable_security=False)
    with TestClient(app) as client:
        yield client

    for k, v in prior.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


@pytest.fixture
def inst_client():
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_role_registry_for_tests(RoleRegistry())
    reset_auth_service_for_tests(AuthService(ps, jwt_secret="test-secret-inst"))
    app = create_app(enable_security=False)
    with TestClient(app) as c:
        yield c
    reset_auth_service_for_tests(None)


def test_dsp_security_login_and_protected_route_and_logout_replay_rejection(
    sec_client, sec_bundle
):
    # 1. Login
    login_resp = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "parityuser", "password": "StrongPass1234!"},
    )
    assert login_resp.status_code == 200
    access_token = login_resp.cookies[ACCESS_COOKIE]
    refresh_token = login_resp.json()["payload"]["refresh_token"]
    csrf_token = login_resp.cookies[CSRF_COOKIE]

    # Verify JWT extra has sid
    claims = sec_bundle.jwt.verify(access_token)
    session_id = claims.extra.get("sid")
    assert session_id is not None
    assert sec_bundle.identity.get_session(session_id) is not None

    # 2. Access genuine protected endpoint
    prot_resp = sec_client.get(
        "/workflow/schema",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert prot_resp.status_code == 200

    # 3. Access session probe
    probe_resp = sec_client.get(
        "/auth/session",
        cookies={ACCESS_COOKIE: access_token, SESSION_COOKIE: session_id},
    )
    assert probe_resp.status_code == 200
    assert probe_resp.json()["payload"]["authenticated"] is True
    assert probe_resp.json()["payload"]["session_id"] == session_id

    # 4. Logout
    logout_resp = sec_client.post(
        "/api/v1/auth/logout",
        cookies={
            ACCESS_COOKIE: access_token,
            REFRESH_COOKIE: refresh_token,
            SESSION_COOKIE: session_id,
            CSRF_COOKIE: csrf_token,
        },
        headers={CSRF_HEADER: csrf_token},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["payload"]["logged_out"] is True
    assert ACCESS_COOKIE not in logout_resp.cookies

    # Server session must be deleted
    assert sec_bundle.identity.get_session(session_id) is None

    # 5. Replay old access token against protected endpoint -> 401
    replay_resp = sec_client.get(
        "/workflow/schema",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert replay_resp.status_code == 401
    assert "session revoked or expired" in replay_resp.json().get("detail", "")

    # 6. Replay old access token against session probe -> authenticated: False
    probe_replay = sec_client.get(
        "/auth/session",
        cookies={ACCESS_COOKIE: access_token, SESSION_COOKIE: session_id},
    )
    assert probe_replay.status_code == 200
    assert probe_replay.json()["payload"]["authenticated"] is False

    # 7. Replay old refresh token against refresh endpoint -> 401
    refresh_replay = sec_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_replay.status_code == 401


def test_dsp_security_refresh_rotation_preserves_session_and_rejects_replay(
    sec_client, sec_bundle
):
    # 1. Login
    login_resp = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "parityuser", "password": "StrongPass1234!"},
    )
    orig_access = login_resp.cookies[ACCESS_COOKIE]
    orig_refresh = login_resp.json()["payload"]["refresh_token"]
    orig_claims = sec_bundle.jwt.verify(orig_access)
    orig_sid = orig_claims.extra["sid"]

    # 2. Refresh rotation
    refresh_resp = sec_client.post(
        "/auth/refresh",
        json={"refresh_token": orig_refresh},
    )
    assert refresh_resp.status_code == 200
    new_access = refresh_resp.json()["payload"]["access_token"]
    new_refresh = refresh_resp.json()["payload"]["refresh_token"]

    # Verify session ID preserved
    new_claims = sec_bundle.jwt.verify(new_access)
    assert new_claims.extra["sid"] == orig_sid

    # Verify old refresh token is marked revoked
    old_rec = sec_bundle.identity.tokens.get_refresh_record(orig_refresh)
    assert old_rec is not None
    assert old_rec.revoked is True

    # 3. Replay old refresh token -> 401
    replay_resp = sec_client.post(
        "/auth/refresh",
        json={"refresh_token": orig_refresh},
    )
    assert replay_resp.status_code == 401

    # 4. New access token works on protected endpoint
    prot_resp = sec_client.get(
        "/workflow/schema",
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert prot_resp.status_code == 200


def test_concurrent_sessions_isolated_on_logout(sec_client, sec_bundle):
    # User logs in on two devices
    login_1 = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "parityuser", "password": "StrongPass1234!"},
    )
    token_1 = login_1.cookies[ACCESS_COOKIE]
    refresh_1 = login_1.json()["payload"]["refresh_token"]
    csrf_1 = login_1.cookies[CSRF_COOKIE]
    sid_1 = sec_bundle.jwt.verify(token_1).extra["sid"]

    login_2 = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "parityuser", "password": "StrongPass1234!"},
    )
    token_2 = login_2.cookies[ACCESS_COOKIE]
    refresh_2 = login_2.json()["payload"]["refresh_token"]
    sid_2 = sec_bundle.jwt.verify(token_2).extra["sid"]

    assert sid_1 != sid_2

    # Both sessions work
    assert (
        sec_client.get(
            "/workflow/schema", headers={"Authorization": f"Bearer {token_1}"}
        ).status_code
        == 200
    )
    assert (
        sec_client.get(
            "/workflow/schema", headers={"Authorization": f"Bearer {token_2}"}
        ).status_code
        == 200
    )

    # Logout session 1 only
    logout_1 = sec_client.post(
        "/api/v1/auth/logout",
        cookies={
            ACCESS_COOKIE: token_1,
            REFRESH_COOKIE: refresh_1,
            SESSION_COOKIE: sid_1,
            CSRF_COOKIE: csrf_1,
        },
        headers={CSRF_HEADER: csrf_1},
    )
    assert logout_1.status_code == 200

    # Session 1 is revoked
    assert sec_bundle.identity.get_session(sid_1) is None
    assert (
        sec_client.get(
            "/workflow/schema", headers={"Authorization": f"Bearer {token_1}"}
        ).status_code
        == 401
    )

    # Session 2 is PRESERVED and active
    assert sec_bundle.identity.get_session(sid_2) is not None
    assert (
        sec_client.get(
            "/workflow/schema", headers={"Authorization": f"Bearer {token_2}"}
        ).status_code
        == 200
    )

    # Session 2 can still refresh
    ref_2 = sec_client.post("/auth/refresh", json={"refresh_token": refresh_2})
    assert ref_2.status_code == 200
    assert (
        sec_bundle.jwt.verify(ref_2.json()["payload"]["access_token"]).extra["sid"]
        == sid_2
    )


def test_dsp_auth_login_logout_and_concurrent_session_preservation(inst_client):
    # Provision institutional user
    u_resp = inst_client.post(
        "/api/v1/auth/rbac/users",
        json={
            "username": "inst_user",
            "email": "inst@example.com",
            "password": "Password1234!",
            "user_id": "u-inst-1",
        },
    )
    assert u_resp.status_code == 200

    # Login 1
    login_1 = inst_client.post(
        "/api/v1/auth/rbac/login",
        json={"username": "inst_user", "password": "Password1234!"},
    )
    assert login_1.status_code == 200
    res_1 = login_1.json()["result"]
    token_1 = res_1["tokens"]["access_token"]
    sid_1 = res_1["session"]["session_id"]
    csrf_1 = login_1.cookies.get(CSRF_COOKIE, "test-csrf")

    # Login 2
    login_2 = inst_client.post(
        "/api/v1/auth/rbac/login",
        json={"username": "inst_user", "password": "Password1234!"},
    )
    assert login_2.status_code == 200
    res_2 = login_2.json()["result"]
    token_2 = res_2["tokens"]["access_token"]
    sid_2 = res_2["session"]["session_id"]

    assert sid_1 != sid_2

    # Both work on /auth/rbac/me
    assert (
        inst_client.get(
            "/api/v1/auth/rbac/me", headers={"Authorization": f"Bearer {token_1}"}
        ).status_code
        == 200
    )
    assert (
        inst_client.get(
            "/api/v1/auth/rbac/me", headers={"Authorization": f"Bearer {token_2}"}
        ).status_code
        == 200
    )

    # Logout session 1 via unified /auth/logout
    logout_resp = inst_client.post(
        "/api/v1/auth/logout",
        cookies={
            ACCESS_COOKIE: token_1,
            SESSION_COOKIE: sid_1,
            CSRF_COOKIE: csrf_1,
        },
        headers={CSRF_HEADER: csrf_1},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["payload"]["logged_out"] is True

    # Token 1 is now rejected on /auth/rbac/me
    me_1 = inst_client.get(
        "/api/v1/auth/rbac/me", headers={"Authorization": f"Bearer {token_1}"}
    )
    assert me_1.status_code == 401

    # Token 2 STILL WORKS on /auth/rbac/me
    me_2 = inst_client.get(
        "/api/v1/auth/rbac/me", headers={"Authorization": f"Bearer {token_2}"}
    )
    assert me_2.status_code == 200

    # Session probe with token 2 succeeds
    probe_2 = inst_client.get(
        "/auth/session",
        cookies={ACCESS_COOKIE: token_2, SESSION_COOKIE: sid_2},
    )
    assert probe_2.status_code == 200
    assert probe_2.json()["payload"]["authenticated"] is True
    assert probe_2.json()["payload"]["session_id"] == sid_2


def test_session_security_properties_validation(sec_client, sec_bundle):
    # 1. Session belonging to another user
    other_user = sec_bundle.identity.users.get_by_username("otheruser")
    other_pair = sec_bundle.identity.tokens.issue_pair(other_user)
    other_sid = other_pair.session_id

    parity_user = sec_bundle.identity.users.get_by_username("parityuser")
    # Craft token for parityuser but pointing to otheruser's session
    spoofed_token = sec_bundle.jwt.issue(
        subject=parity_user.user_id,
        role=parity_user.role,
        username=parity_user.username,
        ttl_seconds=3600,
        extra={"sid": other_sid},
    )
    resp = sec_client.get(
        "/workflow/schema", headers={"Authorization": f"Bearer {spoofed_token}"}
    )
    assert resp.status_code == 401
    assert "session user mismatch" in resp.json().get("detail", "")

    # 2. Expired session
    expired_sid = "expired-sid-123"
    sec_bundle.identity.tokens._sessions.create(
        SessionRecord(
            session_id=expired_sid,
            user_id=parity_user.user_id,
            expires_at=datetime.now(tz=UTC) - timedelta(hours=1),
        )
    )
    expired_token = sec_bundle.jwt.issue(
        subject=parity_user.user_id,
        role=parity_user.role,
        username=parity_user.username,
        ttl_seconds=3600,
        extra={"sid": expired_sid},
    )
    resp_exp = sec_client.get(
        "/workflow/schema", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert resp_exp.status_code == 401
    assert "session expired" in resp_exp.json().get("detail", "")

    # 3. Invalid signature
    tampered = spoofed_token[:-5] + "xxxxx"
    assert (
        sec_client.get(
            "/workflow/schema", headers={"Authorization": f"Bearer {tampered}"}
        ).status_code
        == 401
    )


def test_conflicting_credentials_and_bearer_policy(sec_client, sec_bundle):
    login_resp = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "parityuser", "password": "StrongPass1234!"},
    )
    access_token = login_resp.cookies[ACCESS_COOKIE]
    csrf_token = login_resp.cookies[CSRF_COOKIE]
    sid = sec_bundle.jwt.verify(access_token).extra["sid"]

    # 1. Conflicting cookie and Bearer header
    login_other = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "otheruser", "password": "StrongPass1234!"},
    )
    other_access = login_other.cookies[ACCESS_COOKIE]

    conflict_resp = sec_client.post(
        "/api/v1/auth/logout",
        cookies={
            ACCESS_COOKIE: access_token,
            CSRF_COOKIE: csrf_token,
        },
        headers={
            CSRF_HEADER: csrf_token,
            "Authorization": f"Bearer {other_access}",
        },
    )
    assert conflict_resp.status_code == 400
    assert conflict_resp.json()["error"] == "ConflictingCredentialsError"

    # 2. Conflicting SESSION_COOKIE vs token sid
    conflict_sid = sec_client.post(
        "/api/v1/auth/logout",
        cookies={
            ACCESS_COOKIE: access_token,
            SESSION_COOKIE: "different-session-id",
            CSRF_COOKIE: csrf_token,
        },
        headers={CSRF_HEADER: csrf_token},
    )
    assert conflict_sid.status_code == 400
    assert conflict_sid.json()["error"] == "ConflictingCredentialsError"

    # 3. Bearer-only logout (no cookies) under documented CSRF policy
    bearer_logout = sec_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert bearer_logout.status_code == 200
    assert sec_bundle.identity.get_session(sid) is None


def test_logout_csrf_and_repeated_logout_and_revocation_failure(sec_client, sec_bundle):
    # 1. Missing CSRF on cookie logout -> 403
    login_res = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "parityuser", "password": "StrongPass1234!"},
    )
    tok = login_res.cookies[ACCESS_COOKIE]
    csrf = login_res.cookies[CSRF_COOKIE]

    bad_csrf = sec_client.post(
        "/api/v1/auth/logout",
        cookies={ACCESS_COOKIE: tok, CSRF_COOKIE: csrf},
    )
    assert bad_csrf.status_code == 403
    assert bad_csrf.json()["error"] == "CSRFError"

    # 2. Repeated logout -> safe 200
    login_resp = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "parityuser", "password": "StrongPass1234!"},
    )
    access_token = login_resp.cookies[ACCESS_COOKIE]
    csrf_token = login_resp.cookies[CSRF_COOKIE]
    sid = sec_bundle.jwt.verify(access_token).extra["sid"]

    rep1 = sec_client.post(
        "/api/v1/auth/logout",
        cookies={
            ACCESS_COOKIE: access_token,
            SESSION_COOKIE: sid,
            CSRF_COOKIE: csrf_token,
        },
        headers={CSRF_HEADER: csrf_token},
    )
    assert rep1.status_code == 200

    # Repeated logout with now-revoked session token -> 401 (token session revoked)
    rep2 = sec_client.post(
        "/api/v1/auth/logout",
        cookies={
            ACCESS_COOKIE: access_token,
            SESSION_COOKIE: sid,
            CSRF_COOKIE: csrf_token,
        },
        headers={CSRF_HEADER: csrf_token},
    )
    assert rep2.status_code == 401

    # Unauthenticated logout with no cookies -> 401 (EPIC-016 contract)
    unauth = sec_client.post("/api/v1/auth/logout")
    assert unauth.status_code == 401

    # 3. Revocation failure handling -> 500 while clearing cookies
    login_3 = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "parityuser", "password": "StrongPass1234!"},
    )
    token_3 = login_3.cookies[ACCESS_COOKIE]
    csrf_3 = login_3.cookies[CSRF_COOKIE]
    sid_3 = sec_bundle.jwt.verify(token_3).extra["sid"]

    with patch.object(
        sec_bundle.identity, "logout", side_effect=RuntimeError("Storage failure")
    ):
        fail_resp = sec_client.post(
            "/api/v1/auth/logout",
            cookies={
                ACCESS_COOKIE: token_3,
                SESSION_COOKIE: sid_3,
                CSRF_COOKIE: csrf_3,
            },
            headers={CSRF_HEADER: csrf_3},
        )
        assert fail_resp.status_code == 500
        assert fail_resp.json()["error"] == "RevocationError"
        assert fail_resp.json()["payload"]["logged_out"] is False
        assert ACCESS_COOKIE not in fail_resp.cookies
