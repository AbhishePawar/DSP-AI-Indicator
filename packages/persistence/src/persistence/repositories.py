"""Typed repositories (EPIC-A008)."""

from __future__ import annotations

from typing import Any, Mapping

from persistence.exceptions import DuplicateIdError, NotFoundError, SnapshotError
from persistence.interfaces import StorageProviderPort
from persistence.models import PersistedEntity, PersistenceSnapshot
from persistence.serde import entity_from_dict, entity_to_dict, snapshot_from_dict, snapshot_to_dict
from persistence.validation import validate_entity, validate_snapshot

__all__ = [
    "EntityRepository",
    "SnapshotRepository",
    "kind_collection",
]


def kind_collection(kind: str) -> str:
    return f"entities:{kind}"


class EntityRepository:
    """CRUD repository for a single entity kind (references/metadata only)."""

    def __init__(self, storage: StorageProviderPort, kind: str) -> None:
        self._storage = storage
        self.kind = kind
        self.collection = kind_collection(kind)

    def put(self, entity: PersistedEntity, *, allow_update: bool = True) -> PersistedEntity:
        validate_entity(entity)
        if entity.kind != self.kind:
            raise ValueError(f"entity kind {entity.kind!r} != repository {self.kind!r}")
        existing = self._storage.get(self.collection, entity.entity_id)
        if existing is not None and not allow_update:
            raise DuplicateIdError(f"duplicate id {entity.entity_id!r}")
        if existing is not None:
            prev = entity_from_dict(existing)
            entity = PersistedEntity(
                entity_id=entity.entity_id,
                kind=entity.kind,
                created_at=prev.created_at,
                updated_at=entity.updated_at,
                version=prev.version + 1,
                payload=entity.payload,
                refs=entity.refs,
                provenance=entity.provenance,
            )
            validate_entity(entity)
        self._storage.put(self.collection, entity.entity_id, entity_to_dict(entity))
        return entity

    def get(self, entity_id: str) -> PersistedEntity | None:
        row = self._storage.get(self.collection, entity_id)
        return entity_from_dict(row) if row is not None else None

    def require(self, entity_id: str) -> PersistedEntity:
        entity = self.get(entity_id)
        if entity is None:
            raise NotFoundError(f"entity not found: {entity_id}")
        return entity

    def delete(self, entity_id: str) -> bool:
        return self._storage.delete(self.collection, entity_id)

    def list_ids(self) -> tuple[str, ...]:
        return self._storage.list_keys(self.collection)

    def list_entities(self) -> tuple[PersistedEntity, ...]:
        return tuple(self.require(eid) for eid in self.list_ids())


class SnapshotRepository:
    """Immutable snapshot store — overwrite forbidden."""

    def __init__(self, storage: StorageProviderPort) -> None:
        self._storage = storage
        self.collection = "snapshots"

    def put(self, snapshot: PersistenceSnapshot) -> PersistenceSnapshot:
        validate_snapshot(snapshot)
        if self._storage.get(self.collection, snapshot.snapshot_id) is not None:
            raise SnapshotError(
                f"snapshot {snapshot.snapshot_id!r} already exists and is immutable"
            )
        self._storage.put(self.collection, snapshot.snapshot_id, snapshot_to_dict(snapshot))
        return snapshot

    def get(self, snapshot_id: str) -> PersistenceSnapshot | None:
        row = self._storage.get(self.collection, snapshot_id)
        return snapshot_from_dict(row) if row is not None else None

    def require(self, snapshot_id: str) -> PersistenceSnapshot:
        snap = self.get(snapshot_id)
        if snap is None:
            raise NotFoundError(f"snapshot not found: {snapshot_id}")
        return snap

    def list_ids(self) -> tuple[str, ...]:
        return self._storage.list_keys(self.collection)
