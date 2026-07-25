# F3.4 — Business Characteristics Intelligence

**Package:** `business_quality` **`0.4.0`** · **Domain:** `0.4.0-business-quality` · **Engine:** `0.4.0-business-characteristics`

**Scope:** Evaluate structural operating characteristics from `FinancialAnalysis` outputs only.

**Mode:** Domain composition · **No forecasting · No valuation · No market data · No provider integrations · No `/api/v1` changes**

**Frozen:** `valuation` · `financial` (consume public `FinancialAnalysis` only)

---

## Objective

Assess how the business operates (simplicity, capital intensity, scalability, durability, resilience) without recalculating statement metrics.

---

## Package layout

```text
packages/business_quality/src/business_quality/
  business_characteristics_engine.py
  business_characteristics_models.py
  business_characteristics_validation.py
  business_characteristics_explainability.py
```

## API

```python
from business_quality import BusinessQualityEngine
from financial import FinancialEngine

fa = FinancialEngine().analyze_financials(history)
bq = BusinessQualityEngine()

bc = bq.analyze_business_characteristics(fa)  # BusinessCharacteristicsAnalysis
analysis = bq.analyze(fa)                     # composes EQ + CA + BC
```

**Input:** `FinancialAnalysis` only.

## Dimensions

Business Simplicity · Capital Intensity · Asset-Light · Operating Leverage · Business Scalability · Margin Durability · Cash Generation · Financial Resilience · Cyclicality · Operational Stability

## Flags

Asset Light · Capital Intensive · Highly Scalable · Operationally Stable · Resilient Business · Cyclical Business · Strong Cash Generator · Margin Durable · High Operating Leverage

## Composition

`BusinessQualityEngine.analyze()` merges Earnings Quality (F3.2), Capital Allocation (F3.3), and Business Characteristics (F3.4) into one `BusinessQualityAnalysis`.

## Next

**F3.5 — Competitive Position Indicators** — completed; see [F3_SPRINT5_COMPETITIVE_POSITION_INDICATORS.md](F3_SPRINT5_COMPETITIVE_POSITION_INDICATORS.md).
