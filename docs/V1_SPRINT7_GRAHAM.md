# V1.7 — Graham Intrinsic Value

**Domain package:** `valuation` **`0.7.0`** · **Graham:** `0.7.0-graham`  

**Scope:** Benjamin Graham intrinsic-value heuristics on Valuation Core.  

**Mode:** Research Mode only · Overall Valuation remains **DISABLED**

---

## Objective

Implement Graham Intrinsic Value as a **valuation heuristic** with explicit
assumptions. Support:

1. **Original:** `IV = EPS × (8.5 + 2G)`
2. **Modern:** `IV = EPS × (8.5 + 2G) × (Y_ref / Y_aaa)`

Does **not** modify DCF / Reverse DCF / Residual Income / EPV / Core / Web VIE / `/api/v1`.

---

## Module

```text
packages/valuation/src/valuation/graham/
  __init__.py
  graham_engine.py
  graham_models.py
  graham_validation.py
  graham_explainability.py
```

## API

```python
from valuation import ValuationEngine, GrahamInputs, GrahamFormula

result = ValuationEngine().analyze_graham(
    GrahamInputs(
        eps_trailing=2.0,
        growth_rate=7.0,  # percent units (G=7)
        aaa_bond_yield=0.044,
        formula=GrahamFormula.ORIGINAL,
        shares_outstanding=100,
        current_market_price=30,
    )
)
assert result.intrinsic_value_per_share.value == 45.0
```

`G` is in **percent units** by default (7 → 7%). Set `growth_as_decimal=True` for 0.07.

## Assumptions (stated)

- Constant expected growth `G`
- No explicit cash-flow / balance-sheet model
- Modern formula only adjusts by AAA yield ratio
- Research / educational only — not investment advice

## Recommended git tag

`milestone/V1.7-graham`
