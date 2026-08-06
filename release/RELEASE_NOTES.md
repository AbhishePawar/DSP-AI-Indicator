# Release Notes — DSP AI Indicator

**Date:** 2026-07-29  
**Frontend:** `2.0.0`  
**Backend:** `dsp_platform 2.0.0`  
**API contract:** `v1.0.0`  
**Channel:** `ga-candidate`  
**Milestone:** `P8.0`

## Summary

P8.0 GA certification and release freeze only. No analytical or API behaviour changes. Live ops conditions remain.

## Frontend 2.0.0

### Added

- GA architecture certification, technical debt register, release freeze policy
- `docs/P8_GENERAL_AVAILABILITY.md` and `scripts/ops/certify_p8.py`
- Platform audit of P1–P7 with living conditions retained

### Changed

- Frontend **2.0.0** · Backend **2.0.0** · channel **`ga-candidate`** · API contract label remains **v1.0.0**
- Engineering enters **RELEASE FREEZE** (hotfixes only)

### Unchanged

- Analytical engines and analyse behaviour


## Backend 2.0.0

_See frontend section (joint commercial channel notes)._

## Compatibility

- Analytical engines and `/api/v1` analyse behaviour are **unchanged**.
- Thin client preserved — no browser-side valuation or AI reasoning.
- Research Mode / User Trust Standard remain in force.

## Upgrade

1. Validate: `python scripts/release/validate_release.py`
2. Deploy: `./scripts/deploy_production.sh` (P7.0 stack)
3. Smoke health endpoints and HTTPS
4. Archive `release/` artifacts with checksums

## Links

- `docs/VERSION_MATRIX.md`
- `docs/P7_PRODUCTION_DEPLOYMENT.md`
- `docs/ENGINEERING_STATUS.md`
