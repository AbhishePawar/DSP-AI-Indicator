"""Backup & recovery ports — interfaces only. Never fabricate backups."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "BACKUP_UNAVAILABLE",
    "BackupPort",
    "NullBackupAdapter",
    "build_backup_adapter",
    "SecretRotationHookPort",
    "NullSecretRotationHook",
    "VaultSecretsProviderPort",
    "NullVaultSecretsProvider",
]

BACKUP_UNAVAILABLE = "Backup provider unavailable."


@runtime_checkable
class BackupPort(Protocol):
    """Provider-neutral backup orchestration. Implementations must not invent snapshots."""

    def provider_name(self) -> str: ...

    def is_available(self) -> bool: ...

    def status(self) -> dict[str, Any]: ...

    def list_snapshots(self, *, limit: int = 20) -> list[dict[str, Any]]: ...

    def create_snapshot(self, *, label: str | None = None) -> dict[str, Any]: ...

    def restore_snapshot(self, snapshot_id: str) -> dict[str, Any]: ...


class NullBackupAdapter:
    """Default — honest unavailable until a real provider is wired."""

    def provider_name(self) -> str:
        return "null"

    def is_available(self) -> bool:
        return False

    def status(self) -> dict[str, Any]:
        return {
            "available": False,
            "provider": self.provider_name(),
            "message": BACKUP_UNAVAILABLE,
            "snapshots": [],
            "last_backup_at": None,
            "note": "Use scripts/ops/backup_postgres.sh until a BackupPort adapter is configured.",
        }

    def list_snapshots(self, *, limit: int = 20) -> list[dict[str, Any]]:
        _ = limit
        return []

    def create_snapshot(self, *, label: str | None = None) -> dict[str, Any]:
        _ = label
        return {
            "ok": False,
            "available": False,
            "message": BACKUP_UNAVAILABLE,
        }

    def restore_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        _ = snapshot_id
        return {
            "ok": False,
            "available": False,
            "message": BACKUP_UNAVAILABLE,
        }


def build_backup_adapter(
    *,
    database: Any | None = None,
    backup_root: str | Path | None = None,
) -> Any:
    """P1-08 — select BackupPort implementation.

    ``DSP_BACKUP_ADAPTER``:
    - ``null`` (default): honest unavailable
    - ``logical``: durable product-state JSON dump via DatabasePort
    - ``shell``: scripts/ops pg_dump wrapper (requires tools + DSN)
    - ``auto``: shell when available, else logical when database present, else null
    """
    mode = (os.environ.get("DSP_BACKUP_ADAPTER") or "null").strip().lower()
    if mode in {"", "null", "none", "off"}:
        return NullBackupAdapter()

    if mode in {"shell", "pg_dump", "postgres"}:
        from production_platform.production.shell_pg_backup import (
            ShellPgDumpBackupAdapter,
        )

        return ShellPgDumpBackupAdapter(backup_root=backup_root)

    if mode == "logical":
        if database is None:
            return NullBackupAdapter()
        from production_platform.production.product_state_backup import (
            LogicalProductStateBackupAdapter,
        )

        return LogicalProductStateBackupAdapter(database, backup_root=backup_root)

    if mode == "auto":
        from production_platform.production.shell_pg_backup import (
            ShellPgDumpBackupAdapter,
        )

        shell = ShellPgDumpBackupAdapter(backup_root=backup_root)
        if shell.is_available():
            return shell
        if database is not None:
            from production_platform.production.product_state_backup import (
                LogicalProductStateBackupAdapter,
            )

            return LogicalProductStateBackupAdapter(database, backup_root=backup_root)
        return NullBackupAdapter()

    return NullBackupAdapter()


@runtime_checkable
class SecretRotationHookPort(Protocol):
    """Hook surface for secret rotation — never stores secrets itself."""

    def provider_name(self) -> str: ...

    def is_available(self) -> bool: ...

    def rotation_status(self) -> dict[str, Any]: ...

    def notify_rotated(self, secret_name: str) -> dict[str, Any]: ...


class NullSecretRotationHook:
    def provider_name(self) -> str:
        return "null"

    def is_available(self) -> bool:
        return False

    def rotation_status(self) -> dict[str, Any]:
        return {
            "available": False,
            "provider": self.provider_name(),
            "message": "Secret rotation provider unavailable.",
            "note": "Wire Vault/cloud KMS rotation webhooks; never hardcode secrets.",
        }

    def notify_rotated(self, secret_name: str) -> dict[str, Any]:
        return {
            "ok": False,
            "secret_name": secret_name,
            "message": "Secret rotation provider unavailable.",
        }


@runtime_checkable
class VaultSecretsProviderPort(Protocol):
    """Vault / external secrets provider interface."""

    def provider_name(self) -> str: ...

    def is_available(self) -> bool: ...

    def status(self) -> dict[str, Any]: ...


class NullVaultSecretsProvider:
    def provider_name(self) -> str:
        return "null"

    def is_available(self) -> bool:
        return False

    def status(self) -> dict[str, Any]:
        return {
            "available": False,
            "provider": self.provider_name(),
            "message": "Vault secrets provider unavailable.",
            "note": "Use EnvSecretsPort / DSP_* env validation until Vault is configured.",
        }
