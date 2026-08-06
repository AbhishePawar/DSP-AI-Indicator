"""Platform façade helpers for Institutional Auth & RBAC (EPIC-A009)."""

from __future__ import annotations

from typing import Any

from auth import get_auth_service

__all__ = [
    "auth_schema",
    "create_auth_user",
    "list_auth_users",
    "get_auth_user",
    "set_auth_user_roles",
    "list_auth_roles",
    "upsert_auth_role",
    "list_auth_permissions",
    "auth_login",
    "auth_logout",
    "auth_refresh",
    "auth_current_user",
    "evaluate_auth_permission",
    "protect_with_permission",
]


def auth_schema() -> dict[str, Any]:
    return get_auth_service().schema()


def create_auth_user(**kwargs: Any) -> dict[str, Any]:
    return get_auth_service().create_user(**kwargs)


def list_auth_users() -> list[dict[str, Any]]:
    return get_auth_service().list_users()


def get_auth_user(user_id: str) -> dict[str, Any] | None:
    return get_auth_service().get_user(user_id)


def set_auth_user_roles(user_id: str, roles: list[str]) -> dict[str, Any]:
    return get_auth_service().set_user_roles(user_id, roles)


def list_auth_roles() -> list[dict[str, Any]]:
    return get_auth_service().list_roles()


def upsert_auth_role(
    role_id: str,
    *,
    name: str | None = None,
    permissions: list[str] | None = None,
) -> dict[str, Any]:
    return get_auth_service().upsert_role(
        role_id, name=name, permissions=permissions
    )


def list_auth_permissions() -> list[str]:
    return get_auth_service().list_permissions()


def auth_login(**kwargs: Any) -> dict[str, Any]:
    return get_auth_service().login(**kwargs)


def auth_logout(**kwargs: Any) -> dict[str, Any]:
    return get_auth_service().logout(**kwargs)


def auth_refresh(**kwargs: Any) -> dict[str, Any]:
    return get_auth_service().refresh(**kwargs)


def auth_current_user(access_token: str, **kwargs: Any) -> dict[str, Any]:
    return get_auth_service().current_user(access_token, **kwargs)


def evaluate_auth_permission(user_id: str, permission: str) -> dict[str, Any]:
    return get_auth_service().evaluate_permission(user_id, permission)


def protect_with_permission(
    access_token: str, permission: str, **kwargs: Any
) -> dict[str, Any]:
    return get_auth_service().protect(access_token, permission, **kwargs)
