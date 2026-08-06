# Pilot User Guide — DSP AI Indicator Version 1.0.0

| Field | Value |
|---|---|
| Product | DSP AI Indicator |
| Version | **1.0.0** |
| Audience | Closed-beta / institutional pilot desks |
| Mode | **Research Mode** — not unrestricted Commercial GA |
| Date | 2026-08-02 |
| Must-read companion | [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md) |

---

## 1. What you are piloting

You are using a **closed-beta institutional Research Mode** UI. Access is **admin-provisioned**. The application is a **thin client**: research values, scores, and recommendations come from the backend `/api/v1` — the browser does not invent valuation or buy/sell advice.

**This is not** a public self-serve commercial product. Pricing pages (if visible) are illustrative and **not for purchase**.

---

## 2. Getting access

1. Your administrator provisions your account (email / credentials).  
2. Sign in at `/login`.  
3. If you cannot sign in, contact your **administrator** — do not expect the forgot-password or Request Access forms to create or reset accounts.  
4. `/signup` is a Request Access message only; it does not open a pilot seat.

---

## 3. Research workflow (primary journey)

Recommended path:

```text
Dashboard → Company Analysis → Research Workspace / Reports → Portfolio (if entitled)
```

| Step | Where | What to do |
|---|---|---|
| 1 | `/dashboard` | Orient; note Research Mode banner; choose next investigation |
| 2 | `/analysis` | Enter an **explicit ticker** (no silent demo default). Run company analysis |
| 3 | `/research` | Use Research Workspace for library / session history |
| 4 | `/research/institutional` | Open Institutional Research Reports — strongest explainability / trust ladder surface |
| 5 | `/research/institutional/dashboard` | Optional supporting Research Panels (IRD) — not the primary company desk |
| 6 | `/portfolio` | Review research coverage for holdings (if your role includes portfolio access) |

Command palette (Ctrl+K / Cmd+K) searches **RBAC-allowed** primary routes. Advisor / Launch / Screening AUX tools are intentionally outside the primary pilot journey.

---

## 4. Trust ladder — how to read the product

DSP is built on **Data Authenticity First** (CV-001) and related Tier-0 values.

| You may see | Meaning |
|---|---|
| **Data unavailable.** | Mandatory or stage data is missing — the UI refuses to fabricate a number |
| **Unable to calculate.** | Calculation cannot proceed honestly on incomplete inputs |
| Coverage / research-available language | Describes what research coverage exists — not a marketing “health score” |
| Trust ladder / source badges (where present) | Traceability of sources and research status — strongest on Company Analysis summary and Institutional Reports |
| Empty Book 07 risk typed rows | Expected until backend risk-stage metrics exist — **not** a license to invent scores |

**Do not** treat empty cells as a defect that should be “filled.” Prefer unavailable over fabrication.

### Research Mode reminder

Research Mode surfaces may include committee / recommendation chrome from the API alongside disclaimers that this is **research tooling**, not a personal buy/sell order. When in doubt, treat outputs as research artefacts for human judgment — not automated execution instructions.

---

## 5. Coverage expectations

| Area | Pilot expectation |
|---|---|
| Market / analyse path | API-backed when backends are healthy |
| Business Quality / Management / Moat | Stage-scoped; many named sub-metrics may be unavailable |
| Risk typed dimensions | Often **Data unavailable.** (honest) |
| Valuation / MoS / Fair Value | Shown when API provides them; otherwise unavailable |
| Portfolio | Coverage language for research-available holdings |
| Trust ladder on every page | **Not yet universal** — use Reports / Analysis summary when auditing provenance |

Full list: [`KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md).

---

## 6. Known limitations (pilot-facing)

1. Admin-provisioned access only.  
2. No self-serve password reset or email verification.  
3. Support contact channels may be unpublished on the public site.  
4. Not for purchase.  
5. Many metrics show **Data unavailable.** until backends expose them.  
6. Trust ladder chrome incomplete on some shells (Dashboard, Portfolio, Workspace, IRD).  
7. Firefox / Safari not formally smoke-certified for Commercial GA; Chrome / Edge are the primary pilot browsers.  
8. AUX Advisor product is out of primary pilot scope.

---

## 7. How to report issues

### Before filing

1. Confirm whether the value is **Data unavailable.** (expected) vs a **fabricated or contradictory** number (defect).  
2. Note ticker, route URL, time (UTC), browser, and screenshot if possible.  
3. Capture any request / correlation ID shown in errors (do not paste full research payloads into public channels).

### Where to report

| Channel | Use |
|---|---|
| Your pilot administrator | Access, credentials, role, “menu missing” |
| Pilot support inbox / ticket system (internal) | Functional defects, performance, trust concerns |
| Immediate escalate | Any invented scores, fake “success” account creation, or restored purchase theatre |

Severity guidance for desks:

| Severity | Examples |
|---|---|
| Critical | Fabricated financial numbers; auth claiming success without provisioning; site down for all pilots |
| High | Primary analysis path broken; systematic wrong labels on BQ/Risk |
| Medium | Layout glitch; incomplete trust chrome already documented |
| Low | Cosmetic density; illustrative pricing copy questions |

See [`SUPPORT_RUNBOOK.md`](./SUPPORT_RUNBOOK.md) for formal triage.

---

## 8. Accessibility & browsers

- Prefer **Chrome** or **Microsoft Edge** (Latest) for pilot work.  
- Keyboard: Escape closes dialogs / mobile nav; focus rings should be visible.  
- Reduced-motion: respect OS preference where implemented.  
- If you use Firefox or Safari, report browser-specific breakage — physical certification for those engines is still an open GA condition.

---

## 9. Quick FAQ

**Q: Why can’t I register myself?**  
A: Closed beta is admin-provisioned by design.

**Q: Why is risk empty?**  
A: Typed risk metrics are not aliased from other stages. Unavailable is correct until the API exposes them.

**Q: Can I buy an edition?**  
A: No — packaging is illustrative for 1.0.0 closed beta.

**Q: Is this investment advice?**  
A: Research Mode tooling for institutional research workflows. Human judgment remains required; follow your firm’s compliance policy.
