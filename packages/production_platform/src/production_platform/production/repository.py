"""Repository factory — reference implementation (PEP-002)."""

from __future__ import annotations

from production_platform.production.database import SqlRepository
from production_platform.production.exceptions import ConfigurationError
from production_platform.production.interfaces import DatabasePort, Repository, RepositoryFactoryPort

__all__ = ["DefaultRepositoryFactory", "ensure_repository_factory"]


class DefaultRepositoryFactory:
    """Creates SqlRepository wrappers bound to a shared DatabasePort."""

    def __init__(self, database: DatabasePort) -> None:
        self._database = database
        self._cache: dict[str, Repository] = {}

    def create(self, name: str) -> Repository:
        cleaned = name.strip()
        if not cleaned:
            raise ConfigurationError("repository name must not be empty")
        existing = self._cache.get(cleaned)
        if existing is not None:
            return existing
        repo: Repository = SqlRepository(repository_name=cleaned, database=self._database)
        self._cache[cleaned] = repo
        return repo


def ensure_repository_factory(
    factory: RepositoryFactoryPort | None, *, database: DatabasePort
) -> RepositoryFactoryPort:
    return factory if factory is not None else DefaultRepositoryFactory(database)
