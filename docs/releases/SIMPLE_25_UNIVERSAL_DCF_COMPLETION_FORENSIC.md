# SIMPLE-25 — Universal DCF Completion & Assumption Validation Forensic

## STATUS

**PASS WITH LIMITATIONS**

Not CLOSED.

SIMPLE-24 proved universal identity, NSE EOD, primary research, filings, TOTAL_OUTSTANDING currentness, and market cap on verified shares. DCF stayed **BLOCKED** because gates were unchanged.

SIMPLE-25 does **not** redo SIMPLE-24. It identifies the exact remaining DCF blockers and builds the **universal input-completion** mechanism required to run a defensible DCF when verified facts and validated assumptions exist.

```text
VERIFIED FACT
      ↓
DERIVED VALUE  (FCF = CFO − |Capex|, market cap, net debt)
      ↓
VALIDATED ASSUMPTION  (PROPOSED → AssumptionValidator → ACCEPTED | REJECTED | REVIEW_REQUIRED)
      ↓
DCF  (canonical DcfMethod / dsp_calculation; no second engine)
```

or:

```text
MISSING FACT → RESEARCH → VERIFIED
MISSING FACT → NO RELIABLE EVIDENCE → DCF_BLOCKED
FORWARD-LOOKING INPUT → AI PROPOSAL → VALIDATOR → ACCEPT / REJECT
```

Never: `AI GUESS → DCF`.

Live automatic path (16 prior names + 5 newly catalog-selected NSE equities, no hand-supplied URLs, capex, WACC, or growth):

| Outcome | Count |
|---|---|
| Identity VERIFIED | 21/21 |
| Price VERIFIED (EOD) | 21/21 |
| Revenue VERIFIED | 18/21 |
| CFO VERIFIED | 18/21 |
| Capex VERIFIED | 18/21 |
| Production `analyse()` DCF CALCULATED | **0/21** (no hidden WACC/growth) |
| Replay DCF RUN with universal fixture assumption pack | **12/21** |
| Replay DCF BLOCKED (bank / FCF≤0 / missing facts) | **9/21** |

Both RUN and BLOCKED are correct forensic outcomes. The objective is not “make every company produce a DCF.”

**NO PRODUCTION DEPLOYMENT.** Frontend remains PARKED. NSE MCP remains `COMMERCIAL_USE_PENDING`. OpenAI was not required and was not used to write facts or IV.

---

## BASELINE

Recorded before SIMPLE-25 edits. SIMPLE-24 = **PASS WITH LIMITATIONS** was **not** redone.

| Item | Value |
|---|---|
| Branch | `fix/asi003-dsp-platform-boundaries` |
| HEAD SHA | `9030287e1808a471a3d8a48c238085093616bad3` |
| HEAD subject | SIMPLE-15-22: fail-closed official research through live universal NSE acquisition |
| SIMPLE-24 | `docs/releases/SIMPLE_24_UNIVERSAL_TOTAL_OUTSTANDING_SHARES_FORENSIC.md` — PASS WITH LIMITATIONS |
| SIMPLE-24 live | Identity 16/16; price 16/16; TOTAL_OUTSTANDING VERIFIED 9/16; DCF **0/16 CALCULATED** |
| Canonical DCF | `packages/valuation/src/valuation/methods/dcf.py` (`DcfMethod`) applied by `dsp_calculation.run_dsp_calculations` to SIMPLE-17 FCF |
| Pre-SIMPLE-25 gap | Capex missing: XBRL map had only `capitalexpenditure` / `capex`. Indian IND-AS cash-flow uses `PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities`. `extract_labeled_field(..., "capex")` correctly refuses PPE (SIMPLE-14N). Live `analyse()` does not inject WACC/growth. |
| Offline regression (14N-E…24, `not network`) | 161 passed, 4 skipped, 6 deselected (this session, before SIMPLE-25 edits) |
| Production revision | **Not queried. Not changed.** |
| Production image | **Unchanged / not inspected.** |
| Production environment | **Not modified.** |
| Production feature flags | RESEARCH_MODE unchanged; RECOMMENDATION_MODE/SEBI locked; production OpenAI off; NSE MCP pending |

Frontend parked items from the mission were **not** implemented.

---

## EXACT DCF BLOCKERS

Capex was **not** the only blocker. Two independent classes:

1. **Historical fact — capex extraction miss.** Live INFY financial XBRL already contained:
   - CFO: `CashFlowsFromUsedInOperatingActivities` = 252,100,000,000 (same `FourD` period)
   - PPE purchases: `PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities` = 22,010,000,000
   - Total investing: `CashFlowsFromUsedInInvestingActivities` = −50,090,000,000 — **not capex**
   - Subsidiary acquisition: `CashFlowsUsedInObtainingControlOfSubsidiariesOrOtherBusinessesClassifiedAsInvestingActivities` = 1,010,000,000 — **not capex**
   DSP only mapped `capitalexpenditure` / `capex`, so capex stayed UNAVAILABLE and FCF could not be derived.

2. **Forward-looking assumption — not a fact.** `default_unverified_assumptions()` are UNAVAILABLE. Production `analyse()` does **not** pass WACC, FCF growth, or terminal growth. `run_dsp_calculations` requires ACCEPTED `discount_rate`/`wacc`, `fcf_growth_rate`, `terminal_growth_rate`. This is fail-closed, not a bug.

Additional live blockers after capex wiring (replay with a **universal** test assumption pack, identical for every name, not production):

| Blocker class | Meaning | Resolve by |
|---|---|---|
| `bank_equity: ordinary DCF not applicable` | Existing bank handling | Bank-specific method (not ordinary DCF) |
| `CFO` / `CAPEX` / `FCF:BLOCKED` | Historical fact missing | Research (XBRL / audited CF) |
| `FCF inputs invalid` | Derived FCF₀ ≤ 0 (`CFO − \|Capex\|`) | Not invented; DCF stays blocked |
| `SHARES:REFRESH_REQUIRED` | Equity DCF may still RUN; IV/share and MOS stay blocked | CA research (SIMPLE-24) |
| `SHARES:UNAVAILABLE` | No verified outstanding | Research |
| Production `ASSUMPTIONS` | No ACCEPTED pack in `analyse()` | User / validated research assumptions — **never hidden defaults** |

Live per-security snapshot (replay DCF; production DCF remained not CALCULATED for all 21):

| Security | Price | Shares | Revenue | NI | CFO | Capex | Cash | Debt | Assumptions (replay pack) | DCF | Blocker |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TCS | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | ACCEPTED | **RUN** | NONE |
| INFY | VERIFIED | REFRESH_REQUIRED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | ACCEPTED | **RUN** | SHARES:REFRESH_REQUIRED |
| RELIANCE | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | ACCEPTED | **RUN** | NONE |
| HDFCBANK | VERIFIED | REFRESH_REQUIRED | UNAVAILABLE | UNKNOWN | VERIFIED | UNAVAILABLE | UNKNOWN | UNAVAILABLE | ACCEPTED pack unused | **BLOCKED** | bank_equity: ordinary DCF not applicable |
| WIPRO | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | ACCEPTED | **RUN** | NONE |
| 20MICRONS | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | ACCEPTED | **RUN** | NONE |
| AADHARHFC | VERIFIED | REFRESH_REQUIRED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | ACCEPTED | **BLOCKED** | SHARES:REFRESH_REQUIRED; FCF inputs invalid |
| 3IINFOLTD | VERIFIED | REFRESH_REQUIRED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | ACCEPTED | **RUN** | SHARES:REFRESH_REQUIRED |
| A2ZINFRA | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | ACCEPTED | **RUN** | NONE |
| ABFRL | VERIFIED | REFRESH_REQUIRED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | ACCEPTED | **RUN** | SHARES:REFRESH_REQUIRED |
| 21STCENMGM | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | ACCEPTED | **BLOCKED** | FCF inputs invalid |
| APOORVA | VERIFIED | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | ACCEPTED | **BLOCKED** | SHARES:UNAVAILABLE; CFO; CAPEX; FCF |
| ADROITINFO | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | ACCEPTED | **BLOCKED** | FCF inputs invalid |
| ABINFRA | VERIFIED | VERIFIED | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | ACCEPTED | **BLOCKED** | CFO; CAPEX; FCF |
| ADFFOODS | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | ACCEPTED | **RUN** | NONE |
| 360ONE | VERIFIED | REFRESH_REQUIRED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | ACCEPTED | **BLOCKED** | SHARES:REFRESH_REQUIRED; FCF inputs invalid |
| 3BBLACKBIO | VERIFIED | UNAVAILABLE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | ACCEPTED | **BLOCKED** | SHARES:UNAVAILABLE; CFO; CAPEX; FCF |
| 3MINDIA | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | ACCEPTED | **RUN** | NONE |
| 3PLAND | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | ACCEPTED | **RUN** | NONE |
| 5PAISA | VERIFIED | REFRESH_REQUIRED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | ACCEPTED | **BLOCKED** | SHARES:REFRESH_REQUIRED; FCF inputs invalid |
| 63MOONS | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | UNKNOWN | ACCEPTED | **RUN** | NONE |

Statuses use the existing vocabulary: VERIFIED / DERIVED (FCF, DCF) / ASSUMPTION / UNKNOWN / REFRESH_REQUIRED / BLOCKED / RUN. Debt UNKNOWN did **not** block this DCF (existing equity-FCF contract; net debt is not subtracted again).

---

## DCF CONTRACT

Inspected canonical `DcfMethod` (`packages/valuation/src/valuation/methods/dcf.py`) and DSP application (`dsp_calculation.py`).

**No second DCF engine. No formula rewrite.**

Preserved:

| Step | Contract |
|---|---|
| FCF₀ | SIMPLE-17: `FCF = CFO − \|Capex\|` (`derived_fields._fcf`). Source sign is kept; abs is applied only in this formula. |
| Forecast | `FCFₜ = FCF₀(1+g)ᵗ` |
| Terminal | Gordon `TV = FCFₙ(1+gₜ)/(r−gₜ)` |
| Discount | `IV = Σ FCFₜ/(1+r)ᵗ + TV/(1+r)ⁿ` |
| Bridge | DcfMethod FCF is after-interest; present value is **equity value**. Net debt is **not** subtracted again. |
| MOS | `(IV/share − Price) / IV/share` — string and arithmetic unchanged |
| Gates | CFO VERIFIED, capex VERIFIED, FCF CALCULATED, ACCEPTED WACC/growth/terminal, WACC > terminal, FCF₀ > 0 |

DCF Intelligence (`FCFF = EBIT(1−t)+D&A−CapEx−ΔNWC`) remains a **separate** unused engine. Mixing formulas is forbidden.

---

## CAPEX FORENSIC

**Why capex was unavailable:** the XBRL concept whitelist did not include the IND-AS investing PPE purchase concept that NSE financial instances actually publish. Document extraction only accepted the words `capex` / `capital expenditure` (SIMPLE-14N). Cash-flow “purchase of PPE” was therefore dropped even when present.

Searched acquisition/extraction paths for:

- capital expenditure / capital expenditures / capex
- purchase of property, plant and equipment / PPE / fixed assets / tangible assets
- additions to PPE
- payments to acquire PPE
- investing cash flows
- intangible purchases / acquisitions

**Not treated as capex:** total investing cash flow, subsidiary acquisitions, goodwill, investment purchases, working-capital movements.

**Sources (priority unchanged):**

1. NSE/XBRL cash-flow concepts (now includes PPE investing purchases)
2. NSE financial filing / official audited statements / cash-flow statement text (classified extractor)
3. Approved cross-check
4. Screener: cross-check only
5. AI: discovery/extraction assistance only; cannot write capex

JSON NSE result particulars remain P&L-oriented. Those rows still do **not** treat unlabeled PPE as capex. DCF capex comes from XBRL cash-flow taxonomy or classified CF extraction.

---

## CAPEX SEMANTICS

`classify_capex_semantic()`:

| Class | DCF capex? |
|---|---|
| CAPITAL_EXPENDITURE | Yes |
| PPE_PURCHASE | Yes |
| INTANGIBLE_PURCHASE | No (not auto-added) |
| LEASE_CAPEX | No |
| ACQUISITION | No |
| INVESTMENT | No |
| WORKING_CAPITAL | No |
| OTHER_INVESTING (total investing CF) | No |
| UNKNOWN | No |

`extract_labeled_field(..., "capex")` **still** returns `None` for “purchase of property, plant and equipment” (SIMPLE-14N preserved). `extract_classified_capex()` is a **separate** cash-flow-statement path that may accept PPE purchases after classification.

**Sign convention:** source sign is preserved (`Purchase of PPE = −₹X` stays negative). Deterministic FCF continues to use `CFO − |Capex|`. The formula was not changed to accommodate presentation.

---

## CAPEX PERIOD

CFO and capex must share a compatible period (`derived_fields._same_period` / `periods_comparable`). FY26 CFO with FY25 capex is `CALCULATION_BLOCKED`. Live XBRL picks both facts from the same annual context. Quarters are refused.

---

## CAPEX CONSOLIDATION

XBRL prefers **consolidated**. Unlabeled consolidation is skipped (`{field} XBRL consolidation unlabeled`). Standalone pages never feed consolidated fields in statement reconstruction. Mixed unlabeled bases stay UNKNOWN. No silent combine of inconsistent bases.

---

## FINANCIAL COMPLETENESS

Canonical ordinary-equity DCF uses **CFO + capex** (for FCF), **price + TOTAL_OUTSTANDING** (for IV/share and MOS), and **ACCEPTED assumptions**. Revenue, NI, cash, debt, equity, assets, liabilities are acquired when present; they are **not** required to run this DCF.

Live extractability (this session):

| Field | Typical live status | Used by this DCF? |
|---|---|---|
| Revenue | VERIFIED for 18/21 | No (research completeness) |
| Net income | VERIFIED for 17/21 | No for ordinary DCF |
| CFO | VERIFIED for 18/21 | **Yes** |
| Capex | VERIFIED for 18/21 | **Yes** |
| Cash | VERIFIED for 18/21 | Net debt only |
| Debt | Often UNKNOWN | Net debt only; **not** required for equity DCF |
| Equity / assets / liabilities | Acquired when labeled | Bank path; not ordinary DCF |

Missing debt is **not** replaced with 0.

---

## ASSUMPTION FORENSIC

| Assumption | Production `analyse()` | Test replay pack | Hidden default? |
|---|---|---|---|
| WACC / discount_rate | UNAVAILABLE (`default_unverified_assumptions`) | ACCEPTED 0.10 (universal fixture) | **No** |
| FCF growth | UNAVAILABLE | ACCEPTED 0.08 | **No** |
| Terminal growth | UNAVAILABLE | ACCEPTED 0.03 | **No** |
| Projection years | Engine uses 5 only if an ACCEPTED years row is absent **after** WACC/growth/terminal are ACCEPTED | ACCEPTED 5 | Years default is documented in `_run_dcf`; WACC/growth are never defaulted |
| User-provided | Supported via `CanonicalAssumption` | Not used live | — |
| AI-proposed | Validator path exists; AI not configured | Not used live | — |

No company-specific WACC or growth. The fixture pack is **one pack for all names**, test-only, sources `primary_research` / `historical_company_performance` / `macro_data` with evidence ids. It is **not** a production default.

---

## ASSUMPTION MODEL

Existing contract reused (`assumption_contract.py` + `assumption_validator.py`):

```text
PROPOSED
    ↓
VALIDATION
    ↓
ACCEPTED  or  REJECTED  or  REVIEW_REQUIRED  or  USER_REQUIRED
```

Never `AI → DCF`. `ignore_ai_valuation()` discards AI IV payloads. Derived fields (FCF, IV, MOS) cannot be assumptions.

---

## ASSUMPTION VALIDATOR

Reused `AssumptionValidator`. SIMPLE-25 added pack-level **conflict detection**: same scenario+field with different numeric values → **REVIEW_REQUIRED** for those rows. Values are **not averaged** (8% vs 18% growth stays 8% and 18%, both REVIEW_REQUIRED).

Validates (already present, unchanged bounds — generic, not company-specific):

- WACC > 0 (`open_low` from 0)
- WACC > terminal growth
- Terminal growth in `[0, 0.08]`
- FCF/revenue growth in `[-0.5, 0.5]`
- Projection years integer 1–30
- Numeric type, unit, scenario, period compatibility
- No NaN / infinity
- Facts and derived values rejected as assumptions
- Circular sources (`intrinsic_value`, DCF outputs) rejected

Accepted assumptions retain source, evidence ids, reason, date, scenario, validator result.

Evidence kinds remain distinguishable: historical, management guidance, industry, analyst/research, AI proposal, user. An assumption is never labeled a fact.

Scenarios BEAR / BASE / BULL already exist on `CanonicalAssumption`. BASE is required for DCF. Extra scenarios are not invented for presentation.

---

## AI STATUS

OpenAI may remain **NOT_CONFIGURED**. SIMPLE-25 offline and live paths do not require it.

Historical facts and deterministic DCF work without AI. AI is an optional later enhancement for **proposing** forward-looking assumptions, not for writing IV.

NSE MCP remains `COMMERCIAL_USE_PENDING`.

---

## AI BOUNDARY

AI may propose: revenue growth, FCF growth, operating margin, WACC, terminal growth, other fields already in `ASSUMPTION_BOUNDS`.

Each proposal must carry: field, value, unit, period, scenario, reason, evidence, source, confidence.

AI **cannot**:

- write capex, CFO, shares, price, or other facts (`refuse_ai_fact` / EvidenceJudge)
- write authoritative IV (`ignore_ai_valuation`)
- override primary evidence (primary wins; `AI_CLAIM_REJECTED`)
- bypass the validator into `run_dsp_calculations`

---

## DCF INPUT GATES

Before DCF RUN (`_run_dcf` + `describe_dcf_blockers` + existing `dsp_gate`):

- capability is ordinary `equity` (not `bank_equity` / unsupported)
- price > 0 when MOS/IV-share is required (verified EOD)
- shares > 0 TOTAL_OUTSTANDING when IV/share required
- CFO VERIFIED, capex VERIFIED
- FCF derivable, same period, FCF₀ > 0
- WACC, growth, terminal ACCEPTED, numeric, finite
- WACC > terminal growth
- currency consistent
- no NaN / infinity

Any failure → `DCF_BLOCKED` (status BLOCKED / CALCULATION_BLOCKED). **No zero substitution** for missing capex, debt, cash, or growth.

Capex was moved from equity **nice-to-have** to **required** on the research plan so the loop seeks it. Gates were **not** weakened.

---

## DCF CALCULATION

Reconciliation (deterministic Decimal, precision 28):

```text
FCF₀ = CFO − |Capex|
    ↓ discount factors (1+r)ᵗ
    ↓ PV of forecast FCF
    ↓ TV = FCFₙ(1+gₜ)/(r−gₜ)
    ↓ PV(TV)
    ↓ equity value  (= DCF IV; net debt not subtracted again)
    ↓ / verified TOTAL_OUTSTANDING
    ↓ IV/share
    ↓ MOS = (IV/share − Price) / IV/share
```

---

## DCF SANITY CHECKS

Existing `_dcf_core` fail-closed (no silent clamp):

- WACC ≤ 0 → blocked
- terminal ≥ WACC → blocked
- FCF₀ ≤ 0 → blocked (`FCF inputs invalid`)
- years not in 1–30 → blocked
- NaN / infinity → blocked
- currency mismatch → CALCULATION_BLOCKED
- period mismatch on FCF inputs → CALCULATION_BLOCKED
- zero IV/share → MOS blocked
- negative/zero shares cannot be valuation shares (SIMPLE-24 semantic)

---

## TERMINAL VALUE

`terminal < WACC` is mandatory. Terminal value must be finite. Generic bound: terminal growth ∈ `[0, 0.08]` (existing validator; not company-specific). No extra issuer thresholds.

---

## NET DEBT

`Net Debt = Debt − Cash` (existing `derived_fields._net_debt`). Missing debt or cash → blocked; **zero is not substituted**. This DSP DCF does **not** require net debt for equity IV (after-interest FCF). Preserve existing semantics.

---

## MARKET CAP

Unchanged: **Verified EOD × Verified TOTAL_OUTSTANDING**. Only `TOTAL_OUTSTANDING` may be used. REFRESH_REQUIRED / UNAVAILABLE shares → market cap blocked. Equity DCF RUN with REFRESH_REQUIRED shares does **not** mint a verified market cap or IV/share.

---

## MOS

Unchanged:

```text
MOS = (intrinsic_value_per_share - market_price_per_share) / intrinsic_value_per_share
```

Requires CALCULATED IV/share and VERIFIED price. Not a trade recommendation.

---

## UNIVERSAL TEST SET

Prior 16 (catalog-resolved ISINs, no hand-typed wrong ISINs):

TCS, INFY, RELIANCE, HDFCBANK, WIPRO, 20MICRONS, AADHARHFC, 3IINFOLTD, A2ZINFRA, ABFRL, 21STCENMGM, APOORVA, ADROITINFO, ABINFRA, ADFFOODS, 360ONE.

Newly dynamically selected from Security Master (eligible XNSE equity, disjoint from the 16):

**3BBLACKBIO, 3MINDIA, 3PLAND, 5PAISA, 63MOONS**.

No manual data injection. No `if ticker ==` DCF logic.

---

## SECURITY-TYPE COVERAGE

| Kind | Names | Ordinary DCF |
|---|---|---|
| Ordinary equity | TCS, INFY, RELIANCE, WIPRO, 20MICRONS, A2ZINFRA, ABFRL, ADFFOODS, 3MINDIA, 3PLAND, 63MOONS, … | Allowed when facts + assumptions exist |
| Bank equity | HDFCBANK | **Not forced.** `bank_equity: ordinary DCF not applicable` |
| Financial / HFC / WAM | AADHARHFC, 360ONE, 5PAISA | Existing classifier is name-token `bank` / `reit` only. Ordinary DCF was attempted; FCF₀ ≤ 0 → BLOCKED. No ticker special-case. |
| Missing filings | APOORVA, ABINFRA, 3BBLACKBIO | BLOCKED on missing facts |

Unsupported types (ETF/REIT/etc.) remain not applicable.

---

## DCF COMPLETION MATRIX

| Security | Status | Evidence missing | Research can resolve? | Assumption can resolve? | Correct status |
|---|---|---|---|---|---|
| TCS | RUN | — | — | Fixture pack only (prod still USER_REQUIRED) | RUN (replay) |
| INFY | RUN | Current TOTAL_OUTSTANDING (CA) | Yes (SIMPLE-24 CA) | No (fact) | RUN equity; IV/share blocked |
| RELIANCE | RUN | Debt (optional) | Yes | No | RUN |
| HDFCBANK | BLOCKED | Ordinary DCF N/A | Bank method / research | No | BLOCKED |
| WIPRO | RUN | Debt optional | Yes | No | RUN |
| 20MICRONS | RUN | Debt optional | Yes | No | RUN |
| AADHARHFC | BLOCKED | FCF₀ ≤ 0; shares CA | Research cannot invent FCF | No | BLOCKED |
| 3IINFOLTD | RUN | Shares CA | Yes | No | RUN equity |
| A2ZINFRA | RUN | Debt optional | Yes | No | RUN |
| ABFRL | RUN | Shares CA | Yes | No | RUN equity |
| 21STCENMGM | BLOCKED | FCF₀ ≤ 0 | No invention | No | BLOCKED |
| APOORVA | BLOCKED | Shares + financials | Yes if filings exist | No | BLOCKED |
| ADROITINFO | BLOCKED | FCF₀ ≤ 0 | No invention | No | BLOCKED |
| ABINFRA | BLOCKED | CFO/capex/financials | Yes if filings exist | No | BLOCKED |
| ADFFOODS | RUN | Debt optional | Yes | No | RUN |
| 360ONE | BLOCKED | FCF₀ ≤ 0; shares CA | No invention of FCF | No | BLOCKED |
| 3BBLACKBIO | BLOCKED | Shares + financials | Yes if filings exist | No | BLOCKED |
| 3MINDIA | RUN | Debt optional | Yes | No | RUN |
| 3PLAND | RUN | — | — | Fixture only | RUN |
| 5PAISA | BLOCKED | FCF₀ ≤ 0; shares CA | No invention of FCF | No | BLOCKED |
| 63MOONS | RUN | Debt optional | Yes | No | RUN |

Production column for every name: **DCF_BLOCKED** until an ACCEPTED assumption pack is supplied by the caller. That is the correct fail-closed production outcome.

---

## RESEARCH VS ASSUMPTION

| Field | Class | Path |
|---|---|---|
| Revenue, NI, CFO, capex, cash, debt, shares, price | VERIFIED FACT | Research first. Never AI as truth. |
| FCF, market cap, net debt, EV, IV, MOS | DERIVED | DSP calculates. |
| Growth, WACC, terminal growth, margins | ASSUMPTION | AI may propose; validator decides. |

---

## ADVERSARIAL TESTS

| Injection | Result |
|---|---|
| Fake AI capex | `refuse_ai_fact` REJECTED; EvidenceJudge does not VERIFY `source_type=llm` |
| AI capex vs NSE primary capex | Primary retained; `AI_CLAIM_REJECTED` |
| Fake AI IV | `ignore_ai_valuation` → None; DCF recalculates independently |
| WACC 2% with terminal 3% | REJECTED (`WACC must exceed terminal growth`) |
| Growth 8% and 18% in one pack | Both REVIEW_REQUIRED; **not averaged** |
| Investing-total as capex | Extractor returns None / XBRL forbidden concept |
| Acquisition as capex | Classified ACQUISITION; rejected |
| Missing capex → 0 | FCF not CALCULATED; DCF not CALCULATED |
| FY26 CFO + FY25 capex | CALCULATION_BLOCKED |

---

## REPRODUCIBILITY

Identical `VerifiedDataset` + identical ACCEPTED pack, two `run_dsp_calculations` calls: same FCF, same terminal PV, same equity IV, same IV/share, same MOS. No randomness.

---

## NUMERIC PRECISION

Internal Decimal precision **28**. Intermediate DCF values are not rounded. `presentation_round` exists for display only. No new rounding introduced.

---

## PERFORMANCE

Live 21-name run (~200 s wall):

| Step | p50 | p95 |
|---|---|---|
| `analyse()` (identity + NSE research + judge) | **4.24 s** | **106.4 s** |
| DCF calculation (`run_dsp_calculations`) | **0.85 ms** | **10.8 ms** |

DCF itself is negligible. Latency is external research / document retrieval. No DCF optimization was attempted.

---

## SECURITY

- No production deployment, flags, DB mutation, or provider activation
- NSE MCP commercial-use pending
- AI cannot write facts or IV
- No secrets committed
- Architecture test: no `if ticker ==`; no fixture ticker tokens in `xbrl.py`, `dsp_calculation.py`, `assumption_validator.py`, `extraction.py`, `acquisition.py`

---

## REGRESSION

Command: pytest SIMPLE-14N-E, 14N-F, 15, 16, 17, 18, 19, 19A, 20, 21, 22, 23, 24, 25, plus 14N acquisition and 14ND (capex/statement touch), `-m "not network"`.

| | Count |
|---|---|
| passed | 219 |
| skipped | 5 (including SIMPLE-25 frontend parked + prior live skips) |
| deselected | 7 (network) |
| failed | 0 |
| xfail | 0 |

SIMPLE-25 offline: **10 passed, 1 skipped** (frontend parked). Live: **1 passed** (21 names).

**New failures:** none. **Pre-existing failures:** none in this set. SIMPLE-14N `test_explicit_capex_vs_ppe` still expects `extract_labeled_field(ppe)==None`.

---

## FILES CHANGED

SIMPLE-25 delta (this forensic):

| File | Change |
|---|---|
| `packages/data_engine/src/data_engine/official_research/xbrl.py` | PPE investing concepts on capex whitelist; `_NON_CAPEX_INVESTING` forbid list |
| `.../extraction.py` | `classify_capex_semantic`, `extract_classified_capex`, DCF_CAPEX_SEMANTICS |
| `.../acquisition.py` | Classified capex fallback; do not skip PPE when a CF page exists |
| `.../field_acquisition.py` | Classified capex after labeled miss |
| `.../orchestrator.py` | Classified capex on document extract |
| `.../statement_tables.py` | PPE labels; classified DCF capex may pass table reconstruction |
| `.../research_plan.py` | Capex required for ordinary equity (still N/A for banks) |
| `.../assumption_validator.py` | Conflicting pack values → REVIEW_REQUIRED, not averaged |
| `.../dsp_calculation.py` | `describe_dcf_blockers` (no formula change) |
| `.../nse_primary.py` | Comment: JSON P&L particulars are not DCF capex |
| `packages/data_engine/tests/test_simple25.py` | Offline + live forensic tests |
| `docs/releases/SIMPLE_25_UNIVERSAL_DCF_COMPLETION_FORENSIC.md` | This report |

Uncommitted SIMPLE-23/24 files remain in the working tree and were **not** redesigned here.

---

## PRODUCTION IMPACT

**None.**

- No production deployment
- No production AI
- No production NSE MCP
- No production provider activation
- No production database mutation
- No production flag changes
- `analyse()` still does **not** inject WACC/growth; production DCF stays BLOCKED until an ACCEPTED assumption pack is supplied by a non-production caller

---

## LIMITATIONS

1. Production DCF remains BLOCKED without ACCEPTED assumptions. That is required fail-closed behavior, not a remaining extraction bug.
2. Names without annual XBRL/CF evidence (APOORVA, ABINFRA, 3BBLACKBIO in this session) cannot invent capex/CFO.
3. FCF₀ ≤ 0 is a hard DCF skip (AADHARHFC, 21STCENMGM, ADROITINFO, 360ONE, 5PAISA). Not clamped, not zeroed.
4. Bank equity is not forced through ordinary DCF.
5. Debt is often UNKNOWN; existing equity-FCF DCF does not require it.
6. SHARES REFRESH_REQUIRED allows equity DCF RUN in replay but blocks IV/share, MOS, and market cap.
7. No multi-year historical series → DSP does not yet **research** a growth assumption from verified facts. The test pack is a universal fixture, not a production default.
8. Frontend parked.

---

## DECISION

**PASS WITH LIMITATIONS.**

The universal mechanism is proven:

- Exact DCF blockers are identified per security.
- Capex is acquired generically from IND-AS PPE investing XBRL and classified cash-flow PPE language **where evidence exists**.
- Capex semantics, sign, period, and consolidation are correct.
- Assumptions are explicit and validated; conflicts are not averaged.
- AI cannot bypass validation or write IV/capex.
- DCF remains deterministic; gates remain intact.
- Market cap still uses verified shares only.
- MOS formula unchanged.
- Bank handling unchanged.
- Dynamic securities tested.
- No company-specific DCF logic.
- Adversarial and reproducibility tests pass.
- Regression green.

SIMPLE-25 is **not CLOSED** because production DCF still requires an ACCEPTED assumption pack (no hidden WACC), and some securities legitimately lack FCF evidence or have FCF₀ ≤ 0.

---

## NEXT FORENSIC

Suggested SIMPLE-26 — **assumption research from verified history** (not hardcoded WACC):

- Derive candidate growth from multi-year verified revenue/CFO/FCF series when those series exist.
- Still: PROPOSED → AssumptionValidator → ACCEPTED.
- Still: no AI → DCF.
- Bank residual-income / book path remains a separate capability, not ordinary DCF.
- Debt extraction completeness (optional for this DCF, required for EV bridge if that contract is ever used).
- Frontend PARKED items remain a dedicated later phase.

```text
FORENSIC → FIND → PROVE → FIX → TEST → VERIFY → CLOSE → NEXT
```
