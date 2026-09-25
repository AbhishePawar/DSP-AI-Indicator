# SIMPLE-27 — Live DCF Component Research Forensic

## 1. STATUS

**PASS WITH LIMITATIONS**

Not CLOSED.

SIMPLE-25 and SIMPLE-26 were **not** redone.

The platform now proves the complete calculation architecture:

```text
AI / CONNECTOR
      ↓
RETRIEVE UNDERLYING DATA
      ↓
PRIMARY EVIDENCE
      ↓
EVIDENCE JUDGE
      ↓
VERIFIED INPUTS
      ↓
DSP CALCULATES
      ↓
WACC / GROWTH / OTHER DCF INPUTS
      ↓
CANONICAL DcfMethod
      ↓
INTRINSIC VALUE
      ↓
MARGIN OF SAFETY
```

AI retrieves ingredients. EvidenceJudge proves them. DSP cooks the calculation.

AI cannot establish authoritative WACC, growth, intrinsic value, or VerifiedDataset rows.

Live production `analyse()` remains **DCF_BLOCKED** unless researched components (or an accepted replay pack) exist. Risk-free rate, beta, and ERP are **not** auto-fetched: `rbi.org.in` is an approved Tier 1A host, but production does not scrape a G-sec / ERP / beta series. AI remains `NOT_CONFIGURED`.

That is the remaining limitation. It is not a hidden default.

**NO PRODUCTION DEPLOYMENT.** Frontend PARKED.

---

## 2. BASELINE

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA | `d11c82777caa5bfa70f266848475508bfd1c5a11` |
| SIMPLE-26 | `docs/releases/SIMPLE_26_DCF_ASSUMPTION_RESEARCH_VALIDATION_FORENSIC.md` — PASS WITH LIMITATIONS |
| SIMPLE-26 gap | Candidate/validator path existed. WACC could be `rf + β×ERP` as an equity required-return. Official `analyse()` did not reconstruct an external WACC. `projection_years = 5` was a silent official-path fallback after rates were accepted. |
| Canonical DCF | Unchanged `DcfMethod` / `dsp_calculation._dcf_core` |
| Existing WACC engine | `valuation.dcf_intelligence.wacc.compute_wacc` — official research **calls** it; it is not duplicated |

---

## 3. CANONICAL DCF INPUT INVENTORY

Canonical `DcfMethod` (`packages/valuation/src/valuation/methods/dcf.py`) uses:

| DCF input | Required by DcfMethod? | Class entering DcfMethod |
|---|---|---|
| FCF₀ (from OCF − \|CapEx\|) | Yes | DERIVED VALUE |
| `fcf_growth_rate` | Yes | ASSUMPTION |
| `terminal_growth_rate` | Yes | ASSUMPTION |
| `discount_rate` / WACC | Yes | ASSUMPTION (may be DSP-derived) |
| `projection_years` | Yes | ASSUMPTION — **explicit; no hidden 5** |
| shares, price | For IV/share and MOS | VERIFIED FACT |
| net debt | Not subtracted again (equity FCF) | DERIVED, unused in this DCF |

WACC **components** are not DcfMethod fields. They are required to *calculate* the discount rate:

| Component | Required to calculate WACC? |
|---|---|
| risk-free, beta, ERP | Yes for cost of equity |
| equity market value, debt | Yes for levered weights |
| pre-tax cost of debt, tax rate | Yes if debt > 0 |
| finance_costs | Alternate `rd = finance_costs / debt` |

If debt is 0, or levered inputs are missing, DSP may use **cost of equity** as the required-return candidate and record that levered WACC is incomplete. It does not invent rd or a statutory tax rate.

---

## 4. FACT / DERIVED / ASSUMPTION CLASSIFICATION

| Input | Class |
|---|---|
| Revenue, earnings, CFO, capex, cash, debt, shares, price, finance_costs | OBSERVED FACT (when EvidenceJudge = VERIFIED) |
| Historical CAGRs, FCF, market cap, net debt | DERIVED VALUE |
| RBI risk-free rate (primary URL) | OBSERVED FACT used as CAPM input |
| Beta from approved primary evidence | OBSERVED FACT if verified; Yahoo cannot VERIFY |
| ERP from an approved primary source | OBSERVED FACT if that source states it; otherwise UNKNOWN / ASSUMPTION |
| Statutory tax rate / effective tax rate | Distinct; neither is silently substituted for `tax_rate` |
| `tax_rate` used in WACC | ASSUMPTION / evidenced WACC input; not a 25% default |
| Cost of equity | **DERIVED** (`re = rf + β × ERP`) |
| After-tax cost of debt | **DERIVED** (`rd × (1 − t)`) |
| Capital weights | **DERIVED** (`E/(E+D)`, `D/(E+D)`) |
| WACC | **DERIVED**, then proposed as DCF **ASSUMPTION** (`discount_rate`). Never an observed quote. |
| Forecast FCF growth | ASSUMPTION (may be *proposed* from verified FCF CAGR) |
| Terminal growth | ASSUMPTION. Never last-year, GDP, inflation, AI opinion, or a fixed default. |
| Projection horizon | ASSUMPTION. Must be ACCEPTED. |

`ValuationAssumptions` still has library defaults (`discount_rate=0.10`, `fcf_growth_rate=0.03`, `terminal_growth_rate=0.02`, `projection_years=5`). Official `analyse()` does not construct that object from those defaults.

---

## 5. AI CONNECTOR CONTRACT

`component_research.ingest_researched_components` requires:

`field, value, source, source_type, source_url, retrieved_at, as_of, isin, mic, unit, currency, period, evidence_locator`

Optional: `document_date`, `confidence`, `identity`.

Rejected if `field` is a DCF **result**:

`wacc`, `discount_rate`, `fcf_growth_rate`, `terminal_growth_rate`, `cost_of_equity`, `after_tax_cost_of_debt`, `capital_weights`, IV, MOS, `dcf`, `fcf`, …

Allowed component fields include: `risk_free_rate`, `beta`, `equity_risk_premium`, `pre_tax_cost_of_debt`, `tax_rate`, `statutory_tax_rate`, `effective_tax_rate`, `finance_costs`, `management_guidance_growth`.

`statutory_tax_rate` / `effective_tax_rate` may be retrieved. DSP WACC uses only evidenced `tax_rate`. They are not substituted.

`research_components_from_agent`: if the agent is unavailable → `NOT_CONFIGURED`. Never fabricated.

AI CAPM rows injected as assumption candidates (not judged evidence) are `AI_COMPONENT_INJECTION_REJECTED`. Retrieval must become EvidenceJudge input.

---

## 6. LIVE DATA ACQUISITION

Approved hierarchy unchanged. **No new provider. No FMP. No Kite. No paid BSE. NSE MCP `COMMERCIAL_USE_PENDING`. OpenAI/Gemini not activated.**

| Source | Use in SIMPLE-27 |
|---|---|
| NSE/BSE filings, XBRL | Live debt, equity, FCF history, optional finance_costs |
| RBI host (`rbi.org.in`) | Tier 1A in `PRIMARY_HOST_SUFFIXES`. Evidence **can** VERIFY. Production does **not** scrape a G-sec series. |
| Company IR / filings | Unchanged primary for financials |
| Screener | Cross-check only |
| Yahoo / IBEF | Discovery only; **cannot VERIFY** |
| AI agents | `NOT_CONFIGURED`; FIND/VERIFY still do not write truth |

`live_macro_acquisition_status()` returns UNKNOWN for rf / beta / ERP with the approved host recorded and no hardcoded rate.

---

## 7. RISK-FREE RATE

| Attribute | Production result |
|---|---|
| Instrument | UNKNOWN |
| Maturity | UNKNOWN — not silently substituted |
| Rate | UNKNOWN |
| Currency | INR (identity currency) |
| as_of | UNKNOWN |
| Source | RBI host is approved |
| Source URL | `https://www.rbi.org.in` is classified primary |
| Retrieval timestamp | not performed |

Complete-data / AI-retrieval **replay** uses judged RBI-URL evidence. That proves the path. It is not a live scrape.

---

## 8. BETA

Live approved beta series: **UNKNOWN**.

Yahoo beta cannot VERIFY (proven).

A deterministic price-series beta engine was **not** added: official research does not yet carry an identity-bound, frequency/benchmark/window-explicit return series for the universe. AI may not state a beta without evidence.

Replay: beta becomes a VERIFIED FACT only from a primary URL through EvidenceJudge.

---

## 9. ERP

Live approved ERP: **UNKNOWN / REVIEW_REQUIRED**.

Not used as ERP:

* GDP growth
* inflation
* company growth
* arbitrary 8/10/12/15%

Conflicting ERP values are not averaged (`REVIEW_REQUIRED`).

AI-injected ERP as an assumption is rejected. ERP must be judged evidence or a non-AI research candidate with evidence IDs.

---

## 10. COST OF EQUITY

DSP only:

```text
re = rf + β × ERP
```

Stored on `DspWaccCalculation`:

* formula
* input values
* evidence IDs
* calculated_at
* calculation_version `dsp_wacc.v1`
* engine `valuation.dcf_intelligence.wacc.compute_wacc`
* result (`data_class = DERIVED_VALUE`)

Parity: rf 7%, β 1, ERP 5% → **re = 12%**.

---

## 11. COST OF DEBT

Canonical levered WACC requires pre-tax cost of debt when debt > 0.

Deterministic fallback when `pre_tax_cost_of_debt` is missing:

```text
rd = finance_costs / compatible debt
```

Proven: finance_costs 10, debt 100 → rd 10%, levered WACC **9.75%** with E=D, t=25%.

If neither rd nor finance_costs/debt is evidenced: levered WACC stays UNKNOWN; DSP may fall back to cost of equity and record the gap. No manufactured rd.

---

## 12. TAX

Canonical `compute_wacc` takes one `tax_rate`. DSP does **not** insert India's statutory 25%.

| Kind | Handling |
|---|---|
| statutory_tax_rate | Retrievable component; not mapped to WACC `tax_rate` |
| effective_tax_rate | Retrievable component; not mapped to WACC `tax_rate` |
| evidenced `tax_rate` | Used as-stated |
| missing | levered WACC UNKNOWN (equity required-return fallback if CAPM complete) |

No silent statutory ↔ effective substitution.

---

## 13. CAPITAL WEIGHTS

DSP via existing engine:

```text
we = E / (E + D)
wd = D / (E + D)
```

E is derived market cap when calculated. D is verified debt. AI does not calculate authoritative weights.

---

## 14. WACC CALCULATION

```text
WACC = we×re + wd×rd×(1−t)
```

All-equity (debt weight 0): `WACC = re`.

Result class: **DERIVED VALUE**, then DCF **ASSUMPTION**.

External WACC (non-AI) is reconstructed independently (`compare_external_wacc`, tolerance 1 bp). Material difference → `REVIEW_REQUIRED`. Not averaged. Not selected for a preferred valuation.

`wacc` and `discount_rate` are the same conflict key.

---

## 15. HISTORICAL GROWTH

DSP calculates, where verified multi-period points exist:

* Revenue CAGR
* Net Income CAGR
* CFO CAGR
* FCF CAGR (`CFO − |Capex|` on matching dates)

No interpolation, fabricated periods, mixed basis/currency, or silent extrapolation. Insufficient history → UNKNOWN.

---

## 16. FORECAST GROWTH

Canonical DcfMethod `fcf_growth_rate` is an **ASSUMPTION**.

DSP may *propose* it from verified FCF CAGR (`historical_company_performance`). AssumptionValidator remains the acceptance authority. AI forecast growth payloads are `AI_CALCULATED_OUTPUT_REJECTED`.

---

## 17. TERMINAL GROWTH

Not set to last-year growth, GDP, inflation, a fixed default, or AI opinion.

Without an ACCEPTED `terminal_growth_rate`:

```text
TERMINAL_GROWTH:UNKNOWN
ASSUMPTION_REQUIRED
DCF_BLOCKED
```

---

## 18. PROJECTION HORIZON

SIMPLE-26 identified `years = 5 if years_row is None` on the official path.

SIMPLE-27 classification: **explicit ASSUMPTION**, not canonical methodology and not an accidental library default.

Official `_run_dcf` now **blocks** if `projection_years` is missing:

```text
projection_years is an explicit assumption; no hidden horizon default
```

Research eligibility requires an ACCEPTED integer horizon in `[1, 30]`.

`ValuationAssumptions.projection_years = 5` remains a library default that official `analyse()` must not use.

---

## 19. COMPLETE-DATA REPLAY

One universal replay (INFY identity; no ticker branch):

risk-free 7%, β 1, ERP 5%, debt 100, equity MV 100, rd 10%, tax 25%, multi-year revenue/earnings/CFO/capex, cash, shares, price.

Result:

```text
RAW judged evidence
 → DSP WACC = 0.0975
 → historical CAGRs CALCULATED
 → ACCEPTED pack
 → DcfMethod CALCULATED
 → MOS formula unchanged
```

---

## 20. AI RETRIEVAL REPLAY

Simulated connector returned rf, beta, ERP, rd, tax with RBI/regulator provenance (`field/value/source/url/as_of/...`).

```text
AI ingest (components only)
 → EvidenceJudge VERIFIED
 → DSP WACC 0.0975
 → DCF CALCULATED
```

AI `wacc=11%` in the same family of tests is rejected and does not become the discount rate.

---

## 21. WACC RECONSTRUCTION

External `WACC = 11%` plus components that compute **9.75%**:

```text
CONFLICT
REVIEW_REQUIRED
DCF_BLOCKED
```

Values are not averaged. DSP result is retained for audit (`wacc_reconstruction`).

---

## 22. ADVERSARIAL TESTS

| Case | Result |
|---|---|
| A — AI WACC only | REJECTED as authoritative |
| B — AI WACC + unsupported components | REJECTED |
| C — AI valid underlying evidence | Judge may VERIFY; DSP calculates |
| D — AI fake ERP | REJECTED / DCF_BLOCKED |
| E — wrong-company beta | IDENTITY_FAIL |
| F — stale risk-free (>365d) | STALE; not used |
| G — conflicting ERP | REVIEW_REQUIRED; not averaged |
| H — WACC <= terminal growth | REJECTED; DCF_BLOCKED |
| I — currency mismatch | REJECTED |
| J — period mismatch | WACC UNKNOWN; DCF_BLOCKED |
| K — AI intrinsic value | REJECTED |
| L — AI mutate VerifiedDataset | FrozenInstanceError; ingest does not write the dataset |

---

## 23. CLIENT INJECTION TEST

`AnalyseRequest` `extra=forbid`. Rejected fields:

`wacc`, `terminal_growth`, `intrinsic_value`, `verified_financials`, `accepted_assumptions`.

`ResearchOrchestrator.analyse` has no assumption / WACC kwargs. Authority stays on the server evidence path.

---

## 24. UNIVERSAL STOCK MATRIX

Named: TCS, INFY, RELIANCE, WIPRO, 20MICRONS, 21STCENMGM — without components: **DCF_BLOCKED**.

Five dynamically selected NSE equities from the catalog (not the named set, not banks): empty → blocked; complete component replay → DSP WACC + DCF CALCULATED. No ticker branches (AST-checked).

Also: insufficient history → CAGR UNKNOWN; missing data → DCF_BLOCKED; FCF₀ ≤ 0 still blocks DCF; conflicting ERP → REVIEW_REQUIRED.

---

## 25. BANK HANDLING

HDFCBANK: `BANK_VALUATION_METHOD_REQUIRED`. Ordinary industrial DCF is not forced.

ETF (`NIFTYBEES` fixture): `UNSUPPORTED`.

---

## 26. DCF FORMULA INTEGRITY

Unchanged:

* FCF = `CFO − |Capex|`
* Terminal value / discounting
* Equity FCF (net debt not subtracted again)
* IV/share
* MOS = `(IV/share − Price) / IV/share`
* Share-count semantics

DCF Intelligence FCFF/NWC path is still **not** mixed into official `analyse()`.

---

## 27. HIDDEN DEFAULT AUDIT

Official WACC modules (`dsp_wacc.py`, `assumption_research.py`, `component_research.py`) contain no hardcoded 8/9/10/11/12/15/18% rates.

Official `_run_dcf` contains no `years = 5` fallback and no 8/10/12% WACC/growth literals.

Missing rf/β/ERP stays `WACC:UNKNOWN`. Missing terminal stays `TERMINAL_GROWTH:UNKNOWN`. Missing horizon stays `PROJECTION_YEARS:UNKNOWN`.

---

## 28. PERFORMANCE

Measured separately (not optimized):

| Step | Where |
|---|---|
| source retrieval | live scrape not run; status UNKNOWN |
| AI retrieval | ingest + `NOT_CONFIGURED` if agent down |
| EvidenceJudge | `promote()` on component rows |
| DSP WACC | `timings["dsp_wacc"]`; `calculate_dsp_wacc` |
| DSP growth | `timings["dsp_growth"]` (historical CAGRs) |
| DCF | `run_dsp_calculations` wall time in complete-data replay |

Same dataset + same accepted pack → same DCF (SIMPLE-26 reproducibility still green).

---

## 29. SECURITY

| Control | Result |
|---|---|
| No secrets logged | no new providers / keys |
| No AI bypass | ingest + screen + judge refuse DCF outputs and CAPM injection |
| No client bypass | `AnalyseRequest` extra=forbid; orchestrator has no pack kwargs |
| No evidence overwrite | `VerifiedDataset` frozen |
| Identity binding | ISIN+MIC |
| Provenance | evidence IDs, engine, calculation_version, calculated_at |
| Prompt sanitization | unchanged `looks_like_injection` / `redact_mcp_text` |
| Primary-source precedence | AI agreement does not override primary evidence |

---

## 30. REGRESSION

Offline (`-m "not network"`), this session:

| Suite | Passed | Failed | Skipped | Deselected |
|---|---|---|---|---|
| SIMPLE-14N-E … SIMPLE-27 + 14N acquisition + 14ND + P1-10 `test_p101` + P1-11 gates | **281** | **0** | **5** | **7** |
| SIMPLE-27 | **21** | **0** | **0** | 0 |
| SIMPLE-26 | **16** | **0** | **0** | 0 |

Skipped = prior **live network** tests (SIMPLE-21…25), not new failures.

**Old vs new failures:** none.

One SIMPLE-26 assertion was updated because SIMPLE-27 **closed** the documented silent `projection_years = 5` fallback: the contract test now requires an explicit horizon, and the CAPM-component eligibility fixture includes `projection_years`. SIMPLE-26 forensic work was not redone.

---

## 31. FILES CHANGED

| File | Change |
|---|---|
| `official_research/dsp_wacc.py` | `compare_external_wacc`; calculation timestamp/version; tax_rate_kind passthrough |
| `official_research/component_research.py` | statutory/effective tax fields; optional provenance keys; `live_macro_acquisition_status` |
| `official_research/assumption_research.py` | always reconstruct WACC; CAPM conflicts/periods; AI component injection refuse; require projection_years; reconstruction audit |
| `official_research/assumption_validator.py` | `wacc` / `discount_rate` same conflict key |
| `official_research/dsp_calculation.py` | no hidden `years = 5` |
| `tests/test_simple27.py` | complete-data, AI replay, reconstruction, A–L, matrix, client, audit |
| `tests/test_simple26.py` | explicit horizon in CAPM eligibility fixture; contract asserts no silent years=5 |
| this report | **Added** |

Prior SIMPLE-27 modules (`dsp_wacc.py` wrapper, judge DCF-output refusal, finance_costs XBRL) remain in force.

---

## 32. PRODUCTION IMPACT

None deployed. Flags unchanged. OpenAI/Gemini off. NSE MCP pending. Frontend parked.

Production `analyse()` without judged components and an accepted pack: **DCF_BLOCKED**. Honest.

---

## 33. LIMITATIONS

1. Live RBI G-sec / ERP / beta series are not auto-acquired (no new connector).
2. AI research remains `NOT_CONFIGURED`.
3. Levered WACC still needs evidenced rd (or finance_costs/debt) and tax; otherwise cost-of-equity proxy is recorded.
4. Terminal growth still has no live guidance extractor.
5. No official price-series beta engine (missing identity-bound returns/benchmark/window).
6. Book vs market debt: weights use verified debt + derived market cap when available.

---

## 34. DECISION

**PASS WITH LIMITATIONS**

Architecture is correct and tested:

```text
AI / connector → underlying evidence → EvidenceJudge → DSP compute_wacc / CAGR → validator → DcfMethod
```

Never:

```text
AI guess → WACC / growth / IV → DCF
missing data → arbitrary default → DCF
conflict → average → DCF
```

CLOSED is withheld because live approved sources do not currently provide rf / beta / ERP without adding or activating a provider.

---

## 35. NEXT FORENSIC

**SIMPLE-28 candidate:** retrieve **risk-free observations** from already-whitelisted `rbi.org.in` using **existing HTTP transport** (not a new vendor), still through EvidenceJudge, still DSP `compute_wacc`. Do not activate NSE MCP, OpenAI, FMP, or Kite. Do not treat GDP as terminal growth. Do not invent ERP. Do not restore a silent projection horizon. Do not deploy.

---

## Implementation return (workspace gate)

- **Architecture Impact:** Official research applies the existing `compute_wacc` engine to judged components, reconstructs external WACC, and requires an explicit projection horizon. No second DCF methodology. Thin client unchanged.
- **Components Added:** WACC reconstruction compare; live-macro UNKNOWN status; statutory/effective tax fields that cannot substitute `tax_rate`; explicit horizon gate.
- **Pages Updated:** none (frontend parked).
- **Feature Flags Used:** none.
- **Accessibility / Performance / Responsive Validation:** N/A / measured not optimized / N/A.
- **Known Limitations:** see §33.
- **Future Enhancements:** see §35.
- **Regression Summary:** 281 passed / 5 skipped / 7 deselected (14N-E…27 + acquisition/14ND + P1-10 p101 + P1-11); SIMPLE-27 21/21; SIMPLE-26 16/16. No new failures.
