# P7.0 — Production Deployment Guide

**Epic:** EPIC-P7.0 — Production Infrastructure & Public Launch  
**Backend:** `dsp_platform` **1.7.0**  
**Frontend:** `dsp-web` **2.0.0**  
**API contract label:** **`v1.0.0`** (behaviour frozen from `v1.0.0-rc1`)  
**Scope:** Deployment & operations only — **no** analytical engine changes.

---

## Infrastructure diagram

```text
                    Internet
                       |
              [ :80 / :443 ]
                       |
                 +-----+-----+
                 |   Caddy   |  Let's Encrypt TLS, HSTS, gzip,
                 |   proxy   |  security headers, access logs
                 +--+--+--+--+
                    |  |
           /api/v1  |  |  UI + /api/health
           /health  |  |
           /metrics |  |
                    v  v
              +-----+  +-----+
              | API |  | Web |
              |:8000|  |:3000|
              +--+--+  +-----+
                 |
        +--------+--------+
        |                 |
   +----+----+       +----+----+
   |Postgres |       |  Redis  |
   |  :5432  |       |  :6379  |
   +---------+       +---------+

   Prometheus  <-- scrape --  API /metrics + cAdvisor (+ Caddy admin metrics)
```

---

## Prerequisites

- Linux host (or Docker Desktop) with Docker + Compose v2
- DNS A/AAAA records for `DSP_PUBLIC_DOMAIN` (and optional `DSP_API_DOMAIN`) pointing to the host
- Ports **80** and **443** open for ACME HTTP-01 / HTTPS
- Secrets available (JWT, admin password, Postgres password)

---

## Environment setup

1. Copy template (never commit secrets):

```bash
cp .env.production.example .env.production
```

2. Fill at minimum:

- `DSP_JWT_SECRET` (≥24 chars, not a template)
- `DSP_SEED_ADMIN_PASSWORD`
- `POSTGRES_PASSWORD` / matching `DSP_DATABASE_URL`
- `DSP_PUBLIC_DOMAIN`, `DSP_ACME_EMAIL`
- `DSP_CORS_ORIGINS=https://<public-domain>`
- `NEXT_PUBLIC_API_BASE_URL=https://<public-domain>/api/v1`

3. Validate:

```bash
set -a; source .env.production; set +a
python scripts/validate_env.py production
```

`.env.production` is gitignored. Only `.env.production.example` is committed.

---

## SSL setup (Let's Encrypt via Caddy)

Caddy (`docker/Caddyfile`) obtains and renews certificates automatically when:

- `DSP_AUTO_HTTPS=on` (default)
- `DSP_PUBLIC_DOMAIN` is a publicly resolvable hostname
- Port 80 is reachable from the internet (ACME challenge)

Certificates persist in the `caddy_data` volume.

**Local dry-run:** use `localhost` domains; Caddy may use internal/local TLS. Full public ACME requires a real domain.

Edge headers include:

- `Strict-Transport-Security`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- gzip/zstd compression
- long-cache for `/_next/static/*`

---

## Deployment guide

```bash
chmod +x scripts/*.sh scripts/ops/*.sh
./scripts/deploy_production.sh
```

What it does:

1. Validates production env  
2. Records previous image tags for rollback  
3. Builds images (`dsp-api:1.7.0`, `dsp-web:2.0.0`)  
4. Starts `docker/docker-compose.production.yml`  
5. Waits for API `/health/ready` and Web `/api/health`  
6. Optionally smokes external HTTPS  

Compose file: `docker/docker-compose.production.yml`  
Services: `proxy`, `api`, `web`, `postgres`, `redis`, `prometheus`, `cadvisor`

---

## Backup

```bash
./scripts/backup_database.sh
```

Creates `backups/dsp_pg_<UTC>.sql.gz` + `.sha256`.  
RPO target: ≤24h (schedule daily cron). See also `docs/ops/BACKUP_AND_RECOVERY.md`.

---

## Restore

```bash
DSP_RESTORE_CONFIRM=YES ./scripts/restore_database.sh backups/dsp_pg_YYYYMMDDTHHMMSSZ.sql.gz
```

Destructive. Verify `/health/ready` and run smoke afterwards.

---

## Rollback

```bash
./scripts/rollback_production.sh 1.6.0 2.0.0-rc
# or rely on DSP_PREVIOUS_IMAGE_TAG / DSP_PREVIOUS_IMAGE_TAG_WEB
```

Redeploys previous API/Web image tags and re-checks health.

---

## Monitoring

| Signal | Source |
|---|---|
| API health | `GET /health`, `/health/live`, `/health/ready` |
| API metrics | `GET /metrics` (Prometheus text) |
| CPU / RAM (containers) | cAdvisor → Prometheus |
| Availability | Proxy + compose healthchecks + restart policies |
| Error rate / latency | API metrics + Caddy JSON access logs |

Prometheus config: `docker/prometheus.yml`  
Retention: 15 days (compose default)

---

## Logging

| Layer | Mechanism |
|---|---|
| API | Structured JSON access logs + `X-Request-Id` (`RequestContextMiddleware`) |
| Caddy | JSON access logs under `caddy_logs` volume with roll size 20MiB |
| Containers | Docker `json-file` driver, max 20m × 5 files |

---

## Migration validation

P7 does **not** change analytical schemas. Pre-deploy:

1. `python scripts/validate_env.py production`  
2. `docker compose -f docker/docker-compose.production.yml config`  
3. Postgres healthcheck green after start  
4. Optional: `pg_isready` inside the postgres container  

---

## Troubleshooting

| Symptom | Action |
|---|---|
| ACME / certificate failure | Check DNS, port 80, `DSP_ACME_EMAIL`, Caddy logs |
| API not ready | `docker compose ... logs api`; check DB URL / Redis |
| CORS errors | Align `DSP_CORS_ORIGINS` with HTTPS public origin |
| 502 from Caddy | Confirm api/web healthy; inspect proxy logs |
| Backup too small | Ensure postgres is up and credentials match |

---

## Security checklist

- [x] HTTPS via Caddy / Let's Encrypt  
- [x] HSTS (edge + Next defense-in-depth)  
- [x] Security headers (nosniff, frame deny, referrer, permissions)  
- [x] CSP (Next)  
- [x] Rate limiting (`DSP_RATE_LIMIT_ENABLED`)  
- [x] Admin auth required in production compose  
- [x] Secrets not committed (`.env.production` gitignored)  

Secure cookies remain the responsibility of the auth stack (`security_platform`) when issuing session cookies over HTTPS.


---

# DSP Fix Protocol — 100% Completion Plan

**Protocol version:** 1.0  
**Last updated:** 2026-10-28  
**Scope:** Audit remediation, evidence integrity, release validation, deployment and post-deployment acceptance.

This section is the completion gate for the DSP Fix Protocol. A task is not complete merely because code was committed, a test was added, or a deployment command returned success. Every item must have an evidence reference and an explicit status.

## Completion rules

Use only these statuses:

- **OPEN** — not implemented or not investigated.
- **IMPLEMENTED / UNVERIFIED** — code change exists, but required tests or review have not passed.
- **BLOCKED** — cannot safely proceed because a dependency, environment or decision is missing.
- **PASS** — required verification ran on the exact commit and passed, with recorded evidence.
- **ACCEPTED EXCEPTION** — explicitly approved, documented risk with owner and review date.

Do not report the project as 100% complete while any P1 security, data-integrity, persistence, recovery, or release-gate item is OPEN, BLOCKED, or only IMPLEMENTED / UNVERIFIED. Do not convert a missing CI result into a pass. Do not suppress, skip, or weaken a failing test merely to obtain a green build.

Percentages are planning estimates only. Release acceptance is a binary gate: all required gates must pass or have a formally accepted exception.

## Phase 0 — Preserve and establish a reproducible baseline

- [ ] Record current branch, HEAD SHA, tracked/untracked changes and remote refs.
- [ ] Preserve the existing working tree and recovery backups; never use destructive reset/clean operations as an audit shortcut.
- [ ] Use a separate worktree or disposable checkout for audit branches and dependency installation.
- [ ] Record the exact tested commit SHA, Python/Node versions, lockfile state and test commands.
- [ ] Determine the project's supported Python versions from project metadata and CI; do not assume the host's installed Python is supported.
- [ ] Install dependencies from the repository lock/configuration in an isolated environment; do not install test tools globally.
- [ ] Reconcile the audit branch history and complete changed-file list, including formatting-only commits, before review.

**Exit gate:** cleanly identified baseline, reproducible environment and recoverable working state.

## Phase 1 — Close original M-series findings

For each M finding, record implementation commit, regression test, test output and reviewer disposition.

- [ ] **M01:** Fix Caddy configuration and bind its administrative endpoint to loopback or an explicitly isolated management network; validate with the exact Caddy image/config.
- [ ] **M02:** Align frontend Docker build context and Dockerfile paths with the actual app layout; prove a clean production image build.
- [ ] **M03:** Correct environment-template quoting and validate loading without exposing secrets.
- [ ] **M04:** Correct executable modes or invoke shell scripts explicitly; verify every direct invocation.
- [ ] **M05:** Normalize API base paths and prevent duplicate `/api/v1` prefixes; test actual generated request URLs.
- [ ] **M06:** Correct cookie/session authentication clients; test valid sessions, invalid bearer tokens, CSRF and unauthorized access.
- [ ] **M07:** Ensure backup and restore target the authoritative production database, not an accidental local Postgres fallback.
- [ ] **M08:** Make health-check timeout, HTTPS failure and smoke-test failure fail closed; record the last known-good image and roll back safely.
- [ ] **M09:** Ensure restore SQL commands use fail-fast error handling (including `ON_ERROR_STOP`) and propagate errors.
- [ ] **M10:** Pass Ruff import-order and unused-import checks.
- [ ] **M11:** Replace private cross-package imports with supported public interfaces.
- [ ] **M12:** Align dashboard rendering and tests with the intended canonical research surface.
- [ ] **M13:** Correct frontend tests for the intended user-facing refresh and research labels; do not change product behavior solely to satisfy stale assertions without review.
- [ ] **M14:** Verify company-analysis behavior when authenticated statements are unavailable; avoid unsupported ticker-only analysis.
- [ ] **M15:** Test rendered accessible touch target dimensions (minimum 44×44 CSS px where required), not merely source-code class names.
- [ ] **M16:** Correct production-ops workflow arguments and remove failure-masking constructs such as `|| true` around required validation.
- [ ] **M17:** Keep broad formatting-only changes separate from behavioral fixes; format, lint and test the final integrated tree.

**Exit gate:** every M item is PASS or a formally accepted exception; no P1 remains unresolved.

## Phase 2 — Close original R-series evidence-integrity findings

- [ ] **R01 — Source authority:** approval alone must not promote secondary evidence to verified primary evidence. Enforce source tier, evidence status and permitted purpose.
- [ ] **R02 — Document validation:** match entity, metric, numerical value, units/scale and reporting period. Reject unrelated numbers, unsupported prose and absent/conflicting periods.
- [ ] **R03 — Share-count isolation:** filter candidates for the requested ticker and eligible source before resolution. Add a regression test with another ticker's share count present; prove it can never be returned as the requested ticker. Distinguish missing eligible evidence from disagreement. Do not label an unverified value verified.
- [ ] **R04 — Source normalization:** centralize normalized source aliases and domain policy; test BSE aliases, SEC, host spoofing, primary/secondary mismatches and purpose restrictions.
- [ ] **R05 — Deduplication:** preserve distinct metric/value/unit/period/revision facts and surface conflicts; collapse only true duplicates.
- [ ] **R06 — Corroboration:** accumulate all corroborating evidence IDs in deterministic order; do not overwrite earlier links.
- [ ] **R07 — Malformed source values:** validate each source independently; values such as `N/A` must reject only that source and not abort the retrieval batch.

**Exit gate:** all R-series regression tests pass on the exact release candidate, including negative and adversarial cases.

## Phase 3 — Validate architecture, AI providers and hosting independence

- [ ] Verify the deterministic DSP pipeline remains authoritative; provider-generated narrative cannot silently override validated financial values.
- [ ] Verify Gemini and OpenAI direct-provider adapters, configuration, timeouts, error handling and secret handling.
- [ ] Confirm API keys are server-side only and never appear in browser bundles, logs, error payloads or committed files.
- [ ] Search tracked files, CI workflows, Docker/Compose, environment templates, package scripts and deployment documentation for active Vercel hosting, deployment or AI Gateway dependencies.
- [ ] Run the repository's hosting-dependency policy test; classify permitted historical documentation and package provenance separately from active dependencies.
- [ ] Verify no runtime path silently falls back to a different provider, model, data source or in-memory store when persistent/authoritative services are required.
- [ ] Verify unknown tickers and unsupported data sources fail explicitly instead of silently defaulting to another exchange or source.

**Exit gate:** architecture decisions are documented, automated dependency policy passes, and no unapproved active hosting dependency remains.

## Phase 4 — Full automated acceptance suite

Run all required checks against the same exact candidate commit, in CI or an equivalent reproducible environment:

- [ ] Backend test suite on every supported Python version (including 3.11 and 3.12 if those remain supported by project policy).
- [ ] Retrieval/evidence regression tests and API composition/authentication tests.
- [ ] Ruff, Black/check-format, configured mypy and package/import checks.
- [ ] Frontend dependency installation from the committed lockfile using the declared package manager.
- [ ] Frontend lint, TypeScript, unit/component tests and production build.
- [ ] Playwright/browser smoke and critical user-journey tests against a locally started production-like stack.
- [ ] Security checks, dependency audit and secret-leak scan.
- [ ] CI workflow validation, diff checks and tracked-tree hosting-dependency policy.
- [ ] Record test totals, skips, failures and artifact links. Investigate all unexpected skips and failures.

**Exit gate:** all mandatory jobs pass on the exact candidate SHA. A test merely existing in source is not evidence of a pass.

## Phase 5 — Production topology, persistence and recovery

- [ ] Select and document the single authoritative production Compose/deployment path.
- [ ] Reconcile the target VPS architecture with environment templates and Compose: API, frontend, Caddy, authoritative Neon/Postgres connection, Redis policy and object storage.
- [ ] Do not start a local Postgres or Redis service unless the chosen architecture requires it; ensure application, migrations, backups and restore use the same authoritative database.
- [ ] Validate production environment requirements without printing secrets.
- [ ] Validate Compose configuration and Caddy configuration using the exact production image versions.
- [ ] Build backend and frontend images from a clean checkout.
- [ ] Verify non-root execution, health checks, resource limits, internal-only service ports, TLS, security headers, admin interface exposure and log rotation.
- [ ] Produce a fresh database backup; record timestamp, target, size, format and checksum.
- [ ] Restore the backup into an isolated database/network; compare schema and required row counts, and test application-level readability.
- [ ] Verify object-storage backup/restore and Redis persistence or explicitly document that Redis is ephemeral/not used.
- [ ] Prove restore failure stops the process and never overwrites production during validation.

**Exit gate:** clean builds/configuration validation and an independently verified recovery path against the actual authoritative data target.

## Phase 6 — Deployment safety and release candidate

- [ ] Verify deployment preflight fails on missing secrets, wrong environment, invalid database configuration, bad image or failed tests.
- [ ] Verify health-check and HTTPS timeouts are fatal, not warnings.
- [ ] Verify smoke tests cover login/session, core research flow, API readiness, evidence provenance and database persistence.
- [ ] Verify rollback restores the previous known-good image/configuration and checks health after rollback.
- [ ] Review database migration compatibility and establish a backup/rollback decision before any migration.
- [ ] Review the complete diff for both audit branches; separate formatting noise from behavior changes and identify all files changed by later commits.
- [ ] Confirm CI results and review approvals belong to the exact candidate SHA.
- [ ] Obtain explicit deployment approval before touching production.

**Exit gate:** release candidate signed off; no deployment from an unreviewed or untested branch.

## Phase 7 — Controlled deployment and post-deployment acceptance

- [ ] Deploy only the approved commit using the documented deployment path.
- [ ] Confirm running image digests/commit identifiers match the approved candidate.
- [ ] Verify HTTPS, Caddy/API/frontend health, authentication, core research flow, evidence verification and provider connectivity.
- [ ] Verify database reads/writes use the authoritative persistent database and no in-memory fallback is active.
- [ ] Inspect logs and metrics for startup errors, 4xx/5xx spikes, provider failures and data-source failures.
- [ ] Run post-deploy smoke tests and record outputs.
- [ ] Verify backup scheduling and alerting after deployment.
- [ ] If any critical gate fails, stop rollout or roll back; record the incident and retest before redeployment.

**Exit gate:** production smoke tests pass, service health is stable, data persistence is verified and rollback remains available.

## Definition of 100% complete

DSP Fix Protocol is 100% complete only when:

1. All M01–M17 and R01–R07 findings are PASS or have explicitly accepted exceptions.
2. All P1 security, evidence-integrity, persistence and recovery blockers are closed.
3. The full mandatory test/quality suite passes on the exact candidate commit.
4. Hosting-independence and AI-provider configuration checks pass.
5. Production builds, configuration validation, backup and isolated restore tests pass.
6. Deployment and rollback behavior are verified.
7. The reviewed candidate is explicitly approved, deployed and verified in production.
8. Evidence links, commit SHAs, test artifacts, exceptions and remaining non-blocking risks are recorded.

Until all gates are satisfied, report the project as **NOT RELEASE-READY** and show remaining tasks. Do not claim 100% based on code volume, commit count, or an estimated completion percentage.

## Audit tracking template

For every finding, keep a row with:

| Field | Required value |
|---|---|
| Finding ID | M01–M17, R01–R07 or a new unique ID |
| Severity | P1 / P2 / P3 |
| Status | OPEN / IMPLEMENTED-UNVERIFIED / BLOCKED / PASS / ACCEPTED EXCEPTION |
| Commit SHA | Exact commit containing the fix |
| Regression test | Test path and test name |
| Execution evidence | CI URL/log artifact, command, totals and result |
| Reviewer | Person approving the result |
| Risk/exception | Rationale, owner and review date if accepted |
| Next action | One specific actionable step |

**Current audit baseline note (2026-10-28):** the Phase 7 retrieval test attempt on the VPS did not execute because system Python 3.14.4 had no pytest installed. The isolated worktree exists at `/root/dsp-phase7-audit-check-20261028` on commit `35b166217a3b8893b58818a94d6fd16bb8c536f2`. The next task is to verify supported Python versions and install the locked development dependencies in that isolated worktree before running the retrieval regression tests. No pass should be recorded until test output is captured.
