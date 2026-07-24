# Epic M1.0 Sprint M1.2 — Capital Allocation Intelligence

**Web:** `2.1.0`

## Mission

Evaluate capital allocation quality with objective financial metrics and evidence. **Category score only** — overall Management Score remains disabled (`finalScoringEnabled=false`).

## Modules

| File | Role |
|------|------|
| `capitalAllocationModels.ts` | Domain types |
| `capitalAllocationEvidence.ts` | Evidence mapping / indexing / traceability |
| `capitalAllocationScoring.ts` | Metric · evidence · confidence · category scores + risks |
| `capitalAllocationBuilders.ts` | Analysis builders + demo fixture |
| `capitalAllocationSelectors.ts` | Pure selectors + ManagementScore mapping |
| `capitalAllocationValidators.ts` | Structural validation |
| `capitalAllocationEngine.ts` | Facade |

## Scoring

- Published weights in `CAPITAL_METRIC_WEIGHTS` (transparent)
- Category score 0–100 for `capital_allocation` only
- `overallManagementScore()` always returns `null`

## Non-goals

Dashboard UI · charts · overall Management Score · governance/execution/strategy modules · Research Engine changes

## Usage

```ts
import { capitalAllocationEngine, managementEngine } from "@/lib/management";

const ca = capitalAllocationEngine.demo();
const mie = managementEngine.applyCapitalAllocation(ca);
// mie.scores capital_allocation may be filled; finalize still disabled
```
