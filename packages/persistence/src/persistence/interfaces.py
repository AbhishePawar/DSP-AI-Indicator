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
    """Storage abstraction — InMemory in development; Postgres in production."""

    provider_id: str

    def put(self, collection: str, key: str, value: Mapping[str, Any]) -> None: ...

    def get(self, collection: str, key: str) -> Mapping[str, Any] | None: ...

    def delete(self, collection: str, key: str) -> bool: ...

    def list_keys(self, collection: str) -> tuple[str, ...]: ...

    def clear(self, collection: str) -> None: ...

    def snapshot_state(self) -> dict[str, dict[str, Mapping[str, Any]]]: ...

    def restore_state(self, state: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> None: ...

    def atomic_consume_unexpired(
        self,
        collection: str,
        key: str,
        *,
        now_iso: str,
        consumed_at: str,
        consumed_field: tuple[str, ...] = ("payload", "consumed_at"),
        expires_field: tuple[str, ...] = ("payload", "expires_at"),
        attempts_field: tuple[str, ...] | None = None,
        max_attempts: int | None = None,
    ) -> Mapping[str, Any] | None:
        """Atomically mark ``consumed_field`` if unset and not expired.

        Returns the stored document after a successful consume, or ``None``
        when the row is missing, already consumed, or expired. Must be
        implemented with a single compare-and-set (not get-then-put).
        When ``attempts_field`` and ``max_attempts`` are set, consume also
        requires the integer counter to be strictly below ``max_attempts``.
        """
        ...

    def atomic_increment_unexpired(
        self,
        collection: str,
        key: str,
        *,
        now_iso: str,
        counter_field: tuple[str, ...] = ("payload", "attempts"),
        max_value: int = 5,
        consumed_field: tuple[str, ...] = ("payload", "consumed_at"),
        expires_field: tuple[str, ...] = ("payload", "expires_at"),
    ) -> Mapping[str, Any] | None:
        """Atomically increment ``counter_field`` when unconsumed, unexpired, and below max."""
        ...


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
