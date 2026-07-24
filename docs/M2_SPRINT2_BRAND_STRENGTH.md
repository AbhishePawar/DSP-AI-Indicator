# Epic M2.0 Sprint M2.2 — Brand Strength Intelligence

**Web:** `2.2.0` · **EMI:** `0.2.0-brand-strength`

## Mission

Evaluate durable brand-based competitive advantage with objective evidence. **Category score only** — Overall Moat Score remains disabled.

## Modules

| File | Role |
|------|------|
| `brandStrengthModels.ts` | Domain types |
| `brandStrengthEvidence.ts` | Mapping / indexing |
| `brandStrengthScoring.ts` | Metrics · category score · risks · `BRAND_STRENGTH_METRIC_WEIGHTS` |
| `brandStrengthBuilders.ts` | Analysis + demo + explainability |
| `brandStrengthSelectors.ts` | Selectors · MoatCategoryScore map |
| `brandStrengthValidators.ts` | Structure · weights · evidence |
| `brandStrengthEngine.ts` | Facade · merge into MoatAnalysis |

## Usage

```ts
import { moatEngine, brandStrengthEngine } from "@/lib/moat";

const brand = brandStrengthEngine.demo();
const moat = moatEngine.applyBrandStrength(brand);

brandStrengthEngine.info.scoringEnabled; // true
moatEngine.overallMoatScore(); // null
```

## Trust

- Published `BRAND_STRENGTH_METRIC_WEIGHTS` (sum = 1)
- Every conclusion links evidence ids
- No AI opinions · no Overall Moat Score
