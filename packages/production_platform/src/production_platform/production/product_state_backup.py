"""P1-08 — logical backup/restore of durable multi-tenant product state.

Archives are JSON + SHA-256 (not pickle). Pickle payloads that already live
inside report snapshot rows are treated as opaque TEXT and only decoded by the
application store after a trusted operator restore.
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
    "PRODUCT_STATE_TABLES",
    "LogicalProductStateBackupAdapter",
    "RESTORE_CONFIRM_ENV",
]

RESTORE_CONFIRM_ENV = "DSP_BACKUP_RESTORE_CONFIRM"
_FORMAT = "dsp_product_state_v1"
_SNAPSHOT_ID_RE = re.compile(r"^dsp_product_\d{8}T\d{6}Z(?:_[A-Za-z0-9_-]+)?$")

PRODUCT_STATE_TABLES: tuple[str, ...] = (
    "enterprise_snapshots",
    "enterprise_audit_log",
    "saas_overlay_snapshots",
    "research_workspace_snapshots",
    "api_report_snapshots",
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
            rows = self._db.fetchall(f"SELECT * FROM {name}")
            tables[name] = [_serialize_row(r) for r in rows]

        archive = {
            "format": _FORMAT,
            "created_at": datetime.now(tz=UTC).isoformat(),
            "label": label,
            "tables": tables,
            "table_names": list(PRODUCT_STATE_TABLES),
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
        missing = [t for t in PRODUCT_STATE_TABLES if t not in tables]
        if missing:
            return {
                "ok": False,
                "available": True,
                "message": f"Incomplete archive; missing tables: {missing}",
            }

        self._ensure_schema()
        restored: dict[str, int] = {}
        for name in PRODUCT_STATE_TABLES:
            rows = tables.get(name) or []
            if not isinstance(rows, list):
                return {
                    "ok": False,
                    "available": True,
                    "message": f"Corrupt table payload: {name}",
                }
            self._db.execute(f"DELETE FROM {name}")
            for row in rows:
                if not isinstance(row, dict):
                    return {
                        "ok": False,
                        "available": True,
                        "message": f"Corrupt row in {name}",
                    }
                self._insert_row(name, row)
            restored[name] = len(rows)

        return {
            "ok": True,
            "available": True,
            "provider": self.provider_name(),
            "snapshot_id": path.stem,
            "path": str(path),
            "tables": restored,
            "message": "Logical product-state restore completed.",
        }

    def _ensure_schema(self) -> None:
        for table in (
            "enterprise_snapshots",
            "saas_overlay_snapshots",
            "research_workspace_snapshots",
            "api_report_snapshots",
        ):
            self._db.execute(_SNAPSHOT_DDL.format(table=table))
        self._db.execute(_AUDIT_DDL)

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

    def _insert_row(self, table: str, row: dict[str, Any]) -> None:
        cols = list(row.keys())
        if not cols:
            return
        col_sql = ", ".join(cols)
        val_sql = ", ".join(_sql_literal(row[c]) for c in cols)
        self._db.execute(f"INSERT INTO {table} ({col_sql}) VALUES ({val_sql})")


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, (bytes, bytearray)):
            # Opaque binary — store as ASCII base64 string marker.
            import base64

            out[str(key)] = {
                "__b64__": base64.b64encode(bytes(value)).decode("ascii")
            }
        else:
            out[str(key)] = value
    return out


def _sql_literal(value: Any) -> str:
    if isinstance(value, dict) and set(value.keys()) == {"__b64__"}:
        # Restore opaque binary as the original base64 text column content
        # when stores keep TEXT payloads; keep string form for InMemory dialect.
        value = value["__b64__"]
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _safe_label(label: str | None) -> str:
    if not label:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(label).strip())[:40]
    return cleaned.strip("_")
