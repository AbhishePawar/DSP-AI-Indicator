# V1.6 — Earnings Power Value (EPV)

**Domain package:** `valuation` **`0.6.0`** · **EPV:** `0.6.0-epv`  

**Scope:** New zero-growth valuation methodology on shared Valuation Core.  

**Mode:** Research Mode only · Overall Valuation remains **DISABLED**

---

## Objective

Implement Earnings Power Value (EPV): capitalize **normalized sustainable earnings**
at the cost of capital assuming **no future growth**.

Integrates with `valuation.core` (confidence, validation, sensitivity, scenario,
explainability, `ValuationResult`). Does **not** modify DCF / Reverse DCF /
Residual Income / Core APIs / Web VIE / `/api/v1`.

---

## Module

```text
packages/valuation/src/valuation/epv/
  __init__.py
  epv_engine.py
  epv_models.py
  epv_validation.py
  epv_explainability.py
```

## Formula (research)

1. Normalize EBIT (average / median / manual / cycle; strip one-offs)  
2. Tax-Adjusted EBIT = EBITₙ × (1 − t)  
3. Owner Earnings = TaxAdj + Depreciation − MaintCapEx − ΔNWC  
4. Enterprise EPV = Owner Earnings / Cost of Capital  
5. Equity = EV + Cash − Debt − MI + Investments  
6. IV/share = Equity / Shares  

## API

```python
from valuation import ValuationEngine, EpvInputs, NormalizationMethod

result = ValuationEngine().analyze_epv(
    EpvInputs(
        revenue=1000,
        ebit=100,
        tax_rate=0.25,
        maintenance_capex=40,
        depreciation=40,
        cost_of_capital=0.10,
        shares_outstanding=100,
        cash=50,
        debt=100,
        current_market_price=5,
        normalization_method=NormalizationMethod.MANUAL_OVERRIDE,
    )
)
assert result.enterprise_epv.value == 750.0
```

Map to shared result: `to_epv_valuation_result(result)`.

## Success criteria

- Domain-only · uses Valuation Core · no breaking API changes  
- Existing methods untouched · Research Mode · Overall Valuation disabled  
- 100% EPV module coverage · regression GREEN  

## Recommended git tag

`milestone/V1.6-epv`
