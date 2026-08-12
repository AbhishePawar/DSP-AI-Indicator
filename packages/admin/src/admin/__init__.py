"""Enterprise Administration & Audit Console (EPIC-A010)."""

from __future__ import annotations

from admin.audit import (
    AuditViewer,
    export_audit_metadata,
    filter_records,
    search_records,
)
from admin.exceptions import AdminError, NotFoundError, ValidationError
from admin.identity_admin import IdentityAdmin
from admin.models import (
    ADMIN_SCHEMA_VERSION,
    ADMIN_SERVICE_VERSION,
    UNAVAILABLE_MESSAGE,
    AdminDashboard,
)
from admin.serde import dashboard_to_dict
from admin.service import AdminService, get_admin_service, reset_admin_service_for_tests
from admin.viewers import (
    ConfigViewer,
    FeatureFlagViewer,
    HealthPanel,
    MetricsViewer,
    VersionViewer,
)
from admin.beta_programme import (
    BetaProgrammeStore,
    get_beta_programme,
    reset_beta_programme_for_tests,
)

__all__ = [
    "ADMIN_SCHEMA_VERSION",
    "ADMIN_SERVICE_VERSION",
    "UNAVAILABLE_MESSAGE",
    "AdminDashboard",
    "AdminError",
    "AdminService",
    "AuditViewer",
    "BetaProgrammeStore",
    "ConfigViewer",
    "FeatureFlagViewer",
    "HealthPanel",
    "IdentityAdmin",
    "MetricsViewer",
    "NotFoundError",
    "ValidationError",
    "VersionViewer",
    "dashboard_to_dict",
    "export_audit_metadata",
    "filter_records",
    "get_admin_service",
    "get_beta_programme",
    "reset_admin_service_for_tests",
    "reset_beta_programme_for_tests",
    "search_records",
]

__version__ = "0.1.0"
