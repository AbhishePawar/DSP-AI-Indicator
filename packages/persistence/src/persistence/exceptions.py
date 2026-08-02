"""Persistence exceptions (EPIC-A008)."""

from __future__ import annotations

__all__ = [
    "PersistenceError",
    "DuplicateIdError",
    "NotFoundError",
    "ValidationError",
    "TransactionError",
    "SnapshotError",
]


class PersistenceError(ValueError):
    """Base persistence error."""


class DuplicateIdError(PersistenceError):
    """Duplicate entity id in repository."""


class NotFoundError(PersistenceError):
    """Entity not found."""


class ValidationError(PersistenceError):
    """Validation failure."""


class TransactionError(PersistenceError):
    """Transaction begin/commit/rollback failure."""


class SnapshotError(PersistenceError):
    """Immutable snapshot violation."""
