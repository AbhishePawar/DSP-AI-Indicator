# Epic M1.0 Sprint M1.6 — Strategic Vision & Communication Intelligence

**Web:** `2.1.0` · **MIE:** `0.6.0-strategy-communication`

## Mission

Evaluate long-term strategic thinking and communication quality with objective evidence. **Category scores only** — overall Management Score remains disabled (`finalScoringEnabled=false`).

Maps to MIE categories `strategic_clarity` and `communication`. Also produces a **Combined Strategic Vision & Communication Score** (published blend of those two categories only — not an Overall Management Score).

## Modules

### Strategy (`strategic_clarity`)

| File | Role |
|------|------|
| `strategyModels.ts` | Domain types · StrategyTimeline |
| `strategyEvidence.ts` | Mapping / indexing |
| `strategyScoring.ts` | Metric · category · risks |
| `strategyBuilders.ts` | Analysis + demo + explainability |
| `strategySelectors.ts` | Selectors · ManagementScore map |
| `strategyValidators.ts` | Structural + evidence checks |
| `strategyEngine.ts` | Facade |

### Communication (`communication`)

| File | Role |
|------|------|
| `communicationModels.ts` | Domain types · CommunicationTimeline · combined score type |
| `communicationEvidence.ts` | Mapping / indexing |
| `communicationScoring.ts` | Metric · category · risks · combined blend |
| `communicationBuilders.ts` | Analysis + demo + explainability |
| `communicationSelectors.ts` | Selectors · ManagementScore map |
| `communicationValidators.ts` | Structural + evidence checks |
| `communicationEngine.ts` | Facade · `combineWithStrategy` |

## Usage

```ts
import {
  strategyEngine,
  communicationEngine,
  managementEngine,
} from "@/lib/management";

const strategy = strategyEngine.demo();
const communication = communicationEngine.demo();
const { analysis, combined } =
  managementEngine.applyStrategicVisionCommunication(strategy, communication);

managementEngine.overallManagementScore(); // null
combined.notes; // clarifies combined ≠ overall
```

## Trust

- Published `STRATEGY_METRIC_WEIGHTS` · `COMMUNICATION_METRIC_WEIGHTS` (each sum = 1)
- Combined uses `STRATEGY_COMMUNICATION_COMBINED_WEIGHTS` from category defaults
- Every conclusion links evidence ids
- No AI opinions · sentiment · hidden scoring · Overall Management Score

## Non-goals

Dashboard UI · Radar · Overall Management Score · Buffett View · Research/Report/Portfolio/Decision integration · Persistence · Auth
