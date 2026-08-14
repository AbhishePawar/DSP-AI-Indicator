"""OAuth adapter nonce generation + additive id_token verification tests."""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest

from auth.enterprise_models import AuthProvider
from auth.exceptions import AuthenticationError
from auth.oauth_providers import OAuthProviderAdapter
from auth.oidc import OidcVerificationUnavailable


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _google_adapter() -> OAuthProviderAdapter:
    return OAuthProviderAdapter(
        provider=AuthProvider.GOOGLE,
        client_id="client-123",
        client_secret="secret",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
        scopes=("openid", "email", "profile"),
        flag_env="DSP_AUTH_PROVIDER_GOOGLE",
        oidc_jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
        oidc_issuers=("https://accounts.google.com", "accounts.google.com"),
    )


def test_begin_login_includes_nonce_when_oidc_configured() -> None:
    adapter = _google_adapter()
    begin = adapter.begin_login(redirect_uri="http://localhost/callback")
    query = parse_qs(urlparse(begin["authorization_url"]).query)
    assert "nonce" in query
    assert len(query["nonce"][0]) > 10


def test_complete_login_cross_checks_id_token_subject(monkeypatch) -> None:
    adapter = _google_adapter()
    begin = adapter.begin_login(redirect_uri="http://localhost/callback")
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
        lambda token, **kwargs: {"sub": "google-sub-1", "email": "user@example.com", "nonce": nonce},
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=20: _FakeResponse(
            {
                "sub": "google-sub-1",
                "email": "user@example.com",
                "email_verified": True,
                "name": "Test User",
                "picture": "https://example.com/pic.png",
            }
        ),
    )

    profile = adapter.complete_login(
        code="auth-code", state=begin["state"], redirect_uri="http://localhost/callback"
    )
    assert profile.subject == "google-sub-1"
    assert profile.email == "user@example.com"


def test_complete_login_rejects_id_token_subject_mismatch(monkeypatch) -> None:
    adapter = _google_adapter()
    begin = adapter.begin_login(redirect_uri="http://localhost/callback")

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
        lambda token, **kwargs: {"sub": "attacker-sub", "email": "user@example.com"},
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=20: _FakeResponse(
            {
                "sub": "google-sub-1",
                "email": "user@example.com",
                "email_verified": True,
            }
        ),
    )

    with pytest.raises(AuthenticationError, match="does not match"):
        adapter.complete_login(
            code="auth-code", state=begin["state"], redirect_uri="http://localhost/callback"
        )


def test_complete_login_rejects_when_id_token_fails_hard_check(monkeypatch) -> None:
    adapter = _google_adapter()
    begin = adapter.begin_login(redirect_uri="http://localhost/callback")

    monkeypatch.setattr(
        adapter,
        "_exchange_code",
        lambda code, redirect_uri, verifier: {
            "access_token": "at-1",
            "id_token": "header.payload.sig",
        },
    )

    def _raise(*args: object, **kwargs: object) -> dict:
        raise ValueError("id_token signature verification failed")

    monkeypatch.setattr("auth.oauth_providers.verify_id_token", _raise)

    with pytest.raises(AuthenticationError, match="id_token rejected"):
        adapter.complete_login(
            code="auth-code", state=begin["state"], redirect_uri="http://localhost/callback"
        )


def test_complete_login_succeeds_when_verification_unavailable(monkeypatch) -> None:
    """No cryptography dependency / JWKS outage must not break existing logins."""
    adapter = _google_adapter()
    begin = adapter.begin_login(redirect_uri="http://localhost/callback")

    monkeypatch.setattr(
        adapter,
        "_exchange_code",
        lambda code, redirect_uri, verifier: {
            "access_token": "at-1",
            "id_token": "header.payload.sig",
        },
    )

    def _unavailable(*args: object, **kwargs: object) -> dict:
        raise OidcVerificationUnavailable("cryptography package not installed")

    monkeypatch.setattr("auth.oauth_providers.verify_id_token", _unavailable)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=20: _FakeResponse(
            {
                "sub": "google-sub-1",
                "email": "user@example.com",
                "email_verified": True,
            }
        ),
    )

    profile = adapter.complete_login(
        code="auth-code", state=begin["state"], redirect_uri="http://localhost/callback"
    )
    assert profile.subject == "google-sub-1"


def test_complete_login_without_id_token_is_unaffected(monkeypatch) -> None:
    """Providers/tokens without an id_token (e.g. Facebook) skip verification entirely."""
    adapter = OAuthProviderAdapter(
        provider=AuthProvider.FACEBOOK,
        client_id="fb-id",
        client_secret="fb-secret",
        authorize_url="https://www.facebook.com/v19.0/dialog/oauth",
        token_url="https://graph.facebook.com/v19.0/oauth/access_token",
        userinfo_url="https://graph.facebook.com/me",
        scopes=("email", "public_profile"),
        flag_env="DSP_AUTH_PROVIDER_FACEBOOK",
    )
    begin = adapter.begin_login(redirect_uri="http://localhost/callback")
    assert "nonce" not in parse_qs(urlparse(begin["authorization_url"]).query)

    monkeypatch.setattr(
        adapter,
        "_exchange_code",
        lambda code, redirect_uri, verifier: {"access_token": "at-1"},
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=20: _FakeResponse({"id": "fb-1", "email": "user@example.com"}),
    )

    profile = adapter.complete_login(
        code="auth-code", state=begin["state"], redirect_uri="http://localhost/callback"
    )
    assert profile.subject == "fb-1"
