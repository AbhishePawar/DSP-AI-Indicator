# F3.2 — Earnings Quality Intelligence

**Package:** `business_quality` **`0.2.0`** · **Domain:** `0.2.0-business-quality` · **Engine:** `0.2.0-earnings-quality`

**Scope:** Evaluate earnings durability / cash support / accrual risk from `FinancialAnalysis` only.

**Mode:** Domain composition · **No forecasting · No valuation · No market data · No provider integrations · No `/api/v1` changes**

**Frozen:** `valuation` · `financial` (consume public `FinancialAnalysis` only)

---

## Objective

Build Earnings Quality Intelligence that reuses Financial Statement Aggregator outputs without duplicating financial calculations.

---

## Package layout

```text
packages/business_quality/src/business_quality/
  earnings_quality_engine.py
  earnings_quality_models.py
  earnings_quality_validation.py
  earnings_quality_explainability.py
```

## API

```python
from business_quality import BusinessQualityEngine
from financial import FinancialEngine

fa = FinancialEngine().analyze_financials(statements)
bq = BusinessQualityEngine()

eq = bq.analyze_earnings_quality(fa)   # EarningsQualityAnalysis
analysis = bq.analyze(fa)              # BusinessQualityAnalysis (composed)
```

**Input:** `FinancialAnalysis` only.

## Dimensions

Revenue Quality · Operating / Net / Cash Earnings Quality · Accrual Quality · Margin Stability · Earnings Consistency · FCF Support · Non-operating Dependence · Recurring vs Non-recurring

## Flags

High Earnings Quality · Cash Supported Earnings · Recurring Earnings · Stable Margins · Aggressive Accounting Risk · Weak Cash Support · Volatile Earnings · High Accrual Risk

## Design rules

- Reads existing income / cash-flow intelligence fields only
- Accrual quality mapped from `cash_conversion` (no OCF/NI recompute)
- Reuses Business Quality scoring / validation / explainability primitives

## Next

**F3.3 — Capital Allocation Intelligence** — completed; see [F3_SPRINT3_CAPITAL_ALLOCATION_INTELLIGENCE.md](F3_SPRINT3_CAPITAL_ALLOCATION_INTELLIGENCE.md).

**F3.4 — Business Characteristics Intelligence**
