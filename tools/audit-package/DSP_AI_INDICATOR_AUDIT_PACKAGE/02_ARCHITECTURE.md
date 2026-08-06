# 02 — Architecture (Thin Client & Research Ownership)

| Field | Value |
|---|---|
| Authority | `docs/ARCHITECTURE_BIBLE.md`, `docs/ARCHITECTURE_GOVERNANCE.md`, EPIC-015 thin-client remediation |
| Boundary | Browser **must not** own valuation, recommendation, or AI reasoning |
| API contract | Frozen `/api/v1` |
| Audit mode | Evaluation / verification only — **no platform redesign** |

---

## 1. Architectural principle

```text
Browser (apps/web)
  → presentation, auth UX honesty, feature flags, Research Mode chrome
  → HTTP clients to /api/v1 only
  ✗ no valuation engines
  ✗ no recommendation engines
  ✗ no AI committee / scoring logic in the client

API (api_platform) + DSPPlatform façade
  → orchestration, research objects, reports, portfolio intelligence
  → engines under packages/* (moat, management, EQI, valuation, risk, …)
  → authenticated data via data_engine ports/providers
```

**Backend owns analytics.** The web app is a **thin client**.

GA certification spot-checks reaffirm: thin client `/api/v1` **PASS**; no browser valuation/recommendation engines for Commercial GA engineering assessment.

---

## 2. Dependency direction (platform)

High-level (from product README / package governance):

```text
contracts ← core ← data_engine
                 ← research / fundamental / economic / … engines
                 ← ai_committee / recommendation / decision_intelligence
                 ← dsp_platform   (public façade)
                 ← api_platform   (HTTP /api/v1)
```

Frontend applications import **network contracts**, not engine internals. External Python consumers should prefer `dsp_platform` + `contracts`.

---

## 3. Web structure (audit-relevant)

Under `source/web/` (mirrored from `apps/web/src` and related):

| Area | Role |
|---|---|
| `app/` | Next.js App Router pages (dashboard, analysis, research, portfolio, auth, admin, …) |
| `components/` | UI / DS / analysis presentation |
| `lib/` | API clients, auth session, feature flags, a11y/perf helpers — **not** engines |
| `foundation/` | routes, tokens, layout, UX foundations |
| `hooks/` · `providers/` | React wiring |
| `e2e/` | Vitest-based e2e / certification helpers |

Configs live under package `configs/web/` (next, eslint, prettier, vitest, postcss, tsconfig, package manifests).

---

## 4. Backend / research packages (audit-relevant)

Under `source/packages/` (selected mirrors of `packages/*`):

| Cluster | Examples | Owns |
|---|---|---|
| Façade / API | `dsp_platform`, `api_platform` | Composition, `/api/v1` routers |
| Identity / security | `auth`, `security_platform`, `admin` | AuthN/Z, admin, beta programme |
| Data authenticity | `data_engine`, `contracts` | Quotes, statements, series, actions |
| Business quality | `economic_moat`, `management_quality`, `earnings_quality`, `financial_strength`, `business_quality*`, `growth_quality` | Category engines + aggregators |
| Valuation / decision | `valuation`, `recommendation`, `investment_*`, `decision_intelligence`, `ai_committee` | Server-side intelligence |
| Research objects | `research`, `copilot`, archive/diff/monitoring façades in `dsp_platform` | Reports, provenance |
| Portfolio / workflow | `portfolio`, `workflow`, `workspace`, `persistence` | Institutional workflows |

Exact inventory is generated into `manifests/PACKAGE_INVENTORY.md` at package build time.

---

## 5. Governance constraints (do not violate in audit remediations)

| ID | Rule |
|---|---|
| CV-001 | No fabricated numbers |
| CV-002 | Source before score |
| CV-009 | Governance over convenience — no bypasses |
| Thin client | No engine/API/model/scoring/boundary redesign under UI epics |
| Product Constitution | Tier-0 CV → RS → Trust → Correctness → … |

If an audit finds an architectural gap: **document it**; do **not** redesign the platform inside the audit package process.

---

## 6. Certification alignment

| Gate | Pilot | Commercial GA |
|---|---|---|
| Thin client boundary | PASS | PASS (not the rejection reason) |
| Architecture redesign required? | No | No — rejection is commercial/trust/evidence posture |
| Trust ladder universality | OPEN (accepted pilot residual) | CRITICAL blocker for unrestricted GA |

See [`05_RELEASE_STATUS.md`](./05_RELEASE_STATUS.md).
