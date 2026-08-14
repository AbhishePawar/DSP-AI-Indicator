# Release Notes — DSP Web 1.9.0 / Platform 1.5.0 (P5.2 RC)

**Channel:** Release Candidate (`rc`)  
**API contract:** `v1.0.0-rc1` (unchanged)  
**Date:** 2026-07-29

## Highlights

- Closed beta stabilisation complete (P5.2).
- Invite gate fails closed in production when the beta API is unreachable.
- Beta programme snapshot export/import for ops backup and reseed.
- Admin Closed Beta panel shows RC assessment and snapshot export.
- Issue dispositions: Fixed / Deferred / Rejected / Known limitation.

## What did not change

- Analysis pipeline, valuation engines, recommendation engine, AI Committee
- Analyse API contracts and deterministic scoring behaviour
- No new analytical product features

## Upgrade notes

1. Bump deploy images to `dsp-api:1.5.0` / `dsp-web:1.9.0`.
2. Export a beta snapshot before restarting API processes that hold invites.
3. Keep `DSP_CLOSED_BETA` / `NEXT_PUBLIC_CLOSED_BETA` aligned with your RC posture.
4. Review `docs/P5_2_BETA_STABILISATION.md` before promoting beyond RC.

## Known issues

See `docs/KNOWN_LIMITATIONS.md` (P5.2 section) and the P5.2 issue table.
