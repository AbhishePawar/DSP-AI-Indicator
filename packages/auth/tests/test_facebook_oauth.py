"""Facebook Login (OAuth 2.0) tests.

Facebook reuses the *same* generic `OAuthProviderAdapter` /
`EnterpriseAuthPlatform` machinery as Google and Microsoft — there is no
parallel Facebook-specific OAuth implementation. Facebook does not issue an
OIDC `id_token`/JWKS, so its trust anchor is the live Graph `/me` profile
call made with the freshly-exchanged access token (same pattern documented
in `auth.oidc` for providers/situations where ID-token verification is
unavailable).
"""

from __future__ import annotations

import json

import pytest

from auth import AuthService, RoleRegistry, reset_auth_service_for_tests, reset_role_registry_for_tests
from auth.enterprise_models import AuthProvider
from auth.enterprise_platform import EnterpriseAuthPlatform
from auth.exceptions import AuthenticationError, OAuthChallengeError, ValidationError
from auth.oauth_providers import OAuthProfile, OAuthProviderAdapter, build_oauth_registry
from auth.otp import OtpService
from auth.sms import DevSmsAdapter
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
)


@pytest.fixture(autouse=True)
def _isolated_a008() -> None:
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    reset_persistence_service_for_tests(PersistenceService(registry))
    yield
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _facebook_adapter() -> OAuthProviderAdapter:
    return OAuthProviderAdapter(
        provider=AuthProvider.FACEBOOK,
        client_id="fb-client-123",
        client_secret="fb-secret",
        authorize_url="https://www.facebook.com/v19.0/dialog/oauth",
        token_url="https://graph.facebook.com/v19.0/oauth/access_token",
        userinfo_url="https://graph.facebook.com/me",
        scopes=("email", "public_profile"),
        flag_env="DSP_AUTH_PROVIDER_FACEBOOK",
    )


def _graph_profile(**overrides) -> dict:
    payload = {
        "id": "fb-user-1",
        "name": "Jamie Rivera",
        "first_name": "Jamie",
        "last_name": "Rivera",
        "email": "jamie@example.com",
        "picture": {"data": {"url": "https://graph.facebook.com/fb-user-1/picture"}},
        "locale": "en_US",
    }
    payload.update(overrides)
    return payload


# --------------------------------------------------------------------- #
# Adapter-level: begin_login / PKCE / state
# --------------------------------------------------------------------- #


def test_begin_login_facebook_no_nonce_no_prompt_no_access_type() -> None:
    """Facebook has no OIDC id_token, so no nonce is generated; the
    `access_type`/`prompt` params (Google-specific) are stripped."""
    adapter = _facebook_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")
    assert begin["available"] is True
    assert begin["authorization_url"].startswith("https://www.facebook.com/v19.0/dialog/oauth?")
    assert "nonce" not in begin["authorization_url"]
    assert "access_type" not in begin["authorization_url"]
    assert "prompt" not in begin["authorization_url"]
    # PKCE challenge is still sent best-effort (harmless if Facebook ignores it).
    assert "code_challenge=" in begin["authorization_url"]
    assert "code_challenge_method=S256" in begin["authorization_url"]
    assert begin["state"]


def test_provider_disabled_reports_coming_soon(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_AUTH_PROVIDER_FACEBOOK", "disabled")
    adapter = _facebook_adapter()
    status = adapter.status()
    assert status["status"] == "coming_soon"
    assert status["available"] is False
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")
    assert begin["available"] is False


def test_provider_unavailable_without_credentials() -> None:
    adapter = OAuthProviderAdapter(
        provider=AuthProvider.FACEBOOK,
        client_id="",
        client_secret="",
        authorize_url="https://www.facebook.com/v19.0/dialog/oauth",
        token_url="https://graph.facebook.com/v19.0/oauth/access_token",
        userinfo_url="https://graph.facebook.com/me",
        scopes=("email", "public_profile"),
        flag_env="DSP_AUTH_PROVIDER_FACEBOOK",
    )
    status = adapter.status()
    assert status["status"] == "unavailable"
    assert status["available"] is False


def test_registry_reads_client_id_env_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_FACEBOOK_CLIENT_ID", "new-style-id")
    monkeypatch.setenv("DSP_FACEBOOK_CLIENT_SECRET", "new-style-secret")
    monkeypatch.delenv("DSP_FACEBOOK_APP_ID", raising=False)
    monkeypatch.delenv("DSP_FACEBOOK_APP_SECRET", raising=False)
    registry = build_oauth_registry()
    adapter = registry.require("FACEBOOK")
    assert adapter.client_id == "new-style-id"
    assert adapter.has_credentials()


def test_registry_falls_back_to_legacy_app_id_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DSP_FACEBOOK_CLIENT_ID", raising=False)
    monkeypatch.delenv("DSP_FACEBOOK_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("DSP_FACEBOOK_APP_ID", "legacy-id")
    monkeypatch.setenv("DSP_FACEBOOK_APP_SECRET", "legacy-secret")
    registry = build_oauth_registry()
    adapter = registry.require("FACEBOOK")
    assert adapter.client_id == "legacy-id"
    assert adapter.has_credentials()


# --------------------------------------------------------------------- #
# Adapter-level: profile mapping / callback completion
# --------------------------------------------------------------------- #


def test_complete_login_maps_full_profile(monkeypatch) -> None:
    adapter = _facebook_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")

    monkeypatch.setattr(
        adapter,
        "_exchange_code",
        lambda code, redirect_uri, verifier: {"access_token": "at-1"},
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=20: _FakeResponse(_graph_profile()),
    )

    profile = adapter.complete_login(
        code="auth-code", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
    )
    assert profile.provider == "FACEBOOK"
    assert profile.subject == "fb-user-1"
    assert profile.email == "jamie@example.com"
    assert profile.email_verified is True
    assert profile.name == "Jamie Rivera"
    assert profile.avatar == "https://graph.facebook.com/fb-user-1/picture"
    assert profile.raw_claims["first_name"] == "Jamie"
    assert profile.raw_claims["last_name"] == "Rivera"
    assert profile.raw_claims["locale"] == "en_US"


def test_complete_login_builds_display_name_from_first_last_when_name_missing(monkeypatch) -> None:
    adapter = _facebook_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")

    monkeypatch.setattr(
        adapter, "_exchange_code", lambda code, redirect_uri, verifier: {"access_token": "at-1"}
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=20: _FakeResponse(
            _graph_profile(name=None, first_name="Alex", last_name="Kim")
        ),
    )

    profile = adapter.complete_login(
        code="auth-code", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
    )
    assert profile.name == "Alex Kim"


def test_complete_login_missing_email_is_unverified_not_an_error(monkeypatch) -> None:
    """Facebook users may decline the `email` permission — profile.email is
    None and email_verified is False; the platform layer decides whether
    that blocks login (it does, since it can't identify/link the account)."""
    adapter = _facebook_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")

    monkeypatch.setattr(
        adapter, "_exchange_code", lambda code, redirect_uri, verifier: {"access_token": "at-1"}
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=20: _FakeResponse(_graph_profile(email=None)),
    )

    profile = adapter.complete_login(
        code="auth-code", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
    )
    assert profile.email is None
    assert profile.email_verified is False


def test_complete_login_rejects_missing_subject(monkeypatch) -> None:
    adapter = _facebook_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")

    monkeypatch.setattr(
        adapter, "_exchange_code", lambda code, redirect_uri, verifier: {"access_token": "at-1"}
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=20: _FakeResponse(_graph_profile(id=None)),
    )

    with pytest.raises(AuthenticationError, match="user id"):
        adapter.complete_login(
            code="auth-code", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
        )


def test_complete_login_rejects_invalid_access_token(monkeypatch) -> None:
    """A token-exchange failure (e.g. bad/expired code) must surface as an
    AuthenticationError, not a raw exception."""
    adapter = _facebook_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")

    def _boom(code, redirect_uri, verifier):
        raise AuthenticationError("OAuth token exchange failed: invalid_grant")

    monkeypatch.setattr(adapter, "_exchange_code", _boom)

    with pytest.raises(AuthenticationError, match="token exchange failed"):
        adapter.complete_login(
            code="auth-code", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
        )


def test_complete_login_rejects_invalid_state_replay(monkeypatch) -> None:
    adapter = _facebook_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")

    monkeypatch.setattr(
        adapter, "_exchange_code", lambda code, redirect_uri, verifier: {"access_token": "at-1"}
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=20: _FakeResponse(_graph_profile()),
    )

    adapter.complete_login(
        code="auth-code", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
    )
    with pytest.raises(OAuthChallengeError) as replayed:
        adapter.complete_login(
            code="auth-code-2", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
        )
    assert replayed.value.reason == "replayed"

    with pytest.raises(OAuthChallengeError) as unknown:
        adapter.complete_login(
            code="auth-code-3", state="never-issued-state", redirect_uri="https://app.dspai.local/callback"
        )
    assert unknown.value.reason == "unknown"


def test_complete_login_surfaces_userinfo_failure(monkeypatch) -> None:
    adapter = _facebook_adapter()
    begin = adapter.begin_login(redirect_uri="https://app.dspai.local/callback")

    monkeypatch.setattr(
        adapter, "_exchange_code", lambda code, redirect_uri, verifier: {"access_token": "at-1"}
    )

    def _boom(req, timeout=20):
        raise TimeoutError("graph api unreachable")

    monkeypatch.setattr("urllib.request.urlopen", _boom)

    with pytest.raises(AuthenticationError, match="OAuth userinfo failed"):
        adapter.complete_login(
            code="auth-code", state=begin["state"], redirect_uri="https://app.dspai.local/callback"
        )


# --------------------------------------------------------------------- #
# EnterpriseAuthPlatform: login / link / unlink / logout / audit
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


def _fb_profile(subject: str = "fb-user-1", email: str | None = "jamie@example.com", verified: bool = True):
    return OAuthProfile(
        provider="FACEBOOK",
        subject=subject,
        email=email,
        email_verified=verified,
        name="Jamie Rivera",
        avatar="https://graph.facebook.com/fb-user-1/picture",
        raw_claims={"first_name": "Jamie", "last_name": "Rivera", "locale": "en_US"},
    )


def test_oauth_callback_new_account_provisioning(platform: EnterpriseAuthPlatform) -> None:
    result = platform._login_from_oauth_profile(_fb_profile())
    assert result["tokens"]["access_token"]
    assert result["tokens"]["refresh_token"]
    user = platform._get_by_provider_subject("FACEBOOK", "fb-user-1")
    assert user is not None
    assert user.email == "jamie@example.com"
    events = platform.audit.list_events(user_id=user.user_id, event_type="oauth.facebook.login")
    assert events


def test_oauth_callback_links_existing_verified_email_account(platform: EnterpriseAuthPlatform) -> None:
    reg = platform.register_email(
        name="Jamie Rivera",
        email="jamie@example.com",
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    platform.verify_email(reg["verification_token"])

    result = platform._login_from_oauth_profile(_fb_profile())
    assert result["tokens"]["access_token"]
    user = platform._get_by_email("jamie@example.com")
    assert user is not None
    links = user.metadata.get("linked_providers") or []
    assert any(lnk["provider"] == "FACEBOOK" for lnk in links)
    all_users = [u for u in platform.auth.users.list_users() if u.email == "jamie@example.com"]
    assert len(all_users) == 1


def test_oauth_callback_rejects_missing_email(
    platform: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Facebook profile with no `email` permission cannot be used to sign
    in — there is nothing to identify/link the account by."""
    monkeypatch.setattr(
        platform.oauth,
        "complete",
        lambda provider, **kwargs: _fb_profile(email=None, verified=False),
    )
    with pytest.raises(AuthenticationError, match="email"):
        platform.oauth_callback(
            "FACEBOOK", code="code", state="state", redirect_uri="https://app/callback"
        )
    events = platform.audit.list_events(event_type="oauth.facebook.failure")
    assert events


def test_oauth_callback_records_failure_and_callback_events(
    platform: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(provider, **kwargs):
        raise AuthenticationError("Invalid or expired OAuth state.")

    monkeypatch.setattr(platform.oauth, "complete", _boom)
    with pytest.raises(AuthenticationError):
        platform.oauth_callback(
            "FACEBOOK", code="bad", state="s", redirect_uri="https://app/callback"
        )
    failures = platform.audit.list_events(event_type="oauth.facebook.failure")
    assert failures
    callbacks = platform.audit.list_events(event_type="oauth.facebook.callback")
    assert not callbacks  # complete() raised before the callback event fires


def test_oauth_callback_records_callback_and_login_events_on_success(
    platform: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(platform.oauth, "complete", lambda provider, **kwargs: _fb_profile())
    result = platform.oauth_callback(
        "FACEBOOK", code="good", state="s", redirect_uri="https://app/callback"
    )
    assert result["tokens"]["access_token"]
    assert platform.audit.list_events(event_type="oauth.facebook.callback")
    assert platform.audit.list_events(event_type="oauth.facebook.login")


def test_link_oauth_provider_binds_facebook_to_authenticated_user(
    platform: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    reg = platform.register_email(
        name="Owner",
        email="owner@example.com",
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    platform.verify_email(reg["verification_token"])
    user = platform._get_by_email("owner@example.com")
    assert user is not None

    monkeypatch.setattr(
        platform.oauth,
        "complete",
        lambda provider, **kwargs: _fb_profile(subject="fb-owner-1", email="owner@example.com"),
    )
    result = platform.link_oauth_provider(
        user.user_id, "FACEBOOK", code="code", state="state", redirect_uri="https://app/callback"
    )
    assert result["ok"] is True
    assert any(lnk["provider"] == "FACEBOOK" for lnk in result["user"]["linkedProviders"])
    events = platform.audit.list_events(user_id=user.user_id, event_type="oauth.facebook.link")
    assert events


def test_link_oauth_provider_rejects_facebook_identity_owned_by_other_user(
    platform: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    platform._login_from_oauth_profile(_fb_profile(subject="shared-fb-id", email="first@example.com"))

    reg = platform.register_email(
        name="Second",
        email="second@example.com",
        password="StrongPass12!",
        confirm_password="StrongPass12!",
    )
    platform.verify_email(reg["verification_token"])
    second = platform._get_by_email("second@example.com")
    assert second is not None

    monkeypatch.setattr(
        platform.oauth,
        "complete",
        lambda provider, **kwargs: _fb_profile(subject="shared-fb-id", email="first@example.com"),
    )
    with pytest.raises(ValidationError, match="already linked"):
        platform.link_oauth_provider(
            second.user_id, "FACEBOOK", code="code", state="state", redirect_uri="https://app/callback"
        )
    failures = platform.audit.list_events(user_id=second.user_id, event_type="oauth.facebook.failure")
    assert failures


def test_unlink_facebook_provider_removes_link_and_records_audit(platform: EnterpriseAuthPlatform) -> None:
    platform._login_from_oauth_profile(_fb_profile())
    user_id = platform._get_by_provider_subject("FACEBOOK", "fb-user-1").user_id  # type: ignore[union-attr]

    out = platform.unlink_provider(user_id, "FACEBOOK")
    links = out.get("linkedProviders") or []
    assert not any(lnk["provider"] == "FACEBOOK" for lnk in links)
    events = platform.audit.list_events(user_id=user_id, event_type="oauth.facebook.unlink")
    assert events


def test_logout_revokes_all_sessions_for_facebook_user(platform: EnterpriseAuthPlatform) -> None:
    result = platform._login_from_oauth_profile(_fb_profile())
    user_id = platform._get_by_provider_subject("FACEBOOK", "fb-user-1").user_id  # type: ignore[union-attr]
    assert result["tokens"]["access_token"]

    out = platform.revoke_sessions_for_user(user_id)
    assert out.get("sessions_revoked", 0) >= 1


def test_facebook_provider_status_unavailable_without_credentials(
    platform: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DSP_FACEBOOK_CLIENT_ID", raising=False)
    monkeypatch.delenv("DSP_FACEBOOK_APP_ID", raising=False)
    monkeypatch.delenv("DSP_FACEBOOK_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("DSP_FACEBOOK_APP_SECRET", raising=False)

    platform.oauth = build_oauth_registry()
    status = platform.provider_status()
    facebook = next(p for p in status["oauth"] if p["provider"] == "FACEBOOK")
    assert facebook["status"] == "unavailable"
    assert facebook["available"] is False


def test_facebook_provider_status_available_when_configured(
    platform: EnterpriseAuthPlatform, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DSP_FACEBOOK_CLIENT_ID", "fb-id")
    monkeypatch.setenv("DSP_FACEBOOK_CLIENT_SECRET", "fb-secret")
    monkeypatch.setenv("DSP_AUTH_PROVIDER_FACEBOOK", "auto")

    platform.oauth = build_oauth_registry()
    status = platform.provider_status()
    facebook = next(p for p in status["oauth"] if p["provider"] == "FACEBOOK")
    assert facebook["status"] == "available"
    assert facebook["available"] is True
