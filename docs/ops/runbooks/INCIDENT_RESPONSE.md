# Runbook — Incident Response

**Epic:** P6.1 · Owner: On-call engineer + Support L1

## When to use

Any unexpected degradation, error spike, or customer-reported outage affecting availability, correctness presentation, or security.

## Severity

Use [Customer Support](../../commercial/CUSTOMER_SUPPORT.md) S1–S4. Security → [SECURITY_INCIDENT.md](./SECURITY_INCIDENT.md).

## Steps

1. **Detect** — alerts from `/health`, `/health/ready`, `/metrics`, logs, or support ticket.
2. **Acknowledge** — page on-call; open incident channel; set status page (if configured).
3. **Triage** — blast radius (API vs web vs DB), recent deploys, rate-limit / auth errors.
4. **Contain** — feature flags / closed-beta gate / traffic shed; do **not** change engine code mid-incident unless approved hotfix.
5. **Mitigate** — rollback ([ROLLBACK.md](./ROLLBACK.md)) or restore ([BACKUP_RECOVERY.md](./BACKUP_RECOVERY.md)) as needed.
6. **Communicate** — Support updates customers; avoid inventing root cause.
7. **Resolve** — verify health + smoke; clear status.
8. **Postmortem** — within 5 business days for S1/S2; file actions; no blame.

## Evidence to capture

Request IDs, deploy SHA/tag, metric screenshots, customer impact count. Never store research payloads or secrets in tickets.
