# P1.1 — Production Deployment & Release Certification

**Status:** COMPLETE (ops milestone)  
**Decision:** **GO WITH CONDITIONS**  
**Backend:** `dsp_platform` **v1.3.0**  
**Frontend:** `dsp-web` **v1.7.0**  
**API contract:** `v1.0.0-rc1` (unchanged)  
**Date:** 2026-07-28

---

## Architecture Review

P1.1 is an **operations & DevOps** milestone only.

| Area | Change |
|---|---|
| Analysis pipeline | None |
| Valuation engines | None |
| Recommendation engine | None |
| AI Committee | None |
| Report rendering | None |
| API contracts | None |
| Product features | None |
| Ops / deploy | Env validation, prod compose, backup/restore scripts, smoke certification, manifests, docs |

Thin-client and frozen `/api/v1` rules preserved.

---

## Deployment Review

| Component | Artifact |
|---|---|
| API image | `docker/backend/Dockerfile` → `dsp-api:1.3.0` |
| Web image | `docker/frontend/Dockerfile` → `dsp-web:1.7.0` |
| Base compose | `docker/docker-compose.yml` |
| Prod override | `docker/docker-compose.prod.yml` |
| Env template | `.env.production.example` |
| Env gate | `scripts/validate_env.py` |
| Offline certify | `scripts/ops/certify_p11.py` |
| Live smoke | `scripts/ops/production_smoke.py` |
| Version manifests | `PRODUCTION_VERSION_MANIFEST.json`, `apps/web/VERSION_MANIFEST.json` |

Prod compose adds: security flags, India TZ, resource limits/reservations, named network `dsp_prod`, backup/tmp volumes, log rotation, tightened healthchecks, image tags.

---

## Infrastructure Validation

| Check | Result |
|---|---|
| Production backend deployment path | PASS (Dockerfile + compose) |
| Production frontend deployment path | PASS |
| Environment variables template | PASS (expanded P1.1 template) |
| Configuration validation | PASS (`validate_env.py` production profile) |
| Timezone | PASS (`Asia/Kolkata` / `TZ`) |
| Locale | PASS (`LANG=en_IN.UTF-8` documented) |
| File / temp / backup storage | PASS (volumes `dsp_api_tmp`, `dsp_backups`) |
| Secrets loading | PASS (template + KMS guidance; refuse weak JWT) |
| Build metadata | PASS (`BUILD_TIMESTAMP`, `GIT_SHA`, web build args) |
| Version consistency | PASS (1.3.0 / 1.7.0 manifests + certify script) |
| Domain & HTTPS (live) | **CONDITION** — edge TLS not exercised in this repo run |
| Docker health / readiness / liveness | PASS (API `/health/*`, Web `/api/health`) |
| Restart policies | PASS (`unless-stopped`) |
| Resource limits | PASS (prod override) |
| Container networking | PASS (`dsp_prod`) |
| Image versioning | PASS (tags 1.3.0 / 1.7.0) |

---

## Security Verification

| Control | Status |
|---|---|
| HTTPS / redirect / TLS cert | **CONDITION** — terminate at edge; not auto-probed here |
| HSTS | PASS (API `DSP_HSTS_ENABLED`; web relies on edge or next headers) |
| CSP | PASS (Next `next.config.ts` from prior work) |
| Rate limiting | PASS (prod flag required) |
| JWT validation | PASS (prod rejects defaults; ≥24 char secret) |
| Admin authentication | PASS (`DSP_REQUIRE_ADMIN_AUTH`) |
| RBAC | PASS (prior P1.2 institutional zone) |
| Secrets | PASS (no commit of real secrets; template markers rejected) |
| No debug / no dev credentials | PASS (validation + compose production env) |
| Mixed content | **CONDITION** — verify after public domain cutover |

Open (deferred, non-blocking for GO WITH CONDITIONS): HttpOnly cookie session migration, MFA, CI CVE audit gate, multi-node rate-limit store (P1.2 backlog).

---

## Operational Readiness

| Capability | Status |
|---|---|
| Application startup | PASS (`start-api.sh` + lifespan) |
| Health / ready / live | PASS (P1.3) |
| Metrics | PASS `/metrics` |
| Graceful shutdown | PASS (`DSP_GRACEFUL_SHUTDOWN_SECONDS`) |
| Monitoring | PASS (P1.3 structured logs) |
| Smoke automation | PASS (`production_smoke.py`) |
| Offline certification | PASS (`certify_p11.py`) |

---

## Backup Validation

Documented in `docs/ops/BACKUP_AND_RECOVERY.md`.

| Item | Value |
|---|---|
| Backup creation | `scripts/ops/backup_postgres.sh` |
| Integrity | size gate + sha256 sidecar |
| Restore | `scripts/ops/restore_postgres.sh` |
| **RPO** | **≤ 24 hours** (daily logical dump; tighten with managed PITR) |
| **RTO** | **≤ 4 hours** (restore + health + smoke) |
| Stateless RC1 without Postgres | Redeploy / re-auth (RPO N/A for ephemeral cache) |

Live restore drill against customer-managed Postgres remains an acceptance **condition**.

---

## Performance Summary

| Signal | Guidance |
|---|---|
| Startup | API health start_period 30s; web 40s |
| API response | Health/metrics smoke within `DSP_SMOKE_TIMEOUT` (default 15s) |
| Resources | API ≤2 CPU / 2G; Web ≤1 CPU / 1G |
| Cold start | Container start_period + uvicorn boot |
| Concurrent behaviour | Rate limit enforced when enabled; multi-node limiter still in-memory (condition) |

No engine/load-test changes in P1.1 — ops envelopes only.

---

## Release Checklist

See `docs/ops/P1_1_RELEASE_CHECKLISTS.md` (Release, Deployment, Rollback, Acceptance).

---

## Rollback Checklist

Image tag rollback + optional Postgres restore; re-run health + smoke. Details in checklists doc.

---

## Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| Live TLS/domain not verified in CI | High (edge) | Condition: ops sign-off after cutover |
| Backup never scheduled | High | Condition: enable cron + quarterly restore drill |
| In-memory rate limit multi-node | Medium | Edge/WAF or Redis limiter (backlog) |
| Web HSTS not set in Next | Medium | Edge HSTS or add header in follow-up |
| Version drift historically | Medium | `certify_p11.py` + manifests |
| P1.2 MFA / HttpOnly cookies open | Medium | Tracked; Research Mode still default |

**Blocking issues for unconditional GO:** none inside repo certification scope.  
**Conditions for production traffic:** listed under Final Decision.

---

## Production Readiness Scorecard

| Dimension | Score (/10) | Grade | Confidence | Rationale |
|---|---|---|---|---|
| Architecture | 9 | A | High | Thin client + frozen API; ops-only delta |
| Security | 8 | B+ | High | P1.2 + prod flags; edge TLS/MFA conditions |
| Reliability | 8 | B+ | High | Health/lifecycle/metrics (P1.3) |
| Monitoring | 8 | B+ | High | Structured logs + Prometheus text |
| Deployment | 8 | B+ | High | Docker/compose/prod override/validate_env |
| Documentation | 9 | A | High | P1.1 + backup + checklists + manifests |
| Compliance | 8 | B+ | Medium | Legal P4.1 present; counsel review still external |
| **Overall** | **8.3** | **B+** | **High** | Ready for controlled production with conditions |

---

## Final GO / NO-GO

### **GO WITH CONDITIONS**

**Conditions (must close or accept before unrestricted public traffic):**

1. Provision production domain + valid TLS + HTTP→HTTPS redirect; re-run `production_smoke.py` against public URLs.  
2. Load real secrets from KMS (JWT, admin password, DB, Redis); `validate_env.py production` PASS on the live host.  
3. Schedule daily Postgres backups; complete one staging restore drill within RTO.  
4. Confirm edge HSTS / secure cookies for the web origin.  
5. Explicitly accept or schedule Redis-backed rate limiting for multi-instance API.

**Blocking issues:** none for certification of the repository deployment pack.

---

## Testing

| Suite | Result |
|---|---|
| `python scripts/ops/certify_p11.py` | Required PASS |
| `validate_env.py` synthetic prod | Covered by certify |
| Frontend release-smoke / foundation | Version **1.7.0** |
| `dsp_platform` architecture version | **1.3.0** |
| API health RC1 / monitoring | Unchanged contracts |

---

## PASS / FAIL

**PASS** (milestone complete) · Decision **GO WITH CONDITIONS**
