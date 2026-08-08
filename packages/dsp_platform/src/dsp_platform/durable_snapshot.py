"""Shared JSON snapshot helpers for DatabasePort-backed product stores (P0-06)."""

from __future__ import annotations

import base64
import json
from typing import Any

__all__ = [
    "decode_snapshot_payload",
    "encode_snapshot_payload",
    "sql_literal",
    "ensure_snapshot_table",
    "load_snapshot",
    "save_snapshot",
]


def encode_snapshot_payload(payload: dict[str, Any]) -> str:
    return base64.b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")


def decode_snapshot_payload(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw:
        return None
    try:
        decoded = base64.b64decode(raw.encode("ascii")).decode("utf-8")
        data = json.loads(decoded)
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except Exception:  # noqa: BLE001
            return None


def sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def ensure_snapshot_table(database: Any, table: str) -> None:
    database.execute(
        f"CREATE TABLE IF NOT EXISTS {table} ("
        "snapshot_key TEXT PRIMARY KEY, "
        "payload TEXT NOT NULL, "
        "updated_at TEXT NOT NULL"
        ")"
    )


def load_snapshot(
    database: Any, *, table: str, snapshot_key: str
) -> dict[str, Any] | None:
    rows = database.fetchall(f"SELECT * FROM {table}")
    for row in rows:
        if str(row.get("snapshot_key")) == snapshot_key:
            return decode_snapshot_payload(row.get("payload"))
    return None


def save_snapshot(
    database: Any,
    *,
    table: str,
    snapshot_key: str,
    payload: dict[str, Any],
    updated_at: str,
) -> None:
    # InMemoryDatabasePort DELETE clears the table — rewrite the snapshot row.
    database.execute(f"DELETE FROM {table}")
    encoded = encode_snapshot_payload(payload)
    database.execute(
        f"INSERT INTO {table} (snapshot_key, payload, updated_at) VALUES ("
        f"{sql_literal(snapshot_key)}, {sql_literal(encoded)}, "
        f"{sql_literal(updated_at)})"
    )
