"""API-level tests for the Facebook Login convenience endpoints.

`GET /auth/facebook`, `GET /auth/facebook/callback`, `POST
/auth/facebook/link` and `POST /auth/facebook/unlink` are thin router
wrappers over `EnterpriseAuthPlatform` (already covered in depth at the
`auth` package level in `packages/auth/tests/test_facebook_oauth.py`) —
these tests only verify routing, redirect behaviour, cookie attachment,
and auth-header handling, following the same pattern already established
for Microsoft in `test_microsoft_oauth_api.py`.
"""

from __future__ import annotations

from urllib.parse import unquote

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
    monkeypatch.setenv("DSP_FACEBOOK_CLIENT_ID", "fb-client")
    monkeypatch.setenv("DSP_FACEBOOK_CLIENT_SECRET", "fb-secret")
    monkeypatch.setenv("DSP_FACEBOOK_REDIRECT_URI", "https://app.dspai.local/auth/facebook/callback")
    monkeypatch.setenv("DSP_AUTH_PROVIDER_FACEBOOK", "auto")
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


def _fb_profile(subject: str = "fb-oid-9", email: str = "user@example.com") -> OAuthProfile:
    return OAuthProfile(
        provider="FACEBOOK",
        subject=subject,
        email=email,
        email_verified=True,
        name="Test User",
        avatar=None,
        raw_claims={},
    )


def test_facebook_start_redirects_to_authorization_url(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/facebook")
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://www.facebook.com/")
    assert "client_id=fb-client" in location


def test_facebook_start_unavailable_without_redirect_uri(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    monkeypatch.delenv("DSP_FACEBOOK_REDIRECT_URI", raising=False)
    resp = client.get("/api/v1/auth/facebook")
    assert resp.status_code == 503


def test_facebook_start_disabled_provider_returns_error(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    monkeypatch.setenv("DSP_AUTH_PROVIDER_FACEBOOK", "disabled")
    resp = client.get("/api/v1/auth/facebook")
    assert resp.status_code == 503
    assert resp.json()["ok"] is False


def test_facebook_callback_success_sets_cookies_and_redirects(
    client: TestClient, env: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(env.oauth, "complete", lambda provider, **kwargs: _fb_profile())
    resp = client.get("/api/v1/auth/facebook/callback", params={"code": "auth-code"})
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://app.dspai.local/dashboard"
    assert "dsp_access" in resp.cookies


def test_facebook_callback_failure_redirects_to_login_with_error(
    client: TestClient, env: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(provider, **kwargs):
        raise ValueError("Invalid or expired OAuth state.")

    monkeypatch.setattr(env.oauth, "complete", _boom)
    resp = client.get("/api/v1/auth/facebook/callback", params={"code": "bad-code"})
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://app.dspai.local/login?")
    assert "provider=facebook" in location
    assert "expired OAuth state" in unquote(location)


def test_facebook_callback_missing_email_redirects_with_error(
    client: TestClient, env: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        env.oauth,
        "complete",
        lambda provider, **kwargs: OAuthProfile(
            provider="FACEBOOK",
            subject="fb-no-email",
            email=None,
            email_verified=False,
            name="No Email",
            avatar=None,
            raw_claims={},
        ),
    )
    resp = client.get("/api/v1/auth/facebook/callback", params={"code": "auth-code"})
    assert resp.status_code == 302
    assert "provider=facebook" in resp.headers["location"]
    events = env.audit.list_events(event_type="oauth.facebook.failure")
    assert events


def test_facebook_link_and_unlink_require_authentication(client: TestClient) -> None:
    link = client.post("/api/v1/auth/facebook/link", json={"code": "c"})
    assert link.status_code == 400
    unlink = client.post("/api/v1/auth/facebook/unlink")
    assert unlink.status_code == 400


def test_facebook_link_binds_identity_and_unlink_removes_it(
    client: TestClient, env: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    reg = env.register_email(
        name="Owner",
        email="owner@example.com",
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    env.verify_email(reg["verification_token"])
    login = env.login_password(identifier="owner@example.com", password="StrongPass12!")
    token = login["tokens"]["access_token"]

    monkeypatch.setattr(
        env.oauth,
        "complete",
        lambda provider, **kwargs: _fb_profile(subject="fb-owner-oid", email="owner@example.com"),
    )
    resp = client.post(
        "/api/v1/auth/facebook/link",
        json={"code": "auth-code"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert any(lnk["provider"] == "FACEBOOK" for lnk in body["result"]["user"]["linkedProviders"])

    unlink = client.post(
        "/api/v1/auth/facebook/unlink",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert unlink.status_code == 200
    assert not any(
        lnk["provider"] == "FACEBOOK" for lnk in unlink.json()["result"]["linkedProviders"]
    )


def test_facebook_link_rejects_identity_owned_by_different_user(
    client: TestClient, env: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    # First account already owns this Facebook identity.
    monkeypatch.setattr(
        env.oauth,
        "complete",
        lambda provider, **kwargs: _fb_profile(subject="shared-fb-id", email="first@example.com"),
    )
    client.get("/api/v1/auth/facebook/callback", params={"code": "c1"})

    reg = env.register_email(
        name="Second",
        email="second@example.com",
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    env.verify_email(reg["verification_token"])
    login = env.login_password(identifier="second@example.com", password="StrongPass12!")
    token = login["tokens"]["access_token"]

    resp = client.post(
        "/api/v1/auth/facebook/link",
        json={"code": "auth-code"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "already linked" in resp.json()["error"]
