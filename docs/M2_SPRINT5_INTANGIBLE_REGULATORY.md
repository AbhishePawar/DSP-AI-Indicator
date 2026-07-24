# Epic M2.0 Sprint M2.5 — Intangible Assets & Regulatory Moat Intelligence

**Web:** `2.2.0` · **EMI:** `0.5.0-intangible-regulatory`

## Mission

Evaluate proprietary IP/intangible assets and regulatory barriers with objective evidence. **Category scores only** — Overall Moat Score remains disabled.

## Modules

### Intangible Assets (`intangible_assets`)

| File | Role |
|------|------|
| `intangibleAssetsModels.ts` | Domain types |
| `intangibleAssetsEvidence.ts` | Mapping / indexing |
| `intangibleAssetsScoring.ts` | `INTANGIBLE_ASSETS_METRIC_WEIGHTS` · risks |
| `intangibleAssetsBuilders.ts` | Analysis + demo |
| `intangibleAssetsSelectors.ts` | Selectors |
| `intangibleAssetsValidators.ts` | Validation |
| `intangibleAssetsEngine.ts` | Facade |

### Regulatory Moat (`regulatory_moat`)

| File | Role |
|------|------|
| `regulatoryMoatModels.ts` | Domain types |
| `regulatoryMoatEvidence.ts` | Mapping / indexing |
| `regulatoryMoatScoring.ts` | `REGULATORY_MOAT_METRIC_WEIGHTS` · risks |
| `regulatoryMoatBuilders.ts` | Analysis + demo |
| `regulatoryMoatSelectors.ts` | Selectors |
| `regulatoryMoatValidators.ts` | Validation |
| `regulatoryMoatEngine.ts` | Facade |

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
