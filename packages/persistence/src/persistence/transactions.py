"""Transaction manager (EPIC-A008)."""

from __future__ import annotations

from typing import Any

from persistence.exceptions import TransactionError
from persistence.interfaces import StorageProviderPort

__all__ = ["TransactionManager"]


class TransactionManager:
    """Deterministic begin / commit / rollback over a storage provider.

    Nested transactions are not supported.
    """

    def __init__(self, storage: StorageProviderPort) -> None:
        self._storage = storage
        self._active = False
        self._checkpoint: dict[str, dict[str, Any]] | None = None

    @property
    def active(self) -> bool:
        return self._active

    def begin(self) -> None:
        if self._active:
            raise TransactionError("transaction already active")
        self._checkpoint = self._storage.snapshot_state()
        self._active = True

    def commit(self) -> None:
        if not self._active:
            raise TransactionError("no active transaction")
        self._checkpoint = None
        self._active = False

    def rollback(self) -> None:
        if not self._active:
            raise TransactionError("no active transaction")
        assert self._checkpoint is not None
        self._storage.restore_state(self._checkpoint)
        self._checkpoint = None
        self._active = False
