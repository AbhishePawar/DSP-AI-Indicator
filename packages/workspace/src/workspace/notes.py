"""Analyst notes (EPIC-A010) — never modify research artifacts."""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from workspace.models import Note, NoteVersion, freeze_mapping, utc_now
from workspace.validation import assert_non_empty

__all__ = ["build_note", "revise_note"]


def build_note(
    *,
    workspace_id: str,
    title: str,
    author_id: str,
    body_markdown: str = "",
    project_id: str | None = None,
    attachment_refs: list[str] | None = None,
    note_id: str | None = None,
    version_id: str | None = None,
    created_at: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> Note:
    created = created_at or utc_now().isoformat()
    author = assert_non_empty(author_id, "author_id")
    body = str(body_markdown or "")
    version = NoteVersion(
        version_id=version_id or str(uuid.uuid4()),
        body_markdown=body,
        author_id=author,
        created_at=created,
    )
    refs = tuple(
        sorted({str(r).strip() for r in (attachment_refs or []) if str(r).strip()})
    )
    return Note(
        note_id=note_id or str(uuid.uuid4()),
        workspace_id=assert_non_empty(workspace_id, "workspace_id"),
        project_id=project_id,
        title=assert_non_empty(title, "note title"),
        author_id=author,
        created_at=created,
        updated_at=created,
        status="active",
        current_body=body,
        versions=(version,),
        attachment_refs=refs,
        metadata=freeze_mapping(dict(metadata or {})),
    )


def revise_note(
    note: Note,
    *,
    body_markdown: str,
    author_id: str,
    version_id: str | None = None,
    created_at: str | None = None,
    title: str | None = None,
) -> Note:
    created = created_at or utc_now().isoformat()
    author = assert_non_empty(author_id, "author_id")
    version = NoteVersion(
        version_id=version_id or str(uuid.uuid4()),
        body_markdown=str(body_markdown or ""),
        author_id=author,
        created_at=created,
    )
    versions = tuple(
        sorted((*note.versions, version), key=lambda v: (v.created_at, v.version_id))
    )
    return Note(
        note_id=note.note_id,
        workspace_id=note.workspace_id,
        project_id=note.project_id,
        title=title or note.title,
        author_id=note.author_id,
        created_at=note.created_at,
        updated_at=created,
        status=note.status,
        current_body=version.body_markdown,
        versions=versions,
        attachment_refs=note.attachment_refs,
        tag_ids=note.tag_ids,
        metadata=note.metadata,
    )
