# Beta → Production Migration Plan

**Epic:** P6.1 · Prerequisite: P5.2 RC readiness.

## Objectives

Move invited closed-beta tenants to commercial editions without changing analysis engines or `/api/v1` analyse contracts.

## Phases

### 1. Freeze & inventory

1. Export beta programme snapshot (`GET /admin/beta/snapshot`).
2. Inventory invites, activated users, open issues, feedback themes.
3. Confirm legal pages and disclaimer acknowledgement are current (P4.1).

### 2. Commercial mapping

| Beta cohort | Target edition | Notes |
|---|---|---|
| Individual analysts | Research or Professional trial | Apply usage limits |
| Desk / multi-seat | Professional | Assign seats |
| Institutional pilots | Enterprise sandbox | SSO deferred until contracted |

### 3. Cutover

1. Communicate migration window (email + in-app banner).
2. Disable invitation-only gate **only** after allowlist → account provisioning is complete **or** keep gate and convert invites to paid seats (preferred for controlled GA).
3. Import snapshot on each API node if still using in-memory invite store; schedule durable store before multi-replica GA.
4. Align `DSP_CLOSED_BETA` / `NEXT_PUBLIC_CLOSED_BETA` with intended posture.
5. Verify health, ready, metrics, and sample analysis (`AAPL`).

### 4. Post-migration

1. Monitor support queue and S1/S2 for 72h.
2. Close beta-only feedback channels or redirect to Support.
3. Archive snapshot + RC assessment in release record.
4. Update `PRODUCTION_VERSION_MANIFEST.json` channel when promoting beyond `rc`.

## Rollback

Re-enable closed-beta flags, restore last known-good snapshot, follow [rollback runbook](../ops/runbooks/ROLLBACK.md).

## Non-goals

No engine, valuation, recommendation, AI Committee, or analyse contract changes during migration.
