# F2.2 — Income Statement Intelligence

**Package:** `financial` **`0.2.0`** · **Domain payload:** `0.2.0-financial` · **Engine:** `0.2.0-income`

**Scope:** Pure domain analysis of normalized `IncomeStatement` series — metrics, quality flags, trends, explainability.

**Mode:** Domain-only · **No forecasting · No valuation · No provider integrations · No `/api/v1` changes**

**Note:** Phase 1 Valuation Suite remains frozen. No git milestone until Phase 2 completes.

---

## Objective

Build analytical intelligence on top of the F2.1 Financial Data Domain so Research, Moat, EQI, and Decision modules can later consume standardized income-statement insights.

---

## Package layout

```text
packages/financial/src/financial/intelligence/
  __init__.py
  income_engine.py
  income_models.py
  income_validation.py
  income_explainability.py
```

## API

```python
from financial import FinancialEngine, IncomeStatement

engine = FinancialEngine()
analysis = engine.analyze_income_statement(income)          # single period
analysis = engine.analyze_income_statement(snapshot)        # multi-period
analysis = engine.analyze_income_statement(payload_dict)    # normalized JSON/dict
```

Inputs accepted: `IncomeStatement`, `FinancialStatements`, `FinancialSnapshot`, normalized dict, or a sequence of periods. Optional `history=` for single-statement growth context.

## Capabilities

| Area | Outputs |
|---|---|
| Revenue | Growth, QoQ, YoY, CAGR, stability, trend class |
| Margins | Gross, EBITDA, EBIT, Operating, Pretax, Net |
| Expenses | COGS/R&D/SG&A/OpEx/Interest/Tax/Other % + expense trend |
| Profitability | Quality scores, margin expand/compress, EPS metrics |
| Consistency | Stability, burdens, other-income dependence, one-time heuristic |
| Quality flags | Healthy Growth, Declining Revenue, Margin Expansion/Compression, High Operating Leverage, Strong/Weak Earnings Quality, High Tax/Interest Burden |
| Trends | Improving / Stable / Weakening |
| Explainability | Formula, inputs, intermediates, result, confidence, interpretation, limitations |

## Validation

Hard failures raise `IncomeAnalysisError` (subclass of `FinancialError`):

- Missing / zero revenue
- NaN / Infinity
- Negative shares / invalid EPS
- Impossible margins (|margin| > 500% or non-finite)

Reuses Financial Domain `validate_statements` when a full period triad is supplied.

## Design rules

- Frozen, typed dataclasses
- Deterministic math only (<20 ms / statement target)
- Provider-agnostic
- Extends `FinancialEngine` without breaking F2.1 methods

## Next

**F2.3 — Balance Sheet Intelligence** — completed; see [F2_SPRINT3_BALANCE_INTELLIGENCE.md](F2_SPRINT3_BALANCE_INTELLIGENCE.md).

**Next:** F2.4 — Cash Flow Intelligence.
