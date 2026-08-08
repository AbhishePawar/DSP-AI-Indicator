# P2.2 — Institutional Explainability Framework

Status: **COMPLETE** · Frontend **v1.4.0** · Backend **unchanged**

## Architecture

Presentation-only expandable explainability over the existing Institutional Rating
Framework (`ModuleRating`). No pipeline, API, engine, valuation, recommendation,
or AI Committee changes. No score recalculation.

```
AnalyseResponse
  → mapResearchView
    → mapInstitutionalRatings (ARCH-002)
      → mapInstitutionalExplainability (P2.2)
        → InstitutionalRatingsSection / ExplainableRatingItem
```

Package: `apps/web/src/lib/explainability/`  
UI: `ExplainableRatingItem` accordion inside `InstitutionalRatingsSection`

## Rendering Rules

### Collapsed

Each rating shows:

- Score (`/10` remapped display from ARCH-002)
- Grade
- Confidence
- One-line summary (first sentence of existing module explanation, ≤28 words)

### Expanded

| Block | Source |
|---|---|
| Evidence | `ModuleRating.dimensions` (label/value) with `evidence` as `sourceField`; falls back to `ModuleRating.evidence` strings |
| Strengths | `ModuleRating.strengths` only — empty → `Unavailable` |
| Weaknesses | `ModuleRating.weaknesses` only — empty → `Unavailable` |
| Explanation | `ModuleRating.explanation`, truncated to ≤120 words |
| Traceability | Evidence rows + `sourceStages` attributed as source fields |

Accordion: Radix DS accordion — smooth open/close animation, keyboard focus ring,
`aria-expanded`, dark-mode tokens, responsive stacked layout.

## Traceability Model

Every displayed metric is a `TraceableMetric`:

```ts
{ label: string; value: string; sourceField: string }
```

`sourceField` is an existing attribution string from ARCH-002 (stage name,
dimension evidence path, or `sourceStages`). No derived formulas. No hidden
scoring. Client never invents numbers.

## Unavailable Rules

- Missing evidence / empty strengths / empty weaknesses → **Unavailable**
- Never estimate, never invent metrics or concerns
- Moat sub-dimensions already marked Unavailable by ARCH-002 remain Unavailable

## Exports

| Format | Content |
|---|---|
| JSON | Full `explainability` object |
| HTML | Explainability Framework section per module |
| CSV | Summary only: `explainabilityVersion`, `explainabilityModules` |
| Server PDF | Unchanged |

## Testing

`apps/web/src/lib/explainability/explainability.test.tsx`

- Word truncation (120)
- Missing-data → Unavailable
- Accordion expand/collapse + aria
- JSON / HTML / CSV export validation
- Regression via foundation version **1.4.0** suite
