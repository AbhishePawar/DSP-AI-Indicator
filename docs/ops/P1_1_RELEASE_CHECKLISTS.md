# P1.1 — Release / Deployment / Rollback / Acceptance Checklists

## Release Checklist

- [ ] `dsp_platform` version **1.3.0** and web **1.7.0** aligned in manifests
- [ ] `PRODUCTION_VERSION_MANIFEST.json` updated (channel, git SHA, build timestamp)
- [ ] API contract remains **v1.0.0-rc1** (no contract change in P1.1)
- [ ] `python scripts/ops/certify_p11.py` PASS
- [ ] Backend regression (`pytest packages/api_platform packages/dsp_platform` health/ops) PASS
- [ ] Frontend `npm test` / release-smoke PASS
- [ ] Docker images build (`dsp-api:1.3.0`, `dsp-web:1.7.0`)
- [ ] Security flags documented: HSTS, admin auth, rate limit, CSP (web)
- [ ] Changelog / certification doc linked: `docs/P1_1_PRODUCTION_DEPLOYMENT_CERTIFICATION.md`
- [ ] Legal pages reachable (P4.1)

## Deployment Checklist

- [ ] Secrets loaded from KMS (JWT, admin seed, DB, Redis) — not image env defaults
- [ ] `python scripts/validate_env.py production` PASS against runtime env
- [ ] `DSP_ENVIRONMENT=production`, TZ `Asia/Kolkata`, currency `INR`
- [ ] Compose: `docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml config`
- [ ] TLS terminator configured (HTTPS, HTTP→HTTPS redirect, valid cert)
- [ ] CORS origins HTTPS-only matching public web origin
- [ ] Volumes: backups + tmp mounted; Postgres data volume if infra profile
- [ ] Healthchecks green: API `/health/ready`, Web `/api/health`
- [ ] Metrics scraped or bookmarked: `/metrics`
- [ ] `production_smoke.py` PASS against production URLs
- [ ] Backup job scheduled (see `BACKUP_AND_RECOVERY.md`)

## Rollback Checklist

- [ ] Identify last known-good image tags / git SHA from manifest
- [ ] Drain traffic / enable maintenance page if available
- [ ] Redeploy previous `dsp-api:<prev>` and `dsp-web:<prev>`
- [ ] If schema/data migration applied: restore Postgres from last good dump
- [ ] Validate `/health/ready` + smoke script
- [ ] Confirm admin auth still required
- [ ] Record rollback reason and duration (feeds RTO measurement)

## Production Acceptance Checklist

- [ ] Home / Login reachable over HTTPS
- [ ] Authentication works (no dev credentials)
- [ ] Company Analysis loads via `/api/v1` (thin client)
- [ ] Research generation acknowledgement + report metadata visible
- [ ] Institutional Ratings / Explainability / Valuation Transparency / Buffett sections render from backend payloads
- [ ] Exports succeed without client-side scoring
- [ ] Health + metrics endpoints OK
- [ ] Admin routes reject unauthenticated callers
- [ ] No debug mode / no template secrets in process env
- [ ] Backup + restore dry-run completed in staging within RTO
- [ ] Sign-off: Ops + Security + Product (Research Mode)
