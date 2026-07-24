# Epic V1.0 Sprint V1.2 — Discounted Cash Flow Intelligence

**Domain package:** `valuation` **`0.2.0`** · **DCF Intelligence:** `0.2.0-dcf-intelligence`  
**Web VIE (presentation):** `0.2.0-discounted-cash-flow` under `apps/web/src/lib/valuation/` (unchanged API)

## Mission

Complete **domain** Discounted Cash Flow engine (Clean Architecture / DDD) inside
`packages/valuation/dcf_intelligence/`. Evidence-first, deterministic, explainable.
**Overall Valuation remains DISABLED** on the web VIE façade.

## Location (canonical domain)

`packages/valuation/src/valuation/dcf_intelligence/`

| Module | Role |
|--------|------|
| `assumptions.py` | Forecast, CAPM, capital structure, terminal, bridge, market, sensitivity specs |
| `explain.py` | `ExplainedValue` (formula · inputs · intermediates · confidence) |
| `wacc.py` | CAPM cost of equity · after-tax debt · WACC |
| `forecast.py` | Historical FCF support · FCFF explicit forecast (default 10y) |
| `terminal.py` | Gordon Growth · Exit Multiple (optional) · blend |
| `present_value.py` | Discount FCFF + TV → Enterprise Value |
| `equity.py` | Cash / debt / minority / investments → Equity · IV/share |
| `margin.py` | MoS ratio + research posture bands |
| `sensitivity.py` | Growth · WACC · terminal growth OTAT grid |
| `engine.py` | `DiscountedCashFlowEngine.analyze` |

## Integration

```python
from valuation import ValuationEngine, DcfAnalysisInputs, ...

result = ValuationEngine().analyze_dcf(inputs)  # additive; analyze() unchanged
```

Legacy multi-method `DcfMethod` / `analyze()` aggregation **unchanged** (no breaking API).

## MoS research postures (not recommendations)

| Band | Threshold |
|------|-----------|
| strong_buy | MoS ≥ 40% |
| buy | MoS ≥ 20% |
| hold | MoS ≥ 0% |
| overvalued | MoS < 0% |

Disclaimer attached on every result. Research Mode UIs must remap via compliance.

## Protected modules (untouched)

Research Platform · MIE · EMI · EQI · Decision Engine · completed web modules · `/api/v1`

## Tests

`packages/valuation/tests/test_dcf_intelligence.py` — WACC, terminal, DCF, MoS, sensitivity, integration.

## Next

Sprint V1.3 — next method engine; Overall Valuation stays disabled.
