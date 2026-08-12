"""Validation helpers (EPIC-A010)."""

from __future__ import annotations

from typing import Any, Mapping

from workspace.exceptions import (
    DuplicateNameError,
    InvalidReferenceError,
    WorkspaceValidationError,
)
from workspace.models import (
    COLLECTION_KINDS,
    MEMBER_ROLES,
    PROJECT_STATUSES,
    WORKSPACE_STATUSES,
)

__all__ = [
    "assert_collection_kind",
    "assert_member_role",
    "assert_non_empty",
    "assert_project_status",
    "assert_unique_name",
    "assert_workspace_status",
    "normalize_companies",
    "normalize_refs",
]


def assert_non_empty(value: str, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise WorkspaceValidationError(f"{field} is required")
    return text


def assert_workspace_status(status: str) -> str:
    s = str(status or "active").strip().lower()
    if s not in WORKSPACE_STATUSES:
        raise WorkspaceValidationError(f"invalid workspace status {status!r}")
    return s


def assert_project_status(status: str) -> str:
    s = str(status or "active").strip().lower()
    if s not in PROJECT_STATUSES:
        raise WorkspaceValidationError(f"invalid project status {status!r}")
    return s


def assert_member_role(role: str) -> str:
    r = str(role or "").strip().lower()
    if r not in MEMBER_ROLES:
        raise WorkspaceValidationError(f"invalid member role {role!r}")
    return r


def assert_collection_kind(kind: str) -> str:
    k = str(kind or "").strip().lower()
    if k not in COLLECTION_KINDS:
        raise WorkspaceValidationError(f"invalid collection kind {kind!r}")
    return k


def assert_unique_name(existing: set[str], name: str, *, entity: str) -> str:
    cleaned = assert_non_empty(name, f"{entity} name")
    key = cleaned.casefold()
    if key in {n.casefold() for n in existing}:
        raise DuplicateNameError(f"duplicate {entity} name {cleaned!r}")
    return cleaned


def normalize_companies(companies: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in companies or []:
        sym = str(raw or "").strip().upper()
        if not sym:
            continue
        if sym in seen:
            raise WorkspaceValidationError(f"duplicate company {sym!r}")
        seen.add(sym)
        out.append(sym)
    return tuple(out)


def normalize_refs(
    refs: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] | None,
) -> tuple[Mapping[str, Any], ...]:
    out: list[Mapping[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in refs or []:
        if not isinstance(row, Mapping):
            raise InvalidReferenceError("artifact ref must be a mapping")
        kind = str(row.get("kind") or row.get("source_kind") or "").strip()
        ref_id = str(row.get("ref_id") or row.get("id") or "").strip()
        if not kind or not ref_id:
            raise InvalidReferenceError(
                "artifact ref requires kind and ref_id (references only)"
            )
        key = (kind, ref_id)
        if key in seen:
            raise InvalidReferenceError(f"duplicate artifact ref {kind}/{ref_id}")
        seen.add(key)
        out.append({"kind": kind, "ref_id": ref_id, "label": row.get("label")})
    out.sort(key=lambda r: (str(r["kind"]), str(r["ref_id"])))
    return tuple(out)
