# SIMPLE-18 — Deterministic DSP Calculation & Assumption Validation Forensic

## STATUS

**PASS WITH LIMITATIONS**

Not CLOSED. Verified facts, validated assumptions, and deterministic DSP calculations are separated. AI may propose assumptions; DSP validates and calculates. Canonical DCF, MoS, FCF, quality/moat weights, and missing-data blocking are proven offline. Two existing DCF implementations remain documented rather than silently merged. No production overall-score mix was invented. Live OpenAI/NSE were not required.

**NO PRODUCTION DEPLOYMENT**

## BASELINE

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA | `d55c8efbd39b9051cd38ff5ec7a5ade4f4b9d345` |
| HEAD subject | SIMPLE-14N-F: universal acquisition and NSE research integration |
| Working tree | SIMPLE-15 + SIMPLE-16 + SIMPLE-17 uncommitted, plus parking leftovers |
| SIMPLE-17 report | `docs/releases/SIMPLE_17_CURRENTNESS_SHARES_DERIVED_FORENSIC.md` |
| Focused regression before edits | **130 passed** (14N-E 16, 14N-F 17, SIMPLE-15 12, SIMPLE-16 19, SIMPLE-17 10, EvidenceJudge 29, NSE MCP 22, OpenAI Responses 5) |

Inspected, not replaced:

| Surface | Location | SIMPLE-18 action |
|---|---|---|
| DcfMethod | `packages/valuation/src/valuation/methods/dcf.py` | Canonical official-research DCF; formula reused with Decimal |
| DCF Intelligence | `packages/valuation/src/valuation/dcf_intelligence/` | Documented as separate FCFF engine; not invoked |
| ValuationAssumptions | `packages/valuation/src/valuation/assumptions.py` | Bounds reused (discount, FCF growth, terminal, years) |
| MoS | `dcf_intelligence/margin.py` | `(IV/share − Price) / IV/share` reused |
| FCF | financial `FORMULA_FCF` / SIMPLE-17 | `CFO − \|capex\|` reused |
| Net debt / EV / market cap | SIMPLE-17 `derived_fields.py` | Reused |
| Quality weights | `DEFAULT_BUSINESS_QUALITY_WEIGHTS` | EQ 0.30 / CA 0.30 / BC 0.20 / CP 0.20 |
| Moat weights | `DEFAULT_MOAT_WEIGHTS` | brand 0.20, network 0.15, switching 0.20, cost 0.15, intangible 0.15, scale 0.15 |
| Risk | `packages/risk` RiskAnalyzer | Qualitative only; no numeric score invented |
| Buffett Indicator | ARCH-001 frontend synthesis | Not a GDP engine; classic ratio only if both inputs verified |
| dsp_gate AssumptionRecord | `dsp_gate.py` | Unchanged; not production-wired |
| Sensitivity deltas | `DcfSensitivitySpec` | growth ±2pp, WACC ±1pp, terminal ±0.5pp |

Existing work was not discarded.

## DATA CLASSES

Explicit classes in `assumption_contract.py`:

| Class | Meaning | Examples |
|---|---|---|
| **VERIFIED_FACT** | Authoritative evidence-backed value | Revenue, NI, CFO, Capex, Cash, Debt, Shares, Price |
| **DERIVED_VALUE** | Calculated from verified inputs | FCF, Market Cap, Net Debt, EV, IV, MoS |
| **ASSUMPTION** | Forward-looking, not an observed fact | Growth, terminal growth, WACC, margins |

AI may research facts and propose assumptions. AI cannot write a numeric fact into DSP. Derived values cannot become source evidence.

## ASSUMPTION CONTRACT

`CanonicalAssumption`:

assumption_id · field · value · unit · period · scenario · source · evidence_ids · reasoning · proposed_by · validated_by · validation_status · confidence · created_at

Statuses: **PROPOSED** · **ACCEPTED** · **REJECTED** · **UNKNOWN** · **USER_REQUIRED** · **REVIEW_REQUIRED**

PROPOSED rows never enter DCF. Only ACCEPTED rows after `AssumptionValidator` are used.

Existing `AssumptionRecord` on `VerifiedDataset` is unchanged.

## ASSUMPTION VALIDATOR

`validate_assumption` / `validate_assumption_pack` / `ai_assumption_workflow`.

Checks: numeric type, unit, period, scenario, configured bounds, historical divergence, revenue vs FCF growth relationship, evidence support, circular derived/valuation dependence.

AI confidence is ignored as proof.

Sources: historical company performance, management guidance, company filings, industry data, regulatory information, macro data, primary research, **ai_synthesis**. AI synthesis without evidence_ids is REJECTED (workflow may map to USER_REQUIRED).

Workflow:

DATA MISSING → AI RESEARCH → candidate assumption (PROPOSED) → validator → ACCEPT → DSP, or REJECT / USER_REQUIRED / BLOCKED.

## DCF FORMULA

Two existing implementations were identified. They were **not** silently merged.

### Canonical for official-research / dsp_gate (SIMPLE-18 runnable path)

`valuation.methods.dcf.DcfMethod` (`valuation.methods.dcf`):

```
FCF₀ = OCF − |CapEx|     # SIMPLE-17 / financial FORMULA_FCF
FCFₜ = FCF₀ (1+g)ᵗ
TV   = FCFₙ (1+gₜ) / (r − gₜ)
IV   = Σ FCFₜ/(1+r)ᵗ + TV/(1+r)ⁿ
```

This FCF is after-interest cash flow. The present value is **equity value**. Net debt is **not** subtracted again.

Default horizon: **5 years** (`ValuationAssumptions.projection_years`), overridable by an ACCEPTED `projection_years` assumption.

### Documented, not invoked from VerifiedDataset

DCF Intelligence `0.2.0-dcf-intelligence`:

```
FCFF = EBIT(1−t) + D&A − CapEx − ΔNWC
EV   = Σ PV(FCFF) + PV(TV)
Equity = EV − Debt − Minority + Cash + Investments
IV/share = Equity / Shares
```

Requires CAPM, NWC, D&A, tax rate — not present on `VerifiedDataset`. Mixing FCFF EV-bridge math onto DcfMethod IV would double-count. SIMPLE-18 does not do that.

## DCF HARD GATES

Before calculation:

* capability is ordinary **equity** (bank equity / ETF / unsupported → BLOCKED)
* FCF CALCULATED and FCF₀ > 0
* ACCEPTED WACC/discount_rate > 0
* ACCEPTED terminal growth < WACC
* terminal within configured bounds
* forecast years in [1, 30]
* shares VERIFIED TOTAL_OUTSTANDING > 0 for per-share IV
* currency consistent
* no NaN / infinity
* no PROPOSED/REJECTED assumptions

Failure → **DCF = BLOCKED**. No approximate number.

## DCF SCENARIOS

BEAR · BASE · BULL each have their own assumption pack. Scenario fields do not leak. A BASE run with only BEAR assumptions is BLOCKED.

## SENSITIVITY

Deterministic one-factor-at-a-time grid from existing `DcfSensitivitySpec`:

* FCF growth ±2pp
* WACC ±1pp
* terminal growth ±0.5pp

Generated by code. AI does not produce sensitivity values. Cells that fail hard gates are BLOCKED, not interpolated.

## INTRINSIC VALUE

```
Equity IV (DcfMethod) ÷ verified TOTAL_OUTSTANDING → IV/share
```

Free float, weighted-average EPS shares, potential/diluted, promoter, and listed-without-proof cannot be the denominator.

## MARGIN OF SAFETY

Existing formula:

```
MoS = (IV/share − Price) / IV/share
```

Equivalent to `1 − Price/IV`. Research posture only; not a trade recommendation.

If IV is blocked: **MOS = BLOCKED**.

## FCF

Existing DSP definition:

```
FCF = CFO − |Capex|
```

Same period, established unit, verified components. No inferred capex. No zero substitution. Missing CFO or Capex → FCF BLOCKED → DCF BLOCKED.

## QUALITY

Existing `compose_overall_score` weights, not redesigned:

| Module | Weight |
|---|---|
| earnings_quality | 0.30 |
| capital_allocation | 0.30 |
| business_characteristics | 0.20 |
| competitive_position | 0.20 |

SIMPLE-18 forensic aggregator requires **all four** numeric engine scores. Missing any → BLOCKED. AI narrative (“10/10”) is ignored. The production BQ engine’s skip-missing behaviour is unchanged.

## MOAT

Existing `DEFAULT_MOAT_WEIGHTS`. Dimension scores must be supplied by the Economic Moat engine. “AI thinks moat = 8/10” is ignored. Missing dimensions → BLOCKED.

## RISK

Existing Risk Analyzer is **qualitative**. It does not emit a numeric risk score. SIMPLE-18 does not invent one. AI numeric risk is ignored. Observations may be recorded; overall numeric risk remains None.

## BUFFETT INDICATOR

Two surfaces:

1. **Product Buffett Indicator** (ARCH-001): frontend synthesis of existing `/api/v1/analyse` scores. No GDP formula. Backend unchanged. SIMPLE-18 does not run it.
2. **Classic market-cap / GDP**: calculated only when **total market cap** and **GDP** are both VERIFIED, same currency, comparable period. Company market cap is not “the market”. Otherwise BLOCKED / UNKNOWN.

## SCORE AGGREGATION

No hidden AI weighting. No overall mix of quality + moat + DCF was invented.

`DSPAnalysisResult.overall_score` remains unused by this forensic layer. Component scores stay separate. Prose cannot create an overall number.

## MISSING DATA POLICY

| Missing input | Result |
|---|---|
| WACC / growth / terminal not ACCEPTED | DCF BLOCKED (AI may propose; validator decides) |
| Shares missing / not TOTAL_OUTSTANDING | per-share IV BLOCKED |
| Cash missing | EV BLOCKED (SIMPLE-17); DcfMethod equity IV may still run |
| Debt missing | EV BLOCKED |
| CFO or Capex missing | FCF BLOCKED → DCF BLOCKED |
| Quality/moat components missing | that score BLOCKED |
| GDP or total market cap missing | Buffett ratio BLOCKED |

Never silently substitute 0, average, industry average, previous value, or AI guess.

## AI-ASSUMPTION WORKFLOW

Implemented as `ai_assumption_workflow`.

Hallucinated revenue ₹500,000 crore vs evidence ₹92,624 crore: AI fact REJECTED (EvidenceJudge).

Hallucinated 5bn shares: REJECTED without authoritative evidence.

AI intrinsic value ₹4,500: ignored; DSP calculates independently.

80% CAGR without evidence: REJECTED / USER_REQUIRED (outside bounds max 50% from DcfForecastAssumptions).

## CIRCULARITY PROTECTION

Blocked:

* intrinsic value / DCF / MoS / AI valuation → assumption
* market cap → shares (existing `cannot_derive_shares`)
* derived metric → primary financial fact
* derived field → source evidence (`refuse_derived_as_evidence`)

## CURRENCY / UNITS

Before calculation: listing currency, price currency, FCF currency, GDP currency must match when used.

₹10,000 million ≠ ₹10,000 crore (`normalize_numeric_to_actual`). Unknown units → CALCULATION_BLOCKED. No guessed conversion. Rate assumptions use decimal, not silent percent/decimal mix.

## PERIOD CONSISTENCY

FY2025 FCF cannot combine with FY2026 capex (SIMPLE-17 FCF already CALCULATION_BLOCKED). Forecast years grow from that single FCF₀. Market cap and GDP periods must be comparable for the Buffett ratio.

## SHARE DEPENDENCY

Per-share DCF uses **VERIFIED TOTAL_OUTSTANDING** only.

## NUMERICAL PRECISION

Internal Decimal precision 28. Rounding is presentation-only (`presentation_round`, 2 decimal places). Internal IV is unrounded. Sensitivity uses the same internal values.

## REPRODUCIBILITY

Identical verified dataset + accepted assumptions + formula version + `calculated_at` → identical DCF, IV/share, quality, and moat. Proven by running the same analysis twice. AI narrative changes do not change numbers.

## ADVERSARIAL TESTS

| ID | Case | Result |
|---|---|---|
| 1 | AI revenue ₹500,000 crore | REJECTED |
| 2 | AI 5bn shares | REJECTED |
| 3 | AI IV ₹4,500 | ignored; DSP calculates |
| 4 | 80% CAGR, no evidence | REJECTED / USER_REQUIRED |
| 5 | WACC 5% / terminal 7% | DCF BLOCKED |
| 6 | Missing cash | EV BLOCKED |
| 7 | Missing shares | per-share IV BLOCKED |
| 8 | ₹10,000 million vs crore | not equal |
| 9 | FY2025 FCF + FY2026 capex | CALCULATION_BLOCKED |
| 10 | Bear assumptions in Base | BASE BLOCKED / scenarios isolated |

## INVARIANTS

1. Same inputs → same output. Proven.
2. AI narrative alone cannot change valuation. Proven.
3. Unverified fact cannot enter DSP. Proven.
4. Rejected/PROPOSED assumption cannot complete DCF. Proven.
5. Missing required input blocks calculation. Proven.
6. Zero is not substituted for missing data. Proven.
7. Invalid/missing shares block per-share valuation. Proven.
8. WACC ≤ terminal growth blocks DCF. Proven.
9. Currency mismatch blocks. Proven.
10. Period mismatch blocks. Proven.
11. Derived values cannot become source evidence. Proven.
12. Weighted-average shares cannot be outstanding. Proven.
13. Scenario assumptions remain isolated. Proven.
14. Sensitivity is deterministic. Proven.
15. Presentation rounding does not replace internal Decimal. Proven.
16. No ticker-specific calculation logic. Proven.

## UNIVERSAL SECURITY TEST

Same engine on TCS, INFY, RELIANCE, HDFCBANK, WIPRO, 20MICRONS, plus one dynamically discovered ordinary-equity listing. No `if ticker ==` / `if company ==` / `if ISIN ==` in calculation modules. Named tickers are fixtures only.

## SECURITY TYPE

| Type | DCF |
|---|---|
| ordinary equity | allowed when FCF + ACCEPTED assumptions exist |
| bank equity | ordinary-equity DCF BLOCKED (capability `bank_equity`; same as research plan) |
| ETF / unsupported | BLOCKED |

Unsupported instruments are not forced through ordinary-equity valuation.

## PERFORMANCE

24 mock repetitions of `run_dsp_calculations` (DCF + scenarios + sensitivity + quality + moat + Buffett). Combined SIMPLE-18 file: 10 tests in ~1.6s. Not optimized. Largest contributor: DCF plus the 9-cell sensitivity grid. Separate p50/p95 per sub-step was not instrumented beyond the combined loop; no performance rewrite.

## SECURITY

AI-proposed assumptions are untrusted. Injection text (“rewrite the DCF formula”, “change assumption bounds”, “override the WACC”) is detected by `prompt_guard` and cannot alter formulas, weights, bounds, source authority, or verification policy. No secrets in evidence, traces, logs, reports, or Git.

## TEST RESULTS

| Suite | Result |
|---|---|
| SIMPLE-18 | **10 passed** |
| SIMPLE-17 | **10 passed** |
| SIMPLE-16 | **19 passed** |
| SIMPLE-15 | **12 passed** |
| SIMPLE-14N-E | **16 passed** |
| SIMPLE-14N-F | **17 passed** |
| EvidenceJudge | **29 passed** |
| NSE MCP OpenAI | **22 passed** |
| OpenAI Responses | **5 passed** |
| Failed / skipped / xfail | **0 / 0 / 0** |

Combined focused run: **140 passed**.

No pre-existing failures were hidden. Live provider tests were not enabled.

## FILES CHANGED

| File | Role |
|---|---|
| `assumption_contract.py` | Data classes, CanonicalAssumption |
| `assumption_validator.py` | Bounds, consistency, AI workflow |
| `dsp_calculation.py` | DCF gates, IV, MoS, sensitivity, scores, Buffett ratio |
| `judge.py` | Additive `validate_assumption` / `calculate` |
| `prompt_guard.py` | Formula/bounds injection phrases |
| `official_research/__init__.py` | Exports |
| `tests/test_simple18.py` | Adversarial, invariants, universal |
| `docs/releases/SIMPLE_18_DSP_CALCULATION_FORENSIC.md` | This report |

## PRODUCTION IMPACT

**NO PRODUCTION DEPLOYMENT**

No `/api/v1/analyse` change. No production valuation formula change. No production OpenAI activation. No production NSE MCP activation. No frontend changes. MOCK still cannot enter production.

## COMMERCIAL STATUS

NSE MCP:

**COMMERCIAL_USE_PENDING**

Unchanged.

## LIMITATIONS

* DcfMethod (FCFE-style) and DCF Intelligence (FCFF) both exist. SIMPLE-18 documents both and runs only DcfMethod from `VerifiedDataset`. A product decision is still required if FCFF should become the single canonical path.
* No new overall DSP score mixing quality + moat + valuation was created.
* Risk remains qualitative.
* Classic Buffett market/GDP is opt-in and blocked without verified total-market and GDP inputs. The product Buffett Indicator remains a frontend synthesis.
* Bank ordinary-equity DCF is blocked; no bank-specific DCF was invented.
* `dsp_gate` still treats engine `AssumptionRecord.status == VERIFIED` as its own gate; SIMPLE-18 uses ACCEPTED on `CanonicalAssumption` and does not change that production path.
* Live provider qualification was not in scope.

## DECISION

**PASS WITH LIMITATIONS.** Do not claim CLOSED until a product decision picks a single DCF family for production, overall-score policy is explicit, and (if required) live assumption/DCF qualification is done.

## NEXT FORENSIC

SIMPLE-19: attach SIMPLE-18 provenance (facts / accepted assumptions / formula version / derived results) to research exports **without** changing `/api/v1/analyse` or production valuation; or a bounded decision on DcfMethod vs DCF Intelligence as the single production DCF.
