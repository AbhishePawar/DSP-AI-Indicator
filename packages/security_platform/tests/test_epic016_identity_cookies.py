"""EPIC-016 — identity ports, cookies, CSRF contract tests."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

from security_platform.security.cookies import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    CSRF_HEADER,
    REFRESH_COOKIE,
    clear_auth_cookies,
    cookie_auth_enabled,
    set_auth_cookies,
    validate_csrf,
)
from security_platform.security.identity.oauth import (
    InMemoryDeviceSessionStore,
    LocalOidcClientAdapter,
    LocalSsoAdapter,
    NullOAuth2AuthorizationServer,
    NullSsoProvider,
)


def test_null_sso_and_oauth_honest_unavailable() -> None:
    sso = NullSsoProvider()
    assert sso.is_available() is False
    begin = sso.begin_login(redirect_uri="https://app.example/callback")
    assert begin["authorization_url"] is None
    assert "unavailable" in begin["message"].lower()

    oauth = NullOAuth2AuthorizationServer()
    with pytest.raises(Exception):
        oauth.discovery()


def test_local_oidc_and_device_sessions() -> None:
    oidc = LocalOidcClientAdapter()
    code = oidc.seed_code(
        subject="user-1", redirect_uri="local://callback", email="a@b.co"
    )
    tokens = oidc.exchange_code(code, redirect_uri="local://callback")
    assert tokens["access_token"]
    assert tokens["claims"]["sub"] == "user-1"

    devices = InMemoryDeviceSessionStore()
    row = devices.register(
        session_id="s1",
        user_id="user-1",
        device_label="laptop",
        ip_hint="198.51.100.1",
    )
    assert row["status"] == "active"
    rotated = devices.rotate("s1")
    assert rotated["session_id"] != "s1"
    assert devices.revoke_all("user-1") >= 1


def test_local_sso_adapter_available() -> None:
    oidc = LocalOidcClientAdapter()
    code = oidc.seed_code(subject="sso-user", redirect_uri="local://callback")
    sso = LocalSsoAdapter(oidc)
    assert sso.is_available() is True
    session = sso.complete_login(code=code)
    assert session.subject == "sso-user"
    sso.logout(session.sso_session_id)


def test_cookie_helpers_httponly_and_csrf() -> None:
    os.environ["DSP_COOKIE_AUTH"] = "true"
    os.environ["DSP_COOKIE_SECURE"] = "false"
    assert cookie_auth_enabled() is True

    response = Response()
    csrf = set_auth_cookies(
        response,
        access_token="access-token-value",
        refresh_token="refresh-token-value",
        session_id="sess-1",
        remember_me=False,
    )
    assert csrf
    header = response.headers.getlist("set-cookie")
    joined = " ".join(header).lower()
    assert ACCESS_COOKIE in joined
    assert REFRESH_COOKIE in joined
    assert "httponly" in joined
    assert CSRF_COOKIE in joined

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [
            (b"cookie", f"{CSRF_COOKIE}={csrf}".encode()),
            (CSRF_HEADER.lower().encode(), csrf.encode()),
        ],
        "query_string": b"",
        "client": ("127.0.0.1", 123),
        "server": ("test", 80),
        "scheme": "http",
        "root_path": "",
        "http_version": "1.1",
    }
    request = Request(scope)
    assert validate_csrf(request) is True

    clear_auth_cookies(response)


def test_api_login_sets_cookies_when_enabled() -> None:
    keys = (
        "DSP_COOKIE_AUTH",
        "DSP_ENABLE_SECURITY",
        "DSP_JWT_SECRET",
        "DSP_COOKIE_SECURE",
        "DSP_CSRF_ENABLED",
    )
    prior = {k: os.environ.get(k) for k in keys}
    try:
        os.environ["DSP_COOKIE_AUTH"] = "true"
        os.environ["DSP_COOKIE_SECURE"] = "false"
        os.environ["DSP_CSRF_ENABLED"] = "true"
        os.environ.pop("DSP_ENABLE_SECURITY", None)

        from api_platform.api.app import create_app
        from security_platform import Role, SecurityBundle, SecuritySettings

        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="unit-test-secret-epic016"),
            seed_admin=False,
        )
        bundle.identity.provision(
            username="cookieuser",
            role=Role.RESEARCHER,
            password="StrongPass12",
        )
        app = create_app(security=bundle, enable_security=False)
        client = TestClient(app)
        res = client.post(
            "/api/v1/auth/login",
            json={"username": "cookieuser", "password": "StrongPass12"},
        )
        assert res.status_code == 200
        assert res.json()["ok"] is True
        assert ACCESS_COOKIE in res.cookies
        assert CSRF_COOKIE in res.cookies
        assert res.json()["payload"]["cookie_auth"] is True

        # Mutating call with access cookie but without CSRF header must fail.
        bad = client.post(
            "/api/v1/auth/logout",
            cookies={
                ACCESS_COOKIE: res.cookies[ACCESS_COOKIE],
                CSRF_COOKIE: res.cookies[CSRF_COOKIE],
            },
        )
        assert bad.status_code == 403

        good = client.post(
            "/api/v1/auth/logout",
            cookies={
                ACCESS_COOKIE: res.cookies[ACCESS_COOKIE],
                CSRF_COOKIE: res.cookies[CSRF_COOKIE],
            },
            headers={CSRF_HEADER: res.cookies[CSRF_COOKIE]},
        )
        assert good.status_code == 200
    finally:
        for k, v in prior.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_logout_revokes_refresh_token_and_clears_cookies() -> None:
    keys = (
        "DSP_COOKIE_AUTH",
        "DSP_ENABLE_SECURITY",
        "DSP_JWT_SECRET",
        "DSP_COOKIE_SECURE",
        "DSP_CSRF_ENABLED",
    )
    prior = {k: os.environ.get(k) for k in keys}
    try:
        os.environ["DSP_COOKIE_AUTH"] = "true"
        os.environ["DSP_COOKIE_SECURE"] = "false"
        os.environ["DSP_CSRF_ENABLED"] = "true"
        os.environ.pop("DSP_ENABLE_SECURITY", None)

        from api_platform.api.app import create_app
        from security_platform import Role, SecurityBundle, SecuritySettings

        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="unit-test-secret-epic016"),
            seed_admin=False,
        )
        bundle.identity.provision(
            username="logoutuser",
            role=Role.RESEARCHER,
            password="StrongPass12",
        )
        app = create_app(security=bundle, enable_security=False)
        client = TestClient(app)

        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "logoutuser", "password": "StrongPass12"},
        )
        assert login_resp.status_code == 200
        assert ACCESS_COOKIE in login_resp.cookies
        assert CSRF_COOKIE in login_resp.cookies
        refresh_token = login_resp.json()["payload"]["refresh_token"]

        logout_resp = client.post(
            "/api/v1/auth/logout",
            cookies={
                ACCESS_COOKIE: login_resp.cookies[ACCESS_COOKIE],
                CSRF_COOKIE: login_resp.cookies[CSRF_COOKIE],
            },
            headers={CSRF_HEADER: login_resp.cookies[CSRF_COOKIE]},
        )
        assert logout_resp.status_code == 200
        assert logout_resp.json()["payload"]["logged_out"] is True

        assert ACCESS_COOKIE not in logout_resp.cookies
        assert REFRESH_COOKIE not in logout_resp.cookies

        refresh_resp = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 401
    finally:
        for k, v in prior.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_logout_without_dsp_session_revokes_via_refresh_token() -> None:
    keys = (
        "DSP_COOKIE_AUTH",
        "DSP_ENABLE_SECURITY",
        "DSP_JWT_SECRET",
        "DSP_COOKIE_SECURE",
        "DSP_CSRF_ENABLED",
    )
    prior = {k: os.environ.get(k) for k in keys}
    try:
        os.environ["DSP_COOKIE_AUTH"] = "true"
        os.environ["DSP_COOKIE_SECURE"] = "false"
        os.environ["DSP_CSRF_ENABLED"] = "true"
        os.environ.pop("DSP_ENABLE_SECURITY", None)

        from api_platform.api.app import create_app
        from security_platform import Role, SecurityBundle, SecuritySettings

        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="unit-test-secret-epic016"),
            seed_admin=False,
        )
        bundle.identity.provision(
            username="partialcookieuser",
            role=Role.RESEARCHER,
            password="StrongPass12",
        )
        app = create_app(security=bundle, enable_security=False)
        client = TestClient(app)

        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "partialcookieuser", "password": "StrongPass12"},
        )
        assert login_resp.status_code == 200
        assert ACCESS_COOKIE in login_resp.cookies
        assert CSRF_COOKIE in login_resp.cookies
        refresh_token = login_resp.json()["payload"]["refresh_token"]

        logout_resp = client.post(
            "/api/v1/auth/logout",
            cookies={
                ACCESS_COOKIE: login_resp.cookies[ACCESS_COOKIE],
                CSRF_COOKIE: login_resp.cookies[CSRF_COOKIE],
            },
            headers={CSRF_HEADER: login_resp.cookies[CSRF_COOKIE]},
        )
        assert logout_resp.status_code == 200
        assert logout_resp.json()["payload"]["logged_out"] is True

        refresh_resp = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 401
    finally:
        for k, v in prior.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_logout_without_any_cookies_returns_401() -> None:
    keys = (
        "DSP_COOKIE_AUTH",
        "DSP_ENABLE_SECURITY",
        "DSP_JWT_SECRET",
        "DSP_COOKIE_SECURE",
        "DSP_CSRF_ENABLED",
    )
    prior = {k: os.environ.get(k) for k in keys}
    try:
        os.environ["DSP_COOKIE_AUTH"] = "true"
        os.environ["DSP_COOKIE_SECURE"] = "false"
        os.environ["DSP_CSRF_ENABLED"] = "true"
        os.environ.pop("DSP_ENABLE_SECURITY", None)

        from api_platform.api.app import create_app
        from security_platform import Role, SecurityBundle, SecuritySettings

        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="unit-test-secret-epic016"),
            seed_admin=False,
        )
        bundle.identity.provision(
            username="nosesuser",
            role=Role.RESEARCHER,
            password="StrongPass12",
        )
        app = create_app(security=bundle, enable_security=False)
        client = TestClient(app)

        logout_resp = client.post("/api/v1/auth/logout")
        assert logout_resp.status_code == 401
    finally:
        for k, v in prior.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
