"""Persistence interfaces / ports (EPIC-A008)."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from persistence.models import PersistedEntity, PersistenceSnapshot

__all__ = [
    "EntityRepositoryPort",
    "SnapshotRepositoryPort",
    "StorageProviderPort",
]


class StorageProviderPort(Protocol):
    """Storage abstraction — InMemory default; Postgres/SQLite/etc. later."""

    provider_id: str

    def put(self, collection: str, key: str, value: Mapping[str, Any]) -> None: ...

    def get(self, collection: str, key: str) -> Mapping[str, Any] | None: ...

    def delete(self, collection: str, key: str) -> bool: ...

    def list_keys(self, collection: str) -> tuple[str, ...]: ...

    def clear(self, collection: str) -> None: ...

    def snapshot_state(self) -> dict[str, dict[str, Mapping[str, Any]]]: ...

    def restore_state(self, state: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> None: ...


class EntityRepositoryPort(Protocol):
    def put(self, entity: PersistedEntity) -> PersistedEntity: ...

    def get(self, entity_id: str) -> PersistedEntity | None: ...

    def delete(self, entity_id: str) -> bool: ...

    def list_ids(self) -> tuple[str, ...]: ...

    def list_entities(self) -> tuple[PersistedEntity, ...]: ...


class SnapshotRepositoryPort(Protocol):
    def put(self, snapshot: PersistenceSnapshot) -> PersistenceSnapshot: ...

    def get(self, snapshot_id: str) -> PersistenceSnapshot | None: ...

    def list_ids(self) -> tuple[str, ...]: ...
