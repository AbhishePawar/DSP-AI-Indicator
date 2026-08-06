# P2.3 — Institutional Valuation Transparency

Status: **COMPLETE** · Frontend **v1.5.0** · Backend **unchanged**

## Architecture

Presentation-only section that remaps existing analyse valuation signals,
`stage_summaries.valuation`, recommendation-stage verdict, and the ARCH-002
valuation module score/grade. No DCF / Reverse DCF / EPV / Residual Income /
Relative / Recommendation / Committee engine changes. No intrinsic-value math.

```
AnalyseResponse + AnalyseRequest.valuation_signals
  → mapResearchView
    → mapInstitutionalRatings (valuation module)
      → mapValuationTransparency (P2.3)
        → ValuationTransparencySection
```

Package: `apps/web/src/lib/valuation-transparency/`  
UI: `ValuationTransparencySection`  
Placement: immediately after **Institutional Ratings**, before Research /
Quality (financial analysis surfaces).

## Rendering Rules

### Executive Valuation Card

| Field | Source |
|---|---|
| Overall Valuation Score (/10) | `ratings.modules.valuation.scoreOutOf10` |
| Grade | `ratings.modules.valuation.grade` |
| Confidence | `valuation.confidence` |
| Current Market Price | `valuation.currentPrice` |
| Intrinsic Value | `valuation.intrinsicValue` |
| Margin of Safety | `valuation.marginOfSafety` |
| Valuation Verdict | `recommendationStage.label` |

### Valuation Method Cards

Eight named methods (DCF, Reverse DCF, Residual Income, EPV, Dividend Discount
Model, Asset Based Valuation, Relative Valuation, Cross Method Consensus).

- **Available** only when the existing `valuation.method` / stage label string
  matches that method (same honesty rule as ARCH-002).
- Intrinsic value / confidence shown only for Available matches.
- Weight, contribution, data completeness, assumptions → **Unavailable**
  (not on AnalyseResponse).
- Purpose sentences are static product copy, not calculated values.

### Consensus Panel

Highest / Lowest / Dispersion / Number of Methods Used → **Unavailable**
(never computed). Consensus Value only when Cross Method Consensus is
Available and an intrinsic value already exists.

### Margin of Safety Panel

Current price + MoS from existing fields. Valuation Category
(Deep Discount / Fairly Valued / …) → **Unavailable** (band not on API).

## Traceability

Every numeric display cites an existing ResearchView / rating / stage field via
`sourceField` on method cards. No frontend formulas. No inferred multi-method
statistics.

## Unavailable Rules

Absent → **Unavailable**. Never estimate weights, categories, dispersion, or
per-engine intrinsic values.

## Exports

| Format | Content |
|---|---|
| JSON | Full `valuationTransparency` |
| HTML | Valuation Transparency section |
| CSV | Summary: version, method count, verdict |
| Server PDF | Unchanged |

## Testing

`apps/web/src/lib/valuation-transparency/valuation-transparency.test.tsx`

- Render executive + method cards
- Unavailable handling (weights, categories, unmatched methods)
- Export validation
- Regression via foundation version **1.5.0**
