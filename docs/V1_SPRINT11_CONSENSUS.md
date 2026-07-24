# V1.11 — Cross-Method Validation & Consensus Engine

**Domain package:** `valuation` **`0.11.0`** · **Consensus:** `0.11.0-consensus`  

**Scope:** Compare standardized results from DCF, Reverse DCF, Residual Income, EPV, Graham, DDM, Asset-Based, Relative — plus future plug-in methods.

**Mode:** Research Mode only · Overall Valuation remains **DISABLED**

**Note:** Do **not** create git tags in this sprint — suite milestone tagging comes after V1.12 Overall Valuation Aggregator.

---

## Objective

Implement a domain-only Cross-Method Validation & Consensus Engine on Valuation Core.
It **never** calls valuation engines. It accepts `ValuationResult` or V2 aggregate payloads only.
Does **not** enable Overall Valuation.

---

## Module

```text
packages/valuation/src/valuation/consensus/
  __init__.py
  consensus_engine.py
  consensus_models.py
  consensus_validation.py
  consensus_explainability.py
```

## Inputs

| Input | Role |
|---|---|
| `ValuationResult` | Preferred standardized Core result |
| V2 aggregate payload | Dict cite from any method `to_v2_aggregate_payload` |
| `CompanyProfile` | Optional applicability context |
| `WeightingMode` | automatic / manual / equal / confidence / applicability / research |
| `OutlierThresholds` | Z-score, IQR, median deviation, extreme ratio |

## Outputs

`ConsensusResult` includes consensus IV / per-share, weighted mean/median, median, trimmed mean, method weights & rankings, applicability, outliers, disagreement analysis, consistency score (0–100), confidence interval, scenarios, sensitivity summary, quality flags, explainability, research disclaimer.

## API

```python
from valuation import (
    ValuationEngine,
    ConsensusInputs,
    WeightingMode,
    CompanyProfile,
)

# After running method engines elsewhere, pass standardized results only:
result = ValuationEngine().analyze_consensus(
    ConsensusInputs(
        methods=[dcf_vr, relative_vr, asset_vr],  # ValuationResult or payloads
        weighting_mode=WeightingMode.AUTOMATIC,
        company_profile=CompanyProfile(pays_dividend=True, growth_company=True),
    )
)
assert result.consensus_per_share.value is not None
assert result.to_dict()["consistency_score"] is not None
```

## Design rules

- Never invokes DCF / Relative / etc. engines
- Future methods plug in via `method` name + optional `category_overrides`
- `ConsensusValidationError` subclasses `ValuationError`
- `to_v2_aggregate_payload` sets `overall_valuation_enabled: False`

## Suite readiness

Absolute methods + Relative + Consensus + **Overall Aggregator** complete Phase 1.
Suite git milestone pending explicit approval → Phase 2 Financial Statement Intelligence.
