"""Process-local Research Workspace store (notes/folders/bookmarks/tags).

Stores analyst workspace artifacts only — never valuation/scoring engine
payloads. Separate from persistence ENTITY_KINDS (refs/metadata freeze).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock
from typing import Any
from uuid import uuid4

__all__ = [
    "ResearchWorkspaceStore",
    "get_research_workspace_store",
    "reset_research_workspace_store_for_tests",
]

NOTE_STATUSES = (
    "draft",
    "review",
    "approved",
    "published",
    "archived",
)

BOOKMARK_KINDS = (
    "company",
    "report",
    "portfolio",
    "comparison",
    "document",
    "copilot_chat",
    "note",
)

TEMPLATE_IDS = (
    "investment_memo",
    "company_report",
    "quarterly_review",
    "management_review",
    "bull_case",
    "bear_case",
    "base_case",
    "meeting_notes",
    "checklist",
)


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class ResearchWorkspaceStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._notes: dict[str, dict[str, Any]] = {}
        self._folders: dict[str, dict[str, Any]] = {}
        self._bookmarks: dict[str, dict[str, Any]] = {}
        self._tags: dict[str, dict[str, Any]] = {}
        self._comments: dict[str, dict[str, Any]] = {}
        self._shares: dict[str, dict[str, Any]] = {}
        self._versions: dict[str, list[dict[str, Any]]] = {}
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        root_id = "folder-root"
        if root_id not in self._folders:
            self._folders[root_id] = {
                "folder_id": root_id,
                "name": "Research",
                "parent_id": None,
                "archived": False,
                "created_at": _now(),
                "updated_at": _now(),
            }

    # -- folders ---------------------------------------------------------

    def create_folder(
        self,
        *,
        name: str,
        parent_id: str | None = None,
        folder_id: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            fid = folder_id or _id("folder")
            parent = parent_id or "folder-root"
            if parent != "folder-root" and parent not in self._folders:
                raise ValueError(f"parent folder not found: {parent}")
            row = {
                "folder_id": fid,
                "name": name.strip() or "Untitled",
                "parent_id": parent,
                "archived": False,
                "created_at": _now(),
                "updated_at": _now(),
            }
            self._folders[fid] = row
            return deepcopy(row)

    def rename_folder(self, folder_id: str, name: str) -> dict[str, Any]:
        with self._lock:
            row = self._folders.get(folder_id)
            if row is None:
                raise ValueError("folder not found")
            if folder_id == "folder-root":
                raise ValueError("cannot rename root folder")
            row["name"] = name.strip() or row["name"]
            row["updated_at"] = _now()
            return deepcopy(row)

    def move_folder(self, folder_id: str, parent_id: str | None) -> dict[str, Any]:
        with self._lock:
            row = self._folders.get(folder_id)
            if row is None:
                raise ValueError("folder not found")
            if folder_id == "folder-root":
                raise ValueError("cannot move root folder")
            parent = parent_id or "folder-root"
            if parent == folder_id:
                raise ValueError("cannot move folder into itself")
            if parent != "folder-root" and parent not in self._folders:
                raise ValueError("parent folder not found")
            row["parent_id"] = parent
            row["updated_at"] = _now()
            return deepcopy(row)

    def archive_folder(self, folder_id: str, archived: bool = True) -> dict[str, Any]:
        with self._lock:
            row = self._folders.get(folder_id)
            if row is None:
                raise ValueError("folder not found")
            if folder_id == "folder-root":
                raise ValueError("cannot archive root folder")
            row["archived"] = archived
            row["updated_at"] = _now()
            return deepcopy(row)

    def delete_folder(self, folder_id: str) -> bool:
        with self._lock:
            if folder_id == "folder-root":
                raise ValueError("cannot delete root folder")
            if folder_id not in self._folders:
                return False
            # orphan notes → root
            for note in self._notes.values():
                if note.get("folder_id") == folder_id:
                    note["folder_id"] = "folder-root"
                    note["updated_at"] = _now()
            # reparent children
            for folder in self._folders.values():
                if folder.get("parent_id") == folder_id:
                    folder["parent_id"] = "folder-root"
                    folder["updated_at"] = _now()
            del self._folders[folder_id]
            return True

    def list_folders(self) -> list[dict[str, Any]]:
        with self._lock:
            return [deepcopy(f) for f in self._folders.values()]

    # -- notes -----------------------------------------------------------

    def create_note(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            nid = str(payload.get("note_id") or _id("note"))
            folder_id = payload.get("folder_id") or "folder-root"
            if folder_id not in self._folders:
                raise ValueError("folder not found")
            now = _now()
            row = {
                "note_id": nid,
                "title": str(payload.get("title") or "Untitled note").strip(),
                "body": str(payload.get("body") or ""),
                "format": str(payload.get("format") or "markdown"),
                "folder_id": folder_id,
                "status": str(payload.get("status") or "draft"),
                "company": payload.get("company"),
                "portfolio_id": payload.get("portfolio_id"),
                "research_object_id": payload.get("research_object_id"),
                "document_refs": list(payload.get("document_refs") or []),
                "attachments": list(payload.get("attachments") or []),
                "tag_ids": list(payload.get("tag_ids") or []),
                "assignee_id": payload.get("assignee_id"),
                "workflow_id": payload.get("workflow_id"),
                "created_at": now,
                "updated_at": now,
                "version": 1,
                "ai_generated": bool(payload.get("ai_generated")),
                "created_by": payload.get("created_by"),
            }
            if row["status"] not in NOTE_STATUSES:
                row["status"] = "draft"
            self._notes[nid] = row
            self._versions[nid] = [
                {
                    "version": 1,
                    "saved_at": now,
                    "title": row["title"],
                    "body": row["body"],
                    "status": row["status"],
                    "actor_id": payload.get("created_by"),
                }
            ]
            return deepcopy(row)

    def update_note(self, note_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            row = self._notes.get(note_id)
            if row is None:
                raise ValueError("note not found")
            # version snapshot before mutation
            versions = self._versions.setdefault(note_id, [])
            next_version = int(row.get("version") or 1) + 1
            versions.append(
                {
                    "version": next_version,
                    "saved_at": _now(),
                    "title": row["title"],
                    "body": row["body"],
                    "status": row["status"],
                    "actor_id": patch.get("actor_id") or patch.get("created_by"),
                    "snapshot_of": "pre_update",
                }
            )
            for key in (
                "title",
                "body",
                "format",
                "folder_id",
                "status",
                "company",
                "portfolio_id",
                "research_object_id",
                "assignee_id",
                "workflow_id",
            ):
                if key in patch and patch[key] is not None:
                    row[key] = patch[key]
            if "document_refs" in patch and patch["document_refs"] is not None:
                row["document_refs"] = list(patch["document_refs"])
            if "attachments" in patch and patch["attachments"] is not None:
                row["attachments"] = list(patch["attachments"])
            if "tag_ids" in patch and patch["tag_ids"] is not None:
                row["tag_ids"] = list(patch["tag_ids"])
            if row.get("folder_id") not in self._folders:
                raise ValueError("folder not found")
            if row.get("status") not in NOTE_STATUSES:
                raise ValueError("invalid status")
            row["version"] = next_version
            row["updated_at"] = _now()
            # post-update version head
            versions.append(
                {
                    "version": next_version,
                    "saved_at": row["updated_at"],
                    "title": row["title"],
                    "body": row["body"],
                    "status": row["status"],
                    "actor_id": patch.get("actor_id"),
                    "snapshot_of": "current",
                }
            )
            return deepcopy(row)

    def delete_note(self, note_id: str) -> bool:
        with self._lock:
            if note_id not in self._notes:
                return False
            del self._notes[note_id]
            self._versions.pop(note_id, None)
            # drop comments on note
            for cid, comment in list(self._comments.items()):
                if comment.get("note_id") == note_id:
                    del self._comments[cid]
            return True

    def get_note(self, note_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._notes.get(note_id)
            return deepcopy(row) if row else None

    def list_notes(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = [deepcopy(n) for n in self._notes.values()]
            rows.sort(key=lambda r: str(r.get("updated_at") or ""), reverse=True)
            return rows

    def list_versions(self, note_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(self._versions.get(note_id, []))

    def restore_version(self, note_id: str, version: int) -> dict[str, Any]:
        with self._lock:
            row = self._notes.get(note_id)
            if row is None:
                raise ValueError("note not found")
            snap = None
            for item in self._versions.get(note_id, []):
                if int(item.get("version") or 0) == int(version) and item.get(
                    "snapshot_of"
                ) in {None, "current", "pre_update", "restore"}:
                    snap = item
            if snap is None:
                for item in self._versions.get(note_id, []):
                    if int(item.get("version") or 0) == int(version):
                        snap = item
                        break
            if snap is None:
                raise ValueError("version not found")
            return self.update_note(
                note_id,
                {
                    "title": snap.get("title"),
                    "body": snap.get("body"),
                    "status": snap.get("status") or row.get("status"),
                    "actor_id": "restore",
                },
            )

    # -- bookmarks -------------------------------------------------------

    def create_bookmark(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            bid = str(payload.get("bookmark_id") or _id("bookmark"))
            kind = str(payload.get("kind") or "company")
            if kind not in BOOKMARK_KINDS:
                raise ValueError(f"invalid bookmark kind: {kind}")
            row = {
                "bookmark_id": bid,
                "kind": kind,
                "label": str(payload.get("label") or kind).strip(),
                "target_id": payload.get("target_id"),
                "company": payload.get("company"),
                "href": payload.get("href"),
                "meta": dict(payload.get("meta") or {}),
                "created_at": _now(),
            }
            self._bookmarks[bid] = row
            return deepcopy(row)

    def delete_bookmark(self, bookmark_id: str) -> bool:
        with self._lock:
            return self._bookmarks.pop(bookmark_id, None) is not None

    def list_bookmarks(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = [deepcopy(b) for b in self._bookmarks.values()]
            rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
            return rows

    # -- tags ------------------------------------------------------------

    def upsert_tag(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            tid = str(payload.get("tag_id") or _id("tag"))
            row = self._tags.get(tid) or {
                "tag_id": tid,
                "created_at": _now(),
            }
            row.update(
                {
                    "label": str(payload.get("label") or row.get("label") or "tag").strip(),
                    "color": payload.get("color") or row.get("color") or "#64748b",
                    "kind": payload.get("kind") or row.get("kind") or "custom",
                    "updated_at": _now(),
                }
            )
            self._tags[tid] = row
            return deepcopy(row)

    def delete_tag(self, tag_id: str) -> bool:
        with self._lock:
            if tag_id not in self._tags:
                return False
            del self._tags[tag_id]
            for note in self._notes.values():
                tags = list(note.get("tag_ids") or [])
                if tag_id in tags:
                    note["tag_ids"] = [t for t in tags if t != tag_id]
            return True

    def list_tags(self) -> list[dict[str, Any]]:
        with self._lock:
            return [deepcopy(t) for t in self._tags.values()]

    # -- comments / share ------------------------------------------------

    def add_comment(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            note_id = payload.get("note_id")
            if not note_id or note_id not in self._notes:
                raise ValueError("note not found")
            cid = str(payload.get("comment_id") or _id("comment"))
            row = {
                "comment_id": cid,
                "note_id": note_id,
                "author_id": payload.get("author_id") or "anonymous",
                "body": str(payload.get("body") or "").strip(),
                "mentions": list(payload.get("mentions") or []),
                "resolved": False,
                "created_at": _now(),
                "updated_at": _now(),
            }
            if not row["body"]:
                raise ValueError("comment body required")
            self._comments[cid] = row
            return deepcopy(row)

    def resolve_comment(self, comment_id: str, resolved: bool = True) -> dict[str, Any]:
        with self._lock:
            row = self._comments.get(comment_id)
            if row is None:
                raise ValueError("comment not found")
            row["resolved"] = resolved
            row["updated_at"] = _now()
            return deepcopy(row)

    def list_comments(self, note_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = [deepcopy(c) for c in self._comments.values()]
            if note_id:
                rows = [c for c in rows if c.get("note_id") == note_id]
            rows.sort(key=lambda r: str(r.get("created_at") or ""))
            return rows

    def share_note(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            note_id = payload.get("note_id")
            if not note_id or note_id not in self._notes:
                raise ValueError("note not found")
            sid = str(payload.get("share_id") or _id("share"))
            row = {
                "share_id": sid,
                "note_id": note_id,
                "user_ids": list(payload.get("user_ids") or []),
                "permission": payload.get("permission") or "read",
                "created_by": payload.get("created_by"),
                "created_at": _now(),
            }
            self._shares[sid] = row
            return deepcopy(row)

    def list_shares(self, note_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = [deepcopy(s) for s in self._shares.values()]
            if note_id:
                rows = [s for s in rows if s.get("note_id") == note_id]
            return rows

    # -- search ----------------------------------------------------------

    def search(self, query: str) -> dict[str, list[dict[str, Any]]]:
        q = (query or "").strip().lower()
        with self._lock:
            if not q:
                return {
                    "notes": [],
                    "folders": [],
                    "bookmarks": [],
                    "tags": [],
                    "comments": [],
                }

            def match_text(*parts: Any) -> bool:
                blob = " ".join(str(p or "") for p in parts).lower()
                return q in blob

            notes = [
                deepcopy(n)
                for n in self._notes.values()
                if match_text(
                    n.get("title"),
                    n.get("body"),
                    n.get("company"),
                    n.get("portfolio_id"),
                    " ".join(n.get("tag_ids") or []),
                )
            ]
            folders = [
                deepcopy(f)
                for f in self._folders.values()
                if match_text(f.get("name"), f.get("folder_id"))
            ]
            bookmarks = [
                deepcopy(b)
                for b in self._bookmarks.values()
                if match_text(b.get("label"), b.get("kind"), b.get("target_id"), b.get("company"))
            ]
            tags = [
                deepcopy(t)
                for t in self._tags.values()
                if match_text(t.get("label"), t.get("kind"), t.get("tag_id"))
            ]
            comments = [
                deepcopy(c)
                for c in self._comments.values()
                if match_text(c.get("body"), " ".join(c.get("mentions") or []))
            ]
            return {
                "notes": notes[:50],
                "folders": folders[:50],
                "bookmarks": bookmarks[:50],
                "tags": tags[:50],
                "comments": comments[:50],
            }


_STORE: ResearchWorkspaceStore | None = None


def get_research_workspace_store() -> ResearchWorkspaceStore:
    global _STORE
    if _STORE is None:
        _STORE = ResearchWorkspaceStore()
    return _STORE


def reset_research_workspace_store_for_tests(
    store: ResearchWorkspaceStore | None = None,
) -> None:
    global _STORE
    _STORE = store
