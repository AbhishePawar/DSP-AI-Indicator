"""P1-08 — logical backup/restore of durable multi-tenant product state.

Archives are JSON + SHA-256 (not pickle). Pickle payloads that already live
inside report snapshot rows are treated as opaque TEXT and only decoded by the
application store after a trusted operator restore.

Persistence Architecture Alignment:
- Active report persistence in the running application is backed by DatabaseReportStore
  and stored in the 'api_report_snapshots' table (part of LEGACY_PRODUCT_STATE_TABLES).
- 'api_report_records' and 'api_export_records' are optional record schemas designed for
  multi-tenant metadata and S3 artifact links. They are NOT created implicitly during
  adapter construction or restore, and are not integrated into current application
  routers or migrations (reports use snapshots; exports are generated in-memory).
- Explicit provisioning methods (ensure_record_tables_schema) are available for test fixtures
  or future migrations without mutating production/staging database schemas at runtime.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

__all__ = [
    "LEGACY_PRODUCT_STATE_TABLES",
    "PRODUCT_STATE_TABLES",
    "TABLE_ALLOWED_COLUMNS",
    "LogicalProductStateBackupAdapter",
    "RESTORE_CONFIRM_ENV",
]

RESTORE_CONFIRM_ENV = "DSP_BACKUP_RESTORE_CONFIRM"
_FORMAT = "dsp_product_state_v1"
_SNAPSHOT_ID_RE = re.compile(r"^dsp_product_\d{8}T\d{6}Z(?:_[A-Za-z0-9_-]+)?$")

LEGACY_PRODUCT_STATE_TABLES: tuple[str, ...] = (
    "enterprise_snapshots",
    "enterprise_audit_log",
    "saas_overlay_snapshots",
    "research_workspace_snapshots",
    "api_report_snapshots",
)

PRODUCT_STATE_TABLES: tuple[str, ...] = (
    *LEGACY_PRODUCT_STATE_TABLES,
    "api_report_records",
    "api_export_records",
)

_SNAPSHOT_DDL = (
    "CREATE TABLE IF NOT EXISTS {table} ("
    "snapshot_key TEXT PRIMARY KEY, "
    "payload TEXT NOT NULL, "
    "updated_at TEXT NOT NULL"
    ")"
)

_AUDIT_DDL = (
    "CREATE TABLE IF NOT EXISTS enterprise_audit_log ("
    "event_id TEXT PRIMARY KEY, "
    "org_id TEXT, "
    "actor_user_id TEXT, "
    "action TEXT NOT NULL, "
    "resource_type TEXT NOT NULL, "
    "resource_id TEXT, "
    "created_at TEXT NOT NULL, "
    "before_state TEXT, "
    "after_state TEXT, "
    "ip_address TEXT, "
    "correlation_id TEXT, "
    "metadata TEXT, "
    "immutable INTEGER NOT NULL"
    ")"
)

_REPORT_RECORDS_DDL = (
    "CREATE TABLE IF NOT EXISTS api_report_records ("
    "id TEXT PRIMARY KEY, "
    "report_id TEXT, "
    "owner_id TEXT, "
    "tenant_id TEXT, "
    "status TEXT, "
    "s3_key TEXT, "
    "s3_bucket TEXT, "
    "created_at TEXT, "
    "updated_at TEXT, "
    "metadata TEXT"
    ")"
)

_EXPORT_RECORDS_DDL = (
    "CREATE TABLE IF NOT EXISTS api_export_records ("
    "id TEXT PRIMARY KEY, "
    "export_id TEXT, "
    "owner_id TEXT, "
    "tenant_id TEXT, "
    "status TEXT, "
    "s3_key TEXT, "
    "s3_bucket TEXT, "
    "content_type TEXT, "
    "size_bytes INTEGER, "
    "created_at TEXT, "
    "metadata TEXT"
    ")"
)

TABLE_ALLOWED_COLUMNS: dict[str, frozenset[str]] = {
    "enterprise_snapshots": frozenset({"snapshot_key", "payload", "updated_at"}),
    "saas_overlay_snapshots": frozenset({"snapshot_key", "payload", "updated_at"}),
    "research_workspace_snapshots": frozenset(
        {"snapshot_key", "payload", "updated_at"}
    ),
    "api_report_snapshots": frozenset({"snapshot_key", "payload", "updated_at"}),
    "enterprise_audit_log": frozenset(
        {
            "event_id",
            "org_id",
            "actor_user_id",
            "action",
            "resource_type",
            "resource_id",
            "created_at",
            "before_state",
            "after_state",
            "ip_address",
            "correlation_id",
            "metadata",
            "immutable",
        }
    ),
    "api_report_records": frozenset(
        {
            "id",
            "report_id",
            "owner_id",
            "tenant_id",
            "status",
            "s3_key",
            "s3_bucket",
            "created_at",
            "updated_at",
            "metadata",
        }
    ),
    "api_export_records": frozenset(
        {
            "id",
            "export_id",
            "owner_id",
            "tenant_id",
            "status",
            "s3_key",
            "s3_bucket",
            "content_type",
            "size_bytes",
            "created_at",
            "metadata",
        }
    ),
}


class LogicalProductStateBackupAdapter:
    """DatabasePort row dump/restore for durable product tables (P1-08)."""

    def __init__(
        self,
        database: Any,
        *,
        backup_root: str | Path | None = None,
    ) -> None:
        if database is None or not all(
            hasattr(database, name) for name in ("execute", "fetchall", "ping")
        ):
            raise ValueError("LogicalProductStateBackupAdapter requires a DatabasePort")
        self._db = database
        root = backup_root or os.environ.get("DSP_BACKUP_DIR") or "./backups"
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def provider_name(self) -> str:
        return "logical_product_state"

    def is_available(self) -> bool:
        try:
            return bool(self._db.ping())
        except Exception:  # noqa: BLE001
            return False

    def status(self) -> dict[str, Any]:
        snaps = self.list_snapshots(limit=5)
        return {
            "available": self.is_available(),
            "provider": self.provider_name(),
            "backup_root": str(self._root),
            "tables": list(PRODUCT_STATE_TABLES),
            "snapshots": snaps,
            "last_backup_at": snaps[0]["created_at"] if snaps else None,
            "message": "Logical product-state backup ready.",
            "note": (
                "Archives are JSON+sha256 under DSP_BACKUP_DIR. "
                "Restore requires DSP_BACKUP_RESTORE_CONFIRM=YES. "
                "For physical PostgreSQL dumps use ShellPgDumpBackupAdapter / "
                "scripts/ops/backup_postgres.sh."
            ),
        }

    def list_snapshots(self, *, limit: int = 20) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(self._root.glob("dsp_product_*.json"), reverse=True):
            meta = self._read_sidecar_meta(path)
            items.append(
                {
                    "snapshot_id": path.stem,
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "created_at": meta.get("created_at"),
                    "label": meta.get("label"),
                    "checksum_ok": self._checksum_ok(path),
                }
            )
            if len(items) >= max(1, limit):
                break
        return items

    def create_snapshot(self, *, label: str | None = None) -> dict[str, Any]:
        if not self.is_available():
            return {"ok": False, "available": False, "message": "Database unavailable."}
        self._ensure_schema()
        stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
        safe_label = _safe_label(label)
        snapshot_id = f"dsp_product_{stamp}" + (f"_{safe_label}" if safe_label else "")
        tables: dict[str, list[dict[str, Any]]] = {}
        for name in PRODUCT_STATE_TABLES:
            if name in (
                "api_report_records",
                "api_export_records",
            ) and not self._table_exists(name):
                continue
            try:
                rows = self._db.fetchall(f"SELECT * FROM {name}")
                tables[name] = [_serialize_row(r) for r in rows]
            except Exception as exc:
                if name in (
                    "api_report_records",
                    "api_export_records",
                ) and _is_table_missing_error(exc):
                    continue
                raise

        archive = {
            "format": _FORMAT,
            "created_at": datetime.now(tz=UTC).isoformat(),
            "label": label,
            "tables": tables,
            "table_names": list(tables.keys()),
        }
        path = self._root / f"{snapshot_id}.json"
        payload = json.dumps(archive, separators=(",", ":"), sort_keys=True)
        path.write_text(payload, encoding="utf-8")
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        (self._root / f"{snapshot_id}.json.sha256").write_text(
            f"{digest}  {path.name}\n", encoding="utf-8"
        )
        if path.stat().st_size < 64:
            path.unlink(missing_ok=True)
            return {
                "ok": False,
                "available": True,
                "message": "Backup archive too small; refused.",
            }
        return {
            "ok": True,
            "available": True,
            "provider": self.provider_name(),
            "snapshot_id": snapshot_id,
            "path": str(path),
            "sha256": digest,
            "tables": {k: len(v) for k, v in tables.items()},
            "bytes": path.stat().st_size,
        }

    def restore_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        if os.environ.get(RESTORE_CONFIRM_ENV, "").strip().upper() != "YES":
            return {
                "ok": False,
                "available": self.is_available(),
                "message": (
                    f"Restore refused: set {RESTORE_CONFIRM_ENV}=YES "
                    "(trusted operator control only)."
                ),
            }
        path = self._resolve_snapshot_path(snapshot_id)
        if path is None:
            return {
                "ok": False,
                "available": True,
                "message": "Snapshot not found or path rejected.",
            }
        if not self._checksum_ok(path):
            return {
                "ok": False,
                "available": True,
                "message": "Checksum verification failed; restore refused.",
            }
        try:
            archive = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "available": True,
                "message": f"Archive unreadable: {exc}",
            }
        if not isinstance(archive, dict) or archive.get("format") != _FORMAT:
            return {
                "ok": False,
                "available": True,
                "message": "Unsupported or untrusted archive format.",
            }
        tables = archive.get("tables")
        if not isinstance(tables, dict):
            return {
                "ok": False,
                "available": True,
                "message": "Archive missing tables map.",
            }

        unexpected = [t for t in tables if t not in PRODUCT_STATE_TABLES]
        if unexpected:
            return {
                "ok": False,
                "available": True,
                "message": f"Archive contains unknown tables: {unexpected}",
            }

        missing_required = [t for t in LEGACY_PRODUCT_STATE_TABLES if t not in tables]
        if missing_required:
            return {
                "ok": False,
                "available": True,
                "message": f"Incomplete archive; missing tables: {missing_required}",
            }

        declared_names = archive.get("table_names")
        if isinstance(declared_names, list):
            missing_declared = [t for t in declared_names if t not in tables]
            if missing_declared:
                return {
                    "ok": False,
                    "available": True,
                    "message": f"Incomplete archive; missing declared tables: {missing_declared}",
                }

        new_tables = ("api_report_records", "api_export_records")
        has_new_in_payload = any(t in tables for t in new_tables)
        has_new_declared = isinstance(declared_names, list) and any(
            t in declared_names for t in new_tables
        )
        if has_new_in_payload or has_new_declared:
            missing_new = [t for t in new_tables if t not in tables]
            if missing_new:
                return {
                    "ok": False,
                    "available": True,
                    "message": f"Incomplete modern archive; missing tables: {missing_new}",
                }
            try:
                missing_in_db = [t for t in new_tables if not self._table_exists(t)]
            except Exception as exc:
                return {
                    "ok": False,
                    "available": True,
                    "message": f"Database inspection failed: {exc}",
                }
            if missing_in_db:
                return {
                    "ok": False,
                    "available": True,
                    "message": (
                        f"Target database missing required record tables: {missing_in_db}. "
                        "These tables must be explicitly provisioned via migrations or schema initialization before restore."
                    ),
                }

        self._ensure_schema()
        restored: dict[str, int] = {}
        tables_to_restore = [t for t in PRODUCT_STATE_TABLES if t in tables]

        def _execute_restore(target: Any) -> None:
            for name in tables_to_restore:
                rows = tables.get(name) or []
                if not isinstance(rows, list):
                    raise ValueError(f"Corrupt table payload: {name}")
                target.execute(f"DELETE FROM {name}")
                for row in rows:
                    if not isinstance(row, dict):
                        raise ValueError(f"Corrupt row in {name}")
                    self._insert_row(target, name, row)
                restored[name] = len(rows)

        try:
            if hasattr(self._db, "transaction") and callable(self._db.transaction):
                with self._db.transaction() as txn:
                    _execute_restore(txn)
            else:
                _execute_restore(self._db)
        except ValueError as exc:
            return {
                "ok": False,
                "available": True,
                "message": str(exc),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "available": True,
                "message": f"Restore failed: {exc}",
            }

        return {
            "ok": True,
            "available": True,
            "provider": self.provider_name(),
            "snapshot_id": path.stem,
            "path": str(path),
            "tables": restored,
            "message": "Logical product-state restore completed.",
        }

    def _table_exists(self, table_name: str) -> bool:
        """Check whether a table exists in the target database without mutating schema.

        Distinguishes demonstrably missing tables from database connection,
        permission, and unexpected query failures.
        """
        if not re.match(r"^[a-z0-9_]+$", table_name):
            raise ValueError(f"Invalid table identifier: {table_name}")

        target: Any = self._db
        while True:
            unwrapped = False
            for attr in ("_inner", "_db", "db", "_target"):
                if hasattr(target, attr) and getattr(target, attr) is not target:
                    target = getattr(target, attr)
                    unwrapped = True
                    break
            if not unwrapped:
                break

        if hasattr(target, "_tables") and isinstance(target._tables, dict):
            try:
                self._db.fetchall(f"SELECT 1 FROM {table_name} WHERE 1=0")
            except Exception as exc:
                if not _is_table_missing_error(exc):
                    raise
            return table_name in target._tables

        try:
            self._db.fetchall(f"SELECT 1 FROM {table_name} WHERE 1=0")
            return True
        except Exception as exc:
            if _is_table_missing_error(exc):
                return False
            raise

    def _ensure_schema(self) -> None:
        """Ensure baseline legacy product state tables exist."""
        for table in (
            "enterprise_snapshots",
            "saas_overlay_snapshots",
            "research_workspace_snapshots",
            "api_report_snapshots",
        ):
            self._db.execute(_SNAPSHOT_DDL.format(table=table))
        self._db.execute(_AUDIT_DDL)

    def ensure_record_tables_schema(self) -> None:
        """Explicit schema initialization for report and export record tables.

        Operational requirement:
        Record table schemas (api_report_records, api_export_records) are not created
        implicitly during adapter construction (__init__). Call this method explicitly
        when bootstrapping local environments or test fixtures without running external migrations.
        In staging and production, these tables must be created via standard database migrations.
        """
        self._db.execute(_REPORT_RECORDS_DDL)
        self._db.execute(_EXPORT_RECORDS_DDL)

    def ensure_schema(self, *, include_records: bool = False) -> None:
        """Ensure durable tables exist in the database.

        By default, only ensures baseline legacy snapshot and audit tables.
        Set include_records=True or call ensure_record_tables_schema() to explicitly
        initialize api_report_records and api_export_records.
        """
        self._ensure_schema()
        if include_records:
            self.ensure_record_tables_schema()

    def _resolve_snapshot_path(self, snapshot_id: str) -> Path | None:
        raw = str(snapshot_id or "").strip()
        if not raw:
            return None
        # Accept bare id or filename; reject path traversal.
        name = Path(raw).name
        if name.endswith(".json"):
            stem = name[: -len(".json")]
        else:
            stem = name
        if not _SNAPSHOT_ID_RE.match(stem):
            return None
        path = (self._root / f"{stem}.json").resolve()
        try:
            path.relative_to(self._root)
        except ValueError:
            return None
        if not path.is_file():
            return None
        return path

    def _checksum_ok(self, path: Path) -> bool:
        side = Path(str(path) + ".sha256")
        if not side.is_file():
            return False
        try:
            expected = side.read_text(encoding="utf-8").strip().split()[0]
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            return expected == actual
        except Exception:  # noqa: BLE001
            return False

    def _read_sidecar_meta(self, path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    "created_at": data.get("created_at"),
                    "label": data.get("label"),
                }
        except Exception:  # noqa: BLE001
            pass
        return {}

    def _insert_row(self, db: Any, table: str, row: dict[str, Any]) -> None:
        cols = list(row.keys())
        if not cols:
            return
        allowed_cols = TABLE_ALLOWED_COLUMNS.get(table)
        if allowed_cols is not None:
            unknown_cols = [c for c in cols if c not in allowed_cols]
            if unknown_cols:
                raise ValueError(f"Unknown column(s) for table {table}: {unknown_cols}")
        for c in cols:
            if not re.match(r"^[a-z0-9_]+$", c):
                raise ValueError(f"Invalid column identifier: {c}")
        col_sql = ", ".join(cols)
        placeholders = ", ".join("%s" for _ in cols)
        params: list[Any] = []
        for c in cols:
            val = row[c]
            if isinstance(val, dict) and set(val.keys()) == {"__b64__"}:
                val = val["__b64__"]
            elif isinstance(val, (dict, list)):
                val = json.dumps(val, sort_keys=True)
            params.append(val)
        db.execute(
            f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})",
            tuple(params),
        )


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, (bytes, bytearray)):
            # Opaque binary — store as ASCII base64 string marker.
            import base64

            out[str(key)] = {"__b64__": base64.b64encode(bytes(value)).decode("ascii")}
        else:
            out[str(key)] = value
    return out


def _safe_label(label: str | None) -> str:
    if not label:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(label).strip())[:40]
    return cleaned.strip("_")


def _is_table_missing_error(exc: BaseException) -> bool:
    """Return True only if exc demonstrably indicates that a table/relation does not exist."""
    if exc.__class__.__name__ == "UndefinedTable":
        return True
    if (
        getattr(exc, "sqlstate", None) == "42P01"
        or getattr(exc, "pgcode", None) == "42P01"
    ):
        return True
    msg = str(exc).lower()
    forbidden_indicators = (
        "connect",
        "connection",
        "network",
        "timeout",
        "refused",
        "closed",
        "permission",
        "denied",
        "privilege",
        "password",
        "authentication",
        "lock",
        "deadlock",
    )
    if any(indicator in msg for indicator in forbidden_indicators):
        return False
    if "no such table" in msg:
        return True
    if ("relation" in msg or "table" in msg) and (
        "does not exist" in msg or "not found" in msg
    ):
        return True
    return False
