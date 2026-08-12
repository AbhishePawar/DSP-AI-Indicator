# Backup & Recovery — P1.1

**Scope:** Operational data stores (PostgreSQL when enabled).  
**RC1 note:** Stateless / ephemeral deployments without Postgres recover by **redeploy + re-auth**; RPO is not applicable to in-memory caches.

## Objectives

| Metric | Target | Notes |
|---|---|---|
| **RPO** (Recovery Point Objective) | **≤ 24 hours** | Daily logical `pg_dump` (gzip + sha256). Tighten to ≤1h with continuous WAL/PITR on managed Postgres. |
| **RTO** (Recovery Time Objective) | **≤ 4 hours** | Restore dump → verify `/health/ready` → run `production_smoke.py` → resume traffic. |

## Backup creation

```bash
export DSP_DATABASE_URL='postgresql://…'
export DSP_BACKUP_DIR=/var/backups/dsp
chmod +x scripts/ops/backup_postgres.sh
./scripts/ops/backup_postgres.sh
```

Outputs:

- `dsp_pg_<UTC>.sql.gz`
- `dsp_pg_<UTC>.sql.gz.sha256`

Schedule via cron / cloud scheduler (recommended: daily 18:30 IST).

## Integrity

- Archive size must be ≥ 64 bytes (script fails otherwise)
- SHA-256 sidecar verified on restore

## Restore procedure

1. Put API in maintenance (stop web or drain load balancer).
2. Confirm target DB URL (never restore to wrong environment).
3. `./scripts/ops/restore_postgres.sh /var/backups/dsp/dsp_pg_….sql.gz`
4. Start API; wait for `GET /health/ready` → 200.
5. `DSP_SMOKE_API_BASE_URL=… DSP_SMOKE_WEB_BASE_URL=… python scripts/ops/production_smoke.py`
6. Spot-check login + one research analyse (manual).

## Recovery checklist

- [ ] Backup artifact and checksum located
- [ ] Environment identity confirmed (prod vs staging)
- [ ] Secrets still valid (JWT, DB password)
- [ ] Restore completed without SQL errors
- [ ] Health live + ready green
- [ ] Metrics endpoint responding
- [ ] Smoke script PASS
- [ ] Incident timeline recorded

## What is not backed up by this script

- Redis cache (rehydratable)
- Browser localStorage / disclaimer acknowledgements
- Object-storage artifacts (use provider versioning / bucket replication)
- Container images (use registry tags `dsp-api:1.3.0`, `dsp-web:1.7.0`)
