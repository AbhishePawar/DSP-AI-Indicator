"""Database port — in-memory adapter + repository base (PEP-002)."""

from __future__ import annotations

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
        sql = " ".join(statement.strip().split())
        upper = sql.upper()
        with lock:
            if upper.startswith("CREATE TABLE"):
                name = _parse_create_table(sql)
                store.setdefault(name, _Table())
                return
            if upper.startswith("INSERT INTO"):
                table, row = _parse_insert(sql)
                store.setdefault(table, _Table()).rows.append(row)
                return
            if upper.startswith("DELETE FROM"):
                table = _parse_delete_table(sql)
                if table in store:
                    store[table].rows.clear()
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
        sql = " ".join(statement.strip().split())
        upper = sql.upper()
        with lock:
            if upper.startswith("SELECT"):
                table = _parse_select_table(sql)
                rows = [dict(r) for r in store.get(table, _Table()).rows]
                if params is None:
                    return rows
                if isinstance(params, dict):
                    return [
                        r
                        for r in rows
                        if all(r.get(k) == v for k, v in params.items())
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


def _parse_insert(sql: str) -> tuple[str, dict[str, Any]]:
    # INSERT INTO name (a, b) VALUES ('x', 'y')
    upper = sql.upper()
    into = upper.index("INTO") + 4
    rest = sql[into:].strip()
    table = rest.split("(", 1)[0].strip().split()[0]
    cols_part, vals_part = rest.split("VALUES", 1)
    cols = [c.strip().strip('"') for c in cols_part[cols_part.index("(") + 1 : cols_part.rindex(")")].split(",")]
    raw_vals = vals_part[vals_part.index("(") + 1 : vals_part.rindex(")")].split(",")
    values: list[Any] = []
    for v in raw_vals:
        item = v.strip()
        if item.startswith("'") and item.endswith("'"):
            values.append(item[1:-1])
        elif item.isdigit():
            values.append(int(item))
        else:
            values.append(item)
    return table, dict(zip(cols, values, strict=True))


def _parse_delete_table(sql: str) -> str:
    tokens = sql.split()
    return tokens[tokens.index("FROM") + 1].strip(";")


def _parse_select_table(sql: str) -> str:
    tokens = sql.replace(",", " , ").split()
    from_idx = [t.upper() for t in tokens].index("FROM")
    return tokens[from_idx + 1].strip(";")
