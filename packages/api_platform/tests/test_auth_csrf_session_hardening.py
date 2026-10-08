"""Focused regression tests for CSRF middleware hardening and session probe."""

from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import JSONResponse

from api_platform.api.app import create_app
from api_platform.api.csrf_middleware import _AUTH_EXEMPT, CsrfMiddleware
from security_platform import Role, SecurityBundle, SecuritySettings
from security_platform.security.cookies import ACCESS_COOKIE, CSRF_COOKIE, CSRF_HEADER


def test_csrf_auth_exempt_includes_oauth_begin_not_callback() -> None:
    assert "/auth/enterprise/oauth/begin" in _AUTH_EXEMPT
    assert "/api/v1/auth/enterprise/oauth/begin" in _AUTH_EXEMPT
    assert "/auth/enterprise/oauth/callback" not in _AUTH_EXEMPT
    assert "/api/v1/auth/enterprise/oauth/callback" not in _AUTH_EXEMPT
    assert "/auth/login" in _AUTH_EXEMPT
    assert "/api/v1/auth/login" in _AUTH_EXEMPT


def test_session_probe_anonymous_returns_200_unauthenticated() -> None:
    keys = ("DSP_COOKIE_AUTH", "DSP_CSRF_ENABLED")
    prior = {k: os.environ.get(k) for k in keys}
    try:
        os.environ["DSP_COOKIE_AUTH"] = "true"
        os.environ["DSP_CSRF_ENABLED"] = "true"

        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="test-hardening-secret"),
            seed_admin=False,
        )
        app = create_app(security=bundle, enable_security=True)
        client = TestClient(app)

        res1 = client.get("/auth/session")
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["ok"] is True
        assert data1["payload"]["authenticated"] is False
        assert "password" not in str(data1).lower()
        assert "secret" not in str(data1).lower()

        res2 = client.get("/api/v1/auth/session")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["ok"] is True
        assert data2["payload"]["authenticated"] is False
    finally:
        for k, v in prior.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_session_probe_with_valid_cookie_session_reports_authenticated() -> None:
    keys = ("DSP_COOKIE_AUTH", "DSP_CSRF_ENABLED")
    prior = {k: os.environ.get(k) for k in keys}
    try:
        os.environ["DSP_COOKIE_AUTH"] = "true"
        os.environ["DSP_CSRF_ENABLED"] = "true"

        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="test-hardening-secret"),
            seed_admin=False,
        )
        bundle.identity.provision(
            username="validuser",
            role=Role.RESEARCHER,
            password="StrongPass12",
        )
        app = create_app(security=bundle, enable_security=True)
        client = TestClient(app)

        login = client.post(
            "/api/v1/auth/login",
            json={"username": "validuser", "password": "StrongPass12"},
        )
        assert login.status_code == 200
        assert ACCESS_COOKIE in login.cookies

        res = client.get(
            "/api/v1/auth/session",
            cookies={
                ACCESS_COOKIE: login.cookies[ACCESS_COOKIE],
                CSRF_COOKIE: login.cookies[CSRF_COOKIE],
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["payload"]["authenticated"] is True
        assert body["payload"]["cookie_auth"] is True
    finally:
        for k, v in prior.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_session_probe_with_stale_or_invalid_cookie_reports_unauthenticated() -> None:
    keys = ("DSP_COOKIE_AUTH", "DSP_CSRF_ENABLED")
    prior = {k: os.environ.get(k) for k in keys}
    try:
        os.environ["DSP_COOKIE_AUTH"] = "true"
        os.environ["DSP_CSRF_ENABLED"] = "true"

        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="test-hardening-secret"),
            seed_admin=False,
        )
        app = create_app(security=bundle, enable_security=True)
        client = TestClient(app)

        res = client.get(
            "/api/v1/auth/session",
            cookies={
                ACCESS_COOKIE: "invalid-expired-junk-token",
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["payload"]["authenticated"] is False
        assert body["payload"]["session_id"] is None
    finally:
        for k, v in prior.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_csrf_middleware_allows_oauth_begin_even_with_stale_access_cookie() -> None:
    keys = ("DSP_COOKIE_AUTH", "DSP_CSRF_ENABLED")
    prior = {k: os.environ.get(k) for k in keys}
    try:
        os.environ["DSP_COOKIE_AUTH"] = "true"
        os.environ["DSP_CSRF_ENABLED"] = "true"

        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="test-hardening-secret"),
            seed_admin=False,
        )
        app = create_app(security=bundle, enable_security=False)
        client = TestClient(app)

        # Calling oauth begin with a stale access cookie and no CSRF token must NOT return 403 CSRFError.
        # It will reach the route handler (which returns 200 with unavailable message if Google is unconfigured).
        res = client.post(
            "/api/v1/auth/enterprise/oauth/begin",
            json={"provider": "GOOGLE", "redirect_uri": "https://example.com/oauth/callback"},
            cookies={ACCESS_COOKIE: "stale-access-cookie"},
        )
        assert res.status_code != 403
    finally:
        for k, v in prior.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_csrf_middleware_still_rejects_mutating_requests_with_access_cookie_missing_csrf() -> None:
    keys = ("DSP_COOKIE_AUTH", "DSP_CSRF_ENABLED")
    prior = {k: os.environ.get(k) for k in keys}
    try:
        os.environ["DSP_COOKIE_AUTH"] = "true"
        os.environ["DSP_CSRF_ENABLED"] = "true"

        bundle = SecurityBundle.create(
            SecuritySettings(jwt_secret="test-hardening-secret"),
            seed_admin=False,
        )
        bundle.identity.provision(
            username="csrfuser",
            role=Role.RESEARCHER,
            password="StrongPass12",
        )
        app = create_app(security=bundle, enable_security=False)
        client = TestClient(app)

        login = client.post(
            "/api/v1/auth/login",
            json={"username": "csrfuser", "password": "StrongPass12"},
        )
        assert login.status_code == 200

        # Mutating request (logout) with valid access cookie and no CSRF header => 403
        bad = client.post(
            "/api/v1/auth/logout",
            cookies={
                ACCESS_COOKIE: login.cookies[ACCESS_COOKIE],
                CSRF_COOKIE: login.cookies[CSRF_COOKIE],
            },
        )
        assert bad.status_code == 403

        # With valid CSRF header => 200
        good = client.post(
            "/api/v1/auth/logout",
            cookies={
                ACCESS_COOKIE: login.cookies[ACCESS_COOKIE],
                CSRF_COOKIE: login.cookies[CSRF_COOKIE],
            },
            headers={CSRF_HEADER: login.cookies[CSRF_COOKIE]},
        )
        assert good.status_code == 200
    finally:
        for k, v in prior.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
