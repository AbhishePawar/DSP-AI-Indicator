"""P1-08 — BackupPort adapter wrapping scripts/ops pg_dump / restore.

Requires host tools (pg_dump, gzip, psql) and DSP_DATABASE_URL. Never fabricates
backup success when tools or DSN are missing.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from production_platform.production.product_state_backup import RESTORE_CONFIRM_ENV

__all__ = ["ShellPgDumpBackupAdapter"]


class ShellPgDumpBackupAdapter:
    """Physical/logical PostgreSQL dump via repository shell scripts."""

    def __init__(
        self,
        *,
        backup_root: str | Path | None = None,
        repo_root: str | Path | None = None,
    ) -> None:
        root = backup_root or os.environ.get("DSP_BACKUP_DIR") or "./backups"
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        if repo_root is not None:
            self._repo = Path(repo_root).resolve()
        else:
            self._repo = _find_repo_root()
        self._backup_script = self._repo / "scripts" / "ops" / "backup_postgres.sh"
        self._restore_script = self._repo / "scripts" / "ops" / "restore_postgres.sh"

    def provider_name(self) -> str:
        return "shell_pg_dump"

    def is_available(self) -> bool:
        dsn = (os.environ.get("DSP_DATABASE_URL") or os.environ.get("DATABASE_URL") or "").strip()
        if not dsn:
            return False
        if shutil.which("pg_dump") is None or shutil.which("gzip") is None:
            return False
        if not self._backup_script.is_file():
            return False
        # bash required to run the scripts on Windows/Linux alike
        if shutil.which("bash") is None and os.name != "posix":
            # On POSIX the script can be executed directly if +x; still need shell.
            pass
        if os.name == "nt" and shutil.which("bash") is None:
            return False
        return True

    def status(self) -> dict[str, Any]:
        snaps = self.list_snapshots(limit=5)
        return {
            "available": self.is_available(),
            "provider": self.provider_name(),
            "backup_root": str(self._root),
            "snapshots": snaps,
            "last_backup_at": snaps[0].get("created_at") if snaps else None,
            "message": (
                "Shell pg_dump backup ready."
                if self.is_available()
                else "pg_dump/DSN/scripts unavailable."
            ),
            "note": "Uses scripts/ops/backup_postgres.sh and restore_postgres.sh.",
        }

    def list_snapshots(self, *, limit: int = 20) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(self._root.glob("dsp_pg_*.sql.gz"), reverse=True):
            items.append(
                {
                    "snapshot_id": path.name,
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "created_at": _mtime_iso(path),
                    "checksum_ok": self._checksum_ok(path),
                }
            )
            if len(items) >= max(1, limit):
                break
        return items

    def create_snapshot(self, *, label: str | None = None) -> dict[str, Any]:
        _ = label
        if not self.is_available():
            return {
                "ok": False,
                "available": False,
                "message": "Shell pg_dump backup unavailable.",
            }
        env = os.environ.copy()
        env["DSP_BACKUP_DIR"] = str(self._root)
        try:
            completed = subprocess.run(
                self._bash_cmd(self._backup_script),
                check=False,
                capture_output=True,
                text=True,
                env=env,
                cwd=str(self._repo),
            )
        except OSError as exc:
            return {
                "ok": False,
                "available": True,
                "message": f"Failed to invoke backup script: {exc}",
            }
        if completed.returncode != 0:
            return {
                "ok": False,
                "available": True,
                "message": (
                    completed.stderr.strip()
                    or completed.stdout.strip()
                    or "backup_postgres.sh failed"
                ),
            }
        # Script prints archive path on last line
        lines = [ln.strip() for ln in completed.stdout.splitlines() if ln.strip()]
        archive = Path(lines[-1]) if lines else None
        if archive is None or not archive.is_file():
            # Fallback: newest archive in root
            candidates = sorted(self._root.glob("dsp_pg_*.sql.gz"), reverse=True)
            archive = candidates[0] if candidates else None
        if archive is None or not archive.is_file():
            return {
                "ok": False,
                "available": True,
                "message": "Backup script succeeded but archive missing.",
            }
        return {
            "ok": True,
            "available": True,
            "provider": self.provider_name(),
            "snapshot_id": archive.name,
            "path": str(archive),
            "bytes": archive.stat().st_size,
            "sha256": self._file_sha256(archive),
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
        if not self.is_available():
            return {
                "ok": False,
                "available": False,
                "message": "Shell pg_dump restore unavailable.",
            }
        if shutil.which("psql") is None:
            return {
                "ok": False,
                "available": False,
                "message": "psql not found; cannot restore.",
            }
        path = self._resolve_archive(snapshot_id)
        if path is None:
            return {
                "ok": False,
                "available": True,
                "message": "Archive not found or path rejected.",
            }
        if not self._checksum_ok(path):
            return {
                "ok": False,
                "available": True,
                "message": "Checksum verification failed; restore refused.",
            }
        env = os.environ.copy()
        try:
            completed = subprocess.run(
                self._bash_cmd(self._restore_script, str(path)),
                check=False,
                capture_output=True,
                text=True,
                env=env,
                cwd=str(self._repo),
            )
        except OSError as exc:
            return {
                "ok": False,
                "available": True,
                "message": f"Failed to invoke restore script: {exc}",
            }
        if completed.returncode != 0:
            return {
                "ok": False,
                "available": True,
                "message": (
                    completed.stderr.strip()
                    or completed.stdout.strip()
                    or "restore_postgres.sh failed"
                ),
            }
        return {
            "ok": True,
            "available": True,
            "provider": self.provider_name(),
            "snapshot_id": path.name,
            "path": str(path),
            "message": "PostgreSQL restore completed.",
        }

    def _bash_cmd(self, script: Path, *args: str) -> list[str]:
        if os.name == "nt":
            return ["bash", str(script), *args]
        return ["bash", str(script), *args]

    def _resolve_archive(self, snapshot_id: str) -> Path | None:
        name = Path(str(snapshot_id or "").strip()).name
        if not name.startswith("dsp_pg_") or not name.endswith(".sql.gz"):
            return None
        if ".." in name:
            return None
        path = (self._root / name).resolve()
        try:
            path.relative_to(self._root)
        except ValueError:
            return None
        return path if path.is_file() else None

    def _checksum_ok(self, path: Path) -> bool:
        side = Path(str(path) + ".sha256")
        if not side.is_file():
            return False
        try:
            expected = side.read_text(encoding="utf-8").strip().split()[0]
            return expected == self._file_sha256(path)
        except Exception:  # noqa: BLE001
            return False

    @staticmethod
    def _file_sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()


def _mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "scripts" / "ops" / "backup_postgres.sh").is_file():
            return parent
    return Path.cwd().resolve()
