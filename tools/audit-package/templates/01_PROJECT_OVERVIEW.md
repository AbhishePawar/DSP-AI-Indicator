# 01 — Project Overview

| Field | Value |
|---|---|
| Product | DSP AI Indicator |
| Tagline | Complex Analysis. Simple Decisions. |
| Category | Explainable AI investment **research** platform — **not** a stock-tip service |
| Version under audit | **1.0.0** |
| Default product mode | **Research Mode** (PR1.0) |
| Web app | `apps/web` (Next.js) — version channel `2.0.0` in `package.json` |
| Platform façade | `packages/dsp_platform` |
| Public API surface | `/api/v1` via `packages/api_platform` |

---

## Purpose

DSP AI Indicator delivers institutional-style investment research: authenticated market/fundamental data, business-quality and risk frameworks, valuation transparency, explainability, and audit/provenance — governed by Tier-0 Core Values (CV-001…CV-010) and Research Standards (RS-001…RS-010).

It is intentionally **not** positioned as:

- Unrestricted commercial self-serve brokerage or tip service
- Browser-side valuation / recommendation engine
- Purchasable edition storefront in the 1.0.0 closed-beta posture

---

## Product posture (Version 1.0.0)

| Claim | Status |
|---|---|
| Closed-beta / institutional pilot | **GO** (PASS WITH CONDITIONS) |
| Research Mode messaging | Required |
| Admin-provisioned access | Required (signup does not create accounts) |
| Pricing / checkout | Illustrative — **not purchasable** |
| Unrestricted Commercial GA | **REJECTED** |

Sources: `docs/releases/GA_CERTIFICATION_REPORT.md`, `docs/releases/RELEASE_BOARD.md`, `docs/releases/KNOWN_LIMITATIONS.md`.

---

## Primary user journeys (pilot IA)

1. **Dashboard** → situational overview (trust-ladder universality still open as GA condition)
2. **Company Analysis** → flagship research surface (strongest trust remediation post-RC2/RC3)
3. **Research / Institutional Reports** → report objects, explainability, provenance
4. **Portfolio** → portfolio intelligence (session/demo constraints apply; see limitations)

AUX / Advisor surfaces may exist in code but are outside primary closed-beta IA (palette demotion / RBAC).

---

## Trust & compliance framing

- Prefer **Data unavailable.** / **Unable to calculate.** over invented completeness (CV-001, CV-005).
- Source before score; never calculate on incomplete mandatory inputs (CV-002).
- Explainability before recommendation (CV-003).
- Determinism and auditability over opaque “AI confidence” (CV-004, CV-006, CV-007).
- Governance over convenience — no certification bypasses (CV-009).

Legal / policy packet (examples under `docs/`): investment research disclaimer, privacy, terms, risk disclosure, DPDP-related architecture notes — treat as compliance evidence, not marketing claims of Commercial GA.

---

## What auditors should expect to find

| Layer | Expectation |
|---|---|
| Web (`source/web`) | Thin client: presentation, auth honesty, feature flags, `/api/v1` clients |
| API / platform (`source/packages`) | Research engines, composition, auth/security, institutional routers |
| Docs | Architecture Bible, CV/RS, release certs, REP-002 ontology |
| Workflows | CI for frontend, security, release engineering |

See [`02_ARCHITECTURE.md`](./02_ARCHITECTURE.md) and [`09_AUDIT_GUIDE.md`](./09_AUDIT_GUIDE.md).
