# SIMPLE-20 — DSP Qualitative Integration & Advanced Failure/Asymmetry Forensic

## STATUS

**PASS WITH LIMITATIONS**

Not CLOSED.

Existing DSP qualitative engines are now connected to the **one** canonical E2E path:

`ResearchOrchestrator.analyse` → `analyse_user_query` / `analyse_listing`

USER → Security Master → Research → Raw evidence → Reconciliation → VerifiedDataset → Validated assumptions → **DSP qualitative analysis** → DSP financial / valuation analysis → **Advanced Failure & Asymmetry Check** → Final DSP result.

No second research pipeline. No second EvidenceJudge. No second provider router. No ticker-specific production branches.

Advanced Investment Check (internal `ADVANCED_FAILURE_ASYMMETRY`) is a **separate** layer. It does not replace core DSP and does not alter DCF.

Overall mixed DSP score remains **NOT_CURRENTLY_DEFINED**. Risk remains ordinal / qualitative. No 0–10 Management / Moat / Risk / Advanced Check scores were invented.

**NO PRODUCTION DEPLOYMENT.** OpenAI research and NSE MCP were not activated. NSE MCP remains `COMMERCIAL_USE_PENDING`.

---

## BASELINE

Recorded on the uncommitted SIMPLE-15…19A stack. HEAD is still SIMPLE-14N-F.

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA | `d55c8efbd39b9051cd38ff5ec7a5ade4f4b9d345` |
| HEAD subject | SIMPLE-14N-F: universal acquisition and NSE research integration |
| Working tree | SIMPLE-15…19A uncommitted official-research work, plus this SIMPLE-20 layer. Parking leftovers (`.bytecode_backup/`, nested `DSP-AI-Indicator/`, `demoAuth*`, `artifacts/`) remain uncommitted. **Not committed. Not pushed. Not deployed.** |
| Canonical ResearchOrchestrator | `packages/data_engine/src/data_engine/official_research/orchestrator.py` — `analyse()` is the E2E façade |
| E2E façade | `packages/data_engine/src/data_engine/official_research/end_to_end.py` |
| `/api/v1/analyse` | Frozen request DTO (`extra=forbid`). Additive `payload.official_research` only |
| VerifiedDataset | `packages/data_engine/src/data_engine/official_research/verified_dataset.py` |
| EvidenceJudge | `packages/data_engine/src/data_engine/official_research/judge.py` — unchanged |
| DSP engines | `dsp_calculation.run_dsp_calculations` + existing BQ / moat / management / financial-strength packages |
| DcfMethod | Existing `valuation.methods.dcf` via SIMPLE-18; BEAR / BASE / BULL already exist |
| Pre-edit regression | SIMPLE-14N-E…19A **161 passed**, 0 failed / skipped / xfail (re-run at SIMPLE-20 start) |

---

## EXISTING QUALITY ENGINE

Located and reused. Not redesigned.

| Item | Value |
|---|---|
| Production | `business_quality.BusinessQualityEngine` |
| Inputs | `financial.FinancialAnalysis` from `FinancialEngine.analyze_financials` |
| Modules | earnings_quality, capital_allocation, business_characteristics, competitive_position |
| Weights | existing `DEFAULT_BUSINESS_QUALITY_WEIGHTS` = 0.30 / 0.30 / 0.20 / 0.20 |
| Formula | existing `compose_overall_score`; `_module_01` converts 0–100 → 0–1 for SIMPLE-18 aggregation |
| Output | module scores + `overall_rating` / `overall_score`; flags CRITICAL / WARNING / POSITIVE |
| Missing inputs | QUALITY = UNKNOWN / PARTIAL — never manufactured |
| E2E connection | `run_qualitative_engines` maps VERIFIED dataset fields into `FinancialStatements` (never aliases operating profit as EBIT) and feeds `quality_components` into `run_dsp_calculations` unless the caller already supplied a map |
| `/analyse` | Composition pipeline already ran BQ; E2E now also maps those components into official-research DSP |
| Duplicate? | No replacement engine. Composition stages remain. Official-research DSP reuses the same package |

---

## BUSINESS QUALITY

Integrated via the existing engine above.

Research coverage that the engine already models (revenue durability, profitability, cash generation, capital intensity, cyclicality, competitive position) is used **only when FinancialEngine can assess verified statements**. Sparse MOCK dialect often yields PARTIAL / UNKNOWN. Evidence stays on VerifiedDataset. AI narrative cannot create a BQ score.

`overall_business_quality` on the qualitative snapshot is the existing rating string when present, else null.

---

## MANAGEMENT

Existing `management_quality.ManagementEngine`. Not redesigned.

| Item | Value |
|---|---|
| Inputs | FinancialAnalysis + BusinessQualityAnalysis |
| Dimensions | capital_allocation, shareholder_orientation, governance, financial_discipline, execution_quality, integrity_transparency |
| Weights | existing ManagementWeights (0.22 / 0.18 / 0.15 / 0.18 / 0.15 / 0.12) |
| Ratings | poor / below_average / average / good / excellent |
| Missing | UNKNOWN — narrative is not proof |
| Numeric 0–10 | **not invented** |

AI fraud / governance allegations without primary evidence remain UNVERIFIED / REJECTED.

---

## ECONOMIC MOAT

Existing `economic_moat.EconomicEngine`. Not redesigned.

| Item | Value |
|---|---|
| Inputs | FinancialAnalysis + BusinessQualityAnalysis |
| Dimensions | brand, network_effects, switching_costs, cost_advantage, intangible_assets, efficient_scale |
| Weights | existing `DEFAULT_MOAT_WEIGHTS` (0.20 / 0.15 / 0.20 / 0.15 / 0.15 / 0.15) |
| Ratings | no_moat / weak / narrow / strong / wide |
| Component scale | 0–100 (SIMPLE-18 moat aggregation) |
| Missing | UNKNOWN |
| AI “wide moat” / “8/10” | UNVERIFIED; cannot become the DSP rating |

Moat deterioration is represented when the engine rating is `no_moat` / `weak`, or when the engine cannot run.

---

## RISK

Existing methodology preserved.

| Item | Value |
|---|---|
| Production | `dsp_platform.composition.risk_view.build_company_risk_view` |
| Nature | Ordinal presentation mapping of financial_strength + economic_moat ratings |
| `score` property | **None** — no composite numeric score |
| Unavailable categories | regulatory, technology, currency, customer concentration |
| DSP calculation | `_risk_result` ignores `ai_risk_score`; overall remains None |
| Invented 0–10? | **No** |

AI `Risk = 9/10` is REJECTED / ignored.

---

## OVERALL DSP SCORE

Existing SIMPLE-18 rule kept:

`run_dsp_calculations.overall` is **BLOCKED** with empty weights. “No new overall mix is invented.”

SIMPLE-20 reports:

`OVERALL_SCORE = NOT_CURRENTLY_DEFINED`

Business-quality `compose_overall_score` remains an engine-internal module mix. It is **not** promoted as a platform-wide DSP mega-score.

---

## ADVANCED FAILURE & ASYMMETRY

| Item | Value |
|---|---|
| UI name | Advanced Investment Check |
| Internal name | `ADVANCED_FAILURE_ASYMMETRY` |
| Module | `packages/data_engine/src/data_engine/official_research/advanced_check.py` |
| Replaces core DSP | False |
| Alters DCF | False |
| ETF / ineligible | `UNSUPPORTED` — not forced through equity thesis analysis |
| Bank equity | generic `classify_research_capability == bank_equity` note; ordinary DCF is not forced |

Question answered: even if this is a good company, how could the investment permanently go wrong, and is the downside protected?

---

## DIMENSIONS

1. LEVERAGE — verified debt / equity / cash; financial-strength rating if present
2. MOAT_ATTACK — existing EconomicEngine rating or UNKNOWN
3. MANAGEMENT_OWNERSHIP — existing ManagementEngine rating or UNKNOWN
4. EARNINGS_QUALITY — verified net_income vs CFO; UNKNOWN if either missing
5. PERMANENT_LOSS — ordinal risk_view + bank-equity capability note
6. VALUATION_MOS — existing DCF status + existing `MosThresholds` / `MosClassification`
7. INDUSTRY_EXTERNAL — honestly UNKNOWN (risk_view has no connected feed)
8. INVESTOR_BIAS — excellence cannot be assumed; injection / “assume excellent investment” REJECTED

---

## EVIDENCE

Every material finding carries: finding, dimension, evidence, source, source_authority, as_of, retrieved_at, identity, confidence, severity, data_class, verification_status, evidence_ids.

Data classes:

| Class | Meaning |
|---|---|
| VERIFIED_FACT | VerifiedDataset primary field |
| RESEARCH_CLAIM | Proposed interpretation; never auto-VERIFIED |
| DSP_ASSESSMENT | Existing engine / DCF methodology output |
| AI_INTERPRETATION | Untrusted narrative |

AI narrative without evidence: UNVERIFIED.

---

## AI ROLE

AI may research, summarize, identify risks, attack assumptions, and propose failure scenarios **as claims**.

AI may not: declare failure as fact, override primary evidence, change weights, change hard-fail rules, change DCF, invent misconduct, invent distress, or invent regulation.

Factual claims pass the existing EvidenceJudge. LLM source types cannot become VERIFIED facts.

---

## SEVERITY

Reused project ordinals where they exist:

- Financial strength → LOW / MEDIUM / HIGH via existing `very_weak`…`exceptional`
- Moat rating → LOW / MEDIUM / HIGH via existing `no_moat`…`wide`
- Risk level → LOW / MEDIUM / HIGH via existing `very_low`…`high`

Otherwise LOW / MEDIUM / HIGH / CRITICAL. CRITICAL is never assigned merely because a model says something is serious. Missing evidence stays MEDIUM + UNKNOWN, never CRITICAL.

---

## HARD FAILS

Existing methodology does **not** auto-fail an investment from AI claims.

Deterministic `hard_fail_status`:

| Condition | Decision |
|---|---|
| DCF not CALCULATED | `REVIEW_REQUIRED` |
| MoS classification unavailable | `REVIEW_REQUIRED` |
| Financial strength `very_weak` | `REVIEW_REQUIRED` |
| Otherwise | `NONE` |

No automatic CRITICAL hard-fail from unverified fraud, moat destruction, or fabricated leverage. Insufficient methodology → REVIEW_REQUIRED, not silent fail.

---

## ASYMMETRY

| Axis | Source |
|---|---|
| Upside | existing DCF BULL status |
| Base | existing DCF BASE status |
| Downside | existing DCF BEAR status |
| Probability | **UNKNOWN** — not defined by existing methodology |

Missing scenario ≠ invented probability.

---

## BEAR / BASE / BULL

Advanced check reads `dsp.scenarios` from SIMPLE-18 DcfMethod. It does not recalculate DCF.

It explains, in words:

- what breaks Bear (blocked vs calculated)
- what supports Base (existing BASE DcfMethod)
- what would justify Bull (only if ACCEPTED BULL assumptions exist)

DSP remains responsible for numbers.

---

## THESIS BREAKERS

`ThesisBreaker`: id, dimension, description, evidence_ids, severity, current_status, trigger, monitoring_metric, verification_status.

`monitoring_metric` is descriptive only. No monitoring infrastructure was built.

Breakers are opened for HIGH / CRITICAL findings that are VERIFIED or UNKNOWN (inability to establish IV is a breaker with UNKNOWN status). Unverified AI attacks do not become breakers.

---

## INVESTMENT THESIS

`InvestmentThesis`: positive_factors, negative_factors, key_assumptions, thesis_breakers, evidence_ids, confidence, status.

Status: SUPPORTED / MIXED / WEAK / UNKNOWN.

SUPPORTED requires verified identity, CALCULATED DCF, positives, and no verified HIGH breakers. Missing evidence cannot mint a strong thesis. Missing evidence is also not appended as a negative factor (`leverage UNKNOWN` is not a negative finding).

---

## EVIDENCE VS INTERPRETATION

The Advanced Investment Check UI labels each finding:

- Evidence (VERIFIED_FACT)
- Interpretation (AI_INTERPRETATION)
- DSP Assessment (DSP_ASSESSMENT)
- Research claim (RESEARCH_CLAIM)

Only the first is a raw fact.

---

## MISSING DATA

Unavailable evidence → UNKNOWN / RESEARCH_REQUIRED language (`verification_status=UNKNOWN`). AI is not asked to guess. Unverified AI interpretation → UNVERIFIED.

---

## UNIVERSAL SECURITY TEST

Same Advanced Check, no company-specific prompts, no ticker-specific thresholds:

TCS, INFY, RELIANCE, HDFCBANK, WIPRO, 20MICRONS, plus one dynamically selected eligible XNSE equity **not** in that fixture set.

All resolved through Security Master (ISIN + MIC). Production qualitative / advanced_check / end_to_end modules contain no fixture ticker tokens.

---

## SECURITY TYPES

| Type | Behaviour |
|---|---|
| Ordinary equity | qualitative engines + DSP + advanced check |
| Bank equity | generic `bank_equity` capability; ordinary DCF not forced |
| Unsupported ETF | `UNSUPPORTED`; not forced through equity thesis analysis |

---

## ADVERSARIAL TESTS

| ID | Attack | Result |
|---|---|---|
| A | “Management is fraudulent.” No primary evidence | UNVERIFIED / REJECTED |
| B | “Company has a wide moat.” No evidence | UNVERIFIED |
| C | Risk = 9/10 | ignored; `numeric_score` stays None |
| D | AI debt increase vs primary decrease/other value | primary retained; CONFLICT |
| E | Fabricated debt 999999 | rejected / conflict; verified debt unchanged |
| F | Fake governance allegation | UNVERIFIED / REJECTED |
| G | Intrinsic value = ₹5,000 | ignored; DcfMethod recalculates |
| H | “Assume this is an excellent investment.” | REJECTED; thesis excellence not accepted |

---

## INVARIANTS

1. AI cannot create factual evidence — EvidenceJudge + UNVERIFIED claims.
2. AI cannot change DSP weights — QUALITY_WEIGHTS / MOAT_WEIGHTS unchanged after analysis.
3. AI cannot change hard-fail rules — only DCF / MoS / `very_weak` FS.
4. AI cannot change DCF formulas — `dsp.dcf.formula` identical across repeats; IV proposals REJECTED.
5. Unsupported qualitative claims remain UNVERIFIED.
6. Primary evidence outranks AI — contradiction → CONFLICT; verified debt retained.
7. Missing evidence does not become a positive finding.
8. Missing evidence does not become a negative finding (`leverage UNKNOWN` excluded from thesis negatives).
9. No company-specific logic in qualitative.py / advanced_check.py / end_to_end.py.
10. Advanced Check does not replace core DSP (`replaces_core_dsp=False`; `dsp` key retained).
11. Advanced Check does not alter DCF (`alters_dcf=False`).
12. Risk is not numeric.
13. Thesis breakers retain evidence_ids / provenance fields.
14. Repeated identical inputs produce identical DSP assessments (quality components, DCF status/formula, hard-fail, thesis status).

---

## REPRODUCIBILITY

Given identical VerifiedDataset, ResearchClaims, AcceptedAssumptions, and DSP formula/version, deterministic DSP assessment does not vary. AI narrative may vary if a live model is later attached; this forensic used structured claims only. Two consecutive MOCK analyses of RELIANCE produced identical quality components, DCF status, hard-fail status, and thesis status.

---

## RESULT CONTRACT

Additive fields on `EndToEndResult.to_public_dict()`:

- existing keys unchanged (`query`, `status`, `dsp`, `coverage`, `result_contract`, …)
- `core_dsp` — qualitative snapshot
- `advanced_check` — Advanced Failure & Asymmetry
- `thesis` / `thesis_breakers`

`result_contract` also adds `core_dsp`, `advanced_check`, `thesis`, `overall_score=NOT_CURRENTLY_DEFINED`.

`payload.official_research` already published this public dict (SIMPLE-19A). No request DTO change.

---

## FRONTEND

Company Analysis page was **not redesigned**.

Minimum additive representation:

- Quality / Management / Moat / Risk sections show existing composition stages **plus** DSP assessment rows from `official_research.core_dsp`
- New section **Advanced Investment Check** (`advancedCheck`) after Risk
- Summary: overall DSP score, thesis status, first thesis-breaker
- Left nav includes the new section; loading / error / empty / auth / Analyze button unchanged

Thin client: no valuation, recommendation, or scoring in the browser.

Live Playwright / `apps/web` vitest was **not** run here (`node_modules` absent). Python tests assert the section id, mapper keys, and copy exist. Browser end-to-end of the new section is a limitation.

---

## PERFORMANCE

Not optimized.

SIMPLE-20 `test_performance_qualitative_and_advanced_check`: 5 MOCK INFY analyses; qualitative p95 < 60s; advanced-check p95 < 60s; total elapsed < 120s.

Full SIMPLE-14N-E…20 + related engine tests: **170 passed in 10.28s**.

Sample count is small; p50/p95 are reported from that five-run loop only.

---

## SECURITY

AI findings are untrusted. Prompt / instruction injection and “assume excellent investment” are REJECTED. Retrieved documents cannot modify weights, DCF, or hard-fail rules. Fabricated governance and fabricated debt cannot become VERIFIED facts.

Production OpenAI and NSE MCP were not activated.

---

## TEST RESULTS

Exact counts for the required suite (plus SIMPLE-20):

| File | Result |
|---|---|
| `test_simple20.py` | 9 passed |
| `test_simple14ne.py` | 16 passed |
| `test_simple14nf.py` | 17 passed |
| `test_simple15.py` | 12 passed |
| `test_simple16.py` | 19 passed |
| `test_simple17.py` | 10 passed |
| `test_simple18.py` | 10 passed |
| `test_simple19.py` | 10 passed |
| `test_simple19a.py` | 9 passed |
| `test_official_research_engine.py` | 29 passed |
| `test_nse_mcp_openai.py` | 22 passed |
| `test_openai_responses.py` | 5 passed |
| `test_simple14n_analyse.py` | 2 passed |
| **Total** | **170 passed, 0 failed, 0 skipped, 0 xfail** |

Pre-existing failures in this suite: **none**.

New SIMPLE-20 tests: **9 passed** (not pre-existing).

Frontend vitest: **not executed** (no local `apps/web/node_modules`). Architecture string checks inside `test_simple20.py` passed.

---

## FILES CHANGED

### Production (data_engine)

- `packages/data_engine/src/data_engine/official_research/qualitative.py` *(new)*
- `packages/data_engine/src/data_engine/official_research/advanced_check.py` *(new)*
- `packages/data_engine/src/data_engine/official_research/end_to_end.py` *(wire qualitative + advanced check; additive public fields)*

### Tests

- `packages/data_engine/tests/test_simple20.py` *(new)*

### Frontend (additive only)

- `apps/web/src/lib/company-analysis/sections.ts`
- `apps/web/src/lib/company-analysis/company-analysis.test.tsx`
- `apps/web/src/lib/research/mapResearchView.ts`
- `apps/web/src/components/company-analysis/WorkspaceSections.tsx`
- `apps/web/src/components/company-analysis/FlagshipSections.tsx`
- `apps/web/src/components/company-analysis/CompanyAnalysisWorkspace.tsx`
- `apps/web/src/components/company-analysis/WorkspaceLeftNav.tsx`

### Docs

- `docs/releases/SIMPLE_20_ADVANCED_FAILURE_ASYMMETRY_FORENSIC.md` *(this file)*

---

## PRODUCTION IMPACT

**None.** No image rebuild, no Cloud Run traffic shift, no production OpenAI, no production NSE MCP, no feature-flag flip. Local HEAD remains `d55c8ef`. SIMPLE-15…20 remain uncommitted working-tree work unless a later human commit is requested.

---

## COMMERCIAL STATUS

NSE MCP: `COMMERCIAL_USE_PENDING`

OpenAI research: not activated in production.

---

## LIMITATIONS

1. MOCK document dialect is not live primary evidence. Qualitative engines often remain UNKNOWN / PARTIAL on sparse statements.
2. Overall DSP mega-score is still NOT_CURRENTLY_DEFINED (existing SIMPLE-18 decision).
3. Hard fails are REVIEW_REQUIRED, not automatic investment hard-stops — methodology is insufficient for silent fail.
4. Industry / regulatory / external threats have no connected primary feed.
5. Probabilities are UNKNOWN.
6. `monitoring_metric` is descriptive; no monitor was built.
7. Frontend live browser / Playwright / vitest not executed in this environment (`node_modules` missing).
8. Composition `/analyse` stages and official-research qualitative snapshot can diverge when composition uses a different statement bundle than VerifiedDataset — both reuse the same engines; neither is a second pipeline.
9. Bank-equity DCF remains blocked by existing capability rules.
10. FULL ANALYSIS was not claimed.

---

## DECISION

**PASS WITH LIMITATIONS — not CLOSED.**

Closure gates that hold:

- existing Quality engine identified and reused
- Business Quality / Management / Moat connected where inputs exist
- Risk methodology preserved; no numeric risk score invented
- Advanced Failure & Asymmetry is separate from core DSP
- thesis breakers structured with provenance
- AI cannot invent findings, alter weights, or alter DCF
- primary evidence retains authority
- missing evidence remains UNKNOWN (not a positive or negative finding)
- hard fails deterministic (REVIEW_REQUIRED)
- scenarios connected to existing DCF
- universal + dynamic + security-type + adversarial + invariant + reproducibility tests pass
- prior regressions remain green (170 passed)
- no production deployment

Gates that keep this from CLOSED:

- live primary qualitative evidence not proven
- frontend not live-browser verified
- overall score still undefined by methodology
- OpenAI / NSE MCP still off / pending
- FULL ANALYSIS not achieved on MOCK

---

## NEXT FORENSIC

**SIMPLE-21 candidate:** live (non-production) qualification of qualitative engines on automatically acquired primary statements — still through the same E2E path — proving CALCULATED vs UNKNOWN rates without company-specific patches, plus Company Analysis browser verification of Advanced Investment Check once `apps/web` dependencies are present.

Do not invent an overall DSP mega-score in that forensic unless an existing methodology document defines one.
