"""Research Workspace domain models (EPIC-A010).

Stores metadata and references only — never duplicates research artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Mapping

__all__ = [
    "COLLECTION_KINDS",
    "MEMBER_ROLES",
    "NOTE_STATUSES",
    "PROJECT_STATUSES",
    "UNAVAILABLE_MESSAGE",
    "WORKSPACE_SCHEMA_VERSION",
    "WORKSPACE_SERVICE_VERSION",
    "WORKSPACE_STATUSES",
    "Member",
    "Note",
    "NoteVersion",
    "Project",
    "ResearchCollection",
    "Tag",
    "Watchlist",
    "Workspace",
    "freeze_mapping",
    "utc_now",
]

WORKSPACE_SCHEMA_VERSION = "1.0.0"
WORKSPACE_SERVICE_VERSION = "1.0.0"
UNAVAILABLE_MESSAGE = "Data unavailable."

WORKSPACE_STATUSES = ("active", "archived", "unavailable")
PROJECT_STATUSES = ("active", "paused", "completed", "archived")
MEMBER_ROLES = ("owner", "administrator", "analyst", "reviewer", "read_only")
COLLECTION_KINDS = (
    "research_report",
    "financial_statement",
    "valuation_result",
    "committee_decision",
    "workflow_record",
    "research_object",
    "archive_snapshot",
    "research_diff",
    "compliance_result",
    "custom",
)
NOTE_STATUSES = ("active", "archived")


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})

    def _freeze(obj: Any) -> Any:
        if isinstance(obj, Mapping):
            return MappingProxyType({str(k): _freeze(v) for k, v in obj.items()})
        if isinstance(obj, list):
            return tuple(_freeze(v) for v in obj)
        if isinstance(obj, tuple):
            return tuple(_freeze(v) for v in obj)
        return obj

    return _freeze(value)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class Member:
    user_id: str
    role: str
    display_name: str | None = None
    added_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "role": self.role,
            "display_name": self.display_name,
            "added_at": self.added_at,
        }


@dataclass(frozen=True, slots=True)
class Tag:
    tag_id: str
    name: str
    scope: str  # global | workspace | project
    workspace_id: str | None = None
    project_id: str | None = None
    colour: str | None = None
    label: str | None = None
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tag_id": self.tag_id,
            "name": self.name,
            "scope": self.scope,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "colour": self.colour,
            "label": self.label,
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class NoteVersion:
    version_id: str
    body_markdown: str
    author_id: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "body_markdown": self.body_markdown,
            "author_id": self.author_id,
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class Note:
    note_id: str
    workspace_id: str
    project_id: str | None
    title: str
    author_id: str
    created_at: str
    updated_at: str
    status: str = "active"
    current_body: str = ""
    versions: tuple[NoteVersion, ...] = ()
    attachment_refs: tuple[str, ...] = ()
    tag_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "note_id": self.note_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "title": self.title,
            "author_id": self.author_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "current_body": self.current_body,
            "versions": [v.to_dict() for v in self.versions],
            "attachment_refs": list(self.attachment_refs),
            "tag_ids": list(self.tag_ids),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class Watchlist:
    watchlist_id: str
    workspace_id: str
    name: str
    created_at: str
    updated_at: str
    kind: str = "custom"  # named | sector | custom
    companies: tuple[str, ...] = ()
    sector: str | None = None
    notes: str | None = None
    order: tuple[str, ...] = ()
    tag_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "watchlist_id": self.watchlist_id,
            "workspace_id": self.workspace_id,
            "name": self.name,
            "kind": self.kind,
            "companies": list(self.companies),
            "sector": self.sector,
            "notes": self.notes,
            "order": list(self.order),
            "tag_ids": list(self.tag_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ResearchCollection:
    collection_id: str
    workspace_id: str
    name: str
    kind: str
    created_at: str
    updated_at: str
    project_id: str | None = None
    # References only — never artifact payloads
    artifact_refs: tuple[Mapping[str, Any], ...] = ()
    tag_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "collection_id": self.collection_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "name": self.name,
            "kind": self.kind,
            "artifact_refs": [dict(r) for r in self.artifact_refs],
            "tag_ids": list(self.tag_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class Project:
    project_id: str
    workspace_id: str
    name: str
    owner_id: str
    created_at: str
    updated_at: str
    description: str | None = None
    sector: str | None = None
    industry: str | None = None
    coverage_universe: tuple[str, ...] = ()
    priority: str = "normal"
    status: str = "active"
    assigned_analysts: tuple[str, ...] = ()
    tag_ids: tuple[str, ...] = ()
    collection_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "workspace_id": self.workspace_id,
            "name": self.name,
            "description": self.description,
            "sector": self.sector,
            "industry": self.industry,
            "coverage_universe": list(self.coverage_universe),
            "priority": self.priority,
            "status": self.status,
            "owner_id": self.owner_id,
            "assigned_analysts": list(self.assigned_analysts),
            "tag_ids": list(self.tag_ids),
            "collection_ids": list(self.collection_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class Workspace:
    workspace_id: str
    name: str
    owner_id: str
    created_at: str
    updated_at: str
    description: str | None = None
    status: str = "active"
    members: tuple[Member, ...] = ()
    project_ids: tuple[str, ...] = ()
    watchlist_ids: tuple[str, ...] = ()
    collection_ids: tuple[str, ...] = ()
    note_ids: tuple[str, ...] = ()
    tag_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "status": self.status,
            "members": [m.to_dict() for m in self.members],
            "project_ids": list(self.project_ids),
            "watchlist_ids": list(self.watchlist_ids),
            "collection_ids": list(self.collection_ids),
            "note_ids": list(self.note_ids),
            "tag_ids": list(self.tag_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }
