"""Canonical, non-destructive application schema for managed PostgreSQL.

This module is deliberately scoped to DSP-owned tables. It never reads,
creates, alters, or drops the ``neon_auth`` schema.
"""

from __future__ import annotations

from dataclasses import dataclass

from production_platform.production.interfaces import DatabasePort
from production_platform.production.migrations import Migration, MigrationRunner

__all__ = ["APPLICATION_MIGRATIONS", "apply_application_schema"]


@dataclass(frozen=True, slots=True)
class _SchemaPart:
    name: str
    sql: str


_SCHEMA_PARTS = (
    _SchemaPart(
        "001_core_persistence",
        """
        CREATE TABLE IF NOT EXISTS a008_entities (
            collection TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (collection, entity_id)
        );
        """,
    ),
    _SchemaPart(
        "002_identity",
        """
        CREATE TABLE IF NOT EXISTS identity_users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            active INTEGER NOT NULL,
            display_name TEXT,
            email TEXT,
            password_hash TEXT,
            email_verified INTEGER NOT NULL,
            org_id TEXT,
            extra_permissions TEXT,
            failed_login_count INTEGER NOT NULL,
            locked_until TEXT
        );
        """,
    ),
    _SchemaPart(
        "003_enterprise",
        """
        CREATE TABLE IF NOT EXISTS enterprise_snapshots (
            snapshot_key TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS enterprise_audit_log (
            event_id TEXT PRIMARY KEY,
            org_id TEXT,
            actor_user_id TEXT,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT,
            created_at TEXT NOT NULL,
            before_state TEXT,
            after_state TEXT,
            ip_address TEXT,
            correlation_id TEXT,
            metadata TEXT,
            immutable INTEGER NOT NULL
        );
        """,
    ),
    _SchemaPart(
        "004_compliance",
        """
        CREATE TABLE IF NOT EXISTS compliance_consents (
            consent_id TEXT PRIMARY KEY, subject_id TEXT, purpose_id TEXT,
            granted INTEGER, policy_version TEXT, recorded_at TEXT,
            locale TEXT, channel TEXT
        );
        CREATE TABLE IF NOT EXISTS compliance_history (
            entry_id TEXT PRIMARY KEY, symbol TEXT, action_label TEXT,
            issued_at TEXT, horizon TEXT, target_price TEXT, report_ref TEXT
        );
        CREATE TABLE IF NOT EXISTS compliance_archive (
            archive_id TEXT PRIMARY KEY, report_ref TEXT, archived_at TEXT,
            retention_class TEXT
        );
        CREATE TABLE IF NOT EXISTS compliance_audit (
            event_id TEXT PRIMARY KEY, action TEXT, actor TEXT,
            occurred_at TEXT, resource_ref TEXT, detail TEXT
        );
        """,
    ),
    _SchemaPart(
        "005_product_snapshots",
        """
        CREATE TABLE IF NOT EXISTS saas_overlay_snapshots (
            snapshot_key TEXT PRIMARY KEY, payload TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS research_workspace_snapshots (
            snapshot_key TEXT PRIMARY KEY, payload TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS api_report_snapshots (
            snapshot_key TEXT PRIMARY KEY, payload TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
    ),
)

APPLICATION_MIGRATIONS: tuple[Migration, ...] = tuple(
    Migration(version=part.name, description=part.name, up_sql=part.sql)
    for part in _SCHEMA_PARTS
)


def apply_application_schema(database: DatabasePort) -> tuple[str, ...]:
    """Apply only pending DSP application migrations.

    The operation is additive and uses ``schema_migrations`` for idempotency.
    It does not perform data import, reset, drop, or any Neon Auth operation.
    """

    return MigrationRunner(database).apply(APPLICATION_MIGRATIONS)
