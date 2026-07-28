"""PostgreSQL adapter — optional psycopg (PEP-002 / ADR-PEP-0004)."""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from production_platform.production.exceptions import ConfigurationError, ProviderError
from production_platform.production.interfaces import DatabasePort, TransactionPort

__all__ = ["PostgresDatabasePort", "try_build_postgres"]


class _PostgresTransaction:
    def __init__(self, conn: Any) -> None:
        self._conn = conn
        self._open = True

    def execute(
        self, statement: str, params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> None:
        self._ensure()
        with self._conn.cursor() as cur:
            cur.execute(statement, params)

    def fetchall(
        self, statement: str, params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        self._ensure()
        with self._conn.cursor() as cur:
            cur.execute(statement, params)
            columns = [d[0] for d in cur.description] if cur.description else []
            return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]

    def commit(self) -> None:
        self._ensure()
        self._conn.commit()
        self._open = False

    def rollback(self) -> None:
        self._ensure()
        self._conn.rollback()
        self._open = False

    def _ensure(self) -> None:
        if not self._open:
            raise ProviderError("postgres transaction is closed")


class PostgresDatabasePort:
    """DatabasePort backed by psycopg (v3) connection factory."""

    def __init__(self, dsn: str, *, connect_timeout: float = 5.0, application_name: str = "dsp") -> None:
        if not dsn.strip():
            raise ConfigurationError("postgres DSN must not be empty")
        self._dsn = dsn
        self._connect_timeout = connect_timeout
        self._application_name = application_name
        self._psycopg = _load_psycopg()

    def _connect(self) -> Any:
        try:
            return self._psycopg.connect(
                self._dsn,
                connect_timeout=self._connect_timeout,
                application_name=self._application_name,
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"postgres connect failed: {exc}") from exc

    def ping(self) -> bool:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return True
        except ProviderError:
            return False
        except Exception:
            return False

    def execute(
        self, statement: str, params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(statement, params)
            conn.commit()

    def fetchall(
        self, statement: str, params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(statement, params)
                columns = [d[0] for d in cur.description] if cur.description else []
                rows = [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]
            conn.commit()
            return rows

    @contextmanager
    def transaction(self) -> Iterator[TransactionPort]:
        conn = self._connect()
        txn = _PostgresTransaction(conn)
        try:
            yield txn
            if txn._open:  # noqa: SLF001
                txn.commit()
        except Exception:
            if txn._open:  # noqa: SLF001
                txn.rollback()
            raise
        finally:
            conn.close()


def try_build_postgres(
    dsn: str | None,
    *,
    connect_timeout: float = 5.0,
    application_name: str = "dsp",
) -> DatabasePort | None:
    """Return PostgresDatabasePort when DSN + driver available; else None."""
    if not dsn:
        return None
    try:
        port = PostgresDatabasePort(
            dsn, connect_timeout=connect_timeout, application_name=application_name
        )
        if not port.ping():
            return None
        return port
    except (ConfigurationError, ProviderError, ImportError):
        return None


def _load_psycopg() -> Any:
    try:
        return importlib.import_module("psycopg")
    except ImportError as exc:
        raise ProviderError(
            "psycopg is not installed; pip install 'production-platform[postgres]'"
        ) from exc
