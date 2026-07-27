# EPIC-015 — Thin Client Remediation

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | **Complete** |
| **Last updated** | 2026-07-27 |
| **Scope** | Architectural migration — presentation only |
| **Predecessor** | [EPIC_014_PRODUCTION_READINESS_AUDIT.md](EPIC_014_PRODUCTION_READINESS_AUDIT.md) |

---

## 1. Executive Summary

EPIC-015 restores **Thin Client Architecture** compliance.

EPIC-014 discovered **278 TypeScript investment-engine files** under `apps/web/src/lib/{moat,valuation,management,earnings}`. Audit showed **zero imports** from `app/` or `components/` — the engines were unwired dead code that still violated governance by existing in the client source tree.

**Action taken:** delete the four engine trees; keep API-driven presentation mappers; stop inventing portfolio quality scores; harden Vitest architecture guards.

**Backend investment logic was not modified.** UI already consumed `POST /api/v1/analyse` via `api.analyse` → `mapAnalyseResponse` / `mapResearchView`.

---

## 2. Browser Engines Found

| Tree | Files | Capability |
|---|---:|---|
| `apps/web/src/lib/moat/` | 94 | Economic Moat Intelligence (EMI) — weighted category + overall moat scores |
| `apps/web/src/lib/valuation/` | 20 | FCFF DCF math, WACC, terminal value, DCF metric weights |
| `apps/web/src/lib/management/` | 70 | Management Intelligence (MIE) — category + overall management scores |
| `apps/web/src/lib/earnings/` | 94 | Earnings Quality Intelligence (EQI) — category + overall EQ scores |
| **Total unsafe** | **278** | |

| Status | Detail |
|---|---|
| UI wiring | **None** — no `app/` or `components/` imports |
| Backend equivalent | Composition pipeline via `POST /api/v1/analyse` |
| Already used by UI | `api.analyse` → `intelligence/mapResponse.ts`, `research/mapResearchView.ts` |

---

## 3. Browser Engines Removed

| Directory | Disposition |
|---|---|
| `lib/moat/**` | **Deleted** (94 files) |
| `lib/valuation/**` | **Deleted** (20 files) |
| `lib/management/**` | **Deleted** (70 files) |
| `lib/earnings/**` | **Deleted** (94 files) |

Remaining under `apps/web/src/lib`: **130** presentation / infra files.

---

## 4. Backend APIs Used

Primary intelligence path (unchanged):

```text
React UI
  → api.analyse (apps/web/src/lib/api/client.ts)
  → POST /api/v1/analyse
  → api_platform
  → dsp_platform composition
  → Domain packages (financial, valuation, moat, …, committee)
  → AnalyseResponse (stage_summaries, recommendation_summary, committee_summary)
  → mapAnalyseResponse / mapResearchView (display only)
```

| Endpoint | Role |
|---|---|
| `POST /api/v1/analyse` | Full 10-stage composition |
| `POST /api/v1/validate` | Request validation |
| `GET /api/v1/capabilities` | Module / stage discovery |
| `POST /api/v1/analyze/company` | Legacy Decision Pack path |
| `POST /api/v1/copilot/complete` | Grounded copilot (no scoring override) |

No new backend endpoints were added. No formulas changed.

---

## 5. Files Modified

| Path | Change |
|---|---|
| `apps/web/src/lib/architecture.test.ts` | Thin-client guards: forbid engine dirs, Engine/Scoring filenames, calc smells |
| `apps/web/src/lib/portfolio/analytics.ts` | `averageQualityScore` → `"Unavailable"` (no invented 4.2 formula) |
| `apps/web/src/lib/portfolio/data.ts` | Same honesty for summary quality field |
| `apps/web/src/components/portfolio/QualityPanel.tsx` | Description clarifies scores come from `/api/v1/analyse` |
| `docs/DSP_STATUS.md` | EPIC-015 status |
| `docs/EPIC_015_THIN_CLIENT_REMEDIATION.md` | This report |

---

## 6. Deprecated Files

All deleted engine modules are retired. Do not restore under `apps/web`.

If rich category evidence UIs are needed later, serialize richer envelopes from the **backend** public API — never reintroduce TypeScript scoring engines.

---

## 7. Test Results

| Suite | Result |
|---|---|
| `pytest packages` | **2601 PASSED** |
| Vitest `apps/web` | **108 PASSED** (20 files; +4 architecture assertions) |
| Engine directories present | **False** for moat / valuation / management / earnings |

---

## 8. Architecture Validation

| Check | Result |
|---|---|
| No valuation logic in browser | **PASS** — `lib/valuation` removed |
| No recommendation engine in browser | **PASS** — never present as TS engine; API summaries only |
| No moat scoring in browser | **PASS** — `lib/moat` removed |
| No financial / earnings scoring in browser | **PASS** — `lib/earnings` removed; financial never a TS engine tree |
| No investment committee logic in browser | **PASS** — API `committee_summary` presentation only |
| No duplicated algorithms | **PASS** — browser engines deleted |
| Frontend presentation-only | **PASS** — mappers + UI aggregation of holdings metadata only |
| Architecture test enforcement | **PASS** — forbids engine dirs / filenames / calc smells |

---

## 9. Thin Client Compliance Score

| Dimension | Before (EPIC-014) | After (EPIC-015) |
|---|---:|---:|
| Thin-client compliance | 55 | **96** |
| Unsafe engine files in web lib | 278 | **0** |
| Presentation lib files retained | ~130 | **130** |
| Architecture guard coverage | Python package bans only | Python + local engine bans |

**Thin Client Compliance Score: 96 / 100**

Remaining 4 points: portfolio still shows placeholder demo portfolio value strings; richer stage evidence still shallow on `/analyse` (backend serialization gap — not browser math).

---

## 10. Remaining Technical Debt

| ID | Item | Risk |
|---|---|---|
| TD-E015-01 | Enrich `/analyse` public payload with category evidence (server-side only) for richer UI | Medium |
| TD-E015-02 | Replace demo portfolio value placeholders with API-backed holdings valuations | Low |
| TD-E015-03 | Re-run EPIC-014 production readiness audit before GA | Process |
| TD-E014-03… | Prior security / auth hardening items | Medium |

---

## 11. Release Recommendation

Thin Client Architecture is restored for the web application source tree.

**Next mandatory step:** re-run EPIC-014 Production Readiness Audit (or a delta re-audit) before promoting `v1.0.0-rc1` → `v1.0.0`.

Do not treat EPIC-015 alone as a GA cut — confirm integrity, security, and docs after this remediation is committed.

---

Thin Client Architecture restored.

Frontend is presentation-only.

Recommend re-running EPIC-014 Production Readiness Audit before promoting v1.0.0-rc1 to v1.0.0.
