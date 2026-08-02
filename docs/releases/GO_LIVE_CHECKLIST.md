# GO-LIVE CHECKLIST — DSP AI Indicator Version 1.0.0

| Field | Value |
|---|---|
| Authority | `docs/releases/RC3_FINAL_CERTIFICATION_REPORT.md` |
| Certification decision | **PASS WITH CONDITIONS** |
| Authorized posture | Closed-beta / institutional pilot UI freeze (Research Mode) |
| Not authorized | Unrestricted commercial public GA / self-serve commerce |

---

## Version

| Item | Value |
|---|---|
| Product | DSP AI Indicator |
| Version | **1.0.0** |
| `VERSION` file | `v1.0.0` |
| Certification date | 2026-08-01 |

---

## Release Branch

| Item | Value |
|---|---|
| Branch | `cursor/p6-1-commercial-readiness` |
| Tip at RC3 cert start | `cdc7d44` |
| Required ancestry | Includes RC3 commits `b3383e1` … `cdc7d44` plus certification commit |

---

## Release Tag

| Item | Guidance |
|---|---|
| Proposed tag | `v1.0.0` |
| Tag when | After this checklist’s Deployment pre-flight is green on the release commit |
| Tag message | `DSP AI Indicator 1.0.0 — closed-beta institutional UI freeze` |
| Do not tag as | “Commercial GA” / “Public self-serve” |

---

## Deployment Checklist

### Pre-flight

- [ ] Confirm branch tip includes RC3 Final Certification commit and green CI (if wired)
- [ ] Confirm `VERSION` == `v1.0.0`
- [ ] Run `apps/web` production build (`next build`) on clean `.next` (avoid OneDrive stale cache)
- [ ] Run primary Vitest set: shell, dashboard, portfolio-intelligence, company-analysis, institutional-reports, institutional-dashboard, ds, a11y-responsive, mapResearchView
- [ ] Confirm feature flags / env for closed beta (`apps/web/.env` / deployment secrets) — no public registration endpoints enabled
- [ ] Confirm `SUPPORT_CONTACT.channelsPublished` remains `false` until real mailboxes exist
- [ ] Confirm pricing remains illustrative (not checkout-enabled)
- [ ] Backend `/api/v1` health check green in target environment
- [ ] Admin accounts provisioned for pilot desks (no reliance on Request Access form submission)

### Deploy

- [ ] Deploy web app artefact from certified commit
- [ ] Deploy/verify API gateway routing to frozen `/api/v1`
- [ ] Smoke: `/login` → provisioned user → `/dashboard`
- [ ] Smoke: `/analysis` requires explicit ticker (no silent default)
- [ ] Smoke: `/research/institutional` loads analyse for selected symbol
- [ ] Smoke: `/portfolio` shows coverage language (not Health/Compounders marketing)
- [ ] Smoke: command palette does not list AUX Advisor/Launch/Screening for analyst role
- [ ] Smoke: `/signup` is Request Access honesty (no account creation)
- [ ] Smoke: `/contact` shows unpublished channels when not published
- [ ] Verify Research Mode disclaimers visible on dashboard / research surfaces

### Post-deploy gate

- [ ] No CRITICAL trust defects in smoke (fabricated BQ / fake auth success)
- [ ] Error/empty states show **Data unavailable.** / coverage copy — not invented scores
- [ ] Rollback plan reviewed (see Rollback Checklist)

---

## Monitoring Checklist

- [ ] Application uptime / 5xx rate on web and API
- [ ] Auth login failure rate (401/403) — expect provisioned-only traffic
- [ ] Analyse latency and error rate (`/api/v1/analyse`)
- [ ] Portfolio intelligence error rate
- [ ] Client error boundary / observability logs (correlation IDs)
- [ ] Synthetic check: login + dashboard + analysis empty-state path
- [ ] Alert on sudden spike of “success” auth flows that imply registration (should not exist)
- [ ] Disk / CDN cache health for static assets

---

## Rollback Checklist

- [ ] Identify previous known-good web artefact / tag
- [ ] Revert web deployment to prior artefact (keep API contract freeze)
- [ ] Confirm `/api/v1` compatibility with rolled-back UI
- [ ] Disable any newly opened public contact channels if they were toggled in error
- [ ] Notify pilot desks of rollback + Research Mode status
- [ ] File incident note: symptoms, commit SHAs, trust impact (CV/RS)
- [ ] Do **not** hot-fix fabrication/aliases under rollback pressure — restore certified build

---

## Known Limitations (ship with pilot packet)

1. Admin-provisioned access only — Request Access does not create accounts.  
2. No public password reset / email verification APIs.  
3. Contact channels may be unpublished.  
4. Pricing is illustrative — not for purchase.  
5. Many research sub-metrics show **Data unavailable.** until backend stages expose them — this is honest, not a bug to “fill.”  
6. Book 07 typed risk scores unavailable without dedicated risk-stage metrics.  
7. Trust ladder not yet identical on every analytical page (strongest on Reports / CA summary).  
8. Visual QA screenshot matrix and Firefox/Safari formal smoke still open conditions for GA.  
9. AUX/Advisor routes exist but are outside primary closed-beta IA.  
10. Thin client: no browser valuation, recommendation, or AI reasoning.

---

## Post-launch Monitoring

| Window | Actions |
|---|---|
| First 24 hours | Watch auth + analyse error budgets; desk feedback on empties vs fabrication; confirm no theatre regressions |
| First 7 days | Collect pilot UX notes; triage HIGH residuals (universal ladder, VQA); do not expand commercial claims |
| Before GA promotion | Close conditions in `RC3_FINAL_CERTIFICATION_REPORT.md` §15; re-run certification decision |

### Exit criteria to lift “closed-beta only” posture

- [ ] Conditions 1–4 in certification report closed with evidence  
- [ ] Client-facing limitations packet updated  
- [ ] Product/governance sign-off for broader release  

Until then, all external messaging must describe **closed-beta Research Mode**, not commercial GA.
