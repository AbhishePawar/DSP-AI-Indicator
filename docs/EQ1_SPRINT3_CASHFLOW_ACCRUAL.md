# Epic EQ1.0 Sprint EQ1.3 — Cash Flow Quality & Accrual Quality Intelligence

**Web:** `2.3.0` · **EQI:** `0.3.0-cashflow-accrual`

## Mission

Evaluate whether earnings are backed by real cash generation and whether accruals are conservative. **Category scores only** — Overall Earnings Quality Score remains disabled.

## Modules

### Cash Flow Quality (`cash_conversion`)

| File | Role |
|------|------|
| `cashFlowQualityModels.ts` | Domain types |
| `cashFlowQualityEvidence.ts` | Mapping / indexing |
| `cashFlowQualityScoring.ts` | `CASH_FLOW_QUALITY_METRIC_WEIGHTS` · risks |
| `cashFlowQualityBuilders.ts` | Analysis + demo |
| `cashFlowQualitySelectors.ts` | Selectors |
| `cashFlowQualityValidators.ts` | Validation |
| `cashFlowQualityEngine.ts` | Facade |

### Accrual Quality (`accruals_quality`)

| File | Role |
|------|------|
| `accrualQualityModels.ts` | Domain types |
| `accrualQualityEvidence.ts` | Mapping / indexing |
| `accrualQualityScoring.ts` | `ACCRUAL_QUALITY_METRIC_WEIGHTS` · risks |
| `accrualQualityBuilders.ts` | Analysis + demo |
| `accrualQualitySelectors.ts` | Selectors |
| `accrualQualityValidators.ts` | Validation |
| `accrualQualityEngine.ts` | Facade |

## Usage

```ts
import { earningsEngine } from "@/lib/earnings";

const eq = earningsEngine.demoWithScoredCategories();
earningsEngine.overallEarningsQuality(); // null
```

## Trust

- Published metric weights (each category sum = 1)
- Evidence-linked conclusions
- No Overall Earnings Quality Score · no AI opinions
