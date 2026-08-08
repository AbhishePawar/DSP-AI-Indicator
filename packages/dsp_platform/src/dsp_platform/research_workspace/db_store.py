"""DatabasePort-backed Research Workspace store (P0-06)."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from typing import Any

from dsp_platform.durable_snapshot import (
    ensure_snapshot_table,
    load_snapshot,
    save_snapshot,
)
from dsp_platform.research_workspace.store import ResearchWorkspaceStore

__all__ = [
    "WORKSPACE_SNAPSHOT_TABLE",
    "WORKSPACE_SNAPSHOT_KEY",
    "DatabaseResearchWorkspaceStore",
    "build_research_workspace_store",
]

WORKSPACE_SNAPSHOT_TABLE = "research_workspace_snapshots"
WORKSPACE_SNAPSHOT_KEY = "research_workspace_v1"

_META = frozenset(
    {
        "ensure_schema",
        "ensure_fresh",
        "hydrate",
        "flush",
        "export_state",
        "import_state",
        "_seed_defaults",
    }
)


class DatabaseResearchWorkspaceStore(ResearchWorkspaceStore):
    """Workspace store hydrated from / flushed to a shared DatabasePort."""

    def __init__(self, database: Any) -> None:
        super().__init__()
        self._db = database
        self._persist_lock = Lock()
        self.ensure_schema()
        self.hydrate()

    def ensure_schema(self) -> None:
        ensure_snapshot_table(self._db, WORKSPACE_SNAPSHOT_TABLE)

    def ensure_fresh(self) -> None:
        with self._persist_lock:
            self.hydrate()

    def export_state(self) -> dict[str, Any]:
        return {
            "notes": dict(self._notes),
            "folders": dict(self._folders),
            "bookmarks": dict(self._bookmarks),
            "tags": dict(self._tags),
            "comments": dict(self._comments),
            "shares": dict(self._shares),
            "versions": {k: list(v) for k, v in self._versions.items()},
        }

    def import_state(self, payload: dict[str, Any]) -> None:
        self._notes = {str(k): dict(v) for k, v in (payload.get("notes") or {}).items()}
        self._folders = {
            str(k): dict(v) for k, v in (payload.get("folders") or {}).items()
        }
        self._bookmarks = {
            str(k): dict(v) for k, v in (payload.get("bookmarks") or {}).items()
        }
        self._tags = {str(k): dict(v) for k, v in (payload.get("tags") or {}).items()}
        self._comments = {
            str(k): dict(v) for k, v in (payload.get("comments") or {}).items()
        }
        self._shares = {
            str(k): dict(v) for k, v in (payload.get("shares") or {}).items()
        }
        self._versions = {
            str(k): [dict(item) for item in (v or [])]
            for k, v in (payload.get("versions") or {}).items()
        }
        self._seed_defaults()

    def hydrate(self) -> None:
        payload = load_snapshot(
            self._db,
            table=WORKSPACE_SNAPSHOT_TABLE,
            snapshot_key=WORKSPACE_SNAPSHOT_KEY,
        )
        if not payload:
            self._seed_defaults()
            return
        self.import_state(payload)

    def flush(self) -> None:
        with self._persist_lock:
            save_snapshot(
                self._db,
                table=WORKSPACE_SNAPSHOT_TABLE,
                snapshot_key=WORKSPACE_SNAPSHOT_KEY,
                payload=self.export_state(),
                updated_at=datetime.now(tz=UTC).isoformat(),
            )

    def __getattribute__(self, name: str) -> Any:
        if name.startswith("_") or name in _META:
            return object.__getattribute__(self, name)
        attr = object.__getattribute__(self, name)
        if not callable(attr):
            return attr

        def bound(*args: Any, **kwargs: Any) -> Any:
            object.__getattribute__(self, "ensure_fresh")()
            result = attr(*args, **kwargs)
            object.__getattribute__(self, "flush")()
            return result

        return bound


def build_research_workspace_store(
    database: Any | None = None,
) -> ResearchWorkspaceStore:
    if database is None:
        return ResearchWorkspaceStore()
    return DatabaseResearchWorkspaceStore(database)
