# Runbook — Service Outage

**Epic:** P6.1

## Symptoms

`/health` or `/health/ready` failing; web 5xx; login failures; analyse timeouts across tenants.

## Immediate actions

1. Confirm from two networks / status of compose or k8s pods.
2. Check Postgres, Redis (if any), disk, CPU, recent deploy.
3. If deploy-correlated → [ROLLBACK.md](./ROLLBACK.md).
4. If DB corruption / loss → [BACKUP_RECOVERY.md](./BACKUP_RECOVERY.md).
5. Enable maintenance page (`/maintenance`) if web is up but API is not.
6. Notify Support; severity S1.

## Verification

```text
GET /health
GET /health/ready
GET /metrics   # optional
```

Run `scripts/ops` smoke / certify scripts used in P1.1 when available.

## Exit criteria

Ready probe green for ≥15 minutes; sample login + sample analysis (`AAPL`) succeeds; Support notified of restoration.
