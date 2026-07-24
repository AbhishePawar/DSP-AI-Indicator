# Epic EQ1.0 Sprint EQ1.5 — Working Capital Quality & Capital Allocation Quality Intelligence

**Web:** `2.3.0` · **EQI:** `0.5.0-workingcapital-capitalallocation`

## Mission

Evaluate whether working capital dynamics and capital allocation decisions support durable earnings quality. **Category scores only** — Overall Earnings Quality Score remains disabled.

## Modules

### Working Capital Quality (`working_capital_quality`)

| File | Role |
|------|------|
| `workingCapitalQualityModels.ts` | Domain types |
| `workingCapitalQualityEvidence.ts` | Mapping / indexing |
| `workingCapitalQualityScoring.ts` | `WORKING_CAPITAL_QUALITY_METRIC_WEIGHTS` · risks |
| `workingCapitalQualityBuilders.ts` | Analysis + demo |
| `workingCapitalQualitySelectors.ts` | Selectors |
| `workingCapitalQualityValidators.ts` | Validation |
| `workingCapitalQualityEngine.ts` | Facade |

### Capital Allocation Quality (`capital_allocation_quality`)

| File | Role |
|------|------|
| `capitalAllocationQualityModels.ts` | Domain types |
| `capitalAllocationQualityEvidence.ts` | Mapping / indexing |
| `capitalAllocationQualityScoring.ts` | `CAPITAL_ALLOCATION_QUALITY_METRIC_WEIGHTS` · risks |
| `capitalAllocationQualityBuilders.ts` | Analysis + demo |
| `capitalAllocationQualitySelectors.ts` | Selectors |
| `capitalAllocationQualityValidators.ts` | Validation |
| `capitalAllocationQualityEngine.ts` | Facade |

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
