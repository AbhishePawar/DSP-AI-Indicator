# P5.1 — Closed Beta Launch Program

**Status:** COMPLETE (ops + product milestone)  
**Backend:** `dsp_platform` **v1.4.0**  
**Frontend:** `dsp-web` **v1.8.0**  
**API contract:** `v1.0.0-rc1` (unchanged)  
**Decision:** **GO WITH CONDITIONS**  
**Date:** 2026-07-29

---

## Beta objectives

1. Validate real-world usability under invitation-only access.  
2. Collect structured feedback without capturing investment decisions or research envelopes.  
3. Operate invites, issues, and aggregate analytics from an admin dashboard.  
4. Prove operational monitoring hooks remain healthy during the soak.  
5. Exit to broader release only when success criteria are met.

---

## Architecture impact

| Area | Change |
|---|---|
| Analysis / valuation / recommendation / AI Committee | None |
| API analyse contracts | None |
| Deterministic scoring | None |
| Ops / product | Closed beta programme store, `/beta/*` + `/admin/beta/*`, flags, banner, invite gate, admin Beta section, feedback acknowledgement |

Thin client preserved. Beta analytics accept **aggregate event kinds only** (login/analysis/export/session) — no portfolio or research payloads.

---

## Beta programme summary

| Control | Mechanism |
|---|---|
| Closed beta mode | `DSP_CLOSED_BETA` / `NEXT_PUBLIC_CLOSED_BETA` |
| Feature flag | `DSP_BETA_FEATURE_FLAG` / product `featureFlags.closedBeta` |
| Invitation-only | `DSP_BETA_INVITATION_ONLY` + invite store |
| Banner | `DSP_BETA_BANNER` + `BetaBanner` |
| Expiry | `DSP_BETA_EXPIRY_AT` ISO timestamp |
| Read-only safeguards | `DSP_BETA_READ_ONLY_SAFEGUARDS` (banner + research-only posture) |
| Allowlist bootstrap | `DSP_BETA_INVITE_ALLOWLIST=user1,user2` |

Participant hub: `/beta` · Admin: Administration → **Closed Beta** (shortcut `9`).

---

## Participant guidelines

- Reports remain research/education — not personalised advice (see disclaimer).  
- Do not paste secrets, JWTs, holdings, or research envelopes into feedback.  
- Acknowledge the feedback checkbox before submit.  
- Prefer Bug Report / Feature Request / General Comments categories.  
- Optional ticker metadata only (`company_analysed`) — never paste full reports.

---

## User management

| Capability | Endpoint / UI |
|---|---|
| Invite list | `GET/POST /api/v1/admin/beta/invites` |
| Roles | `beta_participant` (default) |
| Admin approval | create invite with `approved` / patch status |
| Statuses | pending → approved → activated → deactivated / revoked |
| Audit log | `GET /api/v1/admin/beta/audit` |

Access check: `GET /api/v1/beta/status?identity=…` · UI gate: `ClosedBetaGate`.

---

## Feedback workflow

1. User opens Feedback dialog → category, severity, rating 1–5, optional screenshot note + ticker.  
2. Acknowledgement required.  
3. Local store + optional `POST /api/v1/beta/feedback`.  
4. Bug-like categories open an issue in status **new**.  
5. Admins advance: **new → triaged → in_progress → resolved → closed**.

---

## Analytics summary

Collected (aggregate): login success rate, analysis completion rate, avg report generation ms, export frequency, error rate, session event count, DAU, most-used features.

**Not collected:** investment decisions, holdings, research envelopes, raw report bodies.

---

## Operational readiness

| Signal | Source |
|---|---|
| Health / ready / live | P1.3 endpoints |
| Metrics | `/metrics` + admin metrics |
| Beta dashboard health slot | Admin Beta section + programme dashboard |
| Incident reporting | Feedback severity + issue workflow + audit |

---

## Success criteria (exit)

| Metric | Target |
|---|---|
| Crash-free sessions | ≥ 99% |
| Analysis success rate | ≥ 99% |
| Critical bugs | = 0 |
| High-severity bugs | ≤ 2 |
| Average feedback | ≥ 4.0 / 5 |
| Infrastructure uptime | ≥ 99.5% |
| Security incidents | = 0 |

Encoded in `admin.beta_programme.SUCCESS_CRITERIA` and `BETA_SUCCESS_CRITERIA` (frontend).

---

## Risk register

| Risk | Mitigation |
|---|---|
| Invite store is process-local | Redeploy loses invites unless allowlist/env reseeded; export audit before restart |
| Fail-open when API down | Local/dev continuity; enforce invite gate once API reachable |
| Screenshot uploads not stored | Note-only attachment substitute (trust) |
| Analytics volume | Cap event buffer; redact actor to hash |

---

## Admin operations

1. Enable `DSP_CLOSED_BETA=true` and set allowlist or create invites.  
2. Confirm banner + gate on web (`NEXT_PUBLIC_CLOSED_BETA=true`).  
3. Monitor Administration → Closed Beta daily.  
4. Triage issues; keep critical = 0.  
5. Run `production_smoke.py` + health checks each soak day.  
6. Review success criteria before exit.

---

## GO / NO-GO recommendation

### **GO WITH CONDITIONS**

**Conditions**

1. Seed invites or allowlist before enabling invitation-only in a shared environment.  
2. Persist invite/feedback store (or scheduled export) before multi-replica production.  
3. Meet success criteria for ≥5 consecutive soak days.  
4. Zero security incidents during the programme.

**Blocking for unconditional public GA:** success criteria not yet measured on a live cohort (repo certification only).

---

## Testing

| Suite | Coverage |
|---|---|
| `packages/api_platform/tests/test_beta_programme_p51.py` | invites, feedback, issues, analytics, dashboard |
| Frontend foundation / release-smoke | v1.8.0 |
| Manual | banner, gate, admin Beta section |

---

## PASS / FAIL

**PASS** (milestone complete) · Decision **GO WITH CONDITIONS**
