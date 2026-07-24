# EQI Release Notes — Earnings Quality Intelligence Engine 1.0.0

**Web:** `2.3.0` · **EQI:** `1.0.0` · **Date:** 2026-07-23 · **Epic:** EQ1.0 · **Sprint:** EQ1.8

## Highlights

Earnings Quality Intelligence is certified **production-ready**.

- Ten evidence-based category engines
- Overall Earnings Quality Score via published `EARNINGS_CATEGORY_WEIGHTS` (sum = 1.0)
- Earnings Quality Dashboard presentation models
- Full explainability (`conclusionEvidenceMap`, methodology, limitations)
- Deterministic, immutable, tree-shakeable TypeScript library under `apps/web/src/lib/earnings/`

## What this release does

- Certifies architecture, performance samples, explainability, and regression compatibility
- Publishes release metadata: `EQI_VERSION`, `ProductionReady`, `FeatureComplete`, `RegressionPassed`

## What this release does NOT do

- Does not change category scoring algorithms
- Does not change published category weights
- Does not change dashboard calculations
- Does not implement Earnings Persistence scoring
- Does not add chart rendering UI or Research Engine integration
- Does not modify Decision, Research, KG, Portfolio, Risk, Valuation, MIE, EMI, Copilot, Reports, Compliance, API, Launch Dashboard, or Advisor Platform

## Upgrade notes

```ts
import {
  earningsEngine,
  EQI_VERSION,
  ProductionReady,
  FeatureComplete,
  RegressionPassed,
  runEqiProductionValidation,
} from "@/lib/earnings";

console.assert(EQI_VERSION === "1.0.0");
console.assert(ProductionReady && FeatureComplete && RegressionPassed);
const report = runEqiProductionValidation();
console.assert(report.ok);
```

## Compatibility

- Backend pytest regression: **1551 passed** (GREEN)
- Independent of Management Intelligence Engine and Economic Moat Intelligence Engine
