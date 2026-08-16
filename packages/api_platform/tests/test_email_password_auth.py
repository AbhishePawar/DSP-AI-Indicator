"""Email + password auth: register, seeded admin login, /auth/me, fail-closed."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DSP_ENABLE_SECURITY", "true")
    monkeypatch.setenv("DSP_JWT_SECRET", "a" * 64)
    monkeypatch.setenv("DSP_ADMIN_EMAIL", "admin@dsp.ai")
    monkeypatch.setenv("DSP_ADMIN_PASSWORD", "DspAdminPass2026")
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    from api_platform.api.app import create_app

    return TestClient(create_app())


def _tok(resp) -> str:
    return resp.json()["payload"]["access_token"]


def test_register_returns_jwt(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "user1@example.com", "password": "UserPass12345"},
    )
    assert r.status_code == 200, r.text
    payload = r.json()["payload"]
    assert payload["access_token"]
    assert payload["role"] == "CLIENT"
    assert payload["email"] == "user1@example.com"


def test_register_weak_password_rejected(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "short"},
    )
    assert r.status_code >= 400  # fail-closed: policy rejects


def test_register_duplicate_email_conflict(client):
    body = {"email": "dup@example.com", "password": "UserPass12345"}
    assert client.post("/api/v1/auth/register", json=body).status_code == 200
    client.cookies.clear()  # avoid CSRF double-submit on repeat POST
    assert client.post("/api/v1/auth/register", json=body).status_code == 409


def test_seeded_admin_login_and_me(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "admin@dsp.ai", "password": "DspAdminPass2026"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["payload"]["role"] == "ADMIN"
    token = _tok(r)

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    p = me.json()["payload"]
    assert p["email"] == "admin@dsp.ai"
    assert p["role"] == "ADMIN"
    assert p["authenticated"] is True


def test_me_without_token_unauthorized(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_login_bad_password_unauthorized(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "admin@dsp.ai", "password": "wrong-password-1"},
    )
    assert r.status_code in (401, 429)
