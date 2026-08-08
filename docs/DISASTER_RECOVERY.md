# Disaster Recovery — EPIC-P7.4

**Scope:** Operational data (PostgreSQL), images, config.  
**Out of scope:** Analytical engines, Redis cache contents (rehydratable), browser state.

## Objectives

| Metric | Target | Stretch (managed Postgres) |
|---|---|---|
| **RPO** | **≤ 24 hours** (daily full logical dump) | ≤ 1 hour with WAL / PITR |
| **RTO** | **≤ 4 hours** (restore → ready → smoke) | ≤ 1 hour with rehearsed runbook |

Incremental dumps (hourly) reduce practical RPO when WAL/PITR is unavailable:

| Mode | Script | Cadence |
|---|---|---|
| Full backup | `scripts/ops/backup_postgres.sh` / `scripts/backup_database.sh` | Daily 18:30 IST |
| Incremental (frequent dump) | `scripts/ops/backup_postgres_incremental.sh` | Hourly (retain 48h) |
| Restore | `scripts/ops/restore_postgres.sh` / `scripts/restore_database.sh` | On demand |
| Rollback (app) | `scripts/rollback_production.sh` | Bad deploy |
| Recovery validation | `scripts/ops/validate_recovery.py` + `production_smoke.py` | After every restore |

## Full backup

```bash
export DSP_DATABASE_URL='postgresql://…'
export DSP_BACKUP_DIR=/var/backups/dsp
./scripts/backup_database.sh
```

Artifacts: `dsp_pg_<UTC>.sql.gz` + `.sha256`.

## Incremental backup

Hourly logical dumps tagged `incr` (still logical dumps — not physical WAL). Use when continuous archiving is not yet enabled:

```bash
./scripts/ops/backup_postgres_incremental.sh
```

Retention: keep last 48 incremental files + last 14 full dumps (operator cron policy).

## Restore

1. Declare incident; stop write traffic (maintenance / drain).
2. Confirm environment identity (prod vs staging).
3. `./scripts/restore_database.sh /var/backups/dsp/<artifact>.sql.gz`
4. Wait for `GET /health/ready` → 200.
5. `python scripts/ops/validate_recovery.py`
6. `python scripts/ops/production_smoke.py`
7. Resume traffic; record RTO clock stop.

## Rollback

Image/tag rollback without DB restore when the failure is application-only:

```bash
./scripts/rollback_production.sh
```

If schema/data corruption: restore dump **before** rolling images forward again.

## Recovery validation

`validate_recovery.py` checks:

- `/health/live` and `/health/ready`
- `/metrics` reachable
- optional Postgres connectivity when `DSP_DATABASE_URL` set
- optional Redis PING when `DSP_REDIS_URL` set

## Drill schedule (CONDITION)

| Drill | Frequency |
|---|---|
| Backup integrity (sha256) | Weekly |
| Staging restore | Monthly |
| Full prod-like RTO clock | Quarterly |

## Related

- `docs/ops/BACKUP_AND_RECOVERY.md`
- `docs/ops/runbooks/BACKUP_RECOVERY.md`
- `docs/OPERATIONS_RUNBOOK.md`
