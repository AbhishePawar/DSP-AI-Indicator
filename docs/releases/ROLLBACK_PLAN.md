# Rollback Plan — DSP AI Indicator Version 1.0.0

| Field | Value |
|---|---|
| Product | DSP AI Indicator |
| Version | **1.0.0** (closed-beta / institutional pilot) |
| Authority | [`GO_LIVE_CHECKLIST.md`](./GO_LIVE_CHECKLIST.md) · [`RC3_FINAL_CERTIFICATION_REPORT.md`](./RC3_FINAL_CERTIFICATION_REPORT.md) |
| Platform detail | `docs/ops/runbooks/ROLLBACK.md` · `docs/OPERATIONS_RUNBOOK.md` |
| Date | 2026-08-02 |

---

## 1. Principles

1. **Prefer image / artefact rollback** over hot-patching engines, scoring, or trust presentation during an incident.  
2. Keep the **API contract freeze** (`/api/v1`) unless the API deploy itself is the failure.  
3. Do **not** reintroduce fabrication, aliases, auth theatre, or silent demo tickers under rollback pressure.  
4. Communicate **Research Mode / closed-beta** status to pilot desks — never imply Commercial GA during recovery.  
5. Quarantine the broken build; do not re-promote without fix + smoke.

---

## 2. Rollback triggers

Execute rollback (or pause pilot) when any of the following is true:

| Trigger | Severity | Notes |
|---|---|---|
| Trust regression: fabricated values, BQ aliases, silent demo tickers | **S1** | Immediate |
| Auth / commerce theatre restored (fake signup success, purchase path) | **S1** | Immediate |
| RBAC / palette leak of AUX to unauthorized roles | **S1** | Immediate |
| Sustained login failure for provisioned users | **S2** | After brief triage (~15 min) |
| Sustained analyse / reports 5xx blocking primary journey | **S2** | After brief triage |
| Failed deploy smoke on go-live checklist critical items | **S2** | Do not leave bad build live |
| Incorrect version channel / wrong artefact promoted | **S2** | Rollback to known-good tag |
| Security incident requiring prior build | **S1** | Follow security runbook in parallel |

**Do not** roll back solely because of documented limitations (empty risk rows, incomplete trust ladder, illustrative pricing).

---

## 3. Pre-rollback readiness (before go-live)

- [ ] Identify **previous known-good** web artefact / image tag / commit SHA.  
- [ ] Identify known-good API artefact if API is co-deployed.  
- [ ] Confirm rollback script / compose procedure available (`scripts/rollback_production.sh` or environment equivalent).  
- [ ] Export beta / invite snapshot if invite state is mutable.  
- [ ] Document who can authorize rollback (Release Board / on-call).  
- [ ] Keep this plan + Support Runbook in the incident channel bookmarks.

---

## 4. Rollback procedure

### 4.1 Announce

1. Declare incident severity (S1/S2).  
2. Announce rollback in the incident channel.  
3. Notify pilot administrators that Research Mode may be briefly unavailable.

### 4.2 Execute (web-focused closed-beta UI freeze)

Platform reference pattern:

```bash
# Example — set previous known-good tags for your environment
export DSP_PREVIOUS_IMAGE_TAG=<prior-api-tag>
export DSP_PREVIOUS_IMAGE_TAG_WEB=<prior-web-tag>
./scripts/rollback_production.sh
```

If your environment uses a different orchestrator:

1. Redeploy previous known-good **web** artefact (commit/tag certified for prior good state).  
2. If API was changed in the bad release, redeploy previous known-good **API** as well.  
3. Restore config / env from last known-good if the bad release changed flags (especially registration, contact publish, commerce).  
4. Re-import beta snapshot if invite / provisioned state was lost.  
5. Disable any newly opened public contact channels if toggled in error.

### 4.3 Hard rules during rollback

| Do | Do not |
|---|---|
| Restore certified build | Hot-fix fabrication/aliases under pressure |
| Keep `/api/v1` compatibility | Redesign engines mid-incident |
| Preserve honest unavailable messaging | Enable self-serve registration “to unblock” |
| File incident note with SHAs | Quietly re-tag broken build as GA |

Detail: `docs/ops/runbooks/ROLLBACK.md`.

---

## 5. Verification after rollback

Run in order; all must pass before declaring recovery:

### 5.1 Platform health

- [ ] Web serves primary routes (HTTP 200 on marketing/login at minimum).  
- [ ] API `/health` (and `/health/ready` if used) **200**.  
- [ ] No elevated 5xx on web and API.

### 5.2 Auth & access

- [ ] Provisioned pilot user: `/login` → `/dashboard`.  
- [ ] Unprovisioned credentials still fail honestly.  
- [ ] `/signup` remains Request Access honesty (no account creation).

### 5.3 Research smoke

- [ ] `/analysis` requires explicit ticker (no silent default).  
- [ ] Sample analyse for a known symbol returns API-backed content or honest unavailable — **not** fabricated BQ.  
- [ ] `/research/institutional` loads.  
- [ ] `/portfolio` coverage language intact.  
- [ ] Palette: AUX not searchable for analyst role.

### 5.4 Trust spot-check

- [ ] No restored auth/commerce theatre.  
- [ ] Empty / unavailable states still say **Data unavailable.** where appropriate.  
- [ ] Contact channels unpublished unless intentionally published with real mailboxes.

### 5.5 Communications

- [ ] Pilot desks notified: rollback complete + Research Mode status.  
- [ ] Incident note filed: symptoms, commit SHAs / image tags, trust impact (CV/RS).  
- [ ] Broken build quarantined; defect ticket linked.

---

## 6. Post-rollback

1. Root-cause analysis for S1/S2.  
2. Fix on a branch; re-run primary Vitest set + production build.  
3. Re-deploy only after go-live checklist pre-flight green.  
4. Update Release Board notes if posture temporarily paused.  
5. Do **not** expand Commercial GA claims while recovering.

---

## 7. Rollback decision owners

| Role | Authority |
|---|---|
| On-call Engineering | Execute technical rollback |
| Trust / Governance | Confirm trust impact / messaging |
| Release Board / Pilot Owner | Authorize pilot pause and external comms |

If owners disagree under S1 trust breach: **default to rollback** to last certified honest build.
