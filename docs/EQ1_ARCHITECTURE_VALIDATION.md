# EQI Architecture Validation — Earnings Quality Intelligence Engine

**Web:** `2.3.0` · **EQI:** `1.0.0`

## Architecture

```
earningsEngine (facade)
├── Category engines (EQ1.2–EQ1.6)
│   earningsSustainability · cashFlowQuality · accrualQuality
│   revenueQuality · expenseQuality · workingCapitalQuality
│   capitalAllocationQuality · accountingQuality
│   financialStatementIntegrity · earningsManipulation
├── overallEarningsAggregation (EQ1.7)
│   EARNINGS_CATEGORY_WEIGHTS → Overall Earnings Quality Score
├── earningsDashboardBuilders (EQ1.7)
│   summary · categories · gauge · contributions
│   evidence · confidence · risks · methodology · limitations
└── eqiProductionValidation / eqiPerformance (EQ1.8)
```

## Module boundaries

| Boundary | Rule |
|----------|------|
| Location | `apps/web/src/lib/earnings/` only |
| Frozen platforms | Decision · Research · KG · Portfolio · Risk · Valuation · MIE · EMI · Copilot · Reports · Compliance · API · Launch · Advisor |
| Category engines | Pure scoring; no Research Engine coupling |
| Overall score | Aggregates category outputs only — no metric recompute |
| Models | Immutable (`Object.freeze`) |
| Barrel | Tree-shakeable named exports via `index.ts` |

## Invariants

1. Category engines never collect Research Engine data directly.
2. Overall score consumes **category outputs only**.
3. Earnings Persistence and `overall_earnings_quality` shells remain unscored / excluded from `EARNINGS_CATEGORY_WEIGHTS`.
4. All conclusions maintain `conclusionEvidenceMap` evidence links.
5. Weights are published and normalizable; no hidden overrides.
6. EQ1.8 does not change category scoring algorithms or published weights.

## Weight publication

| Category | Weight |
|----------|--------|
| Earnings Sustainability | 0.15 |
| Cash Flow Quality | 0.15 |
| Accrual Quality | 0.12 |
| Revenue Quality | 0.10 |
| Expense Quality | 0.10 |
| Working Capital Quality | 0.10 |
| Capital Allocation Quality | 0.10 |
| Accounting Quality | 0.08 |
| Financial Statement Integrity | 0.05 |
| Earnings Manipulation Risk | 0.05 |
| **Sum** | **1.00** |

Missing categories → renormalize effective weights over present scored categories.

## Public API surface

- Facade: `earningsEngine` / `EarningsEngine`
- Release: `EQI_VERSION`, `ProductionReady`, `FeatureComplete`, `RegressionPassed`, `EQI_RELEASE`
- Overall: `EARNINGS_CATEGORY_WEIGHTS`, `buildOverallEarningsQuality`, `aggregateOverallEarningsQualityScore`
- Dashboard: `buildEarningsDashboard`, `validateEarningsDashboard`
- Certification: `runEqiProductionValidation`, `benchmarkEqiPipeline`

## Validation result

**PASS** — architecture consistent with EQ1.0 mission and production enablement rules.
