# Epic V1.0 Sprint V1.3 — Reverse DCF Intelligence

**Domain package:** `valuation` **`0.3.0`** · **Reverse DCF:** `0.3.0-reverse-dcf`  
**Scope:** Domain only · Research Mode · **not** a recommendation engine

## Mission

Answer: *What future growth assumptions are implied by the current market price?*

## Location (canonical)

`packages/valuation/src/valuation/reverse_dcf/`

| File | Role |
|------|------|
| `reverse_dcf_models.py` | Inputs · result · scenarios · sensitivity · solver metadata |
| `reverse_dcf_validation.py` | Hard rejects → `ValuationError` |
| `reverse_dcf_explainability.py` | `ReverseExplainedValue` |
| `reverse_dcf_engine.py` | Binary-search solver + scenarios + sensitivity |

## Integration (additive)

```python
from valuation import ValuationEngine, ReverseDcfInputs

result = ValuationEngine().analyze_reverse_dcf(inputs)
```

Unchanged: `analyze()`, `analyze_dcf()`, DCF Intelligence modules, `/api/v1`, Web VIE.

## Solver

- Binary search on implied revenue CAGR  
- Precision ±0.01% (`1e-4`)  
- Max 200 iterations  
- Convergence metadata returned  

## Scenarios

Bear / Base / Bull — independent implied-growth solves (margin overlays).

## Protected / untouched

Research · MIE · EMI · EQI · Decision · Copilot · Overall Valuation · `/api/v1` · Web VIE · `dcf_intelligence/`

## Next

V1.4+ method engines as scheduled; Overall Valuation stays disabled until unlock.
