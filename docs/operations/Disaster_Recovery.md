# Disaster Recovery (EPIC-017)

Builds on `docs/ops/BACKUP_AND_RECOVERY.md`. **No schema redesign.**

## Objectives

| Metric | Target | Notes |
|---|---|---|
| **RPO** | ≤ 24h (logical dumps); ≤ 1h with managed PITR | Tighten via continuous WAL |
| **RTO** | ≤ 4h | Restore → health → smoke → traffic |

| Tier | Workload | RPO / RTO |
|---|---|---|
| Critical | Auth, sessions, enterprise durable state (Postgres) | RPO ≤24h / RTO ≤4h |
| Degraded OK | Redis cache / rate-limit counters | Rebuild; RPO N/A |
| Stateless | API/Web pods | Redeploy from registry |

## Backup schedule

| Asset | Method | Schedule | Retention |
|---|---|---|---|
| Postgres | `scripts/ops/backup_postgres.sh` (gzip + sha256) | Daily 18:30 IST | 30 days |
| Postgres WAL / PITR | Managed service continuous archive | Continuous | Per cloud policy (≥7 days) |
| Redis | AOF in compose; not primary DR | — | Rehydratable |
| Images | Registry tags immutable | On release | Keep N-2 |
| Secrets | Vault / Secrets Manager versioning | On change | Per policy |
| Object storage | Bucket versioning / cross-region | Provider | Per policy |

## Backup procedure

```bash
export DSP_DATABASE_URL='postgresql://…'
export DSP_BACKUP_DIR=/var/backups/dsp
./scripts/ops/backup_postgres.sh
# Outputs: dsp_pg_<UTC>.sql.gz (+ .sha256)
```

Incremental helper (when used): `scripts/ops/backup_postgres_incremental.sh`.

## Restore validation

**Staging restore drill (monthly recommended):**

1. Provision empty staging DB
2. `./scripts/ops/restore_postgres.sh /path/to/dsp_pg_….sql.gz`
3. `python scripts/ops/validate_recovery.py` (if configured) or:
   - `GET /health/ready` → 200
   - `python scripts/ops/production_smoke.py`
4. Record drill result in change log

**Production restore (incident):**

1. Declare SEV-1; freeze writes / enable maintenance
2. Confirm environment identity (never restore prod dump to wrong cluster without intent)
3. Restore dump or PITR to timestamp (RPO)
4. Rotate app secrets if compromise-related
5. Start API/Web; readiness; smoke
6. Resume traffic; postmortem

## PITR

Prefer managed Postgres:

- AWS RDS: automated backups + PITR
- GCP Cloud SQL: point-in-time recovery
- Azure Database for PostgreSQL: PITR

In-cluster StatefulSet in `deploy/k8s/base/postgres.yaml` is **reference only** — enable WAL archiving or migrate to managed before relying on PITR.

## What is not covered by DB restore

- Redis ephemeral state
- In-flight jobs (replay from DLQ / re-enqueue)
- Browser local state
- Fabricated analytics (CV-001) — N/A; engines unchanged

## Incident response linkage

See [Incident_Response.md](./Incident_Response.md) for roles, comms, and severity.
