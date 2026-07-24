# Epic EQ1.0 Sprint EQ1.7 — Earnings Quality Dashboard & Overall Earnings Quality Score

**Web:** `2.3.0` · **EQI:** `1.0.0`

## Mission

Enable the Overall Earnings Quality Score and Earnings Quality Dashboard by aggregating completed category outputs only. Category scoring engines are unchanged. Earnings Persistence remains an unscored foundation shell.

## Published Weights (`EARNINGS_CATEGORY_WEIGHTS`)

| Category | Weight |
|----------|--------|
| Earnings Sustainability | 15% |
| Cash Flow Quality | 15% |
| Accrual Quality | 12% |
| Revenue Quality | 10% |
| Expense Quality | 10% |
| Working Capital Quality | 10% |
| Capital Allocation Quality | 10% |
| Accounting Quality | 8% |
| Financial Statement Integrity | 5% |
| Earnings Manipulation Risk | 5% |
| **Sum** | **100%** |

Earnings Persistence is **excluded** until implemented.

## Modules

| File | Role |
|------|------|
| `overallEarningsModels.ts` | OverallEarningsQualityAnalysis / Score / Summary |
| `overallEarningsAggregation.ts` | `EARNINGS_CATEGORY_WEIGHTS` · aggregate |
| `overallEarningsBuilders.ts` | `buildOverallEarningsQuality` · apply |
| `overallEarningsSelectors.ts` | Selectors |
| `overallEarningsValidators.ts` | Weight / aggregation / evidence validation |
| `earningsDashboardModels.ts` | Dashboard panels |
| `earningsDashboardBuilders.ts` | `buildEarningsDashboard` · `buildDemoEarningsDashboard` |
| `earningsDashboardSelectors.ts` | Selectors |
| `earningsDashboardValidators.ts` | Completeness / serialization |

## Usage

```ts
import { earningsEngine, EARNINGS_CATEGORY_WEIGHTS } from "@/lib/earnings";

const { analysis, dashboard } = earningsEngine.demoComplete();
earningsEngine.overallEarningsQuality(analysis); // number
earningsEngine.validateDashboard(dashboard);
```

## Trust

- Published category weights only
- Every contribution traceable to category evidence
- Persistence shell excluded · no AI opinions · no category engine recomputation

## Next

EQ1.8 — production validation / readiness certification (mirrors EMI M2.8).

