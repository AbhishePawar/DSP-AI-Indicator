# Epic EQ1.0 Sprint EQ1.1 — Earnings Quality Intelligence Foundation

**Web:** `2.3.0` · **EQI:** `0.2.0-earnings-sustainability`

## Mission

Reusable foundation for the Earnings Quality Intelligence Engine. **Overall Earnings Quality Score DISABLED.** Category shells prepared; Earnings Sustainability scoring lands in EQ1.2 (same version stamp).

## Location

`apps/web/src/lib/earnings/` — independent of EMI / MIE packages.

## Modules

| File | Role |
|------|------|
| `earningsTypes.ts` | Core primitives |
| `earningsConstants.ts` | Version · categories · defaults · trust |
| `earningsModels.ts` | Domain aggregates |
| `earningsEvidence.ts` | Evidence mapping · index · repository |
| `earningsTimeline.ts` | Timeline lanes · events |
| `earningsRisk.ts` | Risk factories · summaries |
| `earningsBuilders.ts` | `buildEarningsAnalysis` · `buildDemoEarnings` |
| `earningsSelectors.ts` | Pure selectors |
| `earningsValidators.ts` | Structure · serialization |
| `earningsUtilities.ts` | Format · normalize · version |
| `earningsViewModels.ts` | ARIA-ready foundation cards |
| `earningsEngine.ts` | Public facade |
| `index.ts` | Tree-shakeable barrel |

## Category shells (scoringEnabled=false in foundation builder)

Earnings Sustainability · Accruals Quality · Cash Conversion · Earnings Persistence · Earnings Manipulation Risk · Accounting Conservatism · Earnings Transparency · Overall Earnings Quality

## Public API

```ts
import { earningsEngine } from "@/lib/earnings";

const analysis = earningsEngine.demo();
earningsEngine.validate(analysis);
earningsEngine.summary(analysis);
earningsEngine.version(); // 0.2.0-earnings-sustainability
earningsEngine.overallEarningsQuality(); // null
```

## Engine flags

- `overallEarningsQualityEnabled: false`
- `finalScoringEnabled: false`
- `earningsSustainabilityScoringEnabled: true` (wiring reserved for EQ1.2)

## Non-goals

Overall Earnings Quality aggregation · Non-sustainability category scoring · Dashboard/charts · Research/MIE/EMI/Decision integration · Persistence
