# EPIC-012 + EPIC-013 — Institutional Company Comparison & Buffett-style Preference Analysis

| Field | Value |
|---|---|
| Programme | EPIC-012 / EPIC-013 · Institutional Company Comparison & Buffett-style Preference (v1.1) |
| Mode | **Implementation** (frontend orchestration vertical slice) |
| Branch | `cursor/p6-1-commercial-readiness` |
| Date | 2026-08-02 |
| Decision | **PASS** for flagship comparison workspace foundation (honest unavailable gaps documented) |

---

## 1. Executive Summary

EPIC-012/013 ships an **Institutional Company Comparison Workspace** — an Investment Decision Workspace that assists decision-making and **never makes investment decisions for users**. The thin client orchestrates **2–5** frozen `/api/v1/analyse` calls (one per symbol), maps each pack through existing `mapResearchView` / institutional rating / Buffett Indicator presentation layers, then builds Winner Matrix, trade-offs, Buffett-style preference alignment, evidence/explainability, Research Intelligence overlays, heatmap, portfolio-fit tags, personal notes, and institutional export.

**No valuation, BQ, management, moat, risk, AI committee, explainability, Research Intelligence calculations, REP-002, Trust Standard, GOV-001, API contracts, or engine behaviour were modified.** CV-001 honesty is preserved: missing fields render **Data unavailable.** / **Unable to calculate.** / **Coverage unavailable.** / **Analysis pending.** / **Analysis unavailable.**

Buffett wording is enforced: always *“According to the Buffett-inspired framework implemented by DSP AI Indicator…”* — never *“Buffett would buy.”*

---

## 2. Workspace Modules

| # | Module | Status |
|---|---|---|
| 1 | Comparison Header (selector, compare, remove, swap, pin, timestamps, coverage, history, export entry) | Implemented |
| 2 | Executive Summary | Implemented |
| 3 | Winner Matrix ★ | Implemented (medals only with evidence) |
| 4 | Trade-off Analysis ★ | Implemented from existing outputs |
| 5 | Valuation Comparison | Implemented (historical → Data unavailable.) |
| 6–10 | BQ / Management / Moat / Risk / Financial | Implemented (engine fields only) |
| 11 | Evidence Comparison ★ | Implemented |
| 12 | Explainability Comparison ★ | Implemented |
| 13 | Research Intelligence Integration ★ | Implemented (consume EPIC-011B APIs only) |
| 14 | Buffett-style Preference Analysis ★★★★★ | Implemented with copy guards |
| 15 | Decision Heatmap | Implemented |
| 16 | Scenario Comparison | Honest **Analysis unavailable.** (no bull/base/bear on `/analyse`) |
| 17 | Portfolio Fit | Style tags only — not personalised advice |
| 18 | Personal Research Workspace ★ | Local Zustand prefs |
| 19 | Institutional Export | JSON / CSV / print-PDF / share; DOCX unavailable |
| 20 | Future Architecture | Documented adapter abstraction |

---

## 3. Winner Matrix

Dimensions: Business Quality, Management, Moat, Risk, Valuation, Capital Allocation, Cash Flow, ROCE, Margins, Growth, Financial Strength, Confidence, Overall.

- Ranking parses **server-provided** score text only (`assignMedals`).
- Gold / silver / bronze only when numeric evidence exists; ties share a tier.
- **Cash Flow, ROCE, Margins** → **Data unavailable.** (no dedicated fields on frozen `/analyse`; CV-001 forbids catalogue substitution).
- **Risk** → unavailable unless institutional `riskAssessment` module has a score (typically unavailable by design).

---

## 4. Trade-off Engine

Pure presentation:

- Dimension leaders from Winner Matrix score gaps
- MoS pairwise notes when both packs expose MoS
- Committee decision divergence with existing rationale/strengths/weaknesses evidence

No new analytical model. Missing scores → no fabricated trade-off winner.

---

## 5. Buffett-style Framework

Dimensions: understandability, moat, management, capital allocation, ROCE, debt, cash, reinvestment, MoS, durability.

- Alignment states: `aligned` | `partial` | `not_aligned` | `unavailable`
- Reasons always prefixed with the mandatory DSP Buffett-inspired framing
- Runtime + unit guards reject forbidden endorsement phrases
- ROCE / cash often **unavailable** when no dedicated engine field exists

---

## 6. Research Intelligence Integration

When `featureFlags.researchIntelligence` is on, each symbol optionally fetches:

- `POST /research/intelligence/performance`
- `POST /research/intelligence/calibration`
- `GET /research/intelligence/timeline?symbol=`

Overlays map API fields only (`overall_accuracy`, calibration drift status, timeline counts, coverage). Failures → **Data unavailable.** / **Coverage unavailable.** — never recalculated locally.

---

## 7. Evidence & Explainability

- Evidence: `evidenceCounts`, recommendation confidence, stage success coverage, analysedAt freshness, correlation/pipeline/platform provenance
- Explainability: existing `InstitutionalExplainabilityFramework` module one-liners side-by-side

---

## 8. Validation Results

| Suite | Result |
|---|---|
| `apps/web/src/lib/company-comparison/company-comparison.test.ts` | Mapping honesty, medals, Buffett copy, 2–5 company support, export |
| `apps/web/src/lib/company-comparison/company-comparison.render.test.tsx` | Empty workspace shell render |
| Analytical engines / API contracts | Untouched by design |

---

## 9. Remaining Gaps

1. **Bull/Base/Bear scenarios** — not on frozen `/analyse` DTO → **Analysis unavailable.**
2. **Dedicated ROCE / margins / cash-flow / income yield fields** — absent → honest unavailable (not substituted from catalogue screening).
3. **Native DOCX/XLSX/PDF generators** — not in existing export patterns; print-to-PDF / HTML / JSON / CSV only.
4. **Backend multi-symbol orchestration** — intentionally deferred; client N×`/analyse` preserves contracts. Future server composition may reduce latency without new scoring.
5. **Research Intelligence performance** is window-global today — per-symbol accuracy depends on timeline/coverage richness in the RI store.
6. **Virtualized mega-tables** — not required at 2–5 columns; can add later if subject kinds expand.

---

## 10. Competitive Advantages

- Institutional decision workspace that **refuses to decide for the user**
- Evidence-gated Winner Matrix (no fake medals)
- Buffett-inspired preference with mandatory non-endorsement framing
- Deep reuse of certified analyse → ResearchView → ratings / Buffett / explainability stacks
- Extensible comparison-engine adapter design for portfolio/ETF/MF/sector/industry/watchlist without shell redesign
- Local personal research (notes/thesis/questions/decision/watch/saved sets) that never pollutes analyse

---

## 11. Architecture Decision — Orchestration

**Choice:** Client orchestration of N existing `/api/v1/analyse` calls.

**Rationale:** Backend `POST /compare` is not an operational qualitative engine today (`accepted_for_orchestration` stub). Adding scoring would violate HARD DO-NOT-MODIFY. Client composition preserves frozen contracts and CV/RS boundaries.

---

## 12. Implementation Return Format

| Item | Detail |
|---|---|
| Architecture Impact | Additive frontend only; no engine/API contract changes |
| Components Added | `components/company-comparison/*`, `lib/company-comparison/*` |
| Pages Updated | `/analysis/compare` (new), `/compare` → redirect, Company Analysis Compare link |
| Feature Flags Used | `NEXT_PUBLIC_COMPANY_COMPARISON` / `companyComparison` (default on); RI gated by existing flag |
| Accessibility Validation | Section nav buttons, labelled inputs, aria-live main, sticky header, reduced-motion safe transitions |
| Performance Validation | Route dynamic import, lazy star sections, parallel analyse calls, Suspense skeletons |
| Responsive Validation | Stacked mobile header/nav; grid scales 2–5 columns |
| Known Limitations | See §9 |
| Future Enhancements | Server multi-pack compose; scenario fields when certified; subject adapters beyond company |
| Regression Summary | Targeted Vitest GREEN for comparison mappers + empty render; engines untouched |

---

## 13. Route + Key Paths

| Item | Path |
|---|---|
| Route | `/analysis/compare` (legacy `/compare` redirects) |
| Workspace | `apps/web/src/components/company-comparison/CompanyComparisonWorkspace.tsx` |
| Lib | `apps/web/src/lib/company-comparison/` |
| Nav | `apps/web/src/lib/shell/navigationRegistry.ts` (`analysis-compare` child) |
| Flag | `apps/web/src/lib/featureFlags.ts` |
| Report | `docs/reviews/EPIC_012_013_IMPLEMENTATION_REPORT.md` |
