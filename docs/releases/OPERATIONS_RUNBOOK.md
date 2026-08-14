# Operations Runbook — DSP AI Indicator Version 1.0.0 (Release Packet)

| Field | Value |
|---|---|
| Product | DSP AI Indicator |
| Version | **1.0.0** |
| Posture | Closed-beta / institutional pilot UI freeze |
| Companion | [`GO_LIVE_CHECKLIST.md`](./GO_LIVE_CHECKLIST.md) · [`ROLLBACK_PLAN.md`](./ROLLBACK_PLAN.md) |
| Platform master index | `docs/OPERATIONS_RUNBOOK.md` · `docs/ops/runbooks/*` |
| Date | 2026-08-02 |

This document is the **Version 1.0.0 release-facing** operations packet. It does not replace deep platform runbooks; it binds closed-beta deploy verification, health checks, monitoring, logging, and backup verification to the RC3 **PASS WITH CONDITIONS** posture.

---

## 1. Deployment verification

### 1.1 Pre-flight

- [ ] Branch tip includes RC3 Final Certification ancestry + subsequent release docs.  
- [ ] `VERSION` == `v1.0.0`.  
- [ ] Production web build on clean `.next` (`apps/web` → `next build`).  
- [ ] Primary Vitest set green (shell, dashboard, portfolio-intelligence, company-analysis, institutional-reports, institutional-dashboard, ds, a11y-responsive, mapResearchView). Optional: `npm run test:quality` (a11y + perf automation).  
- [ ] Closed-beta env: no public registration endpoints; contact unpublished; pricing not checkout-enabled.  
- [ ] Backend `/api/v1` health green in target environment.  
- [ ] Admin accounts provisioned for pilot desks.  
- [ ] Rollback known-good artefact identified ([`ROLLBACK_PLAN.md`](./ROLLBACK_PLAN.md)).

Platform deploy detail: `docs/ops/runbooks/DEPLOYMENT.md` · `scripts/deploy_production.sh` (or environment equivalent).

### 1.2 Deploy

1. Deploy web artefact from certified commit / image tag.  
2. Deploy or verify API gateway routing to frozen `/api/v1`.  
3. Confirm foundation / version surfaces show **1.0.0** / expected channel (not “Commercial GA”).  
4. Run post-deploy smokes (§2).

### 1.3 Do not

- Deploy untagged `latest` as production.  
- Change analyse contracts, valuation, recommendation, or AI Committee in this release path.  
- Enable self-serve commerce to “make pilot easier.”

---

## 2. Health checks

| Check | Target | Pass criteria |
|---|---|---|
| API live | `/api/v1/health` or `/health` / `/health/live` (env-specific) | HTTP 200 |
| API ready | `/health/ready` when used | HTTP 200; dependencies up |
| Web marketing | `/` | HTTP 200 |
| Web login | `/login` | HTTP 200 |
| Auth path | provisioned login | Session → `/dashboard` |
| Analyse | `/api/v1/analyse` (or env analyse path) | Success or honest error — not fabricated UI fill |
| Synthetic | login + dashboard + analysis empty-state | Green |

Post-deploy product smokes (required):

- [ ] `/login` → provisioned user → `/dashboard`  
- [ ] `/analysis` requires explicit ticker  
- [ ] `/research/institutional` loads for selected symbol  
- [ ] `/portfolio` coverage language  
- [ ] Palette hides AUX for analyst  
- [ ] `/signup` Request Access honesty  
- [ ] `/contact` unpublished when not published  
- [ ] Research Mode disclaimers visible  

Reference: [`GO_LIVE_CHECKLIST.md`](./GO_LIVE_CHECKLIST.md).

---

## 3. Monitoring

### 3.1 Closed-beta watch list

| Signal | Why |
|---|---|
| Web / API uptime and 5xx rate | Availability |
| Auth login failure rate (401/403) | Expect provisioned-only traffic; spike of “success registrations” is anomalous |
| Analyse latency and error rate | Primary research path |
| Portfolio intelligence error rate | Desk workflow |
| Client error boundary / observability logs | Correlation IDs |
| CDN / static asset health | Shell load |
| Disk / volume for DB and backups | Continuity |

Prefer Grafana **DSP Operations Dashboard** (or env equivalent) per `docs/OPERATIONS_RUNBOOK.md`.

### 3.2 Alerting posture

| Alert | First action |
|---|---|
| API unavailable | Check API container / upstream; restart; rollback if deploy-related |
| High latency | CPU/memory/DB locks/rate limits — do not multi-worker without Redis-backed limits when that condition applies |
| High error rate | Correlate logs by `request_id`; prefer rollback over analytical hot-patch |
| Sudden auth “success” without provisioning | Treat as trust/security anomaly |
| Low disk | Purge per retention; never delete sole unverified backup |

### 3.3 Post-launch windows

| Window | Actions |
|---|---|
| First 24 hours | Auth + analyse error budgets; desk feedback on empties vs fabrication; no theatre regressions |
| First 7 days | Collect pilot UX notes; triage HIGH residuals; do not expand commercial claims |
| Before GA promotion | Close RC3 §15 conditions; re-certify |

---

## 4. Logging

| Practice | Guidance |
|---|---|
| Correlation | Capture `X-Request-Id` / `request_id` on incidents |
| PII / research payloads | Do not paste full research payloads into public tickets |
| Trust incidents | Log SHA, route, whether value was fabricated vs unavailable |
| Retention | Follow platform retention policy |
| Access | Limit production log access to ops / security roles |

Client error boundaries should surface enough context for support without exposing secrets.

---

## 5. Backup verification

| Step | Action |
|---|---|
| Pre-deploy | Confirm backup completed (DB / required volumes) per `docs/ops/runbooks/BACKUP_RECOVERY.md` |
| Beta snapshot | Export invite / provisioned-user snapshot if mutable |
| Post-backup check | Spot-verify backup artefact exists and is non-zero; run `validate_recovery` tooling when available |
| Restore drill | At least one restore validation in the pilot window before calling ops “ready” for broader GA |
| On failure | Follow `docs/DISASTER_RECOVERY.md` / database failure section in platform ops index |

**Cache note:** Redis/cache corruption — prefer restore empty cache (rehydratable) over inventing research facts.

---

## 6. Service restart (quick)

```bash
# Example compose production profile — adjust to environment
docker compose -f docker/docker-compose.production.yml restart api
# or: web | postgres | redis | proxy | prometheus | grafana
```

Wait for healthchecks; re-run §2 smokes after restart of web or API.

---

## 7. Planned maintenance

1. Announce window to pilot admins.  
2. Take fresh full backup + beta snapshot.  
3. Drain / maintenance page if available.  
4. Apply change (compose up / image pull).  
5. Validate health + smokes.  
6. Clear status; record duration.

---

## 8. Related runbooks

| Topic | Path |
|---|---|
| Platform ops index | `docs/OPERATIONS_RUNBOOK.md` |
| Deployment | `docs/ops/runbooks/DEPLOYMENT.md` |
| Rollback (platform) | `docs/ops/runbooks/ROLLBACK.md` |
| Rollback (release) | [`ROLLBACK_PLAN.md`](./ROLLBACK_PLAN.md) |
| Incident response | `docs/ops/runbooks/INCIDENT_RESPONSE.md` |
| Service outage | `docs/ops/runbooks/SERVICE_OUTAGE.md` |
| Backup / recovery | `docs/ops/runbooks/BACKUP_RECOVERY.md` |
| Security incident | `docs/ops/runbooks/SECURITY_INCIDENT.md` |
| Support triage | [`SUPPORT_RUNBOOK.md`](./SUPPORT_RUNBOOK.md) |
