"""Platform façade helpers for Enterprise Admin Console (EPIC-A010)."""

from __future__ import annotations

from typing import Any

from admin import get_admin_service

__all__ = [
    "admin_schema",
    "admin_dashboard",
    "admin_list_users",
    "admin_get_user",
    "admin_create_user",
    "admin_set_user_roles",
    "admin_list_roles",
    "admin_upsert_role",
    "admin_list_permissions",
    "admin_list_sessions",
    "admin_list_audit_records",
    "admin_list_workflow_history",
    "admin_list_research_archive_metadata",
    "admin_activity_timeline",
    "admin_search",
    "admin_export_audit",
    "admin_health_panel",
    "admin_configuration",
    "admin_versions",
    "admin_feature_flags",
    "admin_system_metrics",
]


def admin_schema() -> dict[str, Any]:
    return get_admin_service().schema()


def admin_dashboard(**kwargs: Any) -> dict[str, Any]:
    return get_admin_service().dashboard(**kwargs)


def admin_list_users() -> list[dict[str, Any]]:
    return get_admin_service().list_users()


def admin_get_user(user_id: str) -> dict[str, Any] | None:
    return get_admin_service().get_user(user_id)


def admin_create_user(**kwargs: Any) -> dict[str, Any]:
    return get_admin_service().create_user(**kwargs)


def admin_set_user_roles(user_id: str, roles: list[str]) -> dict[str, Any]:
    return get_admin_service().set_user_roles(user_id, roles)


def admin_list_roles() -> list[dict[str, Any]]:
    return get_admin_service().list_roles()


def admin_upsert_role(**kwargs: Any) -> dict[str, Any]:
    return get_admin_service().upsert_role(**kwargs)


def admin_list_permissions() -> list[str]:
    return get_admin_service().list_permissions()


def admin_list_sessions(*, user_id: str | None = None) -> list[dict[str, Any]]:
    return get_admin_service().list_sessions(user_id=user_id)


def admin_list_audit_records(**kwargs: Any) -> list[dict[str, Any]]:
    return get_admin_service().list_audit_records(**kwargs)


def admin_list_workflow_history() -> list[dict[str, Any]]:
    return get_admin_service().list_workflow_history()


def admin_list_research_archive_metadata() -> list[dict[str, Any]]:
    return get_admin_service().list_research_archive_metadata()


def admin_activity_timeline(*, limit: int = 100) -> list[dict[str, Any]]:
    return get_admin_service().activity_timeline(limit=limit)


def admin_search(query: str, *, scope: str = "audit") -> dict[str, Any]:
    return get_admin_service().search(query, scope=scope)


def admin_export_audit(**kwargs: Any) -> dict[str, Any]:
    return get_admin_service().export_audit(**kwargs)


def admin_health_panel() -> dict[str, Any]:
    return get_admin_service().health_panel()


def admin_configuration() -> dict[str, Any]:
    return get_admin_service().configuration()


def admin_versions() -> dict[str, Any]:
    return get_admin_service().versions()


def admin_feature_flags(flags: dict[str, bool] | None = None) -> dict[str, Any]:
    return get_admin_service().feature_flags(flags)


def admin_system_metrics() -> dict[str, Any]:
    return get_admin_service().system_metrics()
