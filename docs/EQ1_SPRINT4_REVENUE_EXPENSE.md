# Epic EQ1.0 Sprint EQ1.4 — Revenue Quality & Expense Quality Intelligence

**Web:** `2.3.0` · **EQI:** `0.4.0-revenue-expense`

## Mission

Evaluate whether reported revenue and operating expenses reflect sustainable business economics. **Category scores only** — Overall Earnings Quality Score remains disabled.

## Modules

### Revenue Quality (`revenue_quality`)

| File | Role |
|------|------|
| `revenueQualityModels.ts` | Domain types |
| `revenueQualityEvidence.ts` | Mapping / indexing |
| `revenueQualityScoring.ts` | `REVENUE_QUALITY_METRIC_WEIGHTS` · risks |
| `revenueQualityBuilders.ts` | Analysis + demo |
| `revenueQualitySelectors.ts` | Selectors |
| `revenueQualityValidators.ts` | Validation |
| `revenueQualityEngine.ts` | Facade |

### Expense Quality (`expense_quality`)

| File | Role |
|------|------|
| `expenseQualityModels.ts` | Domain types |
| `expenseQualityEvidence.ts` | Mapping / indexing |
| `expenseQualityScoring.ts` | `EXPENSE_QUALITY_METRIC_WEIGHTS` · risks |
| `expenseQualityBuilders.ts` | Analysis + demo |
| `expenseQualitySelectors.ts` | Selectors |
| `expenseQualityValidators.ts` | Validation |
| `expenseQualityEngine.ts` | Facade |

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
