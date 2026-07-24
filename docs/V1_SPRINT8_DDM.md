# V1.8 — Dividend Discount Model (DDM)

**Domain package:** `valuation` **`0.8.0`** · **DDM:** `0.8.0-ddm`  

**Scope:** Comprehensive DDM on Valuation Core (zero-growth, Gordon, two-stage, multi-stage).  

**Mode:** Research Mode only · Overall Valuation remains **DISABLED**

**Note:** Do **not** create git tags in this sprint — suite milestone tagging comes later.

---

## Objective

Implement Dividend Discount Model variants with explicit assumptions/limitations.
Uses `valuation.core`. Does **not** modify DCF / Reverse DCF / Residual Income /
EPV / Graham / Core / Web VIE / `/api/v1`.

---

## Module

```text
packages/valuation/src/valuation/ddm/
  __init__.py
  ddm_engine.py
  ddm_models.py
  ddm_validation.py
  ddm_explainability.py
```

## Methods

| Method | Formula |
|---|---|
| Zero growth | `IV = DPS / r` |
| Gordon | `IV = DPS₁ / (r − g)` |
| Two-stage | `Σ PV(D_t) + PV(Gordon terminal)` |
| Multi-stage | User growth schedule + Gordon terminal |

## API

```python
from valuation import ValuationEngine, DdmInputs, DdmMethod

result = ValuationEngine().analyze_ddm(
    DdmInputs(
        current_dps=2.0,
        cost_of_equity=0.10,
        expected_dividend_growth=0.03,
        method=DdmMethod.GORDON,
        shares_outstanding=100,
        current_market_price=30,
    )
)
assert result.intrinsic_value_per_share.value == pytest.approx(2.06 / 0.07)
```

## Recommended later tag (suite completion)

`milestone/V1.8-ddm` — create only after full Valuation Suite milestone.
