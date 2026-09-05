"""Storage providers (EPIC-A008)."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
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

    def atomic_consume_unexpired(
        self,
        collection: str,
        key: str,
        *,
        now_iso: str,
        consumed_at: str,
        consumed_field: tuple[str, ...] = ("payload", "consumed_at"),
        expires_field: tuple[str, ...] = ("payload", "expires_at"),
    ) -> Mapping[str, Any] | None:
        with self._lock:
            bucket = self._data.get(collection)
            if not bucket or key not in bucket:
                return None
            row = bucket[key]
            if _nested_get(row, consumed_field) not in (None, ""):
                return None
            expires_raw = _nested_get(row, expires_field)
            if not _is_unexpired(expires_raw, now_iso):
                return None
            _nested_set(row, consumed_field, consumed_at)
            if isinstance(row, dict):
                row["updated_at"] = consumed_at
            bucket[key] = to_plain_jsonable(row)
            return deepcopy(bucket[key])


def _nested_get(row: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    cursor: Any = row
    for part in path:
        if not isinstance(cursor, Mapping) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def _nested_set(row: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    cursor: dict[str, Any] = row
    for part in path[:-1]:
        nxt = cursor.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[part] = nxt
        cursor = nxt
    cursor[path[-1]] = value


def _is_unexpired(expires_raw: Any, now_iso: str) -> bool:
    if not expires_raw:
        return False
    try:
        expires = datetime.fromisoformat(str(expires_raw).replace("Z", "+00:00"))
        now = datetime.fromisoformat(str(now_iso).replace("Z", "+00:00"))
    except ValueError:
        return False
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now < expires
