"""User / principal models and permission helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from security_platform.security.exceptions import SecurityError
from security_platform.security.permissions import Permission, assert_permission
from security_platform.security.roles import ROLE_PERMISSIONS, Role, assert_role

__all__ = [
    "PermissionManager",
    "SecurityContext",
    "UserPrincipal",
    "UserRecord",
    "UserStore",
]


@dataclass(frozen=True, slots=True)
class UserRecord:
    """User identity record — durable via UserRepositoryPort adapters."""

    user_id: str
    username: str
    role: Role
    active: bool = True
    display_name: str | None = None
    extra_permissions: tuple[Permission, ...] = ()
    email: str | None = None
    password_hash: str | None = None
    email_verified: bool = False
    org_id: str | None = None
    failed_login_count: int = 0
    locked_until: datetime | None = None

    def __post_init__(self) -> None:
        if not self.user_id.strip():
            raise SecurityError("user_id must not be empty")
        if not self.username.strip():
            raise SecurityError("username must not be empty")
        object.__setattr__(self, "role", assert_role(self.role))
        object.__setattr__(
            self,
            "extra_permissions",
            tuple(assert_permission(p) for p in self.extra_permissions),
        )


@dataclass(frozen=True, slots=True)
class UserPrincipal:
    """Authenticated principal identity."""

    subject: str
    role: Role
    permissions: frozenset[Permission]
    auth_method: str
    username: str | None = None
    api_key_id: str | None = None
    session_id: str | None = None

    def has_permission(self, permission: Permission | str) -> bool:
        return assert_permission(permission) in self.permissions


@dataclass(frozen=True, slots=True)
class SecurityContext:
    """Request-scoped security context attached by middleware."""

    principal: UserPrincipal
    authenticated: bool
    guest: bool
    request_id: str | None = None
    issued_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def require(self, permission: Permission | str) -> None:
        from security_platform.security.exceptions import AuthorizationError

        perm = assert_permission(permission)
        if not self.principal.has_permission(perm):
            raise AuthorizationError(
                f"permission denied: {perm.value} (role={self.principal.role.value})"
            )


class UserStore:
    """Compatibility façade over a UserRepositoryPort (in-memory by default)."""

    def __init__(self, repository: Any | None = None) -> None:
        if repository is None:
            from security_platform.security.identity.repository import (
                InMemoryUserRepository,
            )

            repository = InMemoryUserRepository()
        self._repo = repository

    @property
    def repository(self) -> Any:
        return self._repo

    def add(self, user: UserRecord, *, replace: bool = False) -> UserRecord:
        existing = self._repo.get(user.user_id)
        if existing is not None and not replace:
            raise SecurityError(f"duplicate user_id: {user.user_id!r}")
        by_name = self._repo.get_by_username(user.username)
        if by_name is not None and by_name.user_id.lower() != user.user_id.lower():
            if not replace:
                raise SecurityError(f"duplicate username: {user.username!r}")
        return self._repo.upsert(user)

    def get(self, user_id: str) -> UserRecord:
        user = self._repo.get(user_id)
        if user is None:
            raise SecurityError(f"unknown user: {user_id!r}")
        return user

    def get_by_username(self, username: str) -> UserRecord:
        user = self._repo.get_by_username(username)
        if user is None:
            raise SecurityError(f"unknown username: {username!r}")
        return user

    def list_users(self) -> tuple[UserRecord, ...]:
        return tuple(self._repo.list_users())

    def __len__(self) -> int:
        return len(self.list_users())


class PermissionManager:
    """Aggregates role + extra permissions for a user / principal."""

    def permissions_for_user(self, user: UserRecord) -> frozenset[Permission]:
        base = set(ROLE_PERMISSIONS[user.role])
        base.update(user.extra_permissions)
        return frozenset(base)

    def permissions_for_role(self, role: Role | str) -> frozenset[Permission]:
        return ROLE_PERMISSIONS[assert_role(role)]
