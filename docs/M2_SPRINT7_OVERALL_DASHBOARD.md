# Epic M2.0 Sprint M2.7 — Economic Moat Dashboard & Overall Moat Score

**Web:** `2.2.0` · **EMI:** `1.0.0-emi-complete`

## Mission

Enable the Overall Moat Score and Economic Moat Dashboard by aggregating completed category outputs only. Category scoring engines are unchanged.

## Published Weights (`MOAT_CATEGORY_WEIGHTS`)

| Category | Weight |
|----------|--------|
| Brand Strength | 15% |
| Network Effects | 12% |
| Switching Costs | 10% |
| Cost Advantage | 10% |
| Scale Advantage | 8% |
| Intangible Assets | 10% |
| Regulatory Moat | 8% |
| Industry Structure | 10% |
| Competitive Position | 10% |
| Moat Sustainability | 7% |
| **Sum** | **100%** |

Distribution Advantage is **excluded** until implemented.

## Modules

| File | Role |
|------|------|
| `overallMoatModels.ts` | OverallMoatAnalysis / Score / Summary |
| `overallMoatAggregation.ts` | `MOAT_CATEGORY_WEIGHTS` · aggregate |
| `overallMoatBuilders.ts` | `buildOverallMoat` · `buildMoatSummary` · apply |
| `overallMoatSelectors.ts` | Selectors |
| `overallMoatValidators.ts` | Weight / aggregation / evidence validation |
| `moatDashboardModels.ts` | Dashboard panels |
| `moatDashboardBuilders.ts` | `buildMoatDashboard` |
| `moatDashboardSelectors.ts` | Selectors |
| `moatDashboardValidators.ts` | Completeness / serialization |

## Usage

```ts
import { moatEngine, MOAT_CATEGORY_WEIGHTS } from "@/lib/moat";

const { analysis, dashboard } = moatEngine.demoComplete();
moatEngine.overallMoatScore(analysis); // number
moatEngine.validateDashboard(dashboard);
```

## Trust

- Published category weights only
- Every contribution traceable to category evidence
- No AI opinions · no category engine recomputation
