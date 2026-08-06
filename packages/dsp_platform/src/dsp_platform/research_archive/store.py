"""Immutable archive store (EPIC-R004)."""

from __future__ import annotations

from threading import RLock
from typing import Protocol

from dsp_platform.research_archive.models import ArchiveSnapshot

__all__ = [
    "ArchiveStore",
    "InMemoryArchiveStore",
    "SnapshotAlreadyExistsError",
    "SnapshotNotFoundError",
]


class SnapshotAlreadyExistsError(ValueError):
    """Refuses mutation of an existing snapshot id."""


class SnapshotNotFoundError(KeyError):
    """Snapshot id not present in archive."""


class ArchiveStore(Protocol):
    def put_if_absent(self, snapshot: ArchiveSnapshot) -> None: ...

    def get(self, snapshot_id: str) -> ArchiveSnapshot | None: ...

    def list_by_lineage(self, lineage_id: str) -> tuple[ArchiveSnapshot, ...]: ...

    def list_ids(self) -> tuple[str, ...]: ...


class InMemoryArchiveStore:
    """Process-local immutable store — overwrite is forbidden."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._by_id: dict[str, ArchiveSnapshot] = {}
        self._by_lineage: dict[str, list[str]] = {}

    def put_if_absent(self, snapshot: ArchiveSnapshot) -> None:
        with self._lock:
            if snapshot.snapshot_id in self._by_id:
                raise SnapshotAlreadyExistsError(
                    f"snapshot already archived: {snapshot.snapshot_id}"
                )
            self._by_id[snapshot.snapshot_id] = snapshot
            lineage = snapshot.version.lineage_id
            self._by_lineage.setdefault(lineage, []).append(snapshot.snapshot_id)

    def get(self, snapshot_id: str) -> ArchiveSnapshot | None:
        with self._lock:
            return self._by_id.get(snapshot_id)

    def list_by_lineage(self, lineage_id: str) -> tuple[ArchiveSnapshot, ...]:
        with self._lock:
            ids = self._by_lineage.get(lineage_id, [])
            snaps = [self._by_id[i] for i in ids if i in self._by_id]
            snaps.sort(key=lambda s: s.version.version_number)
            return tuple(snaps)

    def list_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._by_id.keys()))
