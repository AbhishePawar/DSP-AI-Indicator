# DCF risk-free tenor policy

**Policy ID:** `dsp.dcf.risk_free_tenor.v1`  
**Status:** **POLICY_GAP** (explicit)  
**Authority:** CapmInputs / official `DcfMethod` / RS-004 / SIMPLE-28 forensic  
**Not a convenience scrape.**

This document is the project’s DCF risk-free tenor policy. It does **not**
select a 91-day T-bill, 182-day T-bill, 364-day T-bill, 5-year G-sec, or
10-year G-sec merely so WACC can calculate.

Machine-readable copy: `packages/data_engine/src/data_engine/official_research/dcf_tenor_policy.py`.

---

## Preferred maturity / tenor

**None established.**

`valuation.dcf_intelligence.assumptions.CapmInputs` has `risk_free_rate`,
`beta`, and `equity_risk_premium` only. Official `DcfMethod` consumes a
discount rate; it does not name a government-security tenor. RS-004
(Valuation) does not specify T-bill vs G-sec maturity. SIMPLE-28 recorded
`POLICY_GAP` after live RBI NSDP retrieval.

Inventing a Damodaran-style 10-year convention here would be a new
methodology, not reuse of an existing one.

## Acceptable alternatives

**None.** There is no preferred tenor, so there are no permitted substitutes.

## Maximum maturity mismatch

**Not applicable.** Mismatch is defined only against a preferred tenor.

When a required tenor is later set: unlabeled → `REVIEW_REQUIRED`; different
labeled tenor → `POLICY_MISMATCH`; exact match → `BOUND`.

## Observation date vs valuation date

- `as_of` / observation date must be **on or before** `valuation_date`.
- `retrieved_at` is **not** `as_of`.
- Observation after valuation date → **REJECTED**.

## Known maturity required to bind

**Yes.** A government-security yield may bind as DCF `risk_free_rate` only
when **all** of the following hold:

- tenor/maturity is **explicitly known** on the source;
- tenor satisfies this policy’s required/preferred maturity (once one exists);
- observation date is acceptable;
- currency is INR for Indian equity (no silent FX);
- source is Tier 1A regulator/exchange;
- semantics are a government yield, not repo/CRR/SLR/Bank Rate/MCLR/inflation;
- EvidenceJudge passes.

## Unlabeled government-yield observations

**VERIFIED_OBSERVATION**, **DCF_BINDING = POLICY_GAP**.

Example: RBI NSDP “Treasury Bill Rates” without 91/182/364-day label.

Do not assume a tenor. Do not bind.

## Stale observations

Age vs valuation date **> 30 calendar days** → **STALE** / **RESEARCH_REQUIRED**.
Not used as a WACC input. (SIMPLE-28 forensic window; risk-free rates are
time-sensitive.)

Missing observation date → **UNKNOWN**, not bound.

## Currency

Indian equity DCF: **INR**. No silent conversion. Wrong currency → **REJECTED**.

## Conflicting observations

Do **not** average. Apply source authority. Unresolved → **REVIEW_REQUIRED**,
WACC incomplete, DCF blocked.

## Multiple eligible maturities

Until a preferred tenor exists, two labeled government yields (e.g. 5-year and
10-year) are **REVIEW_REQUIRED**, not a silent pick.

## Binding outcomes

| Case | Observation | DCF binding |
|---|---|---|
| Unlabeled T-bill | VERIFIED_OBSERVATION | POLICY_GAP |
| Labeled 10-year G-sec while policy is GAP | VERIFIED_OBSERVATION | POLICY_GAP (not a silent 10-year choice) |
| Repo / Bank Rate / MCLR | REJECTED as risk-free | REJECTED |
| Required tenor set, mismatch | — | POLICY_MISMATCH |
| Required tenor set, exact labeled match, judge PASS | VERIFIED | BOUND |

---

**Unsupported assumptions (not used):** 10-year G-sec as default; T-bill as
cash-like rf; Damodaran India ERP; GDP/inflation as rf or ERP.
