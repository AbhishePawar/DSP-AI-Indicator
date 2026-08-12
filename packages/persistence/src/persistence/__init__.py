"""Institutional Persistence Layer (EPIC-A008)."""

from __future__ import annotations

from persistence.exceptions import (
    DuplicateIdError,
    NotFoundError,
    PersistenceError,
    SnapshotError,
    TransactionError,
    ValidationError,
)
from persistence.models import (
    ENTITY_KINDS,
    PERSISTENCE_SCHEMA_VERSION,
    PERSISTENCE_SERVICE_VERSION,
    UNAVAILABLE_MESSAGE,
    PersistedEntity,
    PersistenceSnapshot,
    freeze_mapping,
    utc_now,
)
from persistence.registry import (
    RepositoryRegistry,
    get_repository_registry,
    reset_repository_registry_for_tests,
)
from persistence.serde import (
    canonical_dumps,
    content_hash,
    entity_from_dict,
    entity_to_dict,
    snapshot_from_dict,
    snapshot_to_dict,
    to_plain_jsonable,
)
from persistence.service import (
    PersistenceService,
    get_persistence_service,
    reset_persistence_service_for_tests,
)
from persistence.storage import InMemoryStorageProvider
from persistence.transactions import TransactionManager

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "ENTITY_KINDS",
    "PERSISTENCE_SCHEMA_VERSION",
    "PERSISTENCE_SERVICE_VERSION",
    "UNAVAILABLE_MESSAGE",
    "DuplicateIdError",
    "InMemoryStorageProvider",
    "NotFoundError",
    "PersistedEntity",
    "PersistenceError",
    "PersistenceService",
    "PersistenceSnapshot",
    "RepositoryRegistry",
    "SnapshotError",
    "TransactionError",
    "TransactionManager",
    "ValidationError",
    "canonical_dumps",
    "content_hash",
    "entity_from_dict",
    "entity_to_dict",
    "freeze_mapping",
    "get_persistence_service",
    "get_repository_registry",
    "reset_persistence_service_for_tests",
    "reset_repository_registry_for_tests",
    "snapshot_from_dict",
    "snapshot_to_dict",
    "to_plain_jsonable",
    "utc_now",
]
