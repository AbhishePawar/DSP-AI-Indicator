"""API-level tests for the Microsoft Entra ID convenience endpoints.

`GET /auth/microsoft`, `GET /auth/microsoft/callback`, `POST
/auth/microsoft/link` and `POST /auth/microsoft/unlink` are thin router
wrappers over the existing `EnterpriseAuthPlatform` OAuth methods (already
covered in depth at the `auth` package level in
`packages/auth/tests/test_microsoft_oauth.py`) — these tests only verify
routing, redirect behaviour, cookie attachment, and auth-header handling.
"""

from __future__ import annotations

from urllib.parse import unquote, urlparse

import pytest
from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from auth import AuthService, RoleRegistry, reset_auth_service_for_tests, reset_role_registry_for_tests
from auth.enterprise_platform import (
    EnterpriseAuthPlatform,
    reset_enterprise_auth_platform_for_tests,
)
from auth.oauth_providers import OAuthProfile
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
    monkeypatch.setenv("DSP_MICROSOFT_CLIENT_ID", "ms-client")
    monkeypatch.setenv("DSP_MICROSOFT_CLIENT_SECRET", "ms-secret")
    monkeypatch.setenv("DSP_MICROSOFT_REDIRECT_URI", "https://app.dspai.local/auth/microsoft/callback")
    monkeypatch.setenv("DSP_AUTH_PROVIDER_MICROSOFT", "auto")
    monkeypatch.setenv("DSP_FRONTEND_URL", "https://app.dspai.local")
    monkeypatch.setenv("DSP_COOKIE_AUTH", "true")

    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret="test-secret")
    reset_auth_service_for_tests(auth)
    platform = EnterpriseAuthPlatform(auth, otp=OtpService(DevSmsAdapter()))
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


def test_microsoft_start_redirects_to_authorization_url(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/microsoft")
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://login.microsoftonline.com/")
    assert "client_id=ms-client" in location


def test_microsoft_start_uses_configured_default_redirect_uri(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/microsoft")
    query = urlparse(resp.headers["location"]).query
    assert "redirect_uri=" in query


def test_microsoft_start_unavailable_without_env(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    monkeypatch.delenv("DSP_MICROSOFT_REDIRECT_URI", raising=False)
    resp = client.get("/api/v1/auth/microsoft")
    assert resp.status_code == 503


def test_microsoft_callback_success_sets_cookies_and_redirects(
    client: TestClient, env: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        env.oauth,
        "complete",
        lambda provider, **kwargs: OAuthProfile(
            provider="MICROSOFT",
            subject="ms-oid-9",
            email="user@contoso.com",
            email_verified=True,
            name="Contoso User",
            avatar=None,
            raw_claims={},
        ),
    )
    resp = client.get("/api/v1/auth/microsoft/callback", params={"code": "auth-code"})
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://app.dspai.local/dashboard"
    assert "dsp_access" in resp.cookies


def test_microsoft_callback_failure_redirects_to_login_with_error(
    client: TestClient, env: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(provider, **kwargs):
        raise ValueError("Invalid or expired OAuth state.")

    monkeypatch.setattr(env.oauth, "complete", _boom)
    resp = client.get("/api/v1/auth/microsoft/callback", params={"code": "bad-code"})
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://app.dspai.local/login?")
    assert "provider=microsoft" in location
    assert "expired OAuth state" in unquote(location)


def test_microsoft_link_and_unlink_require_authentication(client: TestClient) -> None:
    link = client.post("/api/v1/auth/microsoft/link", json={"code": "c"})
    assert link.status_code == 400
    unlink = client.post("/api/v1/auth/microsoft/unlink")
    assert unlink.status_code == 400


def test_microsoft_link_binds_identity_to_current_user(
    client: TestClient, env: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    reg = env.register_email(
        name="Owner",
        email="owner@contoso.com",
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    env.verify_email(reg["verification_token"])
    login = env.login_password(identifier="owner@contoso.com", password="StrongPass12!")
    token = login["tokens"]["access_token"]

    monkeypatch.setattr(
        env.oauth,
        "complete",
        lambda provider, **kwargs: OAuthProfile(
            provider="MICROSOFT",
            subject="ms-owner-oid",
            email="owner@contoso.com",
            email_verified=True,
            name="Owner",
            avatar=None,
            raw_claims={},
        ),
    )
    resp = client.post(
        "/api/v1/auth/microsoft/link",
        json={"code": "auth-code"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert any(
        lnk["provider"] == "MICROSOFT" for lnk in body["result"]["user"]["linkedProviders"]
    )

    unlink = client.post(
        "/api/v1/auth/microsoft/unlink",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert unlink.status_code == 200
    assert not any(
        lnk["provider"] == "MICROSOFT"
        for lnk in unlink.json()["result"]["linkedProviders"]
    )
