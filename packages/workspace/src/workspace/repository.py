"""Persistence repository (EPIC-A010).

A008-compatible WorkspaceStorePort with in-memory default.
Does not mutate research artifacts.
"""

from __future__ import annotations

from threading import RLock
from typing import Protocol

from workspace.models import (
    Note,
    Project,
    ResearchCollection,
    Tag,
    Watchlist,
    Workspace,
)

__all__ = [
    "InMemoryWorkspaceStore",
    "WorkspaceStorePort",
    "get_workspace_store",
    "reset_workspace_store_for_tests",
]


class WorkspaceStorePort(Protocol):
    """Persistence port — EPIC-A008 adapters should implement this."""

    def put_workspace(self, workspace: Workspace) -> None: ...
    def get_workspace(self, workspace_id: str) -> Workspace | None: ...
    def list_workspaces(self) -> tuple[Workspace, ...]: ...
    def delete_workspace(self, workspace_id: str) -> None: ...

    def put_project(self, project: Project) -> None: ...
    def get_project(self, project_id: str) -> Project | None: ...
    def list_projects(self, workspace_id: str | None = None) -> tuple[Project, ...]: ...
    def delete_project(self, project_id: str) -> None: ...

    def put_collection(self, collection: ResearchCollection) -> None: ...
    def get_collection(self, collection_id: str) -> ResearchCollection | None: ...
    def list_collections(
        self, workspace_id: str | None = None
    ) -> tuple[ResearchCollection, ...]: ...
    def delete_collection(self, collection_id: str) -> None: ...

    def put_watchlist(self, watchlist: Watchlist) -> None: ...
    def get_watchlist(self, watchlist_id: str) -> Watchlist | None: ...
    def list_watchlists(
        self, workspace_id: str | None = None
    ) -> tuple[Watchlist, ...]: ...
    def delete_watchlist(self, watchlist_id: str) -> None: ...

    def put_note(self, note: Note) -> None: ...
    def get_note(self, note_id: str) -> Note | None: ...
    def list_notes(self, workspace_id: str | None = None) -> tuple[Note, ...]: ...
    def delete_note(self, note_id: str) -> None: ...

    def put_tag(self, tag: Tag) -> None: ...
    def get_tag(self, tag_id: str) -> Tag | None: ...
    def list_tags(self, workspace_id: str | None = None) -> tuple[Tag, ...]: ...
    def delete_tag(self, tag_id: str) -> None: ...


class InMemoryWorkspaceStore:
    """Process-local A008 stand-in until durable persistence is wired."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._workspaces: dict[str, Workspace] = {}
        self._projects: dict[str, Project] = {}
        self._collections: dict[str, ResearchCollection] = {}
        self._watchlists: dict[str, Watchlist] = {}
        self._notes: dict[str, Note] = {}
        self._tags: dict[str, Tag] = {}

    def put_workspace(self, workspace: Workspace) -> None:
        with self._lock:
            self._workspaces[workspace.workspace_id] = workspace

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        with self._lock:
            return self._workspaces.get(workspace_id)

    def list_workspaces(self) -> tuple[Workspace, ...]:
        with self._lock:
            return tuple(
                self._workspaces[k] for k in sorted(self._workspaces.keys())
            )

    def delete_workspace(self, workspace_id: str) -> None:
        with self._lock:
            self._workspaces.pop(workspace_id, None)

    def put_project(self, project: Project) -> None:
        with self._lock:
            self._projects[project.project_id] = project

    def get_project(self, project_id: str) -> Project | None:
        with self._lock:
            return self._projects.get(project_id)

    def list_projects(self, workspace_id: str | None = None) -> tuple[Project, ...]:
        with self._lock:
            rows = list(self._projects.values())
            if workspace_id:
                rows = [p for p in rows if p.workspace_id == workspace_id]
            rows.sort(key=lambda p: p.project_id)
            return tuple(rows)

    def delete_project(self, project_id: str) -> None:
        with self._lock:
            self._projects.pop(project_id, None)

    def put_collection(self, collection: ResearchCollection) -> None:
        with self._lock:
            self._collections[collection.collection_id] = collection

    def get_collection(self, collection_id: str) -> ResearchCollection | None:
        with self._lock:
            return self._collections.get(collection_id)

    def list_collections(
        self, workspace_id: str | None = None
    ) -> tuple[ResearchCollection, ...]:
        with self._lock:
            rows = list(self._collections.values())
            if workspace_id:
                rows = [c for c in rows if c.workspace_id == workspace_id]
            rows.sort(key=lambda c: c.collection_id)
            return tuple(rows)

    def delete_collection(self, collection_id: str) -> None:
        with self._lock:
            self._collections.pop(collection_id, None)

    def put_watchlist(self, watchlist: Watchlist) -> None:
        with self._lock:
            self._watchlists[watchlist.watchlist_id] = watchlist

    def get_watchlist(self, watchlist_id: str) -> Watchlist | None:
        with self._lock:
            return self._watchlists.get(watchlist_id)

    def list_watchlists(
        self, workspace_id: str | None = None
    ) -> tuple[Watchlist, ...]:
        with self._lock:
            rows = list(self._watchlists.values())
            if workspace_id:
                rows = [w for w in rows if w.workspace_id == workspace_id]
            rows.sort(key=lambda w: w.watchlist_id)
            return tuple(rows)

    def delete_watchlist(self, watchlist_id: str) -> None:
        with self._lock:
            self._watchlists.pop(watchlist_id, None)

    def put_note(self, note: Note) -> None:
        with self._lock:
            self._notes[note.note_id] = note

    def get_note(self, note_id: str) -> Note | None:
        with self._lock:
            return self._notes.get(note_id)

    def list_notes(self, workspace_id: str | None = None) -> tuple[Note, ...]:
        with self._lock:
            rows = list(self._notes.values())
            if workspace_id:
                rows = [n for n in rows if n.workspace_id == workspace_id]
            rows.sort(key=lambda n: n.note_id)
            return tuple(rows)

    def delete_note(self, note_id: str) -> None:
        with self._lock:
            self._notes.pop(note_id, None)

    def put_tag(self, tag: Tag) -> None:
        with self._lock:
            self._tags[tag.tag_id] = tag

    def get_tag(self, tag_id: str) -> Tag | None:
        with self._lock:
            return self._tags.get(tag_id)

    def list_tags(self, workspace_id: str | None = None) -> tuple[Tag, ...]:
        with self._lock:
            rows = list(self._tags.values())
            if workspace_id:
                rows = [
                    t
                    for t in rows
                    if t.scope == "global"
                    or t.workspace_id == workspace_id
                    or (t.workspace_id is None and t.scope == "global")
                ]
            rows.sort(key=lambda t: t.tag_id)
            return tuple(rows)

    def delete_tag(self, tag_id: str) -> None:
        with self._lock:
            self._tags.pop(tag_id, None)


_STORE: InMemoryWorkspaceStore | None = None


def get_workspace_store() -> InMemoryWorkspaceStore:
    global _STORE
    if _STORE is None:
        _STORE = InMemoryWorkspaceStore()
    return _STORE


def reset_workspace_store_for_tests(
    store: InMemoryWorkspaceStore | None = None,
) -> None:
    global _STORE
    _STORE = store
