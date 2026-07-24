# F2.7 — Financial Statement Aggregator

**Package:** `financial` **`0.7.0`** · **Domain payload:** `0.7.0-financial` · **Engine:** `0.7.0-aggregator`

**Scope:** Canonical orchestration layer composing F2.2–F2.6 into one immutable `FinancialAnalysis`.

**Mode:** Domain-only · **No new financial calculations · No forecasting · No valuation · No provider integrations · No market data · No `/api/v1` changes**

**Note:** Completes Phase 2 Financial Statement Intelligence. Suite git milestone remains deferred until explicit approval.

---

## Objective

Provide a single primary entry point for downstream Research / Risk / EQI / Decision consumers that reuses Income, Balance, Cash Flow, Ratio, and Trend intelligence without duplicating math.

---

## Package layout

```text
packages/financial/src/financial/intelligence/
  aggregator_engine.py
  aggregator_models.py
  aggregator_validation.py
  aggregator_explainability.py
```

## API

```python
from financial import FinancialEngine, FinancialStatementsHistory

engine = FinancialEngine()
analysis = engine.analyze_financials(statements)          # single period
analysis = engine.analyze_financials(history)             # multi-period (+ trends)
```

**Inputs:** `FinancialStatements` or `FinancialStatementsHistory` (ordered sequences of statements also accepted as history).

Single-period runs omit `TrendAnalysis` (warning recorded). Multi-period (≥2) includes trends.

## Output — `FinancialAnalysis`

| Section | Source |
|---|---|
| Income | F2.2 Income Statement Intelligence |
| Balance Sheet | F2.3 Balance Sheet Intelligence |
| Cash Flow | F2.4 Cash Flow Intelligence |
| Ratios | F2.5 Financial Ratio Engine |
| Trends | F2.6 Trend Intelligence (multi-period only) |
| Quality flags | Boolean composition of module flags |
| Overall summary | Template composition from flags + insights |
| Explainability | Concatenated module records + aggregator provenance |

## Aggregated flags

Excellent Financial Health · Healthy Financial Position · Needs Attention · Liquidity / Leverage / Cash Flow Concern · Consistent Compounder · Improving Fundamentals · Financial Deterioration

## Design rules

- Pure orchestration — no duplicated ratios or statement math
- Deterministic · immutable · typed · provider-agnostic
- Performance target: **&lt;50 ms** for complete multi-period aggregation (uninstrumented)

## Phase 2 status

F2.1–F2.7 **complete**. Valuation Suite remains frozen. No git tag/commit from this sprint.
