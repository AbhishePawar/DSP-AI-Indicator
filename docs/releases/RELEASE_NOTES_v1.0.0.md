# Release Notes — DSP AI Indicator Version 1.0.0

| Field | Value |
|---|---|
| Product | DSP AI Indicator |
| Version | **1.0.0** (`VERSION` → `v1.0.0`) |
| Release posture | **Closed-beta / institutional pilot** (Research Mode) |
| Certification | [`RC3_FINAL_CERTIFICATION_REPORT.md`](./RC3_FINAL_CERTIFICATION_REPORT.md) — **PASS WITH CONDITIONS** |
| Branch | `cursor/p6-1-commercial-readiness` |
| Date | 2026-08-02 |
| Audience | Pilot desks, administrators, release board, support |

---

## 1. Version summary

DSP AI Indicator **1.0.0** is the first certified closed-beta UI freeze for institutional Research Mode. The thin-client web application consumes frozen `/api/v1` only. Access is **admin-provisioned**. Pricing and packaging are **illustrative — not for purchase**. Self-serve commercial onboarding is **not** enabled.

**Authorized:** closed-beta / institutional pilot UI freeze with written limitations.  
**Not authorized:** unrestricted Commercial public GA, public checkout, or claims that headed Visual QA / Firefox-Safari physical smoke / field CWV are complete.

Companion package: [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md) · [`GO_LIVE_CHECKLIST.md`](./GO_LIVE_CHECKLIST.md) · [`RELEASE_BOARD.md`](./RELEASE_BOARD.md).

---

## 2. Major capabilities

### 2.1 Primary research journey

| Surface | Route | Capability |
|---|---|---|
| Dashboard | `/dashboard` | Executive overview, Research Mode banner, next investigation steps |
| Company Analysis | `/analysis` | Flagship analyse workspace over `/api/v1/analyse`; explicit ticker required (no silent demo defaults) |
| Research Workspace | `/research` | Research library / session history |
| Research Reports | `/research/institutional` | Institutional report publication / export surface (strongest trust ladder) |
| Research Panels (IRD) | `/research/institutional/dashboard` | Supporting RS panel view — not a competing primary desk |
| Portfolio | `/portfolio` | Research coverage / research-available holdings language (not marketing Health/Compounders claims) |
| Settings / Profile | `/settings`, `/profile` | Preferences and identity |

### 2.2 Trust & honesty (closed-beta bar)

- No fabricated Business Quality sub-dimensions — aggregator-only sourcing; **Data unavailable.** when metrics absent (CV-001).
- Auth / marketing honesty: Request Access does not create accounts; no password-reset / verify theatre; contact channels may be unpublished; pricing not purchasable.
- Command palette and shell nav are RBAC-filtered; AUX Advisor / Launch / Screening routes are not primary-searchable.
- Thin client preserved: no browser valuation, recommendation, or AI reasoning engines.

### 2.3 Quality gates established

| Area | Artefact | Closed-beta status |
|---|---|---|
| Final certification | `RC3_FINAL_CERTIFICATION_REPORT.md` | PASS WITH CONDITIONS |
| Visual QA | `VISUAL_QA_MATRIX.md` · `SCREENSHOT_APPROVAL.md` | PASS WITH CONDITIONS (headed matrix open) |
| Browser | `BROWSER_CERTIFICATION.md` | Chrome/Edge live PASS; Firefox/Safari code-review |
| Accessibility | `ACCESSIBILITY_CERTIFICATION.md` | Automation established (`test:a11y`); full-route axe open |
| Performance | `PERFORMANCE_CERTIFICATION.md` | Automation established (`test:perf`); field LHCI/CWV open |
| Go-live | `GO_LIVE_CHECKLIST.md` | Operational pre-flight for pilot deploy |

---

## 3. Closed-beta scope

| In scope | Out of scope |
|---|---|
| Admin-provisioned Research Mode UI | Self-serve signup / password reset / email verify |
| Thin-client `/api/v1` research workflow | Client-side scoring or recommendation engines |
| Primary IA: Dashboard → Analysis → Research → Portfolio | AUX Advisor product completion |
| Honest empty / unavailable states | Filling missing backend metrics in the UI |
| Illustrative packaging language | Public purchase / checkout |
| Chromium (Chrome/Edge) pilot browsers | Claiming physical Firefox/Safari GA certification |

Pilot desks receive: provisioned credentials, this release packet, [`PILOT_USER_GUIDE.md`](./PILOT_USER_GUIDE.md), and [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md).

---

## 4. Known limitations (summary)

Full detail: [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md).

1. Admin-provisioned access only — Request Access does not create accounts.  
2. No public password reset / email verification APIs.  
3. Contact channels may be unpublished (`channelsPublished: false`).  
4. Pricing is illustrative — not for purchase.  
5. Many research sub-metrics show **Data unavailable.** until backend stages expose them — prefer honesty over fill (CV-001/CV-005).  
6. Book 07 typed risk dimensions unavailable without dedicated risk-stage metrics.  
7. Trust ladder chrome is strongest on Company Analysis summary and Institutional Reports; not yet universal on Dashboard, Portfolio, Research Workspace, and IRD.  
8. Headed Desktop/Tablet/Mobile × Light/Dark screenshot archive still open for Commercial GA.  
9. Firefox / Safari physical smoke pending.  
10. Field Lighthouse / Core Web Vitals on a stable production URL not yet published as GA evidence.  
11. AUX / Advisor surfaces exist but are outside primary closed-beta IA.  
12. Recommendation chrome vs Research Mode “no buy/sell” messaging tension remains a product-comms residual.

---

## 5. Upgrade / deploy notes

1. Deploy only from a commit that includes RC3 certification ancestry and subsequent release-doc commits on `cursor/p6-1-commercial-readiness` (or the tagged release commit).  
2. Confirm `VERSION` == `v1.0.0`.  
3. Follow [`GO_LIVE_CHECKLIST.md`](./GO_LIVE_CHECKLIST.md) and [`OPERATIONS_RUNBOOK.md`](./OPERATIONS_RUNBOOK.md).  
4. Provision pilot accounts before go-live — do not rely on `/signup`.  
5. Keep public registration, checkout, and published contact channels disabled until GA conditions close.  
6. Proposed tag message (when tagging): `DSP AI Indicator 1.0.0 — closed-beta institutional UI freeze` — **do not** tag as Commercial GA.

---

## 6. Support & operations

| Document | Use |
|---|---|
| [`ADMINISTRATOR_GUIDE.md`](./ADMINISTRATOR_GUIDE.md) | Provisioning, roles, admin duties |
| [`PILOT_USER_GUIDE.md`](./PILOT_USER_GUIDE.md) | Desk research workflow |
| [`SUPPORT_RUNBOOK.md`](./SUPPORT_RUNBOOK.md) | Triage and escalation |
| [`ROLLBACK_PLAN.md`](./ROLLBACK_PLAN.md) | Rollback triggers and verification |
| [`OPERATIONS_RUNBOOK.md`](./OPERATIONS_RUNBOOK.md) | Deploy verification, health, monitoring |

---

## 7. Release recommendation

**Ship as closed-beta / institutional pilot** under Research Mode with admin-provisioned access and the limitations packet.

**Do not** promote Version 1.0.0 as unrestricted Commercial public GA until outstanding conditions in [`RC3_FINAL_CERTIFICATION_REPORT.md`](./RC3_FINAL_CERTIFICATION_REPORT.md) §15 and [`GA_004_COMPLETION_REPORT.md`](./GA_004_COMPLETION_REPORT.md) are closed with evidence.
