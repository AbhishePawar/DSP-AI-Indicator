# Backup & Recovery (RC1 Milestone 10)

This document is the RC1 product entrypoint. Detailed ops scripts remain under
[`docs/ops/BACKUP_AND_RECOVERY.md`](ops/BACKUP_AND_RECOVERY.md).

## Interfaces

| Interface | Location | Default |
|---|---|---|
| `BackupPort` | `production_platform.production.backup` | `NullBackupAdapter` unless `DSP_BACKUP_ADAPTER` is set |
| Adapters (P1-08) | `logical` / `shell` / `auto` via `build_backup_adapter` | Logical product-state JSON+sha256; shell wraps `pg_dump` scripts |
| HTTP status | `GET /ops/backup` | Honest unavailable by default; Non-Null when adapter configured |
| Shell backups | `scripts/ops/backup_postgres.sh` | Operational |
| Isolation drill | `scripts/ops/restore_drill_isolation.py` | Ownership + tenant isolation after restore |

**Never fabricate backup snapshots in software.** Restore requires `DSP_BACKUP_RESTORE_CONFIRM=YES` and checksum verification.

## Configuration backup

- Export Helm values / Kustomize overlays to secure storage
- Keep `secrets.example.yaml` templates — never commit live secrets
- Feature flags / env profiles via `scripts/validate_env.py`

## Export backup

- Research / report exports remain via Export Engine
- Org commercial artifacts via enterprise store durability (when DB attached)

## Recovery steps (summary)

1. Halt writers if corruption suspected
2. Restore Postgres via `scripts/ops/restore_postgres.sh` (or provider tool)
3. Validate with `scripts/ops/validate_recovery.py` when available
4. Confirm `/health/ready` and `/ops/dependencies`
5. Confirm `/ops/version` matches intended release

## RPO / RTO

Document org-specific RPO/RTO with the chosen BackupPort provider. Until a
provider is configured, treat shell backups as the operational path and report
backup status as **Data unavailable.** in product surfaces.
