"""Repository registry (EPIC-A008)."""

from __future__ import annotations

from persistence.interfaces import StorageProviderPort
from persistence.models import ENTITY_KINDS
from persistence.repositories import EntityRepository, SnapshotRepository
from persistence.storage import InMemoryStorageProvider

__all__ = [
    "RepositoryRegistry",
    "get_repository_registry",
    "reset_repository_registry_for_tests",
]


class RepositoryRegistry:
    """Process-local registry of typed repositories over a storage provider."""

    def __init__(self, storage: StorageProviderPort | None = None) -> None:
        self.storage = storage or InMemoryStorageProvider()
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


def get_repository_registry(
    storage: StorageProviderPort | None = None,
) -> RepositoryRegistry:
    global _REG
    if _REG is None:
        _REG = RepositoryRegistry(storage=storage)
    return _REG


def reset_repository_registry_for_tests(
    registry: RepositoryRegistry | None = None,
) -> None:
    global _REG
    _REG = registry
