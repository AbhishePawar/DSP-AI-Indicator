# Epic M1.0 Sprint M1.3 — Governance Intelligence

**Web:** `2.1.0`

## Mission

Evaluate corporate governance with objective indicators and disclosure evidence. **Category score only** — overall Management Score remains disabled.

## Modules

| File | Role |
|------|------|
| `governanceModels.ts` | Domain types |
| `governanceEvidence.ts` | Evidence mapping / indexing / traceability |
| `governanceScoring.ts` | Metric · evidence · confidence · category scores + risks |
| `governanceBuilders.ts` | Analysis builders + demo fixture |
| `governanceSelectors.ts` | Pure selectors + ManagementScore mapping |
| `governanceValidators.ts` | Structural validation |
| `governanceEngine.ts` | Facade |

## Usage

```ts
import { governanceEngine, managementEngine } from "@/lib/management";

const gov = governanceEngine.demo();
const mie = managementEngine.applyGovernance(gov);
```
