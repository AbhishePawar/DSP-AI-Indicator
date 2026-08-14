# EPIC-012/013A — Institutional Decision Support Completion (v1.1)

| Field | Value |
|---|---|
| Programme | EPIC-012 / EPIC-013A · Institutional Decision Support Completion |
| Mode | **Implementation** (presentation / orchestration only) |
| Branch | `cursor/p6-1-commercial-readiness` |
| Date | 2026-08-02 |
| Decision | **PASS** for institutional decision-support completion on existing Company Comparison Workspace |

---

## 1. Executive Summary

EPIC-012/013A completes institutional decision support on the **existing** Company Comparison Workspace (`/analysis/compare`). The thin client still orchestrates N frozen `/api/v1/analyse` calls and maps existing research packs only.

**Added:** Executive Comparison Scorecard, Investment Committee Memo Generator, Contradictory Evidence Panel, Why Not Analysis, Evidence Strength Meter, immutable Comparison History, Institutional Review Mode, presentation-only Weighting Profiles, Sector Context (honest unavailable for medians), Sensitivity Panel (Analysis unavailable.), guided Decision Workspace, and institutional UX question coverage.

**Not modified:** Valuation · BQ · Management · Moat · Risk · AI Committee · Explainability · RI calculations · API contracts · REP-002 · Trust · GOV-001 · analytical outputs · Winner Matrix ranking essence.

Buffett wording remains mandatory: *“According to the Buffett-inspired framework implemented by DSP AI Indicator…”* — never *“Buffett would buy.”* The platform **never** produces the investment decision.

---

## 2. Completed Features

| # | Feature | Status |
|---|---|---|
| 1 | Executive Comparison Scorecard | Implemented |
| 2 | Investment Committee Memo Generator | Implemented (JSON / Print-PDF / HTML; DOCX gap documented) |
| 3 | Contradictory Evidence Panel | Implemented — conflicts never hidden |
| 4 | Why Not Analysis | Implemented — evidence-backed differentials |
| 5 | Evidence Strength Meter | Implemented — Strong / Moderate / Limited / Data unavailable. |
| 6 | Comparison History | Implemented — local immutable append-only |
| 7 | Institutional Review Mode | Implemented — standard / presentation / IC / print / fullscreen / evidence-first + keyboard nav |
| 8 | Weighting Profiles | Implemented — presentation emphasis only |
| 9 | Sector Context | Implemented — labels when catalogue known; medians Data unavailable. |
| 10 | Sensitivity Panel | Implemented — inputs shown; sensitivity Analysis unavailable. |
| 11 | Decision Workspace | Implemented — guided workflow; user always decides |
| 12 | Institutional UX questions | Implemented on summary + decision workspace |
| 13 | Future Architecture (subject adapters) | Extended documentation |

---

## 3. Decision Support / Committee Memo

The IC memo assembles:

- Companies compared
- Executive summary
- Winner Matrix leaders
- Trade-offs
- Supporting + contradictory evidence
- Buffett-style framework summary (mandatory non-endorsement framing)
- Confidence
- Outstanding questions (user questions + institutional prompts)
- Decision notes (user-authored only)

Exports: **JSON**, **Print/PDF** (browser), **HTML**. **Native DOCX unavailable** — documented in UI and export payload (`exportFormats.docx: false`).

---

## 4. Evidence Review

### Contradictory Evidence
Both supporting and contradictory lists are always rendered. When a side has no fields, an honest **Data unavailable.** message is shown — absence of conflicts is never treated as proof of absence.

### Why Not Analysis
Per-company reasons from Winner Matrix score gaps, committee opposing reasons, weaknesses, and MoS differentials. No generic “not preferred” copy when differentials exist.

### Evidence Strength Meter
Classifies from existing coverage / freshness / completeness / source provenance / research confidence only. Never fabricates Strong without signals.

---

## 5. Comparison History

- Local Zustand persist store: `dsp.company-comparison.history.v1`
- Append-only; entries frozen (`immutable: true`)
- Fields: date, research version (pipeline/platform), confidence, winner summary, changes vs prior
- Timeline UI with filter/search
- Prior entries are never mutated

---

## 6. Weighting / Review Mode

### Weighting Profiles
Equal · Quality · Value · Growth · Conservative · Buffett-style

- Visual emphasis on scorecard rows only
- Winner Matrix numerics / medals / analytical fields **identical** across profiles
- Guard: `assertWeightingIsPresentationOnly`

### Review Modes
Standard · Presentation · IC Review · Print · Fullscreen · Evidence-first

Keyboard: `↑/↓` or `j/k` section navigation; `Esc` exits fullscreen.

---

## 7. Validation Results

| Suite | Result |
|---|---|
| `company-comparison.test.ts` | **15/15 GREEN** (includes 013A scorecard, memo, contradictory, why-not, strength, weighting, history, sector/sensitivity) |
| `company-comparison.render.test.tsx` | **GREEN** empty workspace shell |
| Analytical engines / API contracts | Untouched by design |

---

## 8. Remaining Future Ideas

1. Native DOCX/XLSX generators when an approved export library lands.
2. Certified sector/industry median API → replace Data unavailable. for relative context.
3. Certified sensitivity surfaces on `/analyse` → replace Analysis unavailable.
4. Server multi-pack composition for latency (still no new scoring).
5. Subject adapters for portfolio / ETF / MF / sector / industry / watchlist (shell already agnostic).
6. Bull/Base/Bear scenarios when present on certified DTO.

---

## 9. Architecture Impact

| Item | Detail |
|---|---|
| Architecture Impact | Additive frontend decision-support layers only; no engine/API redesign |
| Components Added/Updated | `components/company-comparison/*`, `lib/company-comparison/*` |
| Pages Updated | `/analysis/compare` (existing route; workspace enhanced) |
| Feature Flags Used | Existing `companyComparison` / RI flags — no new engine flags |
| Accessibility Validation | Section nav, labelled inputs, aria-live, review-mode group, keyboard nav, reduced-motion safe classes |
| Performance Validation | Lazy star sections retained; parallel analyse orchestration unchanged |
| Responsive Validation | Stacked header/nav; scorecard/matrix overflow-x; mobile-safe controls |
| Known Limitations | See §8 |
| Future Enhancements | Subject adapters; certified sector/sensitivity APIs |
| Regression Summary | Targeted Vitest GREEN; engines untouched |

---

## 10. Implementation Return Format

| Item | Detail |
|---|---|
| Architecture Impact | Presentation/orchestration completion of EPIC-012/013 decision support |
| Components Added | Scorecard, IC Memo, Contradictory, Why Not, Evidence Strength, History, Weighting, Sector, Sensitivity, Decision Workspace, Review Mode |
| Pages Updated | Company Comparison Workspace shell |
| Feature Flags Used | Existing comparison + RI flags |
| Accessibility Validation | Keyboard section nav; review mode controls; labelled filters |
| Performance Validation | Lazy sections; no new analyse fan-out beyond existing N calls |
| Responsive Validation | Preserved 2–5 column grids + stacked mobile chrome |
| Known Limitations | DOCX; sector medians; sensitivity analysis |
| Future Enhancements | Adapter expansion; certified aggregates |
| Regression Summary | GREEN |

---

## 11. Route + Key Paths

| Item | Path |
|---|---|
| Route | `/analysis/compare` |
| Workspace | `apps/web/src/components/company-comparison/CompanyComparisonWorkspace.tsx` |
| Sections UI | `apps/web/src/components/company-comparison/Sections.tsx` |
| Lib | `apps/web/src/lib/company-comparison/` |
| History store | `apps/web/src/lib/company-comparison/comparisonHistoryStore.ts` |
| Weighting | `apps/web/src/lib/company-comparison/weightingProfiles.ts` |
| Decision workflow | `apps/web/src/lib/company-comparison/decisionWorkflow.ts` |
| Tests | `apps/web/src/lib/company-comparison/company-comparison.test.ts` |
| Report | `docs/reviews/EPIC_012_013A_COMPLETION_REPORT.md` |
