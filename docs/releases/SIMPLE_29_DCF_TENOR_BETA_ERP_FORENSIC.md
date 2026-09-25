# SIMPLE-29 — DCF TENOR POLICY + APPROVED BETA/ERP COMPONENT RESEARCH FORENSIC

## 1. Executive Verdict

**PASS WITH LIMITATIONS**

Not CLOSED.

SIMPLE-25, SIMPLE-26, SIMPLE-27, and SIMPLE-28 were **not** redone except as regression.

The architecture remains:

```text
PRIMARY / APPROVED RESEARCH
          ↓
      RAW EVIDENCE
          ↓
     EvidenceJudge
          ↓
   VERIFIED COMPONENTS
          ↓
          DSP
          ↓
   ┌──────┴────────┐
   ↓               ↓
WACC             Growth/
                 CAGRs
   ↓
DcfMethod
   ↓
Intrinsic Value
   ↓
Margin of Safety
```

Never:

```text
AI → WACC → DCF
AI → Intrinsic Value
Unknown → guessed assumption → DCF
```

SIMPLE-29 established an **explicit DCF risk-free tenor policy**. That policy is **POLICY_GAP**. It does not invent 91-day, 182-day, 364-day, or 10-year G-sec merely so WACC can run.

Against that policy, the SIMPLE-28 RBI Treasury Bill observation remains:

```text
STATUS: VERIFIED_OBSERVATION
DCF_BINDING: POLICY_GAP
REASON: tenor unavailable AND no preferred tenor exists
```

Approved live **beta** and **ERP** series still do not exist on the authorized HTTPS/research path. Yahoo cannot VERIFY. AI is NOT_CONFIGURED and is not the authority. Therefore:

```text
RBI T-bill VERIFIED (unbound)
+
BETA UNKNOWN
+
ERP UNKNOWN
        ↓
WACC INCOMPLETE
        ↓
DCF BLOCKED
```

That is the correct fail-closed outcome.

DSP still calculates WACC **only** through `valuation.dcf_intelligence.wacc.compute_wacc` when verified components are supplied. Replay Case 1: cost of equity **0.12**, WACC **0.0975**. AI/provider WACC cannot override that engine.

**NO PRODUCTION DEPLOYMENT.** Frontend PARKED. No FMP, Kite, NSE MCP, OpenAI, Gemini, Damodaran ERP, or Yahoo beta.

---

## 2. Starting State

SIMPLE-28 — **PASS WITH LIMITATIONS** (`docs/releases/SIMPLE_28_RBI_RISK_FREE_LIVE_WACC_FORENSIC.md`). Not CLOSED.

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA (pre-SIMPLE-29 work) | `d11c82777caa5bfa70f266848475508bfd1c5a11` |
| SIMPLE-28 live RBI | NSDP `https://www.rbi.org.in/Scripts/BS_NSDPDisplay.aspx` |
| Observation | Treasury Bill Rates **5.2089%**, as_of **2026-09-09**, INR |
| Tenor | **UNSPECIFIED** on the source page |
| Binding | **POLICY_GAP** — not fed to `compute_wacc` |
| Beta / ERP | UNKNOWN on approved architecture |
| WACC engine | one: `valuation.dcf_intelligence.wacc.compute_wacc` via `calculate_dsp_wacc` |
| DCF | blocked on live `analyse()` |
| OpenAI / Gemini | NOT_CONFIGURED |
| NSE MCP | COMMERCIAL_USE_PENDING |

SIMPLE-28 next-forensic candidate was exactly this work: document tenor policy without a convenience scrape; research beta/ERP through EvidenceJudge; keep DSP as the only WACC calculator.

---

## 3. Tenor Policy

### Chosen policy

```text
Policy ID: dsp.dcf.risk_free_tenor.v1
DCF_RISK_FREE_MATURITY_POLICY = POLICY_GAP
preferred_maturity = None
required_maturity = None
acceptable_alternatives = ()
maximum_maturity_mismatch = None
known_maturity_required_to_bind = True
unlabeled_treatment = VERIFIED_OBSERVATION_NON_BINDING
```

Human copy: `docs/valuation/DCF_RISK_FREE_TENOR_POLICY.md`  
Machine copy: `packages/data_engine/src/data_engine/official_research/dcf_tenor_policy.py`

| Rule | Statement |
|---|---|
| Preferred maturity/tenor | **None established** |
| Acceptable alternatives | **None** (no preferred tenor, so no substitutes) |
| Maximum maturity mismatch | **Not applicable** until a required tenor exists |
| Observation vs valuation date | `as_of` must be on or before `valuation_date`; `retrieved_at` is not `as_of`; later observation → REJECTED |
| Known maturity required to bind | **Yes** |
| Unlabeled government yield | VERIFIED_OBSERVATION, DCF_BINDING = POLICY_GAP |
| Stale observations | Age vs valuation date **> 30 calendar days** → RESEARCH_REQUIRED; missing date → UNKNOWN, not bound |
| Currency | Indian equity: **INR**; no silent FX; mismatch → REJECTED |
| Conflicting observations | Do **not** average; unresolved → REVIEW_REQUIRED, WACC blocked |
| Multiple eligible maturities | Until a preferred tenor exists → REVIEW_REQUIRED, not a silent pick |

Binding table:

| Case | Observation | DCF binding |
|---|---|---|
| Unlabeled T-bill | VERIFIED_OBSERVATION | POLICY_GAP |
| Labeled 10-year G-sec while policy is GAP | VERIFIED_OBSERVATION | POLICY_GAP (not a silent 10-year choice) |
| Repo / Bank Rate / MCLR | REJECTED as risk-free | REJECTED |
| Required tenor later set, mismatch | — | POLICY_MISMATCH |
| Required tenor later set, exact labeled match, judge PASS | VERIFIED | BOUND |

When a required tenor is later set: unlabeled → `REVIEW_REQUIRED`; different labeled tenor → `POLICY_MISMATCH`; exact match → `BOUND`. `binding_decision` in `rbi_risk_free.py` maps `POLICY_MISMATCH` → `REJECTED` so SIMPLE-28 adversarial D remains fail-closed.

### Evidence/policy basis

Inspected first (no invention):

- `valuation.dcf_intelligence.assumptions.CapmInputs` — fields `risk_free_rate`, `beta`, `equity_risk_premium` only; **no tenor**.
- Official `DcfMethod` (`valuation/methods/dcf.py`) — consumes a discount rate; **does not name** T-bill vs G-sec maturity.
- RS-004 Valuation — does **not** specify 91-day / 10-year.
- SIMPLE-28 forensic — already recorded `POLICY_GAP` after live NSDP retrieval.

### Rationale

The mission forbids inventing a finance convention merely to make DCF run. Damodaran-style 10-year G-sec, cash-like 91-day T-bill, and “any government yield is rf” are **new methodology**, not reuse of an existing project convention.

Therefore the documented policy **is** POLICY_GAP. That is a positive contract, not an omission.

### Unsupported assumptions (not used)

- 91-day / 182-day / 364-day T-bill
- 10-year G-sec as default DCF rf
- Damodaran India ERP
- GDP / inflation as rf or ERP
- Yahoo / AI-estimated beta

---

## 4. RBI Risk-Free Observation

Evaluated **after** the tenor policy existed. Outcome **B — VERIFIED BUT NON-BINDING**.

| Attribute | Value |
|---|---|
| Source | RBI NSDP, Tier 1A `rbi.org.in` |
| Source URL | `https://www.rbi.org.in/Scripts/BS_NSDPDisplay.aspx` |
| Observation | Treasury Bill Rates **5.2089%** p.a. (decimal `0.052089`) |
| Date | as_of **2026-09-09** (NSDP Date of Publish 2026-09-11) |
| Tenor | **UNSPECIFIED** (page does not label 91/182/364-day) |
| Currency | **INR** |
| Semantics | `treasury_bill` / GOVERNMENT_YIELD_CANDIDATE — not repo, Bank Rate, MCLR, CRR, SLR, inflation |
| EvidenceJudge | observation may be judged; **not** promoted as verified `risk_free_rate` WACC input while unbound |
| Binding status | **POLICY_GAP** |
| `wacc_input` | **None** |

Bank Rate 5.50% and MCLR remain **REJECTED as risk-free**.

A labeled **10-year G-sec** under the current POLICY_GAP is also **POLICY_GAP**, not BOUND. Silent 10-year binding would violate the policy.

Wrong currency (USD listing vs INR yield) → REJECTED (adversarial J).

---

## 5. Beta Research

### Sources

Preferred hierarchy inspected; **no new provider added**.

| Tier | Sources considered | Live WACC-eligible beta? |
|---|---|---|
| 1A | NSE, BSE, SEBI, MCA, RBI, NSDL, CDSL | **No** identity-bound company beta series on the approved HTTPS path |
| 1B | issuer IR / annual reports / filings | Not auto-extracted as levered-equity beta in this forensic |
| 1C | Screener | Cross-check only; **cannot VERIFY**; cannot override primary |
| 2 | Yahoo Finance, IBEF | Yahoo URL → qualifier **REJECTED** (`secondary/forbidden beta cannot VERIFY`) |
| 3 | Gemini / ChatGPT / Deep Search / Claude | **NOT_CONFIGURED**; AI output is not evidence |

`live_macro_acquisition_status()["beta"]`:

```text
UNKNOWN
no approved live beta series; Yahoo cannot VERIFY;
official path has no price-series beta engine
```

No FMP, Kite, paid BSE, commercial NSE MCP, or unauthorized scrape.

### Candidates

Qualifier: `qualify_capm_component` in `capm_components.py`. Not a second WACC engine.

Required / checked:

- company / ticker / ISIN / MIC identity match
- provenance (`source_url`)
- source class (secondary/forbidden cannot VERIFY)
- methodology / period / as_of (all three missing → REJECTED)
- forbidden kinds: industry, unlevered, peer, ETF, index, AI estimate
- freshness: observation after valuation → REJECTED; age **> 365 days** vs valuation → REVIEW_REQUIRED / STALE
- AI proposer without primary evidence cannot become authoritative

`research_live_capm_components` does **not** scrape Yahoo. If an agent is unavailable → `AI = NOT_CONFIGURED`. Live status stays UNKNOWN. Candidates that later appear still go through EvidenceJudge; only judged/eligible rows can become DSP inputs.

SIMPLE-27 fixtures that lack methodology continue through `research_dcf_assumptions` / `official_filing_detail` and are **not** silently failed by the new qualifier.

### EvidenceJudge results

Forbidden `semantic_kind` for field `beta`: `industry_beta`, `unlevered_beta`, `peer_beta`, `etf_beta`, `index_beta`, `ai_estimate` → **REJECTED**.

Yahoo / industry-beta adversarial tests: **REJECTED**.

Wrong-company ISIN and wrong MIC: ingest **IDENTITY_FAIL**.

Stale beta (as_of 2024-01-01 vs valuation 2026-09-12): **REVIEW_REQUIRED**, `wacc_eligible=False`.

AI beta without provenance: ingest **REJECTED**.

### Final status

```text
BETA = UNKNOWN
WACC = INCOMPLETE
DCF = BLOCKED
```

Legitimate: no synthetic live beta was created to obtain a green DCF.

---

## 6. ERP Research

### Sources

Same hierarchy. No approved India-equity ERP series on authorized hosts. GDP, inflation, and company growth are **not** ERP. US-market ERP is incompatible with Indian equity DCF.

`live_macro_acquisition_status()["equity_risk_premium"]`:

```text
UNKNOWN
no approved ERP series; GDP/inflation/company growth/fixed % are not used
```

AI not configured. Damodaran / commercial ERP feeds **not added**.

### Candidates / methodology

Qualifier requires **methodology and observation date**. Missing either → REJECTED.

Also rejected:

- market/geography in `{us, usa, united states, sp500, nyse, nasdaq, us_market, us_erp, gdp, inflation, ai_estimate, company_growth}`
- currency mismatch vs listing
- methodology tokens `gdp` / `inflation` / `ai estimate` / `ai opinion`
- secondary/forbidden source class
- AI proposer without primary source
- as_of after valuation_date
- age **> 548 days** vs valuation → REVIEW_REQUIRED / STALE

Conflicting ERP 5.5% vs 7.0% → **REVIEW_REQUIRED**, values **not averaged**, DSP WACC remains `None`.

### EvidenceJudge results

Forbidden `semantic_kind` for `equity_risk_premium`: `us_market`, `us_erp`, `gdp`, `inflation`, `ai_estimate`, `company_growth` → **REJECTED**.

US ERP applied to TCS: qualifier and judge **REJECTED**.

ERP without methodology/date: **REJECTED**.

### Final status

```text
ERP = UNKNOWN
WACC = INCOMPLETE
DCF = BLOCKED
```

Research may later return `ERP candidate + provenance + methodology + date + market`. EvidenceJudge decides. DSP consumes only verified ERP. That path is implemented; live evidence is still absent.

---

## 7. WACC Architecture

Forensic search for parallel engines:

| Symbol | Location | Role |
|---|---|---|
| `compute_wacc` | `packages/valuation/src/valuation/dcf_intelligence/wacc.py` | **Sole calculation** |
| `calculate_dsp_wacc` | `official_research/dsp_wacc.py` | Wrapper: missing components → UNKNOWN; calls `compute_wacc` |
| `DSP_WACC_ENGINE` | `"valuation.dcf_intelligence.wacc.compute_wacc"` | Public engine id |
| Nested checkout copy | `DSP-AI-Indicator/packages/valuation/.../wacc.py` | Duplicate tree on disk; **not imported** by data_engine |

**Not created:**

```text
compute_rbi_wacc()
compute_ai_wacc()
compute_beta_wacc()
compute_market_wacc()
```

`capm_components.py` and `dcf_tenor_policy.py` contain none of those names (AST + string checks in tests).

External/provider WACC quotes:

- ingest of AI `wacc` → **REJECTED** (`AI_FORBIDDEN_RESULT_FIELDS`)
- EvidenceJudge treats `wacc` as a derived field, not a VERIFIED fact
- `compare_external_wacc(0.0975, 0.11)` → **REVIEW_REQUIRED**, never averaged
- DSP engine remains authoritative

CAPM inside the one engine (unchanged):

```text
Cost of Equity = Risk Free + Beta × ERP
WACC = we × re + wd × rd × (1 − t)
```

---

## 8. DSP Calculation Proof

### Inputs (Replay Case 1 — complete verified components)

| Component | Value |
|---|---|
| risk_free | 0.07 |
| beta | 1 |
| ERP | 0.05 |
| equity market value | 100 |
| debt market value | 100 |
| pre-tax cost of debt | 0.10 |
| tax | 0.25 |
| engine | `valuation.dcf_intelligence.wacc.compute_wacc` |

### Calculated cost of equity

**0.12** = 0.07 + 1 × 0.05

### Calculated WACC

**0.0975** = 0.5 × 0.12 + 0.5 × 0.10 × (1 − 0.25)

### No AI override

Replay Case 2: AI supplies `wacc = 0.11` (`proposed_by=AI_RESEARCH`).

- AI WACC assumption **REJECTED** (`AI_CALCULATED_OUTPUT_REJECTED`)
- reconstruction does not average
- DSP WACC **retained**: `0.0975`
- `wacc_source != ai_synthesis`

Provider quote vs DSP (`compare_external_wacc`): REVIEW_REQUIRED; DSP remains the calculated value.

Missing beta or missing ERP → `calculate_dsp_wacc` status **UNKNOWN**, `wacc is None`.

Live `analyse_listing` with unbound RBI T-bill + UNKNOWN beta/ERP → `wacc_status UNKNOWN`, DCF_BLOCKED. DSP did **not** invent rates.

---

## 9. DCF Integration

Official `DcfMethod` (`valuation/methods/dcf.py`) and `compute_wacc` have **zero git diff** in SIMPLE-29.

Not modified:

- FCF calculation
- terminal value formula
- discounting formula
- margin-of-safety formula (`MOS_FORMULA` unchanged)
- shares logic
- capex logic

WACC enters DCF only as the DSP-calculated discount rate after AssumptionValidator acceptance.

| Case | Result |
|---|---|
| Complete verified components (replay) | DSP WACC calculated; DCF may run only if remaining assumptions (growth, terminal, years) are also ACCEPTED |
| Live / MOCK NSDP without bound rf, beta, ERP | **DCF_BLOCKED** — precise reason: WACC incomplete / assumptions not accepted |
| Unresolved tenor even if beta+ERP proposed | RBI `binding_status=POLICY_GAP`; `wacc_status=UNKNOWN`; **DCF_BLOCKED** |
| Missing beta | WACC incomplete; **DCF_BLOCKED** |
| Missing ERP | WACC incomplete; **DCF_BLOCKED** |
| Banks | `BANK_VALUATION_METHOD_REQUIRED` unchanged |
| ETFs | `UNSUPPORTED` unchanged |

`AnalyseRequest` remains `extra=forbid`: client cannot inject `wacc`, `beta`, `intrinsic_value`.

---

## 10. Universal Coverage

Identity path (no ticker branches in `dcf_tenor_policy.py` / `capm_components.py`):

```text
ticker/company → ISIN → MIC/exchange → security identity
→ research → evidence → judge → DSP
```

Named fixtures (not a supported universe):

| Ticker | ISIN | MIC | RBI binding | Live beta | Live ERP |
|---|---|---|---|---|---|
| TCS | INE467B01029 | XNSE | POLICY_GAP | UNKNOWN | UNKNOWN |
| INFY | INE009A01021 | XNSE | POLICY_GAP | UNKNOWN | UNKNOWN |
| RELIANCE | INE002A01018 | XNSE | POLICY_GAP | UNKNOWN | UNKNOWN |
| WIPRO | INE075A01022 | XNSE | POLICY_GAP | UNKNOWN | UNKNOWN |
| 20MICRONS | INE144J01027 | XNSE | POLICY_GAP | UNKNOWN | UNKNOWN |
| 21STCENMGM | INE253B01015 | XNSE | POLICY_GAP | UNKNOWN | UNKNOWN |

Plus **4 dynamically selected** XNSE ordinary equities from the catalog (not in the named set, not bank names): same pipeline, beta/ERP UNKNOWN.

Special handling preserved:

- HDFCBANK → `BANK_VALUATION_METHOD_REQUIRED`
- ETF listing → `UNSUPPORTED`

AST check: named tickers are **not** hardcoded in `dcf_tenor_policy.py` or `capm_components.py`.

---

## 11. Adversarial Tests

`packages/data_engine/tests/test_simple29.py` — **25 passed** (`not network`).

| ID | Case | Result |
|---|---|---|
| A | AI supplies `wacc=11%` | **REJECTED** / NON-AUTHORITATIVE; judge status ≠ VERIFIED |
| B | AI beta without provenance | **REJECTED**; `wacc_eligible=False` |
| C | AI/ERP without methodology/date | **REJECTED** (`methodology/date`) |
| D | Wrong-company beta | **REJECTED** (`IDENTITY_FAIL`) |
| E | Wrong MIC/listing beta | **REJECTED** (`IDENTITY_FAIL`) |
| F | Stale beta | **REVIEW_REQUIRED** / STALE; not a WACC input |
| G | Conflicting ERP 5.5% vs 7.0% | **REVIEW_REQUIRED**; not averaged; DSP WACC `None` |
| H | RBI T-bill unknown tenor | **VERIFIED_OBSERVATION**, **DCF_BINDING = POLICY_GAP** |
| I | 10-year G-sec vs required 91-day; labeled 10Y under GAP | **POLICY_MISMATCH** / **POLICY_GAP** (NON_BINDING); `wacc_input is None` |
| J | Risk-free in wrong currency | **REJECTED** |
| K | US ERP on Indian equity | **REJECTED** (qualifier + EvidenceJudge) |
| L | AI intrinsic value | ingest **REJECTED**; `AnalyseRequest(intrinsic_value=…)` **ValidationError** |
| M | Provider WACC ≠ DSP WACC | DSP **0.0975** authoritative; compare → **REVIEW_REQUIRED** |
| N | Missing beta | WACC **UNKNOWN** / incomplete; DCF **BLOCKED** |
| O | Missing ERP | WACC **UNKNOWN** / incomplete; DCF **BLOCKED** |

Replay:

| Case | Result |
|---|---|
| 1 Complete verified components | CoE **0.12**, WACC **0.0975**, engine `compute_wacc` |
| 2 AI WACC injection | AI rejected; DSP **0.0975** retained |
| 3 Missing beta | DCF_BLOCKED |
| 4 Missing ERP | DCF_BLOCKED |
| 5 Unresolved tenor | observation POLICY_GAP; WACC UNKNOWN; DCF_BLOCKED |
| 6 Live/retrieved complete evidence | **Not obtained.** Approved beta/ERP remain UNKNOWN. Fail-closed preserved. No synthetic live evidence. |

---

## 12. Regression

Command (markers `not network`):

SIMPLE-14N-E, 14N-F, 15, 16, 17, 18, 19, 19A, 20, 21, 22, 23, 24, 25, 26, 27, 28, **29**, 14N acquisition, 14ND, P1-10 (`test_p101_authenticated_valuation`), P1-11 (`test_p111_hard_release_gates`), plus existing DSP/DcfMethod/WACC tests (`packages/valuation/tests/test_dcf_intelligence.py`).

| | Count |
|---|---|
| passed | **334** |
| skipped | **5** (pre-existing live-network skips inside 21–25) |
| deselected | **8** (`not network`, including SIMPLE-28 live HTTPS) |
| failed | **0** |
| xfail | **0** |
| new failures | **0** |
| pre-existing failures | **0** |

SIMPLE-29 unit tests: **25 passed**.  
SIMPLE-28: 18 passed (`not network`). SIMPLE-27: 21 passed. SIMPLE-26: 16 passed. Unchanged.

Valuation `TestWacc::test_capm_and_wacc_deterministic` and `TestDcfEngine` **PASSED**. Canonical DCF/WACC formulas untouched.

---

## 13. Performance

Research measured separately from DSP calculation. Not optimized. MOCK NSDP (no live HTTP in this pass); valuation date 2026-09-12.

| Stage | Seconds (representative) |
|---|---|
| Tenor policy dict | 0.00019 |
| `evaluate_risk_free_binding` | 0.00007 |
| Risk-free retrieval (MOCK extract) | 0.016 HTTP=0; extraction ≈ 0.016; judge ≈ 0.00026 |
| Beta retrieval (live path, no series) | ≈ 0.0 (`UNKNOWN` / NOT_CONFIGURED) |
| ERP retrieval (live path, no series) | ≈ 0.0 |
| `qualify_capm_component` (candidate) | 0.00006 |
| EvidenceJudge (RBI MOCK) | 0.00011–0.00026 |
| DSP WACC (complete replay Case 1) | 0.00013 |
| DSP WACC (live incomplete via `analyse_listing`) | 0.00011 |
| `analyse_listing` complete (MOCK) | 0.0039 |

Live RBI HTTPS timing remains SIMPLE-28 (~0.84 s HTTP). SIMPLE-29 did not re-fetch production networks for beta/ERP because no approved series exists to fetch.

---

## 14. Production State

**NO PRODUCTION DEPLOYMENT.**

- Feature flags not enabled
- No new UI; frontend remains parked
- Production data not altered
- Commercial APIs not activated
- Source authorization not weakened
- OpenAI / Gemini remain **NOT_CONFIGURED**
- NSE MCP remains **COMMERCIAL_USE_PENDING**
- FMP / Kite / paid BSE / FBIL / Yahoo VERIFY path **not added**
- MOCK `analyse_listing` still skips RBI HTTP unless tests supply document text or `retrieve_fn`

---

## 15. Known Limitations

1. **POLICY_GAP is explicit and still unbound.** A genuine RBI T-bill exists; DCF cannot legally consume it until a preferred tenor is established by valuation methodology (not by scrape convenience) **and** the source labels that tenor.
2. NSDP still **does not label T-bill maturity**.
3. A labeled 10-year G-sec would also remain **POLICY_GAP** today. That is intentional.
4. **Beta** cannot be retrieved as a verified WACC ingredient on approved sources. Yahoo is Tier 2 and cannot VERIFY. No price-series beta engine was added (that would be a new calculation authority).
5. **ERP** cannot be retrieved as a verified WACC ingredient. US ERP, GDP, inflation, and AI opinion are rejected.
6. Therefore **live WACC remains incomplete** and **DCF_BLOCKED**. Replay mathematics are proven; live auto-completion is not.
7. `research_live_capm_components` classifies candidates; it does not invent values. AI availability is not an architectural dependency.
8. Terminal growth, bank DCF redesign, share-count, capex, frontend, FMP, Kite, NSE MCP — **out of scope** (unchanged).
9. SIMPLE-29 is **not CLOSED** under §22: tenor policy exists but is GAP; live β/ERP remain legitimately unavailable; DSP/DCF fail closed. That is the required honest verdict.

---

## 16. Next Forensic

Candidate **SIMPLE-30** (only if separately scoped):

1. Establish a **defensible preferred DCF tenor** from valuation methodology / RS-004 elaboration — still without inventing a convention to make DCF run. If still unjustified, remain POLICY_GAP.
2. Bind an RBI/approved government yield **only** when tenor is labeled, policy matches, currency/date/source/judge pass.
3. Independently: an **approved identity-bound beta** series and an **India-market ERP** series with methodology and date — still through EvidenceJudge, still into existing `compute_wacc`. Do not use Yahoo as VERIFY. Do not activate commercial NSE MCP / FMP / Kite. Do not let AI write WACC or intrinsic value.

Do not solve terminal growth, bank valuation, or frontend in that forensic unless separately scoped.

Permanent rule:

> **Research retrieves evidence. EvidenceJudge verifies evidence. DSP calculates WACC. DCF consumes DSP-calculated WACC.**

---

### Files changed (SIMPLE-29)

| File | Change |
|---|---|
| `docs/valuation/DCF_RISK_FREE_TENOR_POLICY.md` | **Added.** Explicit POLICY_GAP tenor contract. |
| `packages/data_engine/src/data_engine/official_research/dcf_tenor_policy.py` | **Added.** Machine-readable policy + `evaluate_risk_free_binding`. |
| `packages/data_engine/src/data_engine/official_research/capm_components.py` | **Added.** Beta/ERP qualifier + live research stub (no Yahoo scrape). |
| `packages/data_engine/src/data_engine/official_research/rbi_risk_free.py` | Binding delegated to tenor policy; POLICY_MISMATCH mapped for SIMPLE-28 compatibility. |
| `packages/data_engine/src/data_engine/official_research/judge.py` | Forbidden beta/ERP semantic kinds. |
| `packages/data_engine/src/data_engine/official_research/end_to_end.py` | `research_live_capm_components`; timings `beta_retrieval` / `erp_retrieval`. |
| `packages/data_engine/src/data_engine/official_research/component_research.py` | Optional methodology/market/beta_kind on candidates; live_macro status unchanged (UNKNOWN). |
| `packages/data_engine/src/data_engine/official_research/__init__.py` | Exports. |
| `packages/data_engine/tests/test_simple29.py` | **Added.** Tenor, A–O, replay, universality, banks/ETFs, injection. |
| `docs/releases/SIMPLE_29_DCF_TENOR_BETA_ERP_FORENSIC.md` | This report. |

Frontend: none. `DcfMethod`: none. `compute_wacc`: none. No second WACC engine.
