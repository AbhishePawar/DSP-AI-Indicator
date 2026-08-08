"""Shared helpers for P0-05 authenticated API tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

FIXED = datetime.now(UTC).replace(microsecond=0).isoformat()


def _clear_session(client: TestClient) -> None:
    """Drop cookies so bootstrap POSTs are not CSRF-gated by a prior login."""
    client.cookies.clear()


def register_user(
    client: TestClient,
    *,
    user_id: str,
    username: str,
    password: str = "StrongPass12!",
    roles: list[str] | None = None,
    email: str | None = None,
) -> dict[str, Any]:
    """Bootstrap a user via open /auth/rbac/users (test bootstrap only)."""
    _clear_session(client)
    payload = {
        "username": username,
        "email": email or f"{username}@example.com",
        "password": password,
        "roles": roles or ["administrator"],
        "user_id": user_id,
        "created_at": FIXED,
        "password_salt": "aabbccddeeff0011",
    }
    created = client.post("/api/v1/auth/rbac/users", json=payload)
    if created.status_code == 400 and "duplicate" in created.text.lower():
        return {"user_id": user_id, "username": username}
    assert created.status_code == 200, created.text
    return created.json()["result"]


def bearer_headers(
    client: TestClient,
    *,
    username: str,
    password: str = "StrongPass12!",
    session_id: str | None = None,
) -> dict[str, str]:
    """Login and return Authorization headers for the authenticated principal."""
    _clear_session(client)
    sid = session_id or f"s-{username}-{uuid4().hex[:12]}"
    login = client.post(
        "/api/v1/auth/rbac/login",
        json={
            "username": username,
            "password": password,
            "created_at": FIXED,
            "session_id": sid,
            "access_jti": f"a-{sid}",
            "refresh_jti": f"r-{sid}",
        },
    )
    assert login.status_code == 200, login.text
    token = login.json()["result"]["tokens"]["access_token"]
    # Prefer explicit Bearer over ambient cookies for deterministic tests.
    _clear_session(client)
    return {"Authorization": f"Bearer {token}"}


def admin_headers(
    client: TestClient,
    *,
    user_id: str = "u-p005-admin",
    username: str = "p005admin",
) -> dict[str, str]:
    """Ensure an administrator exists and return Bearer headers."""
    register_user(
        client,
        user_id=user_id,
        username=username,
        roles=["administrator"],
    )
    return bearer_headers(client, username=username)
