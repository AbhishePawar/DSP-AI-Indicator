"""Project helpers (EPIC-A010)."""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from workspace.models import Project, freeze_mapping, utc_now
from workspace.validation import (
    assert_non_empty,
    assert_project_status,
    assert_unique_name,
    normalize_companies,
)

__all__ = ["build_project"]


def build_project(
    *,
    workspace_id: str,
    name: str,
    owner_id: str,
    description: str | None = None,
    sector: str | None = None,
    industry: str | None = None,
    coverage_universe: list[str] | None = None,
    priority: str = "normal",
    status: str = "active",
    assigned_analysts: list[str] | None = None,
    project_id: str | None = None,
    created_at: str | None = None,
    existing_names: set[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> Project:
    cleaned = assert_unique_name(existing_names or set(), name, entity="project")
    created = created_at or utc_now().isoformat()
    analysts = tuple(
        sorted({str(a).strip() for a in (assigned_analysts or []) if str(a).strip()})
    )
    return Project(
        project_id=project_id or str(uuid.uuid4()),
        workspace_id=assert_non_empty(workspace_id, "workspace_id"),
        name=cleaned,
        description=description,
        sector=sector,
        industry=industry,
        coverage_universe=normalize_companies(coverage_universe),
        priority=str(priority or "normal"),
        status=assert_project_status(status),
        owner_id=assert_non_empty(owner_id, "owner_id"),
        assigned_analysts=analysts,
        created_at=created,
        updated_at=created,
        metadata=freeze_mapping(dict(metadata or {})),
    )
