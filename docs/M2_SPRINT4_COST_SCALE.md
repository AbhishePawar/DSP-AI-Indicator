# Epic M2.0 Sprint M2.4 — Cost Advantage & Scale Advantage Intelligence

**Web:** `2.2.0` · **EMI:** `0.4.0-cost-scale`

## Mission

Evaluate durable cost leadership and economies of scale with objective evidence. **Category scores only** — Overall Moat Score remains disabled.

## Modules

### Cost Advantage (`cost_advantage`)

| File | Role |
|------|------|
| `costAdvantageModels.ts` | Domain types |
| `costAdvantageEvidence.ts` | Mapping / indexing |
| `costAdvantageScoring.ts` | `COST_ADVANTAGE_METRIC_WEIGHTS` · risks |
| `costAdvantageBuilders.ts` | Analysis + demo |
| `costAdvantageSelectors.ts` | Selectors |
| `costAdvantageValidators.ts` | Validation |
| `costAdvantageEngine.ts` | Facade |

### Scale Advantage (`scale_advantage`)

| File | Role |
|------|------|
| `scaleAdvantageModels.ts` | Domain types |
| `scaleAdvantageEvidence.ts` | Mapping / indexing |
| `scaleAdvantageScoring.ts` | `SCALE_ADVANTAGE_METRIC_WEIGHTS` · risks |
| `scaleAdvantageBuilders.ts` | Analysis + demo |
| `scaleAdvantageSelectors.ts` | Selectors |
| `scaleAdvantageValidators.ts` | Validation |
| `scaleAdvantageEngine.ts` | Facade |

## Usage

```ts
import { moatEngine } from "@/lib/moat";

const moat = moatEngine.demoWithScoredCategories();
moatEngine.overallMoatScore(); // null
```

## Trust

- Published metric weights (each category sum = 1)
- Evidence-linked conclusions
- No Overall Moat Score · no AI opinions
