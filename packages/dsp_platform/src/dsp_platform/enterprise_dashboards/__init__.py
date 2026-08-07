"""RC1 Milestone 6 — Enterprise role dashboards (aggregation only)."""

from __future__ import annotations

from dsp_platform.enterprise_dashboards.service import (
    UNAVAILABLE_MESSAGE,
    DASHBOARD_ROLES,
    enterprise_dashboard_schema,
    get_enterprise_dashboard,
)

__all__ = [
    "UNAVAILABLE_MESSAGE",
    "DASHBOARD_ROLES",
    "enterprise_dashboard_schema",
    "get_enterprise_dashboard",
]
