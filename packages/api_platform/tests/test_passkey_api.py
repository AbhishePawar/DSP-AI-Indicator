"""API-level tests for the primary Passkey sign-in endpoints.

`POST /auth/passkey/register/begin|complete`, `POST
/auth/passkey/login/begin|complete`, `GET /auth/passkey`, and `DELETE
/auth/passkey/{credential_id}` are thin router wrappers over the same
`EnterpriseAuthPlatform.webauthn_*` methods already covered in depth in
`packages/auth/tests/test_passkey_platform.py` — these tests verify
routing, request/response shape, auth-header handling, cookie
attachment on login, and the 501 "not enabled" contract.
"""

from __future__ import annotations

import time

import pytest

webauthn_lib = pytest.importorskip("webauthn", reason="optional 'webauthn' package not installed")

from fastapi.testclient import TestClient  # noqa: E402

from api_platform.api.app import create_app  # noqa: E402
from auth import AuthService, RoleRegistry, reset_auth_service_for_tests, reset_role_registry_for_tests  # noqa: E402
from auth.enterprise_platform import (  # noqa: E402
    EnterpriseAuthPlatform,
    reset_enterprise_auth_platform_for_tests,
)
from auth.mfa import MfaGateway  # noqa: E402
from auth.mfa_webauthn import WebAuthnAdapter, _b64url_decode  # noqa: E402
from auth.oauth_providers import OAuthProviderRegistry  # noqa: E402
from auth.otp import OtpService  # noqa: E402
from auth.sms import DevSmsAdapter  # noqa: E402
from persistence import (  # noqa: E402
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
)

_AUTH_CREDENTIAL = {
    "id": "EDx9FfAbp4obx6oll2oC4-CZuDidRVV4gZhxC529ytlnqHyqCStDUwfNdm1SNHAe3X5KvueWQdAX3x9R1a2b9Q",
    "rawId": "EDx9FfAbp4obx6oll2oC4-CZuDidRVV4gZhxC529ytlnqHyqCStDUwfNdm1SNHAe3X5KvueWQdAX3x9R1a2b9Q",
    "response": {
        "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MBAAAATg",
        "clientDataJSON": "eyJjaGFsbGVuZ2UiOiJ4aTMwR1BHQUZZUnhWRHBZMXNNMTBEYUx6VlFHNjZudi1fN1JVYXpIMHZJMll2RzhMWWdERW52TjVmWlpOVnV2RUR1TWk5dGUzVkxxYjQyTjBma0xHQSIsImNsaWVudEV4dGVuc2lvbnMiOnt9LCJoYXNoQWxnb3JpdGhtIjoiU0hBLTI1NiIsIm9yaWdpbiI6Imh0dHA6Ly9sb2NhbGhvc3Q6NTAwMCIsInR5cGUiOiJ3ZWJhdXRobi5nZXQifQ",
        "signature": "MEUCIGisVZOBapCWbnJJvjelIzwpixxIwkjCCb5aCHafQu68AiEA88v-2pJNNApPFwAKFiNuf82-2hBxYW5kGwVweeoxCwo",
    },
    "type": "public-key",
    "clientExtensionResults": {},
}
_AUTH_CHALLENGE_B64URL = (
    "xi30GPGAFYRxVDpY1sM10DaLzVQG66nv-_7RUazH0vI2YvG8LYgDEnvN5fZZNVuvEDuMi9te3VLqb42N0fkLGA"
)
_AUTH_PUBLIC_KEY_B64URL = (
    "pQECAyYgASFYIIeDTe-gN8A-zQclHoRnGFWN8ehM1b7yAsa8I8KIvmplIlgg4nFGT5px8o6gpPZZhO01wdy9crDSA_Ngtkx0vGpvPHI"
)


@pytest.fixture()
def env(monkeypatch: pytest.MonkeyPatch) -> EnterpriseAuthPlatform:
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    monkeypatch.setenv("DSP_PASSWORD_HASHER", "pbkdf2")
    monkeypatch.setenv("DSP_AUTH_MFA", "true")
    monkeypatch.setenv("DSP_COOKIE_AUTH", "true")

    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret="test-secret")
    reset_auth_service_for_tests(auth)
    webauthn = WebAuthnAdapter(
        auth.persistence, auth.users, rp_id="localhost", origin="http://localhost:5000"
    )
    mfa = MfaGateway(webauthn=webauthn, enabled=True)
    platform = EnterpriseAuthPlatform(
        auth, oauth=OAuthProviderRegistry({}), otp=OtpService(DevSmsAdapter()), mfa=mfa
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
        name=f"Passkey User {suffix}",
        email=f"passkey{suffix}@example.com",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username=f"passkeyuser{suffix}",
    )
    env.verify_email(reg["verification_token"])
    login = env.login_password(identifier=f"passkeyuser{suffix}", password="StrongPass1!")
    return str(reg["user"]["user_id"]), str(login["tokens"]["access_token"])


def test_register_begin_requires_authentication(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/passkey/register/begin")
    assert resp.status_code == 400


def test_register_begin_returns_ceremony_options(client: TestClient, env: EnterpriseAuthPlatform) -> None:
    _, token = _make_user(env)
    resp = client.post(
        "/api/v1/auth/passkey/register/begin", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["result"]["state"]
    assert body["result"]["authenticatorSelection"]["residentKey"] == "required"


def test_register_begin_reports_501_when_mfa_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
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
                "/api/v1/auth/passkey/register/begin", headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 501
            body = resp.json()
            assert body["ok"] is False
            assert "Passkey" in body["error"]
    finally:
        reset_enterprise_auth_platform_for_tests(None)
        reset_auth_service_for_tests(None)
        reset_role_registry_for_tests(None)
        reset_persistence_service_for_tests(None)
        reset_repository_registry_for_tests(None)


def test_login_begin_returns_discoverable_options_without_auth(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/passkey/login/begin", json={})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["result"]["state"]
    assert body["result"]["rpId"] == "localhost"


def test_login_complete_issues_session_and_sets_cookies(
    client: TestClient, env: EnterpriseAuthPlatform
) -> None:
    user_id, _ = _make_user(env)
    cred_id = _AUTH_CREDENTIAL["id"]
    env.mfa.webauthn._save_credentials(  # noqa: SLF001
        user_id,
        [
            {
                "credential_id": cred_id,
                "public_key": _AUTH_PUBLIC_KEY_B64URL,
                "sign_count": 77,
                "device_type": "single_device",
                "backed_up": False,
                "transports": [],
                "label": "Test key",
                "created_at": time.time(),
            }
        ],
    )
    env.auth.persistence.put(
        kind="metadata",
        entity_id=f"auth-webauthn-cred-index-{cred_id}",
        payload={"auth_entity": "webauthn_cred_index", "user_id": user_id, "credential_id": cred_id},
        refs={"auth_entity": "webauthn_cred_index"},
        created_at=None,
        allow_update=True,
    )
    state = "api-auth-state-1"
    env.mfa.webauthn._pending[state] = {  # noqa: SLF001
        "kind": "authentication",
        "challenge": _b64url_decode(_AUTH_CHALLENGE_B64URL),
        "created_at": time.time(),
    }
    resp = client.post(
        "/api/v1/auth/passkey/login/complete",
        json={"state": state, "credential": _AUTH_CREDENTIAL},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["result"]["tokens"]["access_token"]
    assert "dsp_access" in resp.cookies

    events = env.audit.list_events(user_id=user_id, event_type="passkey.login.success")
    assert events


def test_login_complete_unknown_credential_returns_401(
    client: TestClient, env: EnterpriseAuthPlatform
) -> None:
    state = "api-auth-state-2"
    env.mfa.webauthn._pending[state] = {  # noqa: SLF001
        "kind": "authentication",
        "challenge": _b64url_decode(_AUTH_CHALLENGE_B64URL),
        "created_at": time.time(),
    }
    resp = client.post(
        "/api/v1/auth/passkey/login/complete",
        json={"state": state, "credential": _AUTH_CREDENTIAL},
    )
    assert resp.status_code == 401
    assert resp.json()["ok"] is False


def test_list_and_delete_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/auth/passkey").status_code == 400
    assert client.delete("/api/v1/auth/passkey/some-cred-id").status_code == 400


def test_list_and_delete_credential_lifecycle(client: TestClient, env: EnterpriseAuthPlatform) -> None:
    user_id, token = _make_user(env)
    env.mfa.webauthn._save_credentials(  # noqa: SLF001
        user_id,
        [
            {
                "credential_id": "cred-abc",
                "public_key": _AUTH_PUBLIC_KEY_B64URL,
                "sign_count": 3,
                "device_type": "single_device",
                "backed_up": False,
                "transports": [],
                "label": "Work laptop",
                "created_at": time.time(),
            }
        ],
    )
    headers = {"Authorization": f"Bearer {token}"}
    listed = client.get("/api/v1/auth/passkey", headers=headers)
    assert listed.status_code == 200
    creds = listed.json()["result"]
    assert len(creds) == 1
    assert creds[0]["credential_id"] == "cred-abc"
    assert "public_key" not in creds[0]

    deleted = client.delete("/api/v1/auth/passkey/cred-abc", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["result"]["ok"] is True

    after = client.get("/api/v1/auth/passkey", headers=headers)
    assert after.json()["result"] == []

    events = env.audit.list_events(user_id=user_id, event_type="passkey.deleted")
    assert events


def test_delete_nonexistent_credential_returns_error(
    client: TestClient, env: EnterpriseAuthPlatform
) -> None:
    _, token = _make_user(env)
    resp = client.delete(
        "/api/v1/auth/passkey/does-not-exist", headers={"Authorization": f"Bearer {token}"}
    )
    # Generic error-mapping bumps "credential"-related messages to 401.
    assert resp.status_code == 401
    assert resp.json()["ok"] is False


def test_discovery_exposes_passkey_availability(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/enterprise/providers")
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["passkey"]["available"] is True
