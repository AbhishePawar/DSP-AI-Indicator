"""Password reset + email verification flows, and role-gating of protected APIs."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DSP_ENABLE_SECURITY", "true")
    monkeypatch.setenv("DSP_JWT_SECRET", "a" * 64)
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    from api_platform.api.app import create_app

    return TestClient(create_app())


def _register(client, email="reset@example.com", pw="UserPass12345"):
    r = client.post("/api/v1/auth/register", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    client.cookies.clear()
    return r.json()["payload"]["access_token"]


def test_password_reset_flow(client):
    _register(client, "reset@example.com", "UserPass12345")
    # forgot-password never leaks existence; returns a token in non-prod
    f = client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    assert f.status_code == 200, f.text
    token = f.json()["payload"]["reset_token"]
    assert token

    # reset to a new password
    r = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewUserPass987"},
    )
    assert r.status_code == 200, r.text
    client.cookies.clear()

    # old password no longer works; new password logs in
    bad = client.post(
        "/api/v1/auth/login",
        json={"username": "reset@example.com", "password": "UserPass12345"},
    )
    assert bad.status_code in (401, 429)
    client.cookies.clear()
    ok = client.post(
        "/api/v1/auth/login",
        json={"username": "reset@example.com", "password": "NewUserPass987"},
    )
    assert ok.status_code == 200, ok.text


def test_forgot_password_no_user_enumeration(client):
    r = client.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.com"})
    assert r.status_code == 200  # same response shape whether or not user exists
    assert r.json()["payload"]["requested"] is True


def test_reset_with_bad_token_rejected(client):
    r = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "NewUserPass987"},
    )
    assert r.status_code == 400


def test_email_verification_flow(client):
    token = _register(client, "verify@example.com", "UserPass12345")
    req = client.post(
        "/api/v1/auth/verify-email/request",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert req.status_code == 200, req.text
    vtoken = req.json()["payload"]["verification_token"]
    conf = client.post("/api/v1/auth/verify-email/confirm", json={"token": vtoken})
    assert conf.status_code == 200, conf.text
    assert conf.json()["payload"]["email_verified"] is True


def test_verify_request_requires_auth(client):
    assert client.post("/api/v1/auth/verify-email/request").status_code == 401


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("post", "/api/v1/analyse", {"ticker": "TCS", "financial_statements": {}}),
        ("get", "/api/v1/analyze/company", None),
        ("get", "/api/v1/portfolio", None),
        ("get", "/api/v1/valuation", None),
    ],
)
def test_protected_apis_require_auth(client, method, path, body):
    resp = getattr(client, method)(path, json=body) if body is not None else getattr(client, method)(path)
    # Gated by SecurityMiddleware -> unauthenticated requests are refused (401/403),
    # never served with data.
    assert resp.status_code in (401, 403), f"{path} -> {resp.status_code}"
