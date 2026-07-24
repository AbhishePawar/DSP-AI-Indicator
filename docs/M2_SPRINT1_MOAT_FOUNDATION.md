# Epic M2.0 Sprint M2.1 — Economic Moat Intelligence Foundation

**Web:** `2.2.0` · **EMI:** `0.1.0-foundation`

## Mission

Reusable foundation for the Economic Moat Intelligence Engine. **No category scoring. No Overall Moat Score. No Dashboard UI.**

## Location

`apps/web/src/lib/moat/` — independent of Management Intelligence Engine.

## Modules

| File | Role |
|------|------|
| `moatTypes.ts` | Core primitives |
| `moatConstants.ts` | Version · categories · defaults · trust |
| `moatModels.ts` | Domain aggregates |
| `moatEvidence.ts` | Evidence mapping · index · repository |
| `moatTimeline.ts` | Timeline lanes · events |
| `moatRisk.ts` | Risk factories · summaries |
| `moatBuilders.ts` | `buildMoatAnalysis` · `buildDemoMoat` |
| `moatSelectors.ts` | Pure selectors |
| `moatValidators.ts` | Structure · serialization |
| `moatUtilities.ts` | Format · normalize · version |
| `moatViewModels.ts` | ARIA-ready foundation cards |
| `moatEngine.ts` | Public facade |
| `index.ts` | Tree-shakeable barrel |

## Category shells (scoringEnabled=false)

Brand Strength · Network Effects · Switching Costs · Cost Advantage · Scale Advantage · Distribution Advantage · Intangible Assets · Regulatory Moat · Industry Structure · Competitive Position · Moat Sustainability · Overall Moat

## Public API

```ts
import { moatEngine } from "@/lib/moat";

const analysis = moatEngine.demo();
moatEngine.validate(analysis);
moatEngine.summary(analysis);
moatEngine.version(); // 0.1.0-foundation
moatEngine.overallMoatScore(); // null
```

## Non-goals

Any moat category scoring · Overall Moat Score · Dashboard/charts · Research/MIE/Decision integration · Persistence
