# Runbook — Deployment

**Epic:** P6.1 · Images: `dsp-api:1.6.0` · `dsp-web:2.0.0-rc`

## Pre-deploy checklist

- [ ] Changelog / release notes reviewed  
- [ ] Env validated (`validate_env` / compose prod)  
- [ ] Beta snapshot exported  
- [ ] Backup completed  
- [ ] Migrations reviewed (none expected for commercial-only release)  
- [ ] Feature flags / closed-beta posture confirmed  

## Deploy steps (compose reference)

1. Pull / build tagged images matching `PRODUCTION_VERSION_MANIFEST.json`.
2. Rolling restart API then web (or recreate compose services).
3. Confirm `/health` and `/health/ready`.
4. Smoke: login, docs links, sample analysis, support mailto path.
5. Confirm foundation version in Settings / Welcome widget = `2.0.0-rc`.

## Do not

- Change analyse contracts, valuation, recommendation, or AI Committee in this release path.
- Deploy untagged `latest` to production.

## Post-deploy

Attach smoke results to release record; monitor metrics 1h; Support on standby for S2+.
