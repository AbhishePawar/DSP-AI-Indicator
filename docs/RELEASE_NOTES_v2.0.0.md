# Release Notes — DSP Web 2.0.0 / Platform 1.7.0 (P7.0)

**Channel:** Stable (`stable`)  
**API contract label:** `v1.0.0` (behaviour unchanged from `v1.0.0-rc1`)  
**Date:** 2026-07-29

## Highlights

- Production Docker Compose with Caddy reverse proxy (HTTPS / Let's Encrypt).
- Postgres + Redis with persistent volumes; Prometheus + cAdvisor monitoring.
- Deploy, rollback, backup, and restore scripts under `scripts/`.
- Production env validation requires database URL + public domain.
- Edge HSTS, compression, security headers, and static asset caching.

## What did not change

- Valuation, Buffett Indicator, financial analysis, business quality
- AI Committee, recommendation, explainability, research engines
- Scoring algorithms and institutional report logic
- `/api/v1` analyse behaviour (label promotion only)

## Upgrade notes

1. Copy `.env.production.example` → `.env.production` and fill secrets.
2. Point DNS at the host; open ports 80/443.
3. Run `./scripts/deploy_production.sh`.
4. Verify `https://<domain>/api/health` and API `/health/ready`.
5. Schedule `./scripts/backup_database.sh` daily.

## Decision

**GO WITH CONDITIONS** — see `docs/P7_PRODUCTION_CERTIFICATION.md`.
