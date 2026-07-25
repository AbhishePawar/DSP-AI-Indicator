# F3.6 — Business Quality Engine

**Package:** `business_quality` **`0.6.0`** · **Domain:** `0.6.0-business-quality` · **Engine:** `0.6.0-business-quality-engine`

**Scope:** Canonical orchestration of completed Business Quality intelligence modules into one `BusinessQualityAnalysis`.

**Mode:** Composition only · **No new analytical dimensions · No financial calculations · No valuation · No forecasting · No peers · No providers · No `/api/v1` changes**

**Frozen:** `valuation` · `financial` (consume public `FinancialAnalysis` only)

---

## Objective

Make `BusinessQualityEngine.analyze()` the single public entry point that composes EQ + CA + BC + CP once each.

---

## Package layout

```text
packages/business_quality/src/business_quality/
  business_quality_engine.py
  business_quality_models.py
  business_quality_validation.py
  business_quality_explainability.py
```

## API

```python
from business_quality import BusinessQualityEngine, BusinessQualityWeights
from financial import FinancialEngine

fa = FinancialEngine().analyze_financials(history)
bq = BusinessQualityEngine()

analysis = bq.analyze(fa)  # BusinessQualityAnalysis
analysis = bq.analyze(
    fa,
    weights=BusinessQualityWeights(
        earnings_quality=0.4,
        capital_allocation=0.3,
        business_characteristics=0.2,
        competitive_position=0.1,
    ),
)
```

**Input:** `FinancialAnalysis` only.

**Optional APIs:** `analyze_earnings_quality()`, `analyze_capital_allocation()`, `analyze_business_characteristics()`, `analyze_competitive_position()`.

## Default weights

| Module | Weight |
|---|---|
| Earnings Quality | 30% |
| Capital Allocation | 30% |
| Business Characteristics | 20% |
| Competitive Position | 20% |

## Overall ratings

Excellent · Strong · Good · Average · Weak · Poor

## Output highlights

Nested module analyses · overall score/rating/confidence · aggregated flags (critical / warning / positive) · merged explainability · validation summary · configurable weights used

## Next

**F3.7 — Business Quality Aggregator** — completed; see [F3_SPRINT7_BUSINESS_QUALITY_AGGREGATOR.md](F3_SPRINT7_BUSINESS_QUALITY_AGGREGATOR.md). **Phase 3 complete.**
