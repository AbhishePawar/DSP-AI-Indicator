# Epic V1.0 Sprint V1.4 — Residual Income Valuation (Enhanced)

**Domain package:** `valuation` **`0.4.1`** · **RIV:** `0.4.1-residual-income`  
**Scope:** Domain only · Research Mode · **not** a recommendation engine

## Mission

Multi-stage Residual Income Valuation with clean-surplus auto book projection,
ROE path models, quality flags, and V2-ready aggregate cites.

## Best practices covered

1. Clean surplus validation (`BV + NI − Div = ending`)  
2. Automatic book value projection (no yearly BV input)  
3. ROE models: Constant · Linear Fade · Mean Reversion · Manual  
4. Multi-stage: Explicit · Continuing RI · Terminal PV  
5. Confidence factors (BV/ROE stability, forecast, AQ, completeness, clean surplus)  
6. Quality flags (sustainability, declining ROE, negative RI, weak BV, accounting, capital efficient)  
7. Enhanced explainability  
8. Sensitivity: ROE · r · g · payout · terminal ROE  
9. Bear / Base / Bull scenarios  
10. Deterministic  
11. `to_v2_aggregate_payload()` for future aggregation  
12. &lt; 50 ms target  
13. Docstrings  
14. Research disclaimer on all outputs  
15. Typed · immutable · 100% module coverage  

## Integration

```python
from valuation import ValuationEngine, ResidualIncomeInputs, RoeForecastModel

result = ValuationEngine().analyze_residual_income(inputs)
```

Unchanged: `analyze()`, DCF, Reverse DCF, legacy `ResidualIncomeMethod`, Web VIE, `/api/v1`.
