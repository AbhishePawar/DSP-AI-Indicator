# Epic EQ1.0 Sprint EQ1.2 — Earnings Sustainability Intelligence

**Web:** `2.3.0` · **EQI:** `0.2.0-earnings-sustainability`

## Mission

Evaluate whether reported earnings are durable, repeatable, and high-quality. **Category score only** — Overall Earnings Quality Score remains disabled.

## Location

`apps/web/src/lib/earnings/` — independent of MIE and EMI.

## Modules

| File | Role |
|------|------|
| `earningsSustainabilityModels.ts` | Domain types |
| `earningsSustainabilityEvidence.ts` | Mapping / indexing |
| `earningsSustainabilityScoring.ts` | `EARNINGS_SUSTAINABILITY_METRIC_WEIGHTS` · risks |
| `earningsSustainabilityBuilders.ts` | Analysis + demo |
| `earningsSustainabilitySelectors.ts` | Selectors |
| `earningsSustainabilityValidators.ts` | Validation |
| `earningsSustainabilityEngine.ts` | Facade |

## Metrics (12)

Revenue Growth Consistency · EPS Growth Consistency · Operating Profit Stability · Net Profit Stability · Free Cash Flow Consistency · Earnings Volatility · Cyclicality of Earnings · One-time Income Dependence · Earnings Diversification · Long-term Earnings Trend · ROE Stability · Margin Stability

## Usage

```ts
import { earningsEngine } from "@/lib/earnings";

const eq = earningsEngine.demoWithScoredCategories();
earningsEngine.overallEarningsQuality(); // null
```

## Trust

- Published metric weights (sum = 1)
- Evidence-linked conclusions
- No Overall Earnings Quality Score · no AI opinions
