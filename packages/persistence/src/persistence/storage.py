"""Storage providers (EPIC-A008)."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock
from typing import Any

from persistence.exceptions import NotFoundError, ValidationError
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
        attempts_field: tuple[str, ...] | None = None,
        max_attempts: int | None = None,
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
            if attempts_field is not None and max_attempts is not None:
                if _as_int(_nested_get(row, attempts_field)) >= max_attempts:
                    return None
            _nested_set(row, consumed_field, consumed_at)
            if isinstance(row, dict):
                row["updated_at"] = consumed_at
            bucket[key] = to_plain_jsonable(row)
            return deepcopy(bucket[key])

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
            current = _as_int(_nested_get(row, counter_field))
            if current >= max_value:
                return None
            _nested_set(row, counter_field, current + 1)
            if isinstance(row, dict):
                row["updated_at"] = now_iso
            bucket[key] = to_plain_jsonable(row)
            return deepcopy(bucket[key])

    def atomic_put_if_absent(
        self, collection: str, key: str, value: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        with self._lock:
            bucket = self._data.setdefault(collection, {})
            if key in bucket:
                return deepcopy(bucket[key])
            bucket[key] = to_plain_jsonable(dict(value))
            return deepcopy(bucket[key])

    def atomic_merge_payload(
        self,
        collection: str,
        key: str,
        *,
        fields: Mapping[str, Any],
        updated_at: str,
        match: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any] | None:
        with self._lock:
            bucket = self._data.get(collection)
            if not bucket or key not in bucket:
                return None
            row = bucket[key]
            inner = row.get("payload")
            if not isinstance(inner, dict):
                inner = {}
            if not _payload_matches(inner, match):
                return None
            inner = dict(inner)
            inner.update(to_plain_jsonable(dict(fields)))
            row["payload"] = inner
            row["updated_at"] = updated_at
            bucket[key] = to_plain_jsonable(row)
            return deepcopy(bucket[key])


    def append_research_turn_atomic(
        self,
        *,
        session_collection: str,
        turns_collection: str,
        session_id: str,
        turn_id: str,
        turn_data: Mapping[str, Any],
        max_turns: int = 20,
        expected_user_id: str | None = None,
        expected_symbol: str | None = None,
        expected_analysis_id: str | None = None,
    ) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        with self._lock:
            bucket = self._data.setdefault(session_collection, {})
            session_row = bucket.get(session_id)
            if session_row is None:
                raise NotFoundError(f"Research session not found: {session_id}")

            if expected_user_id is not None and str(session_row.get("user_id", "")) != str(expected_user_id):
                raise ValidationError("Ownership validation failed: unauthorized user")

            if expected_symbol is not None and str(session_row.get("symbol", "")).upper() != str(expected_symbol).upper():
                raise ValidationError("Context validation failed: symbol mismatch")
            if expected_analysis_id is not None and str(session_row.get("analysis_id", "")) != str(expected_analysis_id):
                raise ValidationError("Context validation failed: analysis_id mismatch")

            turn_ids = list(session_row.get("turn_ids") or [])
            turn_ids.append(turn_id)

            turns_bucket = self._data.setdefault(turns_collection, {})
            clean_turn = to_plain_jsonable(dict(turn_data))
            turns_bucket[turn_id] = clean_turn

            if len(turn_ids) > max_turns:
                excess = len(turn_ids) - max_turns
                for _ in range(excess):
                    evicted_id = turn_ids.pop(0)
                    turns_bucket.pop(evicted_id, None)

            now_iso = str(clean_turn.get("created_at") or _utc_now())
            session_row["turn_ids"] = turn_ids
            session_row["turn_count"] = len(turn_ids)
            session_row["updated_at"] = now_iso
            bucket[session_id] = to_plain_jsonable(session_row)

            return deepcopy(clean_turn), deepcopy(bucket[session_id])


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _payload_matches(inner: Mapping[str, Any], match: Mapping[str, Any] | None) -> bool:
    if not match:
        return True
    for field, expected in match.items():
        actual = inner.get(field)
        if field == "revoked" and expected is False:
            if actual in (True, "true", "True"):
                return False
            continue
        if actual != expected:
            return False
    return True


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


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _is_unexpired(expires_raw: Any, now_iso: str) -> bool:
    if not expires_raw:
        return False
    try:
        expires = datetime.fromisoformat(str(expires_raw).replace("Z", "+00:00"))
        now = datetime.fromisoformat(str(now_iso).replace("Z", "+00:00"))
    except ValueError:
        return False
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return now < expires
