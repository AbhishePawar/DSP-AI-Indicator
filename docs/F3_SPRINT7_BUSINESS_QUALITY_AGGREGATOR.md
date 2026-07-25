# F3.7 — Business Quality Aggregator

**Package:** `business_quality` **`0.7.0`** · **Domain:** `0.7.0-business-quality` · **Aggregator:** `0.7.0-business-quality-aggregator`

**Scope:** Reporting / packaging layer for canonical `BusinessQualityAnalysis`.

**Mode:** Aggregation only · **No new analytics · No ratios · No valuation · No forecasting · No peers · No providers · No `/api/v1` changes**

**Frozen:** `valuation` · `financial`

---

## Objective

Finalize Phase 3 by exposing Business Quality as deterministic, immutable report objects for Decision Engine, Research, Copilot, and future APIs.

---

## Package layout

```text
packages/business_quality/src/business_quality/
  business_quality_aggregator.py
  business_quality_summary.py
  business_quality_report_models.py
  business_quality_report_validation.py
  business_quality_report_explainability.py
```

## API

```python
from business_quality import BusinessQualityEngine, BusinessQualityAggregator
from financial import FinancialEngine

fa = FinancialEngine().analyze_financials(history)
analysis = BusinessQualityEngine().analyze(fa)
report = BusinessQualityAggregator().aggregate(analysis)  # BusinessQualityReport
```

**Input:** `BusinessQualityAnalysis` only.

## Report contents

Executive Summary · Business Quality Rating · Strengths · Weaknesses · Key Risks · Positive Signals · Warning Signals · Confidence Summary · Evidence Summary · Module Breakdown · Recommended Interpretation · Limitations · Metadata · Explainability

## Guarantees

- Pure aggregation / packaging of existing analysis fields
- Deduplicated, deterministically ordered collections
- UI-agnostic immutable models (no HTML/Markdown/PDF)
- Full explainability and validation

## Phase 3 status

**COMPLETE** (F3.1–F3.7)
