"""Repository registry (EPIC-A008)."""

from __future__ import annotations

import os

from persistence.exceptions import PersistenceError
from persistence.interfaces import StorageProviderPort
from persistence.models import ENTITY_KINDS
from persistence.repositories import EntityRepository, SnapshotRepository
from persistence.storage import InMemoryStorageProvider

__all__ = [
    "RepositoryRegistry",
    "build_default_storage",
    "get_repository_registry",
    "reset_repository_registry_for_tests",
]


class RepositoryRegistry:
    """Process-local registry of typed repositories over a storage provider."""

    def __init__(self, storage: StorageProviderPort | None = None) -> None:
        self.storage = storage if storage is not None else build_default_storage()
        self._repos: dict[str, EntityRepository] = {
            kind: EntityRepository(self.storage, kind) for kind in ENTITY_KINDS
        }
        self.snapshots = SnapshotRepository(self.storage)

    def repository(self, kind: str) -> EntityRepository:
        if kind not in self._repos:
            raise KeyError(f"unknown repository kind {kind!r}")
        return self._repos[kind]

    def kinds(self) -> tuple[str, ...]:
        return tuple(sorted(self._repos.keys()))


_REG: RepositoryRegistry | None = None


def build_default_storage() -> StorageProviderPort:
    """Select A008 storage. Production never silently uses in-memory."""
    environment = (os.environ.get("DSP_ENVIRONMENT") or "").strip().lower()
    if environment == "production":
        dsn = (
            os.environ.get("DSP_DATABASE_URL") or os.environ.get("DATABASE_URL") or ""
        ).strip()
        if not dsn:
            raise PersistenceError(
                "DSP_DATABASE_URL must be set for A008 persistence in production"
            )
        from persistence.postgres_storage import build_postgres_storage

        return build_postgres_storage(dsn)
    return InMemoryStorageProvider()


def get_repository_registry(
    storage: StorageProviderPort | None = None,
) -> RepositoryRegistry:
    global _REG
    if _REG is None:
        _REG = RepositoryRegistry(storage=storage) if storage is not None else RepositoryRegistry()
    return _REG


def reset_repository_registry_for_tests(
    registry: RepositoryRegistry | None = None,
) -> None:
    global _REG
    _REG = registry
