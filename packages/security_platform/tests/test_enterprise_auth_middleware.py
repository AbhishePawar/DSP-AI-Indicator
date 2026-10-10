"""Enterprise AuthService token bridge tests for SecurityMiddleware."""

from __future__ import annotations

import auth

from security_platform.security.middleware import _authenticate_enterprise_bearer
from security_platform.security.roles import Role


class _FakeAuthService:
    def __init__(self, user: dict[str, object]) -> None:
        self._user = user

    def current_user(self, token: str) -> dict[str, object]:
        assert token == "signed-enterprise-token"
        return self._user


def test_enterprise_admin_token_maps_to_admin_permissions(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "get_auth_service",
        lambda: _FakeAuthService(
            {
                "user_id": "admin-1",
                "username": "admin",
                "roles": ["administrator"],
            }
        ),
    )

    principal = _authenticate_enterprise_bearer(
        "Bearer signed-enterprise-token"
    )

    assert principal is not None
    assert principal.subject == "admin-1"
    assert principal.role is Role.ADMIN
    assert principal.has_permission("ANALYZE_COMPANY")
    assert principal.auth_method == "enterprise_jwt"


def test_enterprise_unknown_role_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "get_auth_service",
        lambda: _FakeAuthService(
            {
                "user_id": "user-1",
                "username": "user",
                "roles": ["unmapped_role"],
            }
        ),
    )

    assert (
        _authenticate_enterprise_bearer("Bearer signed-enterprise-token")
        is None
    )


def test_enterprise_bridge_rejects_non_bearer_tokens() -> None:
    assert _authenticate_enterprise_bearer("ApiKey signed-enterprise-token") is None
