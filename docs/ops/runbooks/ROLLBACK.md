# Runbook — Rollback

**Epic:** P6.1

## When

Failed deploy, rising 5xx, auth breakage, or incorrect version channel after release.

## Steps

1. Announce rollback in incident channel (S1/S2 as appropriate).
2. Redeploy previous known-good image tags (e.g. `dsp-api:1.5.0` / `dsp-web:1.9.0`).
3. Restore config / env from last known-good if changed.
4. Re-import beta snapshot if invite state was lost.
5. Verify health, ready, login, sample analysis.
6. Keep broken build quarantined; file defect; do not re-promote without fix.

## Notes

Prefer image rollback over hot-patching engines during commercial incidents. Database roll-forward only with explicit DBA approval.
