"""Database port — in-memory adapter + repository base (PEP-002)."""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from production_platform.production.exceptions import ProviderError
from production_platform.production.interfaces import DatabasePort, TransactionPort

__all__ = [
    "InMemoryDatabasePort",
    "InMemoryTransaction",
    "SqlRepository",
    "ensure_database_port",
]


@dataclass
class _Table:
    rows: list[dict[str, Any]] = field(default_factory=list)


class InMemoryTransaction:
    """Process-local transaction over an in-memory store."""

    def __init__(self, store: dict[str, _Table], lock: Lock) -> None:
        self._store = store
        self._lock = lock
        self._snapshot: dict[str, list[dict[str, Any]]] | None = None
        self._open = True

    def _ensure_open(self) -> None:
        if not self._open:
            raise ProviderError("transaction is closed")

    def begin(self) -> None:
        with self._lock:
            self._snapshot = {
                name: [dict(row) for row in table.rows]
                for name, table in self._store.items()
            }

    def execute(
        self, statement: str, params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> None:
        self._ensure_open()
        _ = params
        # In-memory adapter supports a tiny SQL dialect for migrations/tests.
        InMemoryDatabasePort._apply(self._store, statement, self._lock)

    def fetchall(
        self, statement: str, params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        self._ensure_open()
        return InMemoryDatabasePort._query(self._store, statement, params, self._lock)

    def commit(self) -> None:
        self._ensure_open()
        self._snapshot = None
        self._open = False

    def rollback(self) -> None:
        self._ensure_open()
        if self._snapshot is not None:
            with self._lock:
                self._store.clear()
                for name, rows in self._snapshot.items():
                    self._store[name] = _Table(rows=[dict(r) for r in rows])
        self._snapshot = None
        self._open = False


class InMemoryDatabasePort:
    """Process-local SQL-ish store — not PostgreSQL.

    Supports a minimal statement set used by the migration runner and tests:
    ``CREATE TABLE IF NOT EXISTS``, ``INSERT INTO``, ``SELECT``, ``DELETE``.
    """

    def __init__(self) -> None:
        self._tables: dict[str, _Table] = {}
        self._lock = Lock()

    def ping(self) -> bool:
        return True

    def execute(
        self, statement: str, params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> None:
        _ = params
        self._apply(self._tables, statement, self._lock)

    def fetchall(
        self, statement: str, params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        return self._query(self._tables, statement, params, self._lock)

    @contextmanager
    def transaction(self) -> Iterator[TransactionPort]:
        txn = InMemoryTransaction(self._tables, self._lock)
        txn.begin()
        try:
            yield txn
            if txn._open:  # noqa: SLF001 — intentional commit-on-success
                txn.commit()
        except Exception:
            if txn._open:  # noqa: SLF001
                txn.rollback()
            raise

    @staticmethod
    def _apply(store: dict[str, _Table], statement: str, lock: Lock) -> None:
        sql = statement.strip()
        upper = sql.upper()
        with lock:
            if upper.startswith("CREATE TABLE"):
                name = _parse_create_table(sql)
                store.setdefault(name, _Table())
                return
            if upper.startswith("INSERT INTO"):
                insert_sql, suffix = _split_insert_upsert(sql)
                table, row = _parse_insert(insert_sql)
                rows = store.setdefault(table, _Table()).rows
                if suffix:
                    if table != "identity_users":
                        raise ProviderError("unsupported upsert table")

                    expected = (
                        "ON CONFLICT (user_id) DO UPDATE SET "
                        + ", ".join(
                            f"{key} = EXCLUDED.{key}"
                            for key in row
                            if key != "user_id"
                        )
                    )

                    if suffix.strip() != expected:
                        raise ProviderError("unsupported upsert clause")

                    for index, existing in enumerate(rows):
                        if existing.get("user_id") == row["user_id"]:
                            rows[index] = row
                            return
                rows.append(row)
                return
            if upper.startswith("DELETE FROM"):
                table, condition = _parse_delete(sql)
                if table in store:
                    if condition is None:
                        store[table].rows.clear()
                    else:
                        column, value = condition
                        store[table].rows[:] = [
                            row for row in store[table].rows
                            if column not in row or row[column] != value
                        ]
                return
            if upper.startswith("SELECT"):
                return
            raise ProviderError(f"unsupported in-memory statement: {sql[:80]}")

    @staticmethod
    def _query(
        store: dict[str, _Table],
        statement: str,
        params: tuple[Any, ...] | dict[str, Any] | None,
        lock: Lock,
    ) -> list[dict[str, Any]]:
        sql = statement.strip()
        upper = sql.upper()
        with lock:
            if upper.startswith("SELECT"):
                table = _parse_select_table(sql)
                rows = [dict(r) for r in store.get(table, _Table()).rows]
                if params is None:
                    return rows
                if isinstance(params, dict):
                    return [
                        r for r in rows if all(r.get(k) == v for k, v in params.items())
                    ]
                return rows
            raise ProviderError(f"unsupported in-memory query: {sql[:80]}")


@dataclass(frozen=True, slots=True)
class SqlRepository:
    """Thin repository base — BC-owned repositories wrap a DatabasePort."""

    repository_name: str
    database: DatabasePort

    @property
    def name(self) -> str:
        return self.repository_name

    def ping(self) -> bool:
        return self.database.ping()


def ensure_database_port(port: DatabasePort | None) -> DatabasePort:
    return port if port is not None else InMemoryDatabasePort()


def _parse_create_table(sql: str) -> str:
    # CREATE TABLE IF NOT EXISTS name (...)
    tokens = sql.replace("(", " (").split()
    if "EXISTS" in tokens:
        idx = tokens.index("EXISTS")
        return tokens[idx + 1].strip('"')
    idx = tokens.index("TABLE")
    return tokens[idx + 1].strip('"')


def _split_sql_values(raw: str) -> list[str]:
    """Split SQL literals without splitting quoted commas."""
    values: list[str] = []
    current: list[str] = []
    quoted = False
    i = 0

    while i < len(raw):
        char = raw[i]

        if char == "'":
            current.append(char)

            if quoted and i + 1 < len(raw) and raw[i + 1] == "'":
                current.append("'")
                i += 2
                continue

            quoted = not quoted

        elif char == "," and not quoted:
            values.append("".join(current).strip())
            current = []

        else:
            current.append(char)

        i += 1

    if quoted:
        raise ProviderError("unterminated SQL string literal")

    values.append("".join(current).strip())
    return values


def _parse_insert(sql: str) -> tuple[str, dict[str, Any]]:
    # INSERT INTO name (a, b) VALUES ('x', 'y')
    upper = sql.upper()
    into = upper.index("INTO") + 4
    rest = sql[into:].strip()
    table = rest.split("(", 1)[0].strip().split()[0]
    cols_part, vals_part = rest.split("VALUES", 1)
    cols = [
        c.strip().strip('"')
        for c in cols_part[cols_part.index("(") + 1 : cols_part.rindex(")")].split(",")
    ]
    raw_vals = _split_sql_values(
        vals_part[vals_part.index("(") + 1 : vals_part.rindex(")")]
    )
    values: list[Any] = []
    for v in raw_vals:
        item = v.strip()
        if item.startswith("'") and item.endswith("'"):
            values.append(item[1:-1].replace("''", "'"))
        elif item.isdigit():
            values.append(int(item))
        else:
            values.append(item)
    return table, dict(zip(cols, values, strict=True))


def _parse_delete(
    sql: str,
) -> tuple[str, tuple[str, Any] | None]:
    """Support unconditional DELETE and a single literal equality."""
    match = re.fullmatch(
        r"DELETE\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)"
        r"(?:\s+WHERE\s+([A-Za-z_][A-Za-z0-9_]*)"
        r"\s*=\s*('(?:[^']|'')*'|[0-9]+))?"
        r"\s*;?",
        sql.strip(),
        flags=re.IGNORECASE,
    )
    if match is None:
        raise ProviderError("unsupported DELETE statement")

    table, column, literal = match.groups()

    if column is None:
        return table, None

    if literal.startswith("'"):
        value = literal[1:-1].replace("''", "'")
    else:
        value = int(literal)

    return table, (column, value)


def _parse_select_table(sql: str) -> str:
    tokens = sql.replace(",", " , ").split()
    from_idx = [t.upper() for t in tokens].index("FROM")
    return tokens[from_idx + 1].strip(";")



def _split_insert_upsert(statement: str) -> tuple[str, str]:
    """Separate INSERT values from a top-level upsert clause."""
    quoted = False
    depth = 0
    i = 0

    while i < len(statement):
        ch = statement[i]

        if ch == "'":
            if quoted and i + 1 < len(statement) and statement[i + 1] == "'":
                i += 2
                continue
            quoted = not quoted

        elif not quoted:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth < 0:
                    raise ProviderError("unbalanced INSERT parentheses")

            elif depth == 0 and ch.isspace():
                suffix = statement[i:].lstrip()
                if suffix.upper().startswith("ON CONFLICT "):
                    return statement[:i].rstrip(), suffix

        i += 1

    if quoted or depth != 0:
        raise ProviderError("malformed INSERT statement")

    return statement, ""
