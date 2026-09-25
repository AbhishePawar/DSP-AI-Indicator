# SIMPLE-27 — Live Data Acquisition & Deterministic WACC/Growth Forensic

Canonical report for this forensic:

**`docs/releases/SIMPLE_27_LIVE_DCF_COMPONENT_RESEARCH_FORENSIC.md`**

This file is the earlier session write-up. Status remains **PASS WITH LIMITATIONS**. Do not treat this copy as the required SIMPLE-27 close-out document.

---

## 1. STATUS

**PASS WITH LIMITATIONS**

Not CLOSED.

SIMPLE-25 and SIMPLE-26 were **not** redone.

The platform now proves:

> **AI retrieves/researches component evidence. DSP calculates WACC and cost of capital.**

It still does **not** accept:

```text
AI → "WACC = 11%"
AI → "growth = 10%"
AI → DCF
```

Live production `analyse()` remains **DCF_BLOCKED** unless researched components (or an accepted replay pack) exist. Risk-free rate, beta, and ERP are **not** auto-fetched from RBI/Yahoo in production: no new provider was added, NSE MCP stays `COMMERCIAL_USE_PENDING`, and AI stays `NOT_CONFIGURED`.

That is the remaining limitation, not a hidden default.

**NO PRODUCTION DEPLOYMENT.** Frontend PARKED.

---

## 2. BASELINE

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA | `d11c82777caa5bfa70f266848475508bfd1c5a11` |
| SIMPLE-26 | `docs/releases/SIMPLE_26_DCF_ASSUMPTION_RESEARCH_VALIDATION_FORENSIC.md` — PASS WITH LIMITATIONS |
| SIMPLE-26 gap | Candidate/validator path existed, but WACC was only `rf + β×ERP` as an equity required-return. No reuse of `compute_wacc`. AI could still propose a WACC number if it attached evidence_ids. Live components were not ingested from `VerifiedDataset.evidence`. |
| Canonical DCF | Unchanged `DcfMethod` / `dsp_calculation._dcf_core` |
| Existing WACC engine | `valuation.dcf_intelligence.wacc.compute_wacc` — **not previously invoked** by official `analyse()` |

---

## 3. EXISTING IMPLEMENTATION (FORENSIC)

Already existed (reused, not duplicated):

| Capability | Where |
|---|---|
| Canonical DCF | `valuation.methods.dcf.DcfMethod` + `dsp_calculation` |
| CAPM + levered WACC | `compute_wacc` (`re = rf+β×ERP`, `rd_at = rd×(1−t)`, `WACC = we×re + wd×rd_at`) |
| Historical CAGRs | SIMPLE-26 `assumption_research._historical_metrics` |
| AssumptionValidator | bounds, WACC > g, conflict ≠ average |
| EvidenceJudge | primary URL may VERIFY; llm/Yahoo cannot |
| Live financials | NSE filings / XBRL (revenue, CFO, capex, debt, equity, …) |
| Derived market cap / FCF | `derived_fields.py` |

Did **not** exist before SIMPLE-27:

- DSP calling `compute_wacc` on official research path
- Connector contract that rejects AI WACC/growth payloads
- Judge refusal to VERIFY DCF output fields (`wacc`, `discount_rate`, growth, IV, …)
- Ingest of verified RBI-class component evidence into WACC calculation
- XBRL `finance_costs` extraction

---

## 4. REQUIRED DATA INVENTORY

Canonical `DcfMethod` still requires only:

| DCF input | Required? | Class entering DcfMethod |
|---|---|---|
| FCF₀ | Yes (derived from verified CFO, capex) | DERIVED VALUE |
| forecast growth `fcf_growth_rate` | Yes | ASSUMPTION |
| terminal growth | Yes | ASSUMPTION |
| WACC / discount_rate | Yes | ASSUMPTION (may be DSP-derived) |
| projection_years | Optional (horizon default 5 after rates accepted) | ASSUMPTION |
| shares, price | For IV/share and MOS | VERIFIED FACT |
| net debt | Not subtracted again (equity FCF) | DERIVED, unused in this DCF |

WACC **components** (not all required by DcfMethod; required to *calculate* WACC):

| Component | Required to calculate WACC? |
|---|---|
| risk-free, beta, ERP | Yes for cost of equity |
| equity market value, debt | Yes for levered weights |
| pre-tax cost of debt, tax rate | Yes if debt > 0 |
| finance_costs | Alternate way to derive pre-tax rd = finance_costs / debt |

If debt is 0 or levered inputs are missing, DSP may use **cost of equity** as the required-return candidate and record that levered WACC is incomplete. It does not invent rd or a statutory tax rate.

---

## 5. CLASSIFY EVERY INPUT

| Input | Class |
|---|---|
| Revenue, earnings, CFO, capex, cash, debt, shares, price, finance_costs | OBSERVED FACT (when EvidenceJudge = VERIFIED) |
| Historical CAGRs, FCF, market cap, net debt | DERIVED VALUE |
| Risk-free rate from RBI (primary URL) | OBSERVED FACT (verified evidence) used as CAPM input |
| Beta from RBI/regulator URL | OBSERVED FACT if verified; Yahoo = cannot VERIFY |
| ERP | OBSERVED if an approved primary source states it; otherwise ASSUMPTION / UNKNOWN |
| Cost of equity | **DERIVED** (`compute_wacc`) |
| After-tax cost of debt | **DERIVED** |
| Capital weights | **DERIVED** (`E/(E+D)`, `D/(E+D)`) |
| WACC | **DERIVED**, then proposed as DCF **ASSUMPTION** (`discount_rate`). Never labeled an observed quote. |
| Forecast / terminal growth | ASSUMPTION (never last-year, GDP, or AI number) |

---

## 6. LIVE DATA ACQUISITION

Approved hierarchy unchanged. **No new provider. No FMP. No Kite. No paid activation. NSE MCP `COMMERCIAL_USE_PENDING`.**

| Source | Use in SIMPLE-27 |
|---|---|
| NSE/BSE filings, XBRL | Live debt, equity, FCF history, optional finance_costs |
| RBI host (`rbi.org.in`) | Already Tier 1A in `PRIMARY_HOST_SUFFIXES`. Evidence **can** VERIFY. Production does **not** scrape a new RBI feed. |
| Screener | Cross-check only (unchanged) |
| Yahoo / IBEF | Discovery only; **cannot VERIFY** (proven) |
| AI agents | `NOT_CONFIGURED`; FIND/VERIFY still do not write truth |

---

## 7. AI CONNECTOR CONTRACT

`component_research.ingest_researched_components` requires:

`field, value, source, source_type, source_url, retrieved_at, as_of, isin, mic, unit, currency, period, evidence_locator`

Rejected if `field` is a DCF **result**:

`wacc`, `discount_rate`, `fcf_growth_rate`, `terminal_growth_rate`, `cost_of_equity`, IV, MOS, …

`research_components_from_agent`: if the agent is unavailable → `NOT_CONFIGURED`, never fabricated.

---

## 8. PRIMARY SOURCE PRIORITY

```text
Tier 1A  →  Tier 1B  →  Tier 1C  →  Tier 2  →  AI discovery
```

**AI agreement does not override primary evidence.** (Mission text was truncated here; this is the enforced rule.)

Yahoo beta is not VERIFIED. AI WACC is rejected even with a primary URL. DSP WACC from verified components wins.

---

## 9. DSP WACC CALCULATION

Official path calls existing `compute_wacc`:

```text
re = rf + β × ERP
rd_at = rd × (1 − t)
we, wd = E/(E+D), D/(E+D)
WACC = we×re + wd×rd_at
```

Engine id: `valuation.dcf_intelligence.wacc.compute_wacc`.

Parity test: levered example WACC = **0.0975** (rf 7%, β 1, ERP 5%, E=D, rd 10%, t 25%).

---

## 10. GROWTH

Historical CAGRs remain DERIVED (SIMPLE-26). They may propose forecast FCF growth with evidence; they **never** become terminal growth.

AI terminal/forecast growth payloads are `AI_CALCULATED_OUTPUT_REJECTED`.

No GDP default. No last-year automatic terminal.

---

## 11. VALIDATION & CONFLICTS

AssumptionValidator unchanged. Conflicts still not averaged.

New: AI-proposed WACC/growth is screened out **before** DSP calculation so a fake 11% cannot skip `compute_wacc`.

---

## 12. JUDGE BOUNDARY

`EvidenceJudge.verify` now treats DCF outputs as **UNAVAILABLE** (same family as market_cap/FCF). An AI or filing row labeled `wacc=11%` cannot become VERIFIED fact.

Component fields (rf, beta, ERP) may VERIFY only from primary URLs.

---

## 13. IDENTITY / CURRENCY / FRESHNESS / PERIOD

Unchanged from SIMPLE-26: ISIN+MIC, currency match, stale 365-day rule, no mixed-year FCF pairing.

---

## 14. PRODUCTION ANALYSE INTEGRATION

```text
analyse()
  → VerifiedDataset (NSE financials live as before)
  → research_dcf_assumptions
       ├── ingest verified component evidence
       ├── calculate_dsp_wacc (compute_wacc)
       └── AssumptionValidator
  → DcfMethod only if ACCEPTED pack includes WACC + growth + terminal
```

Without rf/β/ERP evidence: `WACC:UNKNOWN`, `DCF_BLOCKED`. Honest.

---

## 15. DCF FORMULA INTEGRITY

FCF, TV, discounting, equity bridge, shares, IV/share, MOS **unchanged**.

---

## 16. UNIVERSAL / ADVERSARIAL TESTS

| Case | Result |
|---|---|
| TCS, INFY, RELIANCE, WIPRO, 20MICRONS, 21STCENMGM without components | DCF_BLOCKED |
| AI returns WACC / growth | REJECTED |
| Agent unavailable | NOT_CONFIGURED |
| Yahoo beta | not VERIFIED |
| RBI rf URL | VERIFIED |
| Verified rf/β/ERP + growth pack | DSP WACC 12% (all-equity proxy); AI 11% rejected; DCF CALCULATED on fixture |
| Levered components | DSP WACC 9.75% |
| XBRL FinanceCosts | fact extracted; not a WACC |
| No ticker branches | AST-checked |

---

## 17. BANKS / ETF

Unchanged: `BANK_VALUATION_METHOD_REQUIRED`; ETF unsupported.

---

## 18. REPRODUCIBILITY / PERFORMANCE

Same dataset + same accepted pack → same DCF (SIMPLE-26 tests still green). WACC path uses `compute_wacc` (float rounded to 10 dp). Not optimized.

---

## 19. SECURITY

| Control | Result |
|---|---|
| AI cannot write WACC/growth | ingest + screen + judge |
| Client HTTP cannot inject assumptions | unchanged `AnalyseRequest` |
| Yahoo/FMP cannot verify | source policy |
| No new secrets | no new providers |

---

## 20. REGRESSION

| Suite | Passed | Failed | Skipped | Deselected |
|---|---|---|---|---|
| SIMPLE-14N-E … SIMPLE-27 (`not network`) | **198** | **0** | **5** | **7** |
| SIMPLE-27 | **11** | **0** | **0** | 0 |
| SIMPLE-26 | **16** | **0** | — | — |
| P1-10 `test_p101_authenticated_valuation` | **13** | **0** | — | — |
| P1-11 gates | **12** | **0** | — | — |

No new failures. Skipped = prior live network tests.

---

## 21. FILES CHANGED

| File | Change |
|---|---|
| `official_research/dsp_wacc.py` | **Added** — wraps `compute_wacc` |
| `official_research/component_research.py` | **Added** — AI component ingest |
| `official_research/assumption_research.py` | DSP WACC from verified components; reject AI DCF outputs |
| `official_research/judge.py` | DCF outputs cannot VERIFY |
| `official_research/assumption_contract.py` | `finance_costs` fact; derived cost of equity/weights; `pre_tax_cost_of_debt` |
| `official_research/assumption_validator.py` | rd bounds |
| `official_research/xbrl.py` / `extraction.py` / `research_plan.py` | finance_costs |
| `official_research/source_policy.py` | macro authority chain |
| `official_research/end_to_end.py` | pipeline comment |
| `tests/test_simple27.py` | **Added** |
| this report | **Added** |

---

## 22. PRODUCTION IMPACT

None deployed. Flags unchanged. OpenAI/Gemini off. NSE MCP pending. Frontend parked.

---

## 23. LIMITATIONS

1. Production does not scrape live RBI G-sec / ERP / beta series (no new connector).
2. AI research remains `NOT_CONFIGURED`.
3. Levered WACC still needs evidenced rd and tax; otherwise cost-of-equity proxy is used and the gap is recorded.
4. Terminal growth still has no live guidance extractor.
5. `projection_years = 5` horizon default remains after rates are accepted.
6. Book vs market debt: weights use verified debt + derived market cap when available.

---

## 24. DECISION

**PASS WITH LIMITATIONS**

Architecture is correct and tested:

```text
external component evidence → EvidenceJudge → DSP compute_wacc → validator → DcfMethod
```

Never:

```text
AI guess → WACC → DCF
```

CLOSED is withheld because live macro acquisition is still unavailable without adding/activating a provider.

---

## 25. NEXT FORENSIC

**SIMPLE-28 candidate:** retrieve **risk-free observations** from already-whitelisted `rbi.org.in` using existing HTTP transport (not a new vendor), still through EvidenceJudge, still DSP-calculated WACC. Do not activate NSE MCP, OpenAI, FMP, or Kite. Do not treat GDP as terminal growth. Do not deploy.

---

## Implementation return (workspace gate)

- **Architecture Impact:** Official research now *applies* the existing `compute_wacc` engine to judged component evidence. No second DCF methodology. Thin client unchanged.
- **Components Added:** `dsp_wacc.py`, `component_research.py`, finance_costs extraction, judge DCF-output refusal.
- **Pages Updated:** none.
- **Feature Flags Used:** none.
- **Accessibility / Responsive Validation:** N/A.
- **Performance Validation:** not optimized; fixture DCF path unchanged.
- **Known Limitations:** see §23.
- **Future Enhancements:** see §25.
- **Regression Summary:** 198 passed / 5 skipped / 7 deselected (14N-E…27); P1-10 13 + P1-11 12 passed; SIMPLE-27 11/11. No new failures.
