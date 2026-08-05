"""API-level tests for the canonical `/auth/mfa/*` TOTP endpoints.

`POST /auth/mfa/enroll|enable|verify|disable`, `GET /auth/mfa/recovery-codes`
and `POST /auth/mfa/recovery-codes/regenerate` are thin router wrappers over
`EnterpriseAuthPlatform.mfa_totp_*` / `mfa_recovery_codes_*` (already covered
in depth at the `auth` package level in
`packages/auth/tests/test_mfa_totp.py` and `test_mfa_totp_advanced.py`) —
these tests verify routing, request/response shape, forced re-authentication,
and the 501 "not enabled" contract.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from auth import AuthService, RoleRegistry, reset_auth_service_for_tests, reset_role_registry_for_tests
from auth.enterprise_platform import (
    EnterpriseAuthPlatform,
    reset_enterprise_auth_platform_for_tests,
)
from auth.mfa_totp import totp_at
from auth.oauth_providers import OAuthProviderRegistry
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
def env(monkeypatch: pytest.MonkeyPatch) -> EnterpriseAuthPlatform:
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    monkeypatch.setenv("DSP_PASSWORD_HASHER", "pbkdf2")
    monkeypatch.setenv("DSP_AUTH_MFA", "true")

    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret="test-secret")
    reset_auth_service_for_tests(auth)
    platform = EnterpriseAuthPlatform(
        auth, oauth=OAuthProviderRegistry({}), otp=OtpService(DevSmsAdapter())
    )
    reset_enterprise_auth_platform_for_tests(platform)
    yield platform
    reset_enterprise_auth_platform_for_tests(None)
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


@pytest.fixture()
def client(env: EnterpriseAuthPlatform) -> TestClient:
    app = create_app(enable_security=False)
    with TestClient(app, follow_redirects=False) as c:
        yield c


def _make_user(env: EnterpriseAuthPlatform, suffix: str = "1") -> tuple[str, str]:
    reg = env.register_email(
        name=f"MFA User {suffix}",
        email=f"mfaapi{suffix}@example.com",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username=f"mfaapiuser{suffix}",
    )
    env.verify_email(reg["verification_token"])
    login = env.login_password(identifier=f"mfaapiuser{suffix}", password="StrongPass1!")
    return str(reg["user"]["user_id"]), str(login["tokens"]["access_token"])


def _enroll_via_api(client: TestClient, token: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    begin = client.post("/api/v1/auth/mfa/enroll", headers=headers)
    assert begin.status_code == 200, begin.text
    secret = begin.json()["result"]["secret"]
    code = totp_at(secret)
    enable = client.post("/api/v1/auth/mfa/enable", json={"code": code}, headers=headers)
    assert enable.status_code == 200, enable.text
    return {"secret": secret, "recovery_codes": enable.json()["result"]["recovery_codes"]}


def test_enroll_requires_authentication(client: TestClient) -> None:
    assert client.post("/api/v1/auth/mfa/enroll").status_code == 400


def test_enroll_returns_secret_and_qr(client: TestClient, env: EnterpriseAuthPlatform) -> None:
    _, token = _make_user(env)
    resp = client.post(
        "/api/v1/auth/mfa/enroll", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["secret"]
    assert result["otpauth_uri"].startswith("otpauth://totp/")


def test_enable_activates_mfa_and_returns_recovery_codes(
    client: TestClient, env: EnterpriseAuthPlatform
) -> None:
    user_id, token = _make_user(env)
    enrolled = _enroll_via_api(client, token)
    assert len(enrolled["recovery_codes"]) == 10
    assert env.mfa.totp.is_enrolled(user_id) is True


def test_enable_rejects_invalid_code(client: TestClient, env: EnterpriseAuthPlatform) -> None:
    _, token = _make_user(env)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/auth/mfa/enroll", headers=headers)
    resp = client.post("/api/v1/auth/mfa/enable", json={"code": "000000"}, headers=headers)
    assert resp.status_code == 401


def test_login_then_verify_step_up_flow(client: TestClient, env: EnterpriseAuthPlatform) -> None:
    user_id, token = _make_user(env, "2")
    enrolled = _enroll_via_api(client, token)

    login_resp = client.post(
        "/api/v1/auth/enterprise/login",
        json={"identifier": "mfaapiuser2", "password": "StrongPass1!"},
    )
    assert login_resp.status_code == 200, login_resp.text
    login_body = login_resp.json()["result"]
    assert login_body["mfa_required"] is True
    mfa_token = login_body["mfa_token"]
    assert "totp" in login_body["methods"]

    # The primary login already set the double-submit CSRF cookie (the
    # additive, non-blocking MFA design issues cookies before step-up) — a
    # real browser client echoes it back via the `X-CSRF-Token` header.
    csrf_headers = {"X-CSRF-Token": client.cookies.get("dsp_csrf", "")}

    # +30s == exactly one TOTP step (deterministic; avoids straddling a step
    # boundary the way a non-multiple-of-30 offset occasionally can).
    stepup_code = totp_at(enrolled["secret"], for_time=time.time() + 30)
    verify_resp = client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": stepup_code},
        headers=csrf_headers,
    )
    assert verify_resp.status_code == 200, verify_resp.text
    assert verify_resp.json()["result"]["ok"] is True

    events = env.audit.list_events(user_id=user_id, event_type="mfa.verify.success")
    assert events


def test_verify_rejects_invalid_code(client: TestClient, env: EnterpriseAuthPlatform) -> None:
    user_id, token = _make_user(env, "3")
    _enroll_via_api(client, token)
    login_resp = client.post(
        "/api/v1/auth/enterprise/login",
        json={"identifier": "mfaapiuser3", "password": "StrongPass1!"},
    )
    mfa_token = login_resp.json()["result"]["mfa_token"]
    csrf_headers = {"X-CSRF-Token": client.cookies.get("dsp_csrf", "")}
    resp = client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": "000000"},
        headers=csrf_headers,
    )
    assert resp.status_code == 401
    assert env.audit.list_events(user_id=user_id, event_type="mfa.verify.failure")


def test_disable_requires_current_password(client: TestClient, env: EnterpriseAuthPlatform) -> None:
    _, token = _make_user(env, "4")
    _enroll_via_api(client, token)
    resp = client.post("/api/v1/auth/mfa/disable", json={}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422  # Pydantic — current_password is mandatory


def test_disable_rejects_wrong_password(client: TestClient, env: EnterpriseAuthPlatform) -> None:
    _, token = _make_user(env, "5")
    _enroll_via_api(client, token)
    resp = client.post(
        "/api/v1/auth/mfa/disable",
        json={"current_password": "wrong-pass"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


def test_disable_succeeds_with_correct_password(client: TestClient, env: EnterpriseAuthPlatform) -> None:
    user_id, token = _make_user(env, "6")
    _enroll_via_api(client, token)
    resp = client.post(
        "/api/v1/auth/mfa/disable",
        json={"current_password": "StrongPass1!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert env.mfa.totp.is_enrolled(user_id) is False
    assert env.audit.list_events(user_id=user_id, event_type="mfa.disable")


def test_recovery_codes_status_endpoint(client: TestClient, env: EnterpriseAuthPlatform) -> None:
    _, token = _make_user(env, "7")
    _enroll_via_api(client, token)
    resp = client.get(
        "/api/v1/auth/mfa/recovery-codes", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["total"] == 10
    assert result["remaining"] == 10
    # Actual code values are never exposed via this endpoint.
    assert "codes" not in result


def test_recovery_codes_regenerate_requires_password(
    client: TestClient, env: EnterpriseAuthPlatform
) -> None:
    _, token = _make_user(env, "8")
    _enroll_via_api(client, token)
    resp = client.post(
        "/api/v1/auth/mfa/recovery-codes/regenerate",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


def test_recovery_codes_regenerate_success(client: TestClient, env: EnterpriseAuthPlatform) -> None:
    user_id, token = _make_user(env, "9")
    enrolled = _enroll_via_api(client, token)
    resp = client.post(
        "/api/v1/auth/mfa/recovery-codes/regenerate",
        json={"current_password": "StrongPass1!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    new_codes = resp.json()["result"]["recovery_codes"]
    assert len(new_codes) == 10
    assert set(new_codes).isdisjoint(enrolled["recovery_codes"])
    assert env.audit.list_events(user_id=user_id, event_type="mfa.recovery.regenerated")


def test_mfa_routes_report_501_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    monkeypatch.setenv("DSP_PASSWORD_HASHER", "pbkdf2")
    monkeypatch.setenv("DSP_AUTH_MFA", "false")
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret="test-secret")
    reset_auth_service_for_tests(auth)
    platform = EnterpriseAuthPlatform(auth, oauth=OAuthProviderRegistry({}), otp=OtpService(DevSmsAdapter()))
    reset_enterprise_auth_platform_for_tests(platform)
    try:
        _, token = _make_user(platform)
        app = create_app(enable_security=False)
        with TestClient(app, follow_redirects=False) as c:
            resp = c.post(
                "/api/v1/auth/mfa/enroll", headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 501
            resp2 = c.get(
                "/api/v1/auth/mfa/recovery-codes", headers={"Authorization": f"Bearer {token}"}
            )
            assert resp2.status_code == 501
    finally:
        reset_enterprise_auth_platform_for_tests(None)
        reset_auth_service_for_tests(None)
        reset_role_registry_for_tests(None)
        reset_persistence_service_for_tests(None)
        reset_repository_registry_for_tests(None)
