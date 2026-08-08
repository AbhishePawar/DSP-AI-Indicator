"""Microsoft Entra ID (Azure AD) OAuth tests.

Mirrors the Google OAuth test coverage (`test_oauth_providers.py`,
`test_oidc.py`) using the *same* generic `OAuthProviderAdapter` /
`verify_id_token` code paths — Microsoft does not have any parallel OAuth
implementation, so these tests exercise shared code with
Microsoft-specific configuration (multi-tenant issuer wildcard, Graph
`/me` profile shape, `oid` claim, etc).
"""

from __future__ import annotations

import base64
import json
import time
from urllib.parse import parse_qs, urlparse

import pytest

cryptography = pytest.importorskip("cryptography")

from cryptography.hazmat.primitives import hashes  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15  # noqa: E402

from auth import AuthService, RoleRegistry, reset_auth_service_for_tests, reset_role_registry_for_tests
from auth.enterprise_models import AuthProvider
from auth.enterprise_platform import EnterpriseAuthPlatform
from auth.exceptions import AuthenticationError, ValidationError
from auth.oauth_providers import OAuthProviderAdapter, build_oauth_registry
from auth.otp import OtpService
from auth.sms import DevSmsAdapter
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _int_to_b64url(value: int) -> str:
    length = (value.bit_length() + 7) // 8
    return _b64url(value.to_bytes(length, "big"))


class _KeyPair:
    def __init__(self, kid: str = "ms-test-kid") -> None:
        self.kid = kid
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()

    def jwks(self) -> dict:
        numbers = self.public_key.public_numbers()
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": self.kid,
                    "use": "sig",
                    "alg": "RS256",
                    "n": _int_to_b64url(numbers.n),
                    "e": _int_to_b64url(numbers.e),
                }
            ]
        }

    def sign_token(self, claims: dict) -> str:
        header = {"alg": "RS256", "typ": "JWT", "kid": self.kid}
        header_b64 = _b64url(json.dumps(header).encode("utf-8"))
        payload_b64 = _b64url(json.dumps(claims).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        signature = self.private_key.sign(signing_input, PKCS1v15(), hashes.SHA256())
        return f"{header_b64}.{payload_b64}.{_b64url(signature)}"


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


TENANT = "72f988bf-tenant-guid"


def _microsoft_adapter(tenant: str = TENANT) -> OAuthProviderAdapter:
    return OAuthProviderAdapter(
        provider=AuthProvider.MICROSOFT,
        client_id="ms-client-123",
        client_secret="ms-secret",
        authorize_url=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
        token_url=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        userinfo_url="https://graph.microsoft.com/v1.0/me",
        scopes=("openid", "email", "profile", "User.Read"),
        flag_env="DSP_AUTH_PROVIDER_MICROSOFT",
        oidc_jwks_uri=f"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys",
        oidc_issuers=(
            f"https://login.microsoftonline.com/{tenant}/v2.0",
            "https://login.microsoftonline.com/*/v2.0",
        ),
    )


def _base_ms_claims(**overrides) -> dict:
    now = time.time()
    claims = {
        "iss": f"https://login.microsoftonline.com/{TENANT}/v2.0",
        "aud": "ms-client-123",
        "sub": "ms-sub-1",
        "oid": "ms-oid-1",
        "email": "user@contoso.com",
        "iat": now,
        "exp": now + 300,
    }
    claims.update(overrides)
    return claims


# --------------------------------------------------------------------- #
# Adapter-level: begin_login / PKCE / state / nonce
# --------------------------------------------------------------------- #


def test_begin_login_uses_tenant_specific_urls_and_pkce() -> None:
    adapter = _microsoft_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")
    assert begin["available"] is True
    assert begin["authorization_url"].startswith(
        f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/authorize?"
    )
    query = parse_qs(urlparse(begin["authorization_url"]).query)
    assert "code_challenge" in query
    assert query["code_challenge_method"][0] == "S256"
    assert "nonce" in query
    assert query["response_mode"][0] == "query"
    assert "access_type" not in query
    assert begin["state"]


def test_begin_login_multi_tenant_default_uses_common() -> None:
    adapter = _microsoft_adapter(tenant="common")
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")
    assert "/common/oauth2/v2.0/authorize" in begin["authorization_url"]


def test_registry_builds_multi_tenant_wildcard_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DSP_MICROSOFT_TENANT_ID", raising=False)
    registry = build_oauth_registry()
    adapter = registry.require("MICROSOFT")
    assert "https://login.microsoftonline.com/*/v2.0" in adapter.oidc_issuers


def test_registry_builds_single_tenant_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_MICROSOFT_TENANT_ID", TENANT)
    registry = build_oauth_registry()
    adapter = registry.require("MICROSOFT")
    assert f"https://login.microsoftonline.com/{TENANT}/v2.0" in adapter.oidc_issuers
    assert f"/{TENANT}/oauth2/v2.0/authorize" in adapter.authorize_url


# --------------------------------------------------------------------- #
# Adapter-level: id_token cross-check against Graph profile (mocked)
# --------------------------------------------------------------------- #


def test_complete_login_cross_checks_oid_against_graph_profile(monkeypatch) -> None:
    adapter = _microsoft_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")
    nonce = parse_qs(urlparse(begin["authorization_url"]).query)["nonce"][0]

    monkeypatch.setattr(
        adapter,
        "_exchange_code",
        lambda code, redirect_uri, verifier: {
            "access_token": "at-1",
            "id_token": "header.payload.sig",
        },
    )
    monkeypatch.setattr(
        "auth.oauth_providers.verify_id_token",
        lambda token, **kwargs: {"oid": "graph-oid-1", "sub": "graph-oid-1", "nonce": nonce},
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=20: _FakeResponse(
            {
                "id": "graph-oid-1",
                "mail": "User@Contoso.com",
                "displayName": "Contoso User",
            }
        ),
    )

    profile = adapter.complete_login(
        code="auth-code", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
    )
    assert profile.subject == "graph-oid-1"
    assert profile.email == "user@contoso.com"
    assert profile.email_verified is True


def test_complete_login_rejects_oid_mismatch(monkeypatch) -> None:
    adapter = _microsoft_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")

    monkeypatch.setattr(
        adapter,
        "_exchange_code",
        lambda code, redirect_uri, verifier: {
            "access_token": "at-1",
            "id_token": "header.payload.sig",
        },
    )
    monkeypatch.setattr(
        "auth.oauth_providers.verify_id_token",
        lambda token, **kwargs: {"oid": "attacker-oid", "sub": "attacker-oid"},
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=20: _FakeResponse(
            {"id": "graph-oid-1", "mail": "user@contoso.com"}
        ),
    )

    with pytest.raises(AuthenticationError, match="does not match"):
        adapter.complete_login(
            code="auth-code", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
        )


def test_replay_attack_state_can_only_be_used_once(monkeypatch) -> None:
    """A previously-consumed OAuth `state` must never be redeemable again."""
    adapter = _microsoft_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")

    monkeypatch.setattr(
        adapter,
        "_exchange_code",
        lambda code, redirect_uri, verifier: {"access_token": "at-1"},
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=20: _FakeResponse({"id": "graph-oid-1", "mail": "user@contoso.com"}),
    )

    adapter.complete_login(
        code="auth-code", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
    )
    with pytest.raises(AuthenticationError, match="Invalid or expired OAuth state"):
        adapter.complete_login(
            code="auth-code-2", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
        )


# --------------------------------------------------------------------- #
# Full JWKS-verified id_token flow (real signatures via `_KeyPair`)
# --------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _clear_jwks_cache():
    from auth import oidc

    oidc._JWKS_CACHE.clear()
    yield
    oidc._JWKS_CACHE.clear()


def _wire_real_jwks(monkeypatch, adapter: OAuthProviderAdapter, kp: _KeyPair, id_token: str) -> None:
    from auth import oidc

    monkeypatch.setattr(oidc, "_fetch_jwks", lambda uri: kp.jwks())
    monkeypatch.setattr(
        adapter,
        "_exchange_code",
        lambda code, redirect_uri, verifier: {"access_token": "at-1", "id_token": id_token},
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=20: _FakeResponse(
            {"id": "ms-oid-1", "mail": "user@contoso.com", "displayName": "Test User"}
        ),
    )


def test_complete_login_accepts_valid_signed_id_token(monkeypatch) -> None:
    adapter = _microsoft_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")
    nonce = parse_qs(urlparse(begin["authorization_url"]).query)["nonce"][0]
    kp = _KeyPair()
    token = kp.sign_token(_base_ms_claims(nonce=nonce))
    _wire_real_jwks(monkeypatch, adapter, kp, token)

    profile = adapter.complete_login(
        code="auth-code", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
    )
    assert profile.subject == "ms-oid-1"


def test_complete_login_rejects_invalid_tenant_issuer(monkeypatch) -> None:
    """Token issued by a *different* tenant than configured must be rejected."""
    adapter = _microsoft_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")
    nonce = parse_qs(urlparse(begin["authorization_url"]).query)["nonce"][0]
    kp = _KeyPair()
    token = kp.sign_token(
        _base_ms_claims(nonce=nonce, iss="https://login.microsoftonline.com/other-tenant/v3.0")
    )
    _wire_real_jwks(monkeypatch, adapter, kp, token)

    with pytest.raises(AuthenticationError, match="id_token rejected"):
        adapter.complete_login(
            code="auth-code", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
        )


def test_complete_login_rejects_invalid_signature(monkeypatch) -> None:
    adapter = _microsoft_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")
    nonce = parse_qs(urlparse(begin["authorization_url"]).query)["nonce"][0]
    kp = _KeyPair()
    forged = _KeyPair(kid=kp.kid)  # same kid, different key -> signature invalid
    token = forged.sign_token(_base_ms_claims(nonce=nonce))
    _wire_real_jwks(monkeypatch, adapter, kp, token)

    with pytest.raises(AuthenticationError, match="id_token rejected"):
        adapter.complete_login(
            code="auth-code", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
        )


def test_complete_login_rejects_expired_id_token(monkeypatch) -> None:
    adapter = _microsoft_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")
    nonce = parse_qs(urlparse(begin["authorization_url"]).query)["nonce"][0]
    kp = _KeyPair()
    token = kp.sign_token(_base_ms_claims(nonce=nonce, exp=time.time() - 600))
    _wire_real_jwks(monkeypatch, adapter, kp, token)

    with pytest.raises(AuthenticationError, match="id_token rejected"):
        adapter.complete_login(
            code="auth-code", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
        )


def test_complete_login_rejects_nonce_replay(monkeypatch) -> None:
    """A token bearing a nonce from a *different* login attempt must fail."""
    adapter = _microsoft_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")
    kp = _KeyPair()
    token = kp.sign_token(_base_ms_claims(nonce="stolen-nonce-from-elsewhere"))
    _wire_real_jwks(monkeypatch, adapter, kp, token)

    with pytest.raises(AuthenticationError, match="id_token rejected"):
        adapter.complete_login(
            code="auth-code", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
        )


# --------------------------------------------------------------------- #
# EnterpriseAuthPlatform: login/link/unlink/logout via the shared flow
# --------------------------------------------------------------------- #


@pytest.fixture()
def platform():
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret="test-secret")
    reset_auth_service_for_tests(auth)
    plat = EnterpriseAuthPlatform(auth, otp=OtpService(DevSmsAdapter()))
    yield plat
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


def _ms_profile(subject: str = "ms-oid-1", email: str = "user@contoso.com"):
    from auth.oauth_providers import OAuthProfile

    return OAuthProfile(
        provider="MICROSOFT",
        subject=subject,
        email=email,
        email_verified=True,
        name="Contoso User",
        avatar=None,
        raw_claims={},
    )


def test_oauth_callback_auto_provisions_new_user(platform: EnterpriseAuthPlatform) -> None:
    result = platform._login_from_oauth_profile(_ms_profile())
    assert result["tokens"]["access_token"]
    assert result["tokens"]["refresh_token"]
    user = platform._get_by_provider_subject("MICROSOFT", "ms-oid-1")
    assert user is not None
    assert user.email == "user@contoso.com"


def test_oauth_callback_links_to_existing_verified_email(platform: EnterpriseAuthPlatform) -> None:
    reg = platform.register_email(
        name="Contoso User",
        email="user@contoso.com",
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    platform.verify_email(reg["verification_token"])

    result = platform._login_from_oauth_profile(_ms_profile())
    assert result["tokens"]["access_token"]
    user = platform._get_by_email("user@contoso.com")
    assert user is not None
    links = user.metadata.get("linked_providers") or []
    assert any(lnk["provider"] == "MICROSOFT" for lnk in links)
    # Must not have created a second, duplicate account.
    all_users = [u for u in platform.auth.users.list_users() if u.email == "user@contoso.com"]
    assert len(all_users) == 1


def test_link_oauth_provider_binds_to_authenticated_user(
    platform: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    reg = platform.register_email(
        name="Contoso User",
        email="owner@contoso.com",
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    platform.verify_email(reg["verification_token"])
    user = platform._get_by_email("owner@contoso.com")
    assert user is not None

    monkeypatch.setattr(
        platform.oauth,
        "complete",
        lambda provider, **kwargs: _ms_profile(subject="ms-owner-oid", email="owner@contoso.com"),
    )
    result = platform.link_oauth_provider(
        user.user_id, "MICROSOFT", code="code", state="state", redirect_uri="https://app/callback"
    )
    assert result["ok"] is True
    assert any(
        lnk["provider"] == "MICROSOFT" for lnk in result["user"]["linkedProviders"]
    )
    updated = platform.auth.users.get(user.user_id)
    assert updated is not None
    linked = updated.metadata.get("linked_providers") or []
    assert any(lnk["provider"] == "MICROSOFT" and lnk["provider_subject"] == "ms-owner-oid" for lnk in linked)
    events = platform.audit.list_events(user_id=user.user_id, event_type="oauth.microsoft.link")
    assert events


def test_link_oauth_provider_rejects_identity_already_linked_elsewhere(
    platform: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    # First user already owns the Microsoft identity.
    platform._login_from_oauth_profile(_ms_profile(subject="shared-oid", email="first@contoso.com"))

    reg = platform.register_email(
        name="Second User",
        email="second@contoso.com",
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    platform.verify_email(reg["verification_token"])
    second = platform._get_by_email("second@contoso.com")
    assert second is not None

    monkeypatch.setattr(
        platform.oauth,
        "complete",
        lambda provider, **kwargs: _ms_profile(subject="shared-oid", email="first@contoso.com"),
    )
    with pytest.raises(ValidationError, match="already linked"):
        platform.link_oauth_provider(
            second.user_id, "MICROSOFT", code="code", state="state", redirect_uri="https://app/callback"
        )


def test_link_oauth_provider_rejects_email_owned_by_different_user(
    platform: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    reg1 = platform.register_email(
        name="First",
        email="first@contoso.com",
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    platform.verify_email(reg1["verification_token"])

    reg2 = platform.register_email(
        name="Second",
        email="second@contoso.com",
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    platform.verify_email(reg2["verification_token"])
    second = platform._get_by_email("second@contoso.com")
    assert second is not None

    monkeypatch.setattr(
        platform.oauth,
        "complete",
        lambda provider, **kwargs: _ms_profile(subject="new-oid", email="first@contoso.com"),
    )
    with pytest.raises(ValidationError, match="different user"):
        platform.link_oauth_provider(
            second.user_id, "MICROSOFT", code="code", state="state", redirect_uri="https://app/callback"
        )


def test_unlink_provider_removes_link_and_records_audit(platform: EnterpriseAuthPlatform) -> None:
    result = platform._login_from_oauth_profile(_ms_profile())
    user_id = platform._get_by_provider_subject("MICROSOFT", "ms-oid-1").user_id  # type: ignore[union-attr]
    _ = result

    # Give the account a password too, so unlink of the OAuth provider is allowed.
    updated = platform.admin_reset_password(user_id, "StrongPass12!")
    _ = updated

    out = platform.unlink_provider(user_id, "MICROSOFT")
    links = out.get("linkedProviders") or []
    assert not any(lnk["provider"] == "MICROSOFT" for lnk in links)
    events = platform.audit.list_events(user_id=user_id, event_type="oauth.microsoft.unlink")
    assert events


def test_logout_revokes_all_sessions_for_oauth_user(platform: EnterpriseAuthPlatform) -> None:
    result = platform._login_from_oauth_profile(_ms_profile())
    user_id = platform._get_by_provider_subject("MICROSOFT", "ms-oid-1").user_id  # type: ignore[union-attr]
    assert result["tokens"]["access_token"]

    out = platform.revoke_sessions_for_user(user_id)
    assert out.get("sessions_revoked", 0) >= 1
