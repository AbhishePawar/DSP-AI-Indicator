"""Serialization helpers (EPIC-A010)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from admin.models import AdminDashboard

__all__ = ["dashboard_to_dict"]


def dashboard_to_dict(dashboard: AdminDashboard | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(dashboard, AdminDashboard):
        return dashboard.to_dict()
    return dict(dashboard)
