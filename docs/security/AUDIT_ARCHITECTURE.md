# Audit Architecture (EPIC-016)

## Purpose

Append-only enterprise audit trail for commercial / trust operations. Supports CV-006 (traceability) and CV-007 (auditability).

## Record shape

`AuditRecord` fields:

| Field | Description |
|---|---|
| `event_id` | Unique immutable id |
| `org_id` | Tenant scope (nullable for platform events) |
| `actor_user_id` | Acting principal |
| `action` | Verb (e.g. `org.create`, `api_key.rotate`) |
| `resource_type` / `resource_id` | Target resource |
| `created_at` | UTC ISO timestamp |
| `before` / `after` | Optional state snapshots |
| `ip_address` | Optional client IP hint |
| `correlation_id` | Request correlation |
| `metadata` | Additional structured context |
| `immutable` | Always `true` |

## Storage

- Working set: `EnterpriseService` → store `audit` list
- Durable: `DatabaseEnterpriseStore` table `enterprise_audit_log`
- Inserts are append-only — existing rows are never updated or deleted by flush
- `mutate_audit_forbidden()` always raises `ForbiddenError`

## Guarantees

1. No overwrite of historical events
2. Rehydrate preserves audit order by `created_at`
3. Snapshot wipe of mutable enterprise state does **not** wipe durable audit rows
4. Missing data surfaces as honest empty lists / `No audit records.`

## Non-goals

- Cryptographic hash chaining / WORM media (future hardening)
- Cross-region replication
- SIEM shipping adapters (future)
