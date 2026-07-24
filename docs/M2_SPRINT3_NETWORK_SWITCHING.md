# Epic M2.0 Sprint M2.3 — Network Effects & Switching Costs Intelligence

**Web:** `2.2.0` · **EMI:** `0.3.0-network-switching`

## Mission

Evaluate network-effect ecosystems and customer switching friction with objective evidence. **Category scores only** — Overall Moat Score remains disabled.

## Modules

### Network Effects (`network_effects`)

| File | Role |
|------|------|
| `networkEffectsModels.ts` | Domain types |
| `networkEffectsEvidence.ts` | Mapping / indexing |
| `networkEffectsScoring.ts` | `NETWORK_EFFECTS_METRIC_WEIGHTS` · risks |
| `networkEffectsBuilders.ts` | Analysis + demo |
| `networkEffectsSelectors.ts` | Selectors |
| `networkEffectsValidators.ts` | Validation |
| `networkEffectsEngine.ts` | Facade |

### Switching Costs (`switching_costs`)

| File | Role |
|------|------|
| `switchingCostsModels.ts` | Domain types |
| `switchingCostsEvidence.ts` | Mapping / indexing |
| `switchingCostsScoring.ts` | `SWITCHING_COSTS_METRIC_WEIGHTS` · risks |
| `switchingCostsBuilders.ts` | Analysis + demo |
| `switchingCostsSelectors.ts` | Selectors |
| `switchingCostsValidators.ts` | Validation |
| `switchingCostsEngine.ts` | Facade |

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
