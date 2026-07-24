# EMI Release Notes — Economic Moat Intelligence Engine 1.0.0

**Web:** `2.2.0` · **EMI:** `1.0.0` · **Date:** 2026-07-23 · **Epic:** M2.0 · **Sprint:** M2.8

## Highlights

Economic Moat Intelligence is certified **production-ready**.

- Ten evidence-based category engines
- Overall Moat Score via published `MOAT_CATEGORY_WEIGHTS` (sum = 1.0)
- Economic Moat Dashboard presentation models
- Full explainability (`conclusionEvidenceMap`, methodology, limitations)
- Deterministic, immutable, tree-shakeable TypeScript library under `apps/web/src/lib/moat/`

## What this release does

- Certifies architecture, performance samples, explainability, and regression compatibility
- Publishes release metadata: `EMI_VERSION`, `ProductionReady`, `FeatureComplete`

## What this release does NOT do

- Does not change category scoring algorithms
- Does not change published category weights
- Does not implement Distribution Advantage scoring
- Does not add chart rendering UI or Research Engine integration
- Does not modify Decision, Research, KG, Portfolio, Risk, Valuation, MIE, Copilot, Reports, Compliance, API, Launch Dashboard, or Advisor Platform

## Upgrade notes

```ts
import {
  moatEngine,
  EMI_VERSION,
  ProductionReady,
  FeatureComplete,
  runEmiProductionValidation,
} from "@/lib/moat";

console.assert(EMI_VERSION === "1.0.0");
console.assert(ProductionReady && FeatureComplete);
const report = runEmiProductionValidation();
console.assert(report.ok);
```

## Compatibility

- Backend pytest regression: **1551 passed** (GREEN)
- Independent of Management Intelligence Engine (`1.0.0-mie-production`)
