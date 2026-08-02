# Known Limitations — DSP AI Indicator Version 1.0.0

| Field | Value |
|---|---|
| Product | DSP AI Indicator |
| Version | **1.0.0** |
| Authority | [`RC3_FINAL_CERTIFICATION_REPORT.md`](./RC3_FINAL_CERTIFICATION_REPORT.md) |
| Certification decision | **PASS WITH CONDITIONS** |
| Authorized posture | Closed-beta / institutional pilot UI freeze (Research Mode) |
| Date | 2026-08-02 |

This document is the client-facing and operational **limitations packet**. Ship it with every pilot desk. Distinguishes three tiers: what is accepted for closed beta, what blocks Commercial GA, and what is deferred roadmap.

---

## 1. Closed-beta limitations (accepted for pilot)

These items are **known and accepted** for Version 1.0.0 closed-beta / institutional pilot. They are **not** defects to “fill with invented numbers.”

| ID | Limitation | Guidance |
|---|---|---|
| CB-01 | **Admin-provisioned access only** | Request Access (`/signup`) does not create accounts. Admins provision users before pilot start. |
| CB-02 | **No public password reset / email verification** | Forgot / reset / verify surfaces are honesty messaging only. Admins handle credential recovery. |
| CB-03 | **Contact channels may be unpublished** | When `SUPPORT_CONTACT.channelsPublished` is `false`, no public mailto is rendered. Use internal support path. |
| CB-04 | **Pricing illustrative — not purchasable** | No checkout. Editions are not for sale in this posture. |
| CB-05 | **Honest Data unavailable.** | Missing mandatory or stage metrics show **Data unavailable.** / coverage language — never fabricate (CV-001, CV-005). |
| CB-06 | **Book 07 typed risk dimensions empty** | Frontend refuses aliases from Financial Strength; typed risk rows remain unavailable until analyse exposes risk-stage metrics. |
| CB-07 | **Partial BQ / Management / Moat sub-metrics** | Aggregator summaries may omit named Book metrics; UI shows unavailable rather than sibling-stage aliases. |
| CB-08 | **Trust ladder not universal** | Strongest on Company Analysis summary and Institutional Reports; Dashboard, Portfolio, Research Workspace, and IRD still incomplete vs universal bar. |
| CB-09 | **AUX / Advisor outside primary IA** | Routes may exist in codebase; not palette-searchable for primary analyst journey. Out of closed-beta product scope. |
| CB-10 | **Research Mode messaging tension** | Recommendation chrome may coexist with Research Mode “no buy/sell” disclaimers — product-comms residual (HIGH, not CRITICAL for pilot). |
| CB-11 | **Thin client** | No valuation, recommendation, or AI reasoning in the browser. All analytical intelligence comes from `/api/v1`. |
| CB-12 | **OneDrive / local build quirks** | Incremental `.next` builds may fail with `readlink` EINVAL on some OneDrive hosts — use clean build. |

**Pilot messaging:** describe the product as **closed-beta Research Mode**, not Commercial GA.

---

## 2. Commercial GA requirements (outstanding conditions)

These must be closed with evidence before unrestricted **Commercial public GA** claims. Until then, Commercial GA would be a **FAIL** (consistent with RC3 §15).

| # | Condition | Evidence expected | Primary refs |
|---|---|---|---|
| GA-C1 | Headed Visual QA screenshot matrix (Desktop/Laptop/Tablet/Mobile × Light/Dark) attached or CI Percy/Playwright | Screenshot archive or CI artefact | `VISUAL_QA_MATRIX.md` · `SCREENSHOT_APPROVAL.md` |
| GA-C2 | Firefox + Safari physical smoke on login, dashboard, analysis, portfolio, reports | Headed smoke log | `BROWSER_CERTIFICATION.md` |
| GA-C3 | Compact trust-ladder / Research Mode chrome on Dashboard, Portfolio, Research Workspace, and IRD | Code + certification re-check | RC3 §5 / §15 |
| GA-C4 | Published Lighthouse / field CWV run on stable production (or staging) URL; axe contrast progression beyond jsdom-only | LHCI report + a11y field evidence | `PERFORMANCE_CERTIFICATION.md` · `ACCESSIBILITY_CERTIFICATION.md` |
| GA-C5 | Self-serve commercial entitlements (if claiming public GA): registration, reset/verify, published support channels, purchasable packaging — **or** explicit decision to remain invite-only | Product / governance sign-off | RC3 §15 · GO-LIVE |
| GA-C6 | Fix stale `commercial.test.tsx` AAPL onboarding assertion | Green test matching honest copy | RC3 §15 #5 |
| GA-C7 | Client-facing limitations packet + release board sign-off for broader release | This file + `RELEASE_BOARD.md` | GO-LIVE exit criteria |

**Non-negotiable before GA messaging:** do not reintroduce auth/commerce theatre or silent demo tickers (RC3 condition #6).

---

## 3. Deferred roadmap items

Not required to keep the closed-beta freeze. Track for later product increments; do not treat as silent scope of 1.0.0 pilot.

| Item | Notes |
|---|---|
| Collapse classic `/research/[ticker]` into primary Analysis IA | Future enhancement per RC3 IA section |
| Full WCAG 2.2 AA marketing claim | Requires field SR smoke (NVDA/VoiceOver) + contrast gate + route axe |
| Hard-fail Lighthouse CI asserts | Keep warn until staging URL + auth stubs stable |
| AUX / Advisor Design System unification | Hidden from primary palette; mixed `ds`/`ui` acceptable for pilot |
| Backend completeness for Book 04–07 named metrics | Engine/API work — out of UI freeze scope |
| Public commerce / edition checkout | Explicitly out of closed-beta posture |
| Playwright + `@axe-core/playwright` full-route gate | Recommended in a11y certification |
| Marketing hero visual redesign | Cosmetic; out of redesign scope for this release |

---

## 4. What is *not* a bug

| Observation | Correct interpretation |
|---|---|
| Empty risk typed rows | Honesty until risk-stage metrics exist |
| “Data unavailable.” on sub-metrics | CV-001 preferred over fabrication |
| Request Access does not log the user in | By design for closed beta |
| Pricing shows not-for-purchase | By design |
| AUX routes return 404 or forbidden for analyst | RBAC / IA by design |
| Trust ladder missing on some shells | Known HIGH residual — condition for GA, accepted for pilot |

---

## 5. How to use this packet

1. Attach to every pilot onboarding email / desk kickoff.  
2. Reference from [`PILOT_USER_GUIDE.md`](./PILOT_USER_GUIDE.md) and [`SUPPORT_RUNBOOK.md`](./SUPPORT_RUNBOOK.md).  
3. When triaging “missing numbers,” confirm whether the field is backend-unavailable (expected) vs trust regression (escalate).  
4. Before any external “Commercial GA” language, re-open §2 and require Release Board sign-off.

---

## 6. Alignment

| Reference | Posture |
|---|---|
| RC3 Known Limitations (§12) | Superset restated here with GA vs pilot split |
| GO-LIVE Known Limitations | Consistent |
| Visual QA / Browser / A11y / Perf certs | Conditions mirrored in §2 |
