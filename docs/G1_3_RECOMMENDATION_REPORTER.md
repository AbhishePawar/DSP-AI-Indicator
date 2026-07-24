# Phase G1.3 — Recommendation Reporter

**Status:** Implemented · Presentation only · No synthesis  

**Package:** `packages/recommendation/` **0.4.0**  
**Freeze:** [G0.0A](G0_0A_RECOMMENDATION_ARCHITECTURE_FREEZE.md)  
**Engine:** [G1.2](G1_2_RECOMMENDATION_ENGINE.md)

## Reporter architecture

```text
RecommendationReport  ──┐
EngineResult.report   ──┼──► ReportingContext
                        │
                        ▼
            RecommendationReporter
                        │
                        ├── preferred + alternate options (pass-through)
                        ├── scores / rationales / conflicts
                        ├── CitationSection[]
                        ├── ReportMetadata + summary sections
                        ├── RecommendationReport (limitations append only)
                        └── ReportingResult
```

APIs: `RecommendationReporter`, `ReportingContext`, `ReportingResult`,
`ReportingStatus`, `ReportMetadata`, `CitationSection`.

## Presentation policy

| Responsibility | Behavior |
|---|---|
| Present options | Preserve engine ordering |
| Preferred / alternates | Split by `preferred_option_id` |
| Confidence | Pass-through `RecommendationScore` Decimal identity |
| Rationales / conflicts | Pass-through tuples |
| Citations | Group upstream refs into `CitationSection` |
| Summary / metadata | Counts + section keys + ids |

## Evidence presentation

Citation sections by kind: decision, comparison, portfolio, risk, research,
quantitative_risk — using opaque `kind:id` keys already on refs.

## Conflict presentation

Conflicts presented as-is with severity, option refs, and report refs —
never reinterpreted or resolved by the reporter.

## Validation rules

Missing report identity; engine↔report id mismatch; duplicate option ids /
summary sections; broken rationale / citation refs; missing score provenance /
method_id / unit; immutable outputs.

## Formatting policy

- Preserve all recommendation values and Decimal precision (object identity).  
- Preserve option ordering and citations / provenance.  
- Never recalculate, infer, or generate new recommendations.  
- May append a presentation-only limitations note.

## Future extension guidance

- Charts / UI adapters outside this package  
- Additional section keys additive without changing values  
- **G1.4** validation & freeze — **DONE** · see [G1.4](G1_4_RECOMMENDATION_VALIDATION_AND_FREEZE.md)  

## Non-goals (this phase)

Recommendation generation, confidence calculation, ranking, optimization,
trading, workflow, charts, persistence, LLM reasoning.
