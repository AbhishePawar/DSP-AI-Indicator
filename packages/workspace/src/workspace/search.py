"""Deterministic search across workspace entities (EPIC-A010)."""

from __future__ import annotations

from typing import Any

from workspace.models import (
    Note,
    Project,
    ResearchCollection,
    Tag,
    Watchlist,
    Workspace,
)

__all__ = ["search_workspace_entities"]


def _match(text: str, query: str) -> bool:
    return query.casefold() in text.casefold()


def search_workspace_entities(
    *,
    query: str,
    workspaces: tuple[Workspace, ...] = (),
    projects: tuple[Project, ...] = (),
    notes: tuple[Note, ...] = (),
    tags: tuple[Tag, ...] = (),
    collections: tuple[ResearchCollection, ...] = (),
    watchlists: tuple[Watchlist, ...] = (),
) -> dict[str, list[dict[str, Any]]]:
    q = str(query or "").strip()
    if not q:
        return {
            "workspaces": [],
            "projects": [],
            "notes": [],
            "tags": [],
            "collections": [],
            "watchlists": [],
        }

    ws_hits = [
        {"workspace_id": w.workspace_id, "name": w.name, "status": w.status}
        for w in workspaces
        if _match(w.name, q) or _match(w.description or "", q)
    ]
    proj_hits = [
        {
            "project_id": p.project_id,
            "workspace_id": p.workspace_id,
            "name": p.name,
            "status": p.status,
        }
        for p in projects
        if _match(p.name, q)
        or _match(p.description or "", q)
        or _match(p.sector or "", q)
        or any(_match(c, q) for c in p.coverage_universe)
    ]
    note_hits = [
        {
            "note_id": n.note_id,
            "workspace_id": n.workspace_id,
            "title": n.title,
        }
        for n in notes
        if _match(n.title, q) or _match(n.current_body, q)
    ]
    tag_hits = [
        {"tag_id": t.tag_id, "name": t.name, "scope": t.scope}
        for t in tags
        if _match(t.name, q) or _match(t.label or "", q)
    ]
    coll_hits = [
        {
            "collection_id": c.collection_id,
            "workspace_id": c.workspace_id,
            "name": c.name,
            "kind": c.kind,
        }
        for c in collections
        if _match(c.name, q) or _match(c.kind, q)
    ]
    wl_hits = [
        {
            "watchlist_id": w.watchlist_id,
            "workspace_id": w.workspace_id,
            "name": w.name,
        }
        for w in watchlists
        if _match(w.name, q)
        or _match(w.sector or "", q)
        or any(_match(c, q) for c in w.companies)
    ]

    def _sort(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        return sorted(rows, key=lambda r: str(r.get(key) or ""))

    return {
        "workspaces": _sort(ws_hits, "workspace_id"),
        "projects": _sort(proj_hits, "project_id"),
        "notes": _sort(note_hits, "note_id"),
        "tags": _sort(tag_hits, "tag_id"),
        "collections": _sort(coll_hits, "collection_id"),
        "watchlists": _sort(wl_hits, "watchlist_id"),
    }
