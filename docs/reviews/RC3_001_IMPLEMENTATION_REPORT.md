# RC3-001 — Trust & Data Integrity Remediation (Phase A1)

| Field | Value |
|---|---|
| Programme | RC3-001 · Trust & Data Integrity Remediation · Phase A1 |
| Mode | **Implementation** (not an audit) |
| Authority | `FINAL_PRODUCT_UX_CERTIFICATION_RC2.md` · `TRUSTED_DATA_SOURCE_POLICY.md` (GOV-001) · REP-002 · DSP Trust Standard |
| Scope | Frontend only — Company Analysis, Institutional Reports presentation, research/ratings mappers |
| Date | 2026-08-01 |
| Decision | **PASS** for Phase A1 frontend trust integrity (Company Analysis + related mappers) |

---

## 1. Executive Summary

RC3-001 removes cross-engine **aliases and fallback substitutions** that caused Business Quality, Management, Risk, and ratings surfaces to display values from the wrong analytical stages.

After this remediation:

- Business Quality sub-dimensions read **only** `business_quality_aggregator` metrics (or show **Data unavailable.**).
- Management sub-dimensions never fall back to stage `decision`.
- Risk Book 07 types never read Financial Strength / Valuation.
- Valuation “Overall” no longer chains unrelated fields with `||`.
- Institutional ratings stop proxying Growth → Earnings Stability and BQ → Expected Long-Term Quality.
- Root mapper `mapResearchView` no longer injects Moat/Management labels into BQ metrics.

No backend, API, database, or engine changes.

---

## 2. Implementation Scope

| In scope | Out of scope |
|---|---|
| `apps/web` company-analysis UI | Backend packages |
| Institutional reports presentation modules | Analytical engines |
| `mapResearchView` / institutional ratings display maps | API contracts |
| Honest empty-state normalization | New data providers |

---

## 3. RC2 Findings Addressed

| RC2 / Task ID | Finding | Status |
|---|---|---|
| Finding 1 | Business Quality aliases (Management/Growth/Earnings/Moat) | **Fixed** |
| Finding 2 | Management decision / fallback substitutions | **Fixed** |
| Finding 3 | Risk aliased from Financial Strength (+ MoS in Risk) | **Fixed** |
| Finding 4 | Valuation overall chaining / method honesty | **Fixed** |
| Finding 5 | Financial Performance duplicate cross-stage panels | **Fixed** (financial stage only) |
| Finding 6 | Honest empty states (`Data unavailable.` etc.) | **Fixed** in touched paths |
| Finding 7 | Trust Standard — no estimate/substitute/fabricate | **Fixed** in touched paths |

Traceability detail:

| Finding | Files | Reason | Satisfaction |
|---|---|---|---|
| 1 | `mapResearchView.ts`, `WorkspaceSections.tsx` QualitySection | Sibling stages were written into BQ metrics / FieldRows | BQ metrics from aggregator only; UI uses `firstStageMetric(bq, …)` |
| 2 | `FlagshipSections.tsx` ManagementSection | Corporate Governance fell back to `m.decision` | Metric lookup only; else Data unavailable. |
| 3 | `FlagshipSections.tsx` RiskSection, `ReportModules.tsx` RiskModule | Book 07 rows read `financialStrength`; MoS shown under Risk | Empty risk metric source; FS shown as separate non-alias stage; MoS removed from Risk |
| 4 | `WorkspaceSections.tsx` ValuationSection | `verdict \|\| consensus \|\| method` substitution | Separate FieldRows; method IV only when present |
| 5 | `FlagshipSections.tsx` FinancialSection | Growth/Earnings staged as peer substitutes in grid | Financial stage only + honest note |
| 6–7 | WorkspacePrimitives, IR Primitives, ExplainableRatingItem, ratings mapper | Inconsistent Unavailable / proxies | Normalized copy; proxies removed |

---

## 4. Files Modified

- `apps/web/src/lib/research/mapResearchView.ts`
- `apps/web/src/lib/research/mapResearchView.test.ts`
- `apps/web/src/lib/institutional-rating/mapInstitutionalRatings.ts`
- `apps/web/src/components/company-analysis/WorkspacePrimitives.tsx`
- `apps/web/src/components/company-analysis/WorkspaceSections.tsx`
- `apps/web/src/components/company-analysis/FlagshipSections.tsx`
- `apps/web/src/components/company-analysis/ExplainableRatingItem.tsx`
- `apps/web/src/components/institutional-reports/Primitives.tsx`
- `apps/web/src/components/institutional-reports/ReportModules.tsx`
- `docs/reviews/RC3_001_IMPLEMENTATION_REPORT.md` (this file)

---

## 5. Mapping Corrections

### Business Quality (Book 04)

| UI Label | Frontend Property | Backend / stage | Engine | REP-002 | Verification |
|---|---|---|---|---|---|
| Overall score | `bq.score` / Overall Score metric | `business_quality_aggregator` (+ summary score when present) | BQ aggregator | Business Quality | Verified |
| Label | `bq.label` | same | BQ aggregator | Business Quality | Verified |
| Capital Allocation Quality | `firstStageMetric(bq, …)` | BQ metrics only | BQ aggregator | Cap Allocation Quality | Unavailable* |
| Industry Structure | `firstStageMetric(bq, …)` | BQ metrics only | BQ aggregator | Industry Structure | Unavailable* |
| Operating Discipline | `firstStageMetric(bq, …)` | BQ metrics only | BQ aggregator | Operating Discipline | Unavailable* |
| Franchise Durability | `firstStageMetric(bq, …)` | BQ metrics only | BQ aggregator | Franchise Durability | Unavailable* |
| Reinvestment Opportunity | `firstStageMetric(bq, …)` | BQ metrics only | BQ aggregator | Reinvestment Opportunity | Unavailable* |
| ~~Management.label as Cap Allocation~~ | — | — | — | — | **Removed** |
| ~~Growth as Reinvestment~~ | — | — | — | — | **Removed** |
| ~~Earnings as Operating Discipline~~ | — | — | — | — | **Removed** |
| ~~Moat as Industry/Franchise~~ | — | — | — | — | **Removed** |

\*Unavailable until analyse stage summaries expose named Book 04 metrics (backend limitation).

### Management (Book 05)

| UI Label | Frontend Property | Stage | Verification |
|---|---|---|---|
| Management Quality | `management.label` | `management_quality` | Verified |
| Corporate Governance | metrics only (no decision fallback) | same | Unavailable* / Verified when metric present |
| Integrity / Execution / Shareholder Orientation / Leadership | same-stage metric synonyms only | same | Unavailable* |

### Economic Moat (Book 06)

| UI Label | Rule | Verification |
|---|---|---|
| Economic Moat + Book 06 dims | `economic_moat` metrics only; **no** `moat.decision` fallback for Durability | Verified / Unavailable* |

### Risk (Book 07)

| UI Label | Rule | Verification |
|---|---|---|
| Business / Financial / Operational / Regulatory Risk / PCL | Never from `financial_strength` | Unavailable* |
| Risk stage status | Presence of risk stage in `stages[]` | Coverage unavailable. / status string |
| Margin of Safety under Risk | **Removed** (belongs to Valuation) | Removed |
| Key risks / Weaknesses | `view.risks` / `view.weaknesses` lists | Verified (warnings, not Book 07 scores) |

### Valuation

| UI Label | Source | Verification |
|---|---|---|
| Intrinsic Value / Price / MoS / Confidence | `view.valuation.*` | Verified |
| DCF / Relative / Residual / EPV | transparency methods by name; IV only | Verified / Unavailable |
| Overall Valuation | `vt.executive.valuationVerdict` only | Verified / Unavailable |
| Valuation method (stage) | `view.valuation.method` separate row | Verified |

### Financial Performance

| UI Label | Source | Verification |
|---|---|---|
| Revenue / Profit / Cash Flow / Margins / Debt / ROE / ROCE | `financial` stage metrics | Unavailable* (labels not on stage summaries today) |
| Label / Score / Confidence | financial stage summary | Verified |
| Historical trends | — | Unavailable |
| Growth / Earnings as financial substitutes | **Removed** from section | Removed |

### Executive Summary / AI / Explainability / Evidence / Timeline

| Surface | Verification |
|---|---|
| Trust ladder Analysis line | Uses BQ label + Moat label + MoS as **separate stage facts** (not BQ sub-dims) | Verified |
| AI Committee | Committee stage fields only | Verified |
| Explainability / Evidence | Strengths labeled as strengths (not “citations”); contradictory evidence retained | Verified |
| Timeline | Unchanged honest empties | Verified |

---

## 6. Fields Now Unavailable

Honest **Data unavailable.** (or **Coverage unavailable.** for missing risk stage) until backend exposes fields:

- Book 04: Capital Allocation Quality, Industry Structure, Operating Discipline, Franchise Durability, Reinvestment Opportunity
- Book 05: Corporate Governance, Integrity, Execution Capability, Shareholder Orientation, Leadership Quality (when not on stage metrics)
- Book 06: Brand Strength, Network Effects, Switching Costs, Distribution Advantage, Cost-Based Moat, Moat Durability (when not on stage metrics)
- Book 07: all typed risk dimensions
- Financial line items: Revenue, Profit, Cash Flow, Margins, Debt, ROE, ROCE (when not on financial stage metrics)
- Ratings: Expected Long-Term Quality; Earnings Revenue/Profit Stability; Capital Allocation module dims
- Documents / datasets / multi-period financial history (unchanged)

---

## 7. Validation Results

| Check | Result |
|---|---|
| Zero BQ cross-stage aliases in CA QualitySection | ✓ |
| Zero Management decision fallbacks | ✓ |
| Zero Risk←Financial Strength type aliases | ✓ |
| Zero fabricated substitutions in touched paths | ✓ |
| REP-002 terminology preserved | ✓ |
| GOV-001 / Trust Standard respected (display layer) | ✓ |
| Vitest: mapResearchView, company-analysis, institutional-reports, institutional-rating | **23/23 passed** |
| RC3 regression test (no BQ←Management/Moat) | ✓ |
| `tsc --noEmit` | Pre-existing errors in portfolio-intelligence lazy casts + e2e login path — **none in RC3-touched files** |

---

## 8. Remaining Backend Limitations

Frozen `/api/v1/analyse` `stage_summaries` expose label/decision/score/confidence per stage — **not** full REP-002 named sub-metrics. Frontend therefore correctly shows **Data unavailable.** for Book 04/05/06/07 sub-dimensions until the API adds them.

No dedicated `risk` stage metrics array is mapped into `ResearchView` today.

---

## 9. Outstanding Risks

| Risk | Severity | Note |
|---|---|---|
| `toSection()` still maps metric *names* by index to score/label/decision/confidence for some stages | Medium | Display UIs now prefer explicit REP-002 lookups → Unavailable; residual StageSectionCard still shows Label/Decision honestly |
| Legacy `components/analysis/*` surfaces | Medium | Not the live `/analysis` route; still searchable via AUX — follow-up IA epic |
| Portfolio “Health / Compounders” language | Medium | RC2 CRITICAL #10–11 — outside Phase A1 engine-mapping list; track for RC3 Phase A2 |
| Strengths still listed under evidence panels | Low | Relabeled as supporting strengths; not filed citations |

---

## 10. Release Recommendation

**Phase A1 frontend trust integrity: PASS** for Company Analysis + Institutional Reports presentation + related mappers.

Safe to proceed to next RC3 phases (universal trust chrome, commerce/auth honesty, IA collapse) once product prioritizes them.

Do **not** claim full production trust certification until backend exposes Book 04–07 metrics and remaining RC2 CRITICAL non-mapping items (auth/commerce/VQA) are closed.

---

## 11. Success Criteria Checklist

| Criterion | Result |
|---|---|
| Zero Business Quality aliases | ✓ |
| Zero Management aliases / decision fallbacks | ✓ |
| Zero Risk aliases from other engines | ✓ |
| Zero fabricated values in touched paths | ✓ |
| Zero substituted values in touched paths | ✓ |
| Honest unavailable states | ✓ |
| REP-002 terminology preserved | ✓ |
| GOV-001 respected | ✓ |
| DSP Trust Standard preserved | ✓ |
| Existing targeted tests pass | ✓ |
| Build/typecheck clean on touched files | ✓ (repo has pre-existing unrelated TS errors) |
