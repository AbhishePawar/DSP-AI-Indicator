# EMI Architecture Validation — Economic Moat Intelligence Engine

**Web:** `2.2.0` · **EMI:** `1.0.0`

## Architecture

```
moatEngine (facade)
├── Category engines (M2.2–M2.6)
│   brandStrength · networkEffects · switchingCosts
│   costAdvantage · scaleAdvantage
│   intangibleAssets · regulatoryMoat
│   industryStructure · competitivePosition · moatSustainability
├── overallMoatAggregation (M2.7)
│   MOAT_CATEGORY_WEIGHTS → Overall Moat Score
├── moatDashboardBuilders (M2.7)
│   summary · categories · gauge · contributions
│   evidence · confidence · risks · methodology · limitations
└── emiProductionValidation / emiPerformance (M2.8)
```

## Module boundaries

| Boundary | Rule |
|----------|------|
| Location | `apps/web/src/lib/moat/` only |
| Frozen platforms | Decision · Research · KG · Portfolio · Risk · Valuation · MIE · Copilot · Reports · Compliance · API · Launch · Advisor |
| Category engines | Pure scoring; no Research Engine coupling |
| Overall score | Aggregates category outputs only — no metric recompute |
| Models | Immutable (`Object.freeze`) |
| Barrel | Tree-shakeable named exports via `index.ts` |

## Invariants

1. Category engines never collect Research Engine data directly.
2. Overall score consumes **category outputs only**.
3. Distribution Advantage and `overall_moat` shells remain unscored / excluded from `MOAT_CATEGORY_WEIGHTS`.
4. All conclusions maintain `conclusionEvidenceMap` evidence links.
5. Weights are published and normalizable; no hidden overrides.
6. M2.8 does not change category scoring algorithms or published weights.

## Weight publication

| Category | Weight |
|----------|--------|
| Brand Strength | 0.15 |
| Network Effects | 0.12 |
| Switching Costs | 0.10 |
| Cost Advantage | 0.10 |
| Scale Advantage | 0.08 |
| Intangible Assets | 0.10 |
| Regulatory Moat | 0.08 |
| Industry Structure | 0.10 |
| Competitive Position | 0.10 |
| Moat Sustainability | 0.07 |
| **Sum** | **1.00** |

Missing categories → renormalize effective weights over present scored categories.

## Public API surface

- Facade: `moatEngine` / `MoatEngine`
- Release: `EMI_VERSION`, `ProductionReady`, `FeatureComplete`, `EMI_RELEASE`
- Overall: `MOAT_CATEGORY_WEIGHTS`, `buildOverallMoat`, `aggregateOverallMoatScore`
- Dashboard: `buildMoatDashboard`, `validateMoatDashboard`
- Certification: `runEmiProductionValidation`, `benchmarkEmiPipeline`

## Validation result

**PASS** — architecture consistent with M2.0 mission and production enablement rules.
