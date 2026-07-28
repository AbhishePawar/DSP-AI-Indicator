"""Vendor-neutral migration framework (PEP-002)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from production_platform.production.exceptions import ConfigurationError, ProviderError
from production_platform.production.interfaces import DatabasePort

__all__ = ["Migration", "MigrationRunner"]


@dataclass(frozen=True, slots=True)
class Migration:
    """One forward migration step."""

    version: str
    description: str
    up_sql: str
    down_sql: str | None = None

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ConfigurationError("migration version must not be empty")
        if not self.up_sql.strip():
            raise ConfigurationError("migration up_sql must not be empty")


class MigrationRunner:
    """Applies ordered migrations through DatabasePort.

    Tracks applied versions in ``schema_migrations`` (configurable).
    Works with InMemoryDatabasePort and PostgresDatabasePort alike.
    """

    def __init__(
        self,
        database: DatabasePort,
        *,
        table_name: str = "schema_migrations",
    ) -> None:
        self._db = database
        self._table = table_name

    def ensure_tracking_table(self) -> None:
        self._db.execute(
            f"CREATE TABLE IF NOT EXISTS {self._table} ("
            "version TEXT PRIMARY KEY, "
            "description TEXT, "
            "applied_at TEXT"
            ")"
        )

    def applied_versions(self) -> tuple[str, ...]:
        self.ensure_tracking_table()
        rows = self._db.fetchall(f"SELECT version, description FROM {self._table}")
        return tuple(sorted(str(r["version"]) for r in rows))

    def apply(self, migrations: Sequence[Migration]) -> tuple[str, ...]:
        """Apply pending migrations in version order; return newly applied versions."""
        ordered = sorted(migrations, key=lambda m: m.version)
        versions = [m.version for m in ordered]
        if len(set(versions)) != len(versions):
            raise ConfigurationError("duplicate migration versions")
        self.ensure_tracking_table()
        applied = set(self.applied_versions())
        newly: list[str] = []
        for migration in ordered:
            if migration.version in applied:
                continue
            try:
                with self._db.transaction() as txn:
                    txn.execute(migration.up_sql)
                    txn.execute(
                        f"INSERT INTO {self._table} (version, description, applied_at) "
                        f"VALUES ('{migration.version}', '{_escape(migration.description)}', 'now')"
                    )
            except Exception as exc:  # noqa: BLE001
                raise ProviderError(
                    f"migration {migration.version} failed: {exc}"
                ) from exc
            newly.append(migration.version)
        return tuple(newly)


def _escape(value: str) -> str:
    return value.replace("'", "''")
