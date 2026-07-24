# F3.3 — Capital Allocation Intelligence

**Package:** `business_quality` **`0.3.0`** · **Domain:** `0.3.0-business-quality` · **Engine:** `0.3.0-capital-allocation`

**Scope:** Evaluate capital allocation quality from `FinancialAnalysis` cash-flow / ratio / trend outputs.

**Mode:** Domain composition · **No forecasting · No valuation · No market data · No provider integrations · No `/api/v1` changes**

**Frozen:** `valuation` · `financial` (consume public `FinancialAnalysis` only)

---

## Objective

Assess management capital deployment discipline without recalculating statement metrics.

---

## Package layout

```text
packages/business_quality/src/business_quality/
  capital_allocation_engine.py
  capital_allocation_models.py
  capital_allocation_validation.py
  capital_allocation_explainability.py
```

## API

```python
from business_quality import BusinessQualityEngine
from financial import FinancialEngine

fa = FinancialEngine().analyze_financials(history)
bq = BusinessQualityEngine()

ca = bq.analyze_capital_allocation(fa)  # CapitalAllocationAnalysis
analysis = bq.analyze(fa)               # composes EQ + CA
```

**Input:** `FinancialAnalysis` only.

## Dimensions

Capital Allocation Discipline · Reinvestment Quality · Capex Discipline · Dividend Allocation · Share Buyback Quality · Debt Reduction · Cash Deployment · Financial Flexibility · Allocation Consistency · Shareholder Stewardship

## Flags

Excellent Capital Allocation · Disciplined Reinvestment · Shareholder Friendly · Healthy Cash Deployment · Excessive Capital Spending · Weak Capital Allocation · Debt Dependent · Dividend At Risk · Inconsistent Allocation

## Composition

`BusinessQualityEngine.analyze()` merges Earnings Quality (F3.2) and Capital Allocation (F3.3) into one `BusinessQualityAnalysis`.

## Next

**F3.4 — Business Characteristics Intelligence**
