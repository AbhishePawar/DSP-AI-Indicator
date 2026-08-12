# 04 — Feature Matrix (Pilot Scope)

Aligned with Version **1.0.0** closed-beta / institutional pilot. This is a scope map for auditors — not a marketing feature list.

Legend: **IN** = in pilot scope · **COND** = present with conditions · **OUT** = not authorized / deferred · **AUX** = code may exist, outside primary IA.

---

## Product capabilities

| Feature | Status | Notes |
|---|---|---|
| Research Mode default | **IN** | PR1.0; required messaging |
| Company Analysis (flagship) | **IN** | Trust remediations post-RC2/RC3 |
| Institutional / research reports | **IN** | Explainability strongest here |
| Dashboard | **COND** | Trust ladder not universal (GA-C3) |
| Portfolio intelligence | **COND** | Session/demo constraints; no broker sync |
| Research workspace | **COND** | Ladder / desk completeness residual |
| Admin provisioning | **IN** | Required; signup ≠ account creation |
| Self-serve registration / reset / verify | **OUT** | Honesty messaging only (CB-02) |
| Public checkout / purchasable editions | **OUT** | Illustrative pricing (CB-04); GA-C5 |
| Thin-client `/api/v1` analytics | **IN** | Backend owns engines |
| Client-side valuation / recommendation | **OUT** | Architecture forbidden |
| Advisor / client CRM | **AUX** | Demo/session; `NEXT_PUBLIC_ADVISOR_DEMO` |
| PDF/DOCX export | **OUT**/deferred | Backend-deferred per limitations |
| Broker APIs / trading / tax / alerts | **OUT** | Explicitly not in scope |
| Silent demo tickers (e.g. AAPL defaults) | **OUT** | Must remain absent (RC3 condition) |

---

## Certification / evidence features

| Evidence area | Pilot | Commercial GA |
|---|---|---|
| Production `next build` | PASS | Required + hygiene |
| Primary Vitest set | PASS | + fix stale commercial test (GA-C6) |
| Chrome / Edge smoke | PASS | Required |
| Firefox / Safari physical smoke | Code-review / pending | **Required** (GA-C2) |
| Headed Visual QA screenshot archive | Matrix only | **Required** (GA-C1) |
| A11y automation (vitest-axe) | Established | + field SR / contrast (GA-C4) |
| Field LHCI / CWV | Unpublished | **Required** (GA-C4) |
| Universal trust ladder | Partial | **Required** (GA-C3) |

---

## Research standards surface (reports)

Reports are expected to cover RS-001…RS-010. Missing RS section = Research Report Validation **FAIL** (governance). Auditors should verify presentation honesty (unavailable vs fabricate), not invent metrics.

Mandatory header concepts (product constitution / RS): Price · IV · MoS · Fair Value Range · CAGR · Confidence · Overall Score · Research Status · Recommendation — subject to Research Mode / availability rules.

---

## Feature flags (audit hint)

Inspect `apps/web/src/lib/featureFlags.ts` (copied under `source/web/`) and `.env.example` files. Closed-beta flags and Research Mode must not be bypassed for “demo completeness.”
