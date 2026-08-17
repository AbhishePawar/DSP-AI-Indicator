# Financial Data Derivation / Calculation Policy

| Field | Value |
|---|---|
| **Status** | **MANDATORY · platform-wide** |
| **Effective** | 2026-08-18 |
| **Authority** | [CV-001](CV_001_DATA_AUTHENTICITY_FIRST.md) · [CV-002](CV_002_TO_010_TIER0_CORE_VALUES.md) · [CV-005](CV_002_TO_010_TIER0_CORE_VALUES.md) · [ARCHITECTURE_BIBLE.md](ARCHITECTURE_BIBLE.md) |
| **Canonical implementation** | `packages/financial/src/financial/derivation/` |

This policy operationalizes CV-001 categories 3 (DSP AI Calculated) and 5
(Derived Metrics). It does **not** add a new Core Value ID.

---

## Invariant

> NEVER GUESS DATA.
> CALCULATE ONLY WHEN THE FORMULA AND ALL REQUIRED VERIFIED INPUTS ARE KNOWN.
> LABEL CALCULATED VALUES AS CALCULATED.
> OTHERWISE RETURN UNAVAILABLE.

Applies across research, indicators, and valuation **inputs**. Valuation
engines remain the owners of IV / MoS / fair value; they must not invent
statement line items to feed those engines.

---

## Field states

Every financial field ultimately has exactly one state:

| Status | Meaning |
|---|---|
| **reported** | Directly supplied by an authoritative provider. Preserve the provider value and provenance. |
| **calculated** | Not directly reported, but deterministically derived from verified inputs using an explicitly defined formula. Store the formula and input references. Never present as provider-reported. |
| **unavailable** | Required information is missing, invalid, incompatible, ambiguous, or mathematically insufficient. |

**Provider did not report this field does not automatically mean unavailable.**
First determine whether the field can be deterministically calculated.

Never estimate, interpolate, infer, or guess merely to fill a field.

---

## Calculation is permitted only when

1. The formula is explicitly defined (registered `formula_id`).
2. Every required input exists.
3. Every required input is valid (finite, not NaN/Inf).
4. Inputs belong to compatible periods (no silent annual ↔ quarterly mix).
5. Inputs use a compatible accounting basis (`consolidated` vs `standalone`).
6. Units are compatible, or an **explicit** scale conversion exists.
7. Currency is compatible. FX conversion is **not** supported in the financial
   derivation layer; currency mismatch → **unavailable**.
8. No required input is silently substituted (including silent `0`).
9. No hidden fallback changes the formula.
10. Division-by-zero and other mathematical invalidity are handled explicitly
    as **unavailable**.

If any condition fails: **unavailable**.

---

## Provenance

Calculated fields preserve (where architecture permits):

- `value`
- `status`: `reported` \| `calculated` \| `unavailable`
- `formula` and `formula_id`
- input field references (id, value, status, period, basis, unit, currency, source)
- compatibility snapshot
- `calculation_version` (`financial-derivation-1.0.0`)
- `unavailable_reason` when status is unavailable

This extends the existing financial-domain models. It does **not** replace
`data_engine.FinancialStatementProvenance` or `dsp_platform` investment
provenance. Adapters may wrap derivation results; they must not invent a
parallel incompatible provenance stack.

---

## Formula classification (repository audit)

Verified against `IncomeStatement`, `BalanceSheet`, `CashFlowStatement`
(`packages/financial`). Authenticated provider periods
(`data_engine.financial_statement.models`) are **reported** line items only.

| Metric | Class | Required inputs / notes |
|---|---|---|
| Statement line items (revenue, NI, equity, assets, liabilities, OCF, …) | **A reported** when provider-mapped | Mapping ≠ guessing. Missing map → try **B**, else **C**. |
| Gross margin | **B** | Preferred: `gross_profit / revenue`. Alternate formula ` (revenue − cogs) / revenue` is a **separate** `formula_id` — not a silent fallback. |
| Operating margin | **B** | Domain model: `ebit / revenue`. There is no `operating_income` on `IncomeStatement`. |
| Net margin | **B** | `net_income / revenue` |
| Average equity | **B** | `(beginning_equity + ending_equity) / 2` — both required |
| ROE | **B** | `net_income / average_equity`. Ending-equity-only is **not** this formula. |
| ROCE | **B** | `ebit / (total_assets − current_liabilities)` |
| Total debt | **B** | `short_term_debt + long_term_debt` — **both** required (no silent zero) |
| Debt / equity | **B** | `total_debt / equity` |
| Working capital | **B** | `current_assets − current_liabilities` |
| FCF | **A** if `free_cash_flow` reported; else **B** | `operating_cash_flow − \|capex\|` only when both present |
| Revenue growth | **B** | Same `period_type`, distinct `period_end`, non-zero prior revenue |
| EPS growth | **B** | Same as revenue growth using `eps` |
| EBITDA if missing | **C** | Do not fabricate from incomplete components |
| Valuation IV / MoS | Engine **calculated** under CV-001 | Out of scope of statement-line derivation; do not guess valuation inputs |

### Existing ratio engine (do not duplicate)

`financial.intelligence.ratio_engine` already computes many ratios with
`formula` + `inputs` on `RatioMetric`, but:

- has **no** `reported \| calculated \| unavailable` status
- `_avg` uses one side when the other is missing
- `_total_debt` / `_current_assets` silently substitute `0`
- ROE is `net_income / ending equity`, not average equity

Those helpers remain for F2.5 compatibility. **Canonical policy-compliant
derivation is `financial.derivation`.** Do not copy unsafe fallbacks into the
derivation engine. Do not rewrite the ratio engine in this change.

`quality_signals.operating_working_capital` already fail-closes on missing
inputs. `_computed_fcf` already requires both OCF and capex.

---

## Forbidden

- Guess missing financial values
- Use management estimates unless the data policy explicitly supports that source
- Substitute annual values for quarterly values silently
- Mix consolidated and standalone data
- Mix reported and calculated inputs **without** provenance
- Fabricate EBITDA, FCF, debt, equity, margins, ratios, or valuation inputs
- Silently use a different formula because preferred inputs are missing
- Label a calculated value as provider-reported

---

## Package boundary

`financial` may depend only on `core`. Derivation **must not** import
`data_engine`, `dsp_platform`, or `valuation`. Unit-scale conversion tables
in this package are the explicit conversion support for statement scales
(`actual` / `thousands` / `millions` / `billions` and known aliases).
They are not FX conversion.
