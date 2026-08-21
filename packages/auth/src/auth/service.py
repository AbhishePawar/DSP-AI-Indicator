"""Auth service façade (EPIC-A009)."""

from __future__ import annotations

from typing import Any, Mapping

from auth.authentication import AuthenticationService
from auth.authorization import AuthorizationService
from auth.exceptions import AuthorizationError, ValidationError
from auth.jwt import JwtService
from auth.models import (
    AUTH_SCHEMA_VERSION,
    AUTH_SERVICE_VERSION,
    PERMISSIONS,
    AuthUser,
)
from auth.roles import RoleRegistry, get_role_registry
from auth.sessions import SessionManager
from auth.users import UserStore

__all__ = [
    "AuthService",
    "get_auth_service",
    "reset_auth_service_for_tests",
]


class AuthService:
    """Institutional authentication + RBAC — identity only; no research mutation."""

    def __init__(
        self,
        persistence_service: Any,
        *,
        jwt_secret: str = "dsp-auth-dev-secret",
        roles: RoleRegistry | None = None,
    ) -> None:
        self.persistence = persistence_service
        self.roles = roles or get_role_registry()
        self.users = UserStore(persistence_service)
        self.sessions = SessionManager(persistence_service)
        self.jwt = JwtService(jwt_secret)
        self.authentication = AuthenticationService(
            self.users, self.sessions, self.jwt
        )
        self.authorization = AuthorizationService(self.roles)

    def schema(self) -> dict[str, Any]:
        return {
            "schema_version": AUTH_SCHEMA_VERSION,
            "service_version": AUTH_SERVICE_VERSION,
            "roles": self.roles.list_roles(),
            "permissions": list(PERMISSIONS),
            "rules": [
                "identity_and_authorization_only",
                "no_research_mutation",
                "no_financial_model_changes",
                "passwords_hashed_never_plaintext",
                "deterministic_jwt_with_fixed_iat",
                "persistence_via_a008_metadata",
            ],
        }

    def create_user(
        self,
        *,
        username: str,
        email: str,
        password: str,
        display_name: str | None = None,
        roles: list[str] | None = None,
        user_id: str | None = None,
        created_at: str | None = None,
        password_salt: str | None = None,
    ) -> dict[str, Any]:
        for role in roles or []:
            self.roles.require(role)
        user = self.users.create(
            username=username,
            email=email,
            password=password,
            display_name=display_name,
            roles=roles,
            user_id=user_id,
            created_at=created_at,
            password_salt=password_salt,
        )
        return user.to_dict()

    def list_users(self) -> list[dict[str, Any]]:
        return [u.to_dict() for u in self.users.list_users()]

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        user = self.users.get(user_id)
        return user.to_dict() if user else None

    def set_user_roles(self, user_id: str, roles: list[str]) -> dict[str, Any]:
        for role in roles:
            self.roles.require(role)
        return self.users.set_roles(user_id, roles).to_dict()

    def list_roles(self) -> list[dict[str, Any]]:
        return self.roles.list_roles()

    def upsert_role(
        self,
        role_id: str,
        *,
        name: str | None = None,
        permissions: list[str] | None = None,
    ) -> dict[str, Any]:
        return self.roles.upsert(
            role_id, name=name, permissions=permissions
        ).to_dict()

    def list_permissions(self) -> list[str]:
        return list(PERMISSIONS)

    def login(self, **kwargs: Any) -> dict[str, Any]:
        return self.authentication.login(**kwargs)

    def logout(self, **kwargs: Any) -> dict[str, Any]:
        return self.authentication.logout(**kwargs)

    def refresh(self, **kwargs: Any) -> dict[str, Any]:
        return self.authentication.refresh(**kwargs)

    def current_user(self, access_token: str, **kwargs: Any) -> dict[str, Any]:
        return self.authentication.current_user_from_access_token(
            access_token, **kwargs
        ).to_dict()

    def evaluate_permission(
        self, user_id: str, permission: str
    ) -> dict[str, Any]:
        user = self.users.get(user_id)
        if user is None:
            raise ValidationError("user not found")
        return self.authorization.evaluate(user, permission)

    def require_permission(self, user: AuthUser | Mapping[str, Any], permission: str) -> None:
        if isinstance(user, AuthUser):
            self.authorization.require_permission(user, permission)
            return
        uid = str(user.get("user_id") or "")
        loaded = self.users.get(uid)
        if loaded is None:
            raise AuthorizationError("user not found")
        self.authorization.require_permission(loaded, permission)

    def protect(
        self, access_token: str, permission: str, *, now: Any = None
    ) -> dict[str, Any]:
        """Validate access token and require permission — for platform service guards."""
        user = self.authentication.current_user_from_access_token(
            access_token, now=now
        )
        self.authorization.require_permission(user, permission)
        return user.to_dict()


_SVC: AuthService | None = None


def get_auth_service(
    persistence_service: Any | None = None,
    *,
    jwt_secret: str | None = None,
) -> AuthService:
    global _SVC
    if _SVC is None:
        if persistence_service is None:
            from persistence import get_persistence_service

            persistence_service = get_persistence_service()
        if jwt_secret is None:
            import os

            from auth.credential_boundary import (
                AUTH_JWT_SECRET_ENV,
                auth_jwt_secret_is_default,
                resolve_auth_jwt_secret,
            )

            jwt_secret = resolve_auth_jwt_secret()
            # P0-05 — fail closed: never mint/validate institutional JWT with
            # a default secret when DSP_ENVIRONMENT=production.
            if os.environ.get("DSP_ENVIRONMENT", "").lower() == "production" and (
                auth_jwt_secret_is_default(jwt_secret)
            ):
                raise RuntimeError(
                    f"{AUTH_JWT_SECRET_ENV} must be set to a non-default value "
                    "in production"
                )
        _SVC = AuthService(persistence_service, jwt_secret=jwt_secret)
    return _SVC


def reset_auth_service_for_tests(service: AuthService | None = None) -> None:
    global _SVC
    _SVC = service
