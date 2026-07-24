# V1.9 — Asset-Based & Liquidation Valuation

**Domain package:** `valuation` **`0.9.0`** · **Asset-Based:** `0.9.0-asset-based`  

**Scope:** Book / TBV / NAV / ANAV / Liquidation / Conservative Liquidation / Replacement Cost.  

**Mode:** Research Mode only · Overall Valuation remains **DISABLED**

**Note:** Do **not** create git tags in this sprint — suite milestone tagging comes after Relative Valuation + Cross-Method Validation.

---

## Objective

Implement a comprehensive Asset-Based Valuation Engine on Valuation Core.
Does **not** modify existing valuation engines, Web VIE, or `/api/v1`.

---

## Module

```text
packages/valuation/src/valuation/asset_based/
  __init__.py
  asset_engine.py
  asset_models.py
  asset_validation.py
  asset_explainability.py
```

## Methods

| Method | Summary |
|---|---|
| Book Value | Equity / shares |
| Tangible Book | Exclude goodwill & intangibles |
| NAV | Fair-value assets − liabilities |
| Adjusted NAV | + hidden / private / RE / appraisal |
| Liquidation | Category haircuts |
| Conservative Liquidation | Capped recoveries; intangibles/GW = 0 |
| Replacement Cost | Replace operating assets |

## API

```python
from valuation import ValuationEngine, AssetBasedInputs, AssetMethod

result = ValuationEngine().analyze_asset_based(
    AssetBasedInputs(
        cash=100,
        ppe=400,
        long_term_debt=200,
        shares_outstanding=100,
        method=AssetMethod.BOOK_VALUE,
    )
)
assert result.book_value.value is not None
```

## Suite readiness

Absolute / fundamental valuation methods (DCF, Reverse DCF, RIV, Core, EPV, Graham, DDM, Asset-Based) plus Relative Suite are in place. Next: Cross-Method Validation, then Overall Aggregator, then suite git milestone.
