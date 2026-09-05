"""PostgreSQL StorageProviderPort for A008 (shared across Cloud Run instances)."""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping

from persistence.exceptions import PersistenceError
from persistence.serde import to_plain_jsonable

__all__ = [
    "PostgresStorageProvider",
    "build_postgres_storage",
]

_TABLE = "a008_entities"
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_URI_CREDENTIALS = re.compile(
    r"(?i)(?P<scheme>[a-z0-9+.\-]+://)(?P<user>[^:/?#@\s]+):[^@\s]*@"
)


def _redact_dsn(text: str) -> str:
    return _URI_CREDENTIALS.sub(r"\g<scheme>\g<user>:***@", text)


def _jsonb_path(field: tuple[str, ...]) -> str:
    if not field or any(not _IDENT.match(part) for part in field):
        raise PersistenceError("invalid JSON path for A008 consume")
    return "{" + ",".join(field) + "}"


def _load_psycopg() -> Any:
    try:
        return __import__("psycopg")
    except ImportError as exc:
        raise PersistenceError(
            "psycopg is required for Postgres A008 persistence "
            "(install with pip install '.[api]' including psycopg[binary]>=3.1)"
        ) from exc


class PostgresStorageProvider:
    """Durable ``StorageProviderPort`` over Cloud SQL / PostgreSQL.

    Production must construct this via :func:`build_postgres_storage` and
    fail closed when the DSN or driver is unavailable. Consume uses a
    single ``UPDATE … RETURNING`` so two Cloud Run instances cannot both
    redeem the same OAuth challenge.
    """

    provider_id = "postgres"

    def __init__(self, dsn: str, *, connect_timeout: float = 5.0) -> None:
        if not (dsn or "").strip():
            raise PersistenceError("DSP_DATABASE_URL must not be empty")
        self._dsn = dsn.strip()
        self._connect_timeout = connect_timeout
        self._psycopg = _load_psycopg()
        self._ensure_schema()

    def _connect(self) -> Any:
        try:
            return self._psycopg.connect(
                self._dsn,
                connect_timeout=self._connect_timeout,
                application_name="dsp-a008",
            )
        except Exception as exc:  # noqa: BLE001
            raise PersistenceError(
                f"postgres A008 connect failed: {_redact_dsn(str(exc))}"
            ) from exc

    def _ensure_schema(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"CREATE TABLE IF NOT EXISTS {_TABLE} ("
                "collection TEXT NOT NULL, "
                "entity_id TEXT NOT NULL, "
                "payload JSONB NOT NULL, "
                "created_at TIMESTAMPTZ NOT NULL, "
                "updated_at TIMESTAMPTZ NOT NULL, "
                "PRIMARY KEY (collection, entity_id)"
                ")"
            )
            conn.commit()

    def put(self, collection: str, key: str, value: Mapping[str, Any]) -> None:
        row = to_plain_jsonable(dict(value))
        created = str(row.get("created_at") or _utc_now())
        updated = str(row.get("updated_at") or created)
        Json = self._psycopg.types.json.Json
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {_TABLE} (collection, entity_id, payload, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s::timestamptz, %s::timestamptz) "
                "ON CONFLICT (collection, entity_id) DO UPDATE SET "
                "payload = EXCLUDED.payload, updated_at = EXCLUDED.updated_at",
                (collection, key, Json(row), created, updated),
            )
            conn.commit()

    def get(self, collection: str, key: str) -> Mapping[str, Any] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"SELECT payload FROM {_TABLE} WHERE collection = %s AND entity_id = %s",
                (collection, key),
            )
            found = cur.fetchone()
        if found is None:
            return None
        payload = found[0]
        return deepcopy(payload) if isinstance(payload, dict) else None

    def delete(self, collection: str, key: str) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {_TABLE} WHERE collection = %s AND entity_id = %s",
                (collection, key),
            )
            deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    def list_keys(self, collection: str) -> tuple[str, ...]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"SELECT entity_id FROM {_TABLE} WHERE collection = %s ORDER BY entity_id",
                (collection,),
            )
            rows = cur.fetchall()
        return tuple(str(r[0]) for r in rows)

    def clear(self, collection: str) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(f"DELETE FROM {_TABLE} WHERE collection = %s", (collection,))
            conn.commit()

    def snapshot_state(self) -> dict[str, dict[str, Mapping[str, Any]]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(f"SELECT collection, entity_id, payload FROM {_TABLE}")
            rows = cur.fetchall()
        out: dict[str, dict[str, Mapping[str, Any]]] = {}
        for collection, entity_id, payload in rows:
            bucket = out.setdefault(str(collection), {})
            bucket[str(entity_id)] = deepcopy(payload) if isinstance(payload, dict) else {}
        return out

    def restore_state(
        self, state: Mapping[str, Mapping[str, Mapping[str, Any]]]
    ) -> None:
        Json = self._psycopg.types.json.Json
        now = _utc_now()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(f"DELETE FROM {_TABLE}")
            for collection, rows in state.items():
                for entity_id, payload in rows.items():
                    row = to_plain_jsonable(dict(payload))
                    created = str(row.get("created_at") or now)
                    updated = str(row.get("updated_at") or created)
                    cur.execute(
                        f"INSERT INTO {_TABLE} "
                        "(collection, entity_id, payload, created_at, updated_at) "
                        "VALUES (%s, %s, %s, %s::timestamptz, %s::timestamptz)",
                        (str(collection), str(entity_id), Json(row), created, updated),
                    )
            conn.commit()

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
        consumed_path = _jsonb_path(consumed_field)
        expires_path = _jsonb_path(expires_field)
        sql = (
            f"UPDATE {_TABLE} SET "
            "payload = jsonb_set("
            f"jsonb_set(payload, '{consumed_path}', to_jsonb(%s::text), true), "
            "'{updated_at}', to_jsonb(%s::text), true"
            "), "
            "updated_at = %s::timestamptz "
            f"WHERE collection = %s AND entity_id = %s "
            f"AND payload #>> '{consumed_path}' IS NULL "
            f"AND payload #>> '{expires_path}' IS NOT NULL "
            f"AND (payload #>> '{expires_path}')::timestamptz > %s::timestamptz "
            "RETURNING payload"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    consumed_at,
                    consumed_at,
                    consumed_at,
                    collection,
                    key,
                    now_iso,
                ),
            )
            found = cur.fetchone()
            conn.commit()
        if found is None:
            return None
        payload = found[0]
        return deepcopy(payload) if isinstance(payload, dict) else None


def build_postgres_storage(
    dsn: str | None,
    *,
    connect_timeout: float = 5.0,
) -> PostgresStorageProvider:
    """Return a verified Postgres A008 provider or raise :class:`PersistenceError`."""
    if not dsn or not str(dsn).strip():
        raise PersistenceError("DSP_DATABASE_URL must be set for A008 persistence in production")
    return PostgresStorageProvider(str(dsn).strip(), connect_timeout=connect_timeout)


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
