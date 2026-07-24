# Epic M2.0 Sprint M2.6 — Industry Structure, Competitive Position & Moat Sustainability

**Web:** `2.2.0` · **EMI:** `0.6.0-industry-competitive-sustainability`

## Mission

Complete the analytical category layer of EMI with Industry Structure, Competitive Position, and Moat Sustainability. **Category scores only** — Overall Moat Score remains disabled until M2.7.

## Modules

### Industry Structure (`industry_structure`)

| File | Role |
|------|------|
| `industryStructureModels.ts` | Domain types |
| `industryStructureEvidence.ts` | Mapping / indexing |
| `industryStructureScoring.ts` | `INDUSTRY_STRUCTURE_METRIC_WEIGHTS` · risks |
| `industryStructureBuilders.ts` | Analysis + demo (Porter inversions) |
| `industryStructureSelectors.ts` | Selectors |
| `industryStructureValidators.ts` | Validation |
| `industryStructureEngine.ts` | Facade |

### Competitive Position (`competitive_position`)

| File | Role |
|------|------|
| `competitivePositionModels.ts` | Domain types |
| `competitivePositionEvidence.ts` | Mapping / indexing |
| `competitivePositionScoring.ts` | `COMPETITIVE_POSITION_METRIC_WEIGHTS` · risks |
| `competitivePositionBuilders.ts` | Analysis + demo |
| `competitivePositionSelectors.ts` | Selectors |
| `competitivePositionValidators.ts` | Validation |
| `competitivePositionEngine.ts` | Facade |

### Moat Sustainability (`moat_sustainability`)

| File | Role |
|------|------|
| `moatSustainabilityModels.ts` | Domain types |
| `moatSustainabilityEvidence.ts` | Mapping / indexing |
| `moatSustainabilityScoring.ts` | `MOAT_SUSTAINABILITY_METRIC_WEIGHTS` · risks |
| `moatSustainabilityBuilders.ts` | Analysis + demo |
| `moatSustainabilitySelectors.ts` | Selectors |
| `moatSustainabilityValidators.ts` | Validation |
| `moatSustainabilityEngine.ts` | Facade |

## Usage

```ts
import { moatEngine } from "@/lib/moat";

const moat = moatEngine.demoWithScoredCategories();
moatEngine.overallMoatScore(); // null — until M2.7
```

## Trust

- Published metric weights (each category sum = 1)
- Evidence-linked conclusions
- No Overall Moat Score · no AI opinions
- Distribution Advantage remains a shell until a later sprint (if scheduled)
