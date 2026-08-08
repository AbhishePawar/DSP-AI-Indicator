# Runbook — Backup Recovery

**Epic:** P6.1 · Detail: also see `docs/ops/BACKUP_AND_RECOVERY.md`

## Backup

1. Schedule daily Postgres dump via `scripts/ops/backup_postgres.sh` (or cloud snapshot).
2. Export beta programme snapshot before API restarts (`GET /admin/beta/snapshot`).
3. Store off-host with retention ≥30 days (RC) / per Enterprise MSA.

## Restore (Postgres)

1. Declare incident; stop writers if possible.
2. Restore latest verified backup to staging first when time allows.
3. Promote restore to production per change window.
4. Re-import beta snapshot if invite store is in-memory.
5. Run health + smoke; sample analysis.

## RPO / RTO (RC targets)

| Metric | Target |
|---|---|
| RPO | ≤24h (daily backup) |
| RTO | ≤4h for Postgres restore drill |

Tighten under Enterprise contracts.
