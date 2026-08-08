"""Enterprise Administration & Audit Console service (EPIC-A010)."""

from __future__ import annotations

from typing import Any

from admin.audit import (
    AuditViewer,
    export_audit_metadata,
    filter_records,
    search_records,
)
from admin.identity_admin import IdentityAdmin
from admin.models import (
    ADMIN_SCHEMA_VERSION,
    ADMIN_SERVICE_VERSION,
    AdminDashboard,
    freeze_mapping,
    utc_now,
)
from admin.viewers import (
    ConfigViewer,
    FeatureFlagViewer,
    HealthPanel,
    MetricsViewer,
    VersionViewer,
)

__all__ = [
    "AdminService",
    "get_admin_service",
    "reset_admin_service_for_tests",
]


class AdminService:
    """Read-only operational console — consumes A008/A009 artifacts only."""

    def __init__(self, persistence_service: Any, auth_service: Any) -> None:
        self.persistence = persistence_service
        self.auth = auth_service
        self.identity = IdentityAdmin(auth_service)
        self.audit = AuditViewer(persistence_service)
        self.health = HealthPanel(persistence_service, auth_service)
        self.config = ConfigViewer()
        self._version_viewer = VersionViewer()
        self._flag_viewer = FeatureFlagViewer()
        self.metrics = MetricsViewer(persistence_service, auth_service)

    def schema(self) -> dict[str, Any]:
        return {
            "schema_version": ADMIN_SCHEMA_VERSION,
            "service_version": ADMIN_SERVICE_VERSION,
            "capabilities": [
                "admin_dashboard",
                "user_management",
                "role_management",
                "permission_viewer",
                "session_viewer",
                "audit_log_viewer",
                "platform_health_panel",
                "configuration_viewer",
                "version_viewer",
                "feature_flag_viewer",
                "system_metrics",
                "activity_timeline",
                "search_and_filters",
                "export_audit_metadata",
            ],
            "rules": [
                "consume_existing_artifacts_only",
                "never_execute_engines",
                "never_call_providers",
                "never_modify_research",
                "never_modify_reports",
                "never_modify_archive",
                "no_calculations_valuation_scoring_recommendations",
                "preserve_provenance_and_timestamps",
                "deterministic",
                "thin_architecture",
                "read_only_api",
            ],
        }

    def dashboard(self, *, generated_at: str | None = None) -> dict[str, Any]:
        health = self.health.snapshot()
        metrics = self.metrics.snapshot()
        dash = AdminDashboard(
            generated_at=generated_at or utc_now().isoformat(),
            users_count=int(metrics["users"]),
            sessions_count=int(metrics["sessions_total"]),
            active_sessions_count=int(metrics["sessions_active"]),
            audit_records_count=int(metrics["audit_records"]),
            workflow_records_count=int(metrics["workflow_records"]),
            research_refs_count=int(metrics["research_refs"]),
            roles_count=len(self.identity.list_roles()),
            permissions_count=len(self.identity.list_permissions()),
            health_status=str(health.get("status") or "unknown"),
            metadata=freeze_mapping(
                {
                    "source": "admin",
                    "research_mutated": False,
                    "engines_executed": False,
                }
            ),
        )
        return dash.to_dict()

    # --- identity admin (delegates to A009; no research mutation) ---

    def list_users(self) -> list[dict[str, Any]]:
        return self.identity.list_users()

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self.identity.get_user(user_id)

    def create_user(self, **kwargs: Any) -> dict[str, Any]:
        return self.identity.create_user(**kwargs)

    def set_user_roles(self, user_id: str, roles: list[str]) -> dict[str, Any]:
        return self.identity.set_user_roles(user_id, roles)

    def list_roles(self) -> list[dict[str, Any]]:
        return self.identity.list_roles()

    def upsert_role(self, **kwargs: Any) -> dict[str, Any]:
        return self.identity.upsert_role(**kwargs)

    def list_permissions(self) -> list[str]:
        return self.identity.list_permissions()

    def list_sessions(self, *, user_id: str | None = None) -> list[dict[str, Any]]:
        return self.identity.list_sessions(user_id=user_id)

    # --- audit / archive metadata ---

    def list_audit_records(
        self,
        *,
        query: str | None = None,
        subject: str | None = None,
        workflow_id: str | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = self.audit.list_audit_records()
        return filter_records(
            rows,
            query=query,
            subject=subject,
            workflow_id=workflow_id,
            event_type=event_type,
        )

    def list_workflow_history(self) -> list[dict[str, Any]]:
        return self.audit.list_workflow_history()

    def list_research_archive_metadata(self) -> list[dict[str, Any]]:
        return self.audit.list_research_archive_metadata()

    def activity_timeline(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return self.audit.activity_timeline(limit=limit)

    def search(self, query: str, *, scope: str = "audit") -> dict[str, Any]:
        scope_l = str(scope or "audit").strip().lower()
        if scope_l == "audit":
            records = search_records(self.audit.list_audit_records(), query)
        elif scope_l == "workflow":
            records = search_records(self.audit.list_workflow_history(), query)
        elif scope_l == "users":
            records = search_records(self.identity.list_users(), query)
        elif scope_l == "sessions":
            records = search_records(self.identity.list_sessions(), query)
        else:
            from admin.exceptions import ValidationError

            raise ValidationError(f"unknown search scope {scope!r}")
        return {"scope": scope_l, "query": query, "count": len(records), "results": records}

    def export_audit(self, **filters: Any) -> dict[str, Any]:
        rows = self.list_audit_records(**filters)
        return export_audit_metadata(rows)

    # --- panels ---

    def health_panel(self) -> dict[str, Any]:
        return self.health.snapshot()

    def configuration(self) -> dict[str, Any]:
        return self.config.snapshot()

    def versions(self) -> dict[str, Any]:
        return self._version_viewer.snapshot()

    def feature_flags(self, flags: dict[str, bool] | None = None) -> dict[str, Any]:
        return self._flag_viewer.snapshot(flags)

    def system_metrics(self) -> dict[str, Any]:
        return self.metrics.snapshot()


_SVC: AdminService | None = None


def get_admin_service(
    persistence_service: Any | None = None,
    auth_service: Any | None = None,
) -> AdminService:
    global _SVC
    if _SVC is None:
        if persistence_service is None:
            from persistence import get_persistence_service

            persistence_service = get_persistence_service()
        if auth_service is None:
            from auth import get_auth_service

            auth_service = get_auth_service(persistence_service)
        _SVC = AdminService(persistence_service, auth_service)
    return _SVC


def reset_admin_service_for_tests(service: AdminService | None = None) -> None:
    global _SVC
    _SVC = service
