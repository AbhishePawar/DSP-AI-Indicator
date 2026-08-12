"""Snapshot loader for diff engine (EPIC-R005) — read-only R004 access."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_archive import get_research_archive
from dsp_platform.research_archive.hashing import to_plain_jsonable
from dsp_platform.research_archive.serde import archive_snapshot_from_dict
from dsp_platform.research_archive.store import SnapshotNotFoundError

__all__ = [
    "LoadedSnapshot",
    "load_snapshot",
]


class LoadedSnapshot:
    """Read-only view of an archive snapshot for diffing."""

    __slots__ = (
        "snapshot_id",
        "kind",
        "archived_at",
        "content_sha256",
        "content_schema_version",
        "archive_schema_version",
        "version",
        "ticker",
        "payload",
        "raw",
    )

    def __init__(self, raw: Mapping[str, Any]) -> None:
        plain = to_plain_jsonable(raw)
        if not isinstance(plain, dict):
            raise TypeError("snapshot must be a mapping")
        # Re-validate structure without mutating archive
        archive_snapshot_from_dict(plain)
        self.raw = plain
        self.snapshot_id = str(plain["snapshot_id"])
        self.kind = str(plain["kind"])
        self.archived_at = str(plain["archived_at"])
        self.content_sha256 = str(plain["content_sha256"])
        self.content_schema_version = str(plain["content_schema_version"])
        self.archive_schema_version = str(plain["archive_schema_version"])
        self.version = dict(plain.get("version") or {})
        self.ticker = plain.get("ticker")
        payload = plain.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("snapshot payload missing")
        self.payload = payload


def load_snapshot(
    snapshot: str | Mapping[str, Any],
) -> LoadedSnapshot:
    """Load by archive id or accept an already-fetched snapshot dict."""
    if isinstance(snapshot, str):
        try:
            raw = get_research_archive().get_dict(snapshot)
        except SnapshotNotFoundError as exc:
            raise SnapshotNotFoundError(snapshot) from exc
        return LoadedSnapshot(raw)
    if isinstance(snapshot, Mapping):
        return LoadedSnapshot(snapshot)
    raise TypeError("snapshot must be an id string or mapping")
