# F3.5 — Competitive Position Indicators

**Package:** `business_quality` **`0.5.0`** · **Domain:** `0.5.0-business-quality` · **Engine:** `0.5.0-competitive-position`

**Scope:** Evaluate structural competitive characteristics inferred from `FinancialAnalysis` outputs only.

**Mode:** Domain composition · **No peer comparisons · No industry datasets · No market share · No forecasting · No valuation · No market data · No provider integrations · No `/api/v1` changes**

**Frozen:** `valuation` · `financial` (consume public `FinancialAnalysis` only)

---

## Objective

Assess competitive position indicators (pricing power, margin defensibility, capital efficiency, cash conversion, resilience) without peer or industry data.

---

## Package layout

```text
packages/business_quality/src/business_quality/
  competitive_position_engine.py
  competitive_position_models.py
  competitive_position_validation.py
  competitive_position_explainability.py
```

## API

```python
from business_quality import BusinessQualityEngine
from financial import FinancialEngine

fa = FinancialEngine().analyze_financials(history)
bq = BusinessQualityEngine()

cp = bq.analyze_competitive_position(fa)  # CompetitivePositionAnalysis
analysis = bq.analyze(fa)                 # composes EQ + CA + BC + CP
```

**Input:** `FinancialAnalysis` only.

## Dimensions

Pricing Power · Margin Defensibility · Return on Capital Strength · Cash Conversion Advantage · Operational Efficiency · Revenue Stability · Profitability Persistence · Capital Efficiency · Competitive Resilience · Financial Competitive Strength

## Flags

Strong Pricing Power · Durable Margins · High Capital Efficiency · Operational Excellence · Strong Competitive Position · Weak Competitive Position · Margin Pressure · Weak Capital Efficiency · Declining Profitability

## Composition

`BusinessQualityEngine.analyze()` merges Earnings Quality (F3.2), Capital Allocation (F3.3), Business Characteristics (F3.4), and Competitive Position (F3.5) into one `BusinessQualityAnalysis`.

## Next

**F3.6 — Business Quality Engine** — completed; see [F3_SPRINT6_BUSINESS_QUALITY_ENGINE.md](F3_SPRINT6_BUSINESS_QUALITY_ENGINE.md).
