# Epic V1.0 Sprint V1.2 — Discounted Cash Flow (DCF) Intelligence

**Web:** `2.4.0` · **VIE:** `0.2.0-discounted-cash-flow`

## Mission

First valuation method for the Valuation Intelligence Engine: **Discounted Cash Flow (FCFF primary)**. Evidence-backed assumptions, deterministic forecasts, sensitivity, explainability. **Overall Valuation remains DISABLED.**

## Location

`apps/web/src/lib/valuation/` — independent of MIE / EMI / EQI.

## Modules

| File | Role |
|------|------|
| `discountedCashFlowModels.ts` | FCFF assumptions · forecast · EV / equity / IV · sensitivity · score · risks |
| `discountedCashFlowEvidence.ts` | Evidence mapping · index · repository helpers |
| `discountedCashFlowScoring.ts` | `DCF_METRIC_WEIGHTS` · FCFF math · sensitivity · risks |
| `discountedCashFlowBuilders.ts` | Analysis builders · healthy demo |
| `discountedCashFlowSelectors.ts` | Pure selectors + category score mapper |
| `discountedCashFlowValidators.ts` | Weights · forecast · sensitivity · serialization |
| `discountedCashFlowEngine.ts` | Facade · `mergeIntoValuationAnalysis` |

## Published weights (`DCF_METRIC_WEIGHTS` sum = 1.0)

| Metric | Weight |
|--------|--------|
| Revenue Growth Assumption | 0.09 |
| EBIT Margin Assumption | 0.09 |
| Tax Rate | 0.06 |
| Depreciation Assumption | 0.06 |
| Capital Expenditure | 0.08 |
| Working Capital Requirement | 0.08 |
| Free Cash Flow Growth | 0.10 |
| Discount Rate (WACC) | 0.12 |
| Terminal Growth Rate | 0.08 |
| Terminal Value Contribution | 0.08 |
| Forecast Period Quality | 0.08 |
| DCF Confidence | 0.08 |

## FCFF math

`FCFF = EBIT(1−t) + D&A − CapEx − ΔNWC`  
`TV = FCFF_n(1+g)/(WACC−g)` · `EV = Σ PV(FCFF) + PV(TV)` · `Equity = EV − netDebt`

FCFE: **structure only** (`enabled=false`).

## Forecast horizons

5 · 7 · 10 years (+ terminal value)

## Sensitivity cases

Base · Bull · Bear · Low WACC · High WACC · Low Growth · High Growth

## Public API

```ts
import { valuationEngine, discountedCashFlowEngine } from "@/lib/valuation";

const dcf = discountedCashFlowEngine.demo();
valuationEngine.applyDiscountedCashFlow(dcf);
valuationEngine.demoWithDCF();
valuationEngine.overallValuation(); // null
valuationEngine.info.overallValuationEnabled; // false
```

## Engine flags

- `discountedCashFlowScoringEnabled: true`
- `overallValuationEnabled: false`
- `finalScoringEnabled: false`

## Risks (healthy demo = 0)

Forecast · Terminal value dependence · Aggressive growth · Low cash flow visibility · Discount rate sensitivity · Working capital uncertainty · CapEx uncertainty

## Non-goals

Overall Valuation · Other method engines · FCFE compute · Chart UI · Research / MIE / EMI / EQI coupling

## Next

Sprint V1.3 — next method engine (e.g. Owner Earnings or Relative Valuation); overall remains disabled.
