"""Storage providers (EPIC-A008)."""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any, Mapping

from persistence.serde import to_plain_jsonable

__all__ = [
    "InMemoryStorageProvider",
]


class InMemoryStorageProvider:
    """Default process-local storage provider.

    Future providers (PostgreSQL, SQLite, DuckDB, object storage) implement the
    same StorageProviderPort without changing repository/service APIs.
    """

    provider_id = "in_memory"

    def __init__(self) -> None:
        self._lock = RLock()
        self._data: dict[str, dict[str, dict[str, Any]]] = {}

    def put(self, collection: str, key: str, value: Mapping[str, Any]) -> None:
        with self._lock:
            bucket = self._data.setdefault(collection, {})
            bucket[key] = to_plain_jsonable(dict(value))

    def get(self, collection: str, key: str) -> Mapping[str, Any] | None:
        with self._lock:
            row = self._data.get(collection, {}).get(key)
            return deepcopy(row) if row is not None else None

    def delete(self, collection: str, key: str) -> bool:
        with self._lock:
            bucket = self._data.get(collection)
            if not bucket or key not in bucket:
                return False
            del bucket[key]
            return True

    def list_keys(self, collection: str) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._data.get(collection, {}).keys()))

    def clear(self, collection: str) -> None:
        with self._lock:
            self._data[collection] = {}

    def snapshot_state(self) -> dict[str, dict[str, Mapping[str, Any]]]:
        with self._lock:
            return deepcopy(self._data)

    def restore_state(
        self, state: Mapping[str, Mapping[str, Mapping[str, Any]]]
    ) -> None:
        with self._lock:
            restored: dict[str, dict[str, dict[str, Any]]] = {}
            for collection, rows in state.items():
                restored[str(collection)] = {
                    str(k): to_plain_jsonable(dict(v))
                    for k, v in sorted(rows.items(), key=lambda x: str(x[0]))
                }
            self._data = restored
