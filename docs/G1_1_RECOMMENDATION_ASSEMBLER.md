# Phase G1.1 — Recommendation Assembler

**Status:** Implemented · Construction / citations only · No synthesis  

**Package:** `packages/recommendation/` **0.2.0**  
**Freeze:** [G0.0A](G0_0A_RECOMMENDATION_ARCHITECTURE_FREEZE.md)  
**Models:** [G1.0](G1_0_RECOMMENDATION_DOMAIN_MODELS.md)

## Assembler responsibilities

| Does | Does not |
|---|---|
| Validate required upstream refs | Generate recommendation options |
| Normalize / preserve citations | Score / confidence calculation |
| Detect missing / duplicate refs | Trade-off or conflict analysis |
| Build deterministic profile + report skeleton | Ranking / optimization / trading |
| Preserve provenance via citation keys | Call legacy `RecommendationMapper` |

## Assembly pipeline

```text
AssemblyContext
  ├── RecommendationIdentity
  ├── DecisionReference[]
  ├── ComparisonReference[]
  ├── PortfolioReference
  ├── RiskReference[]
  ├── ResearchReference[]
  └── QuantitativeRiskReference[]
        │
        ▼
RecommendationAssembler.assemble
        │
        ├── RecommendationProfile  (empty options / scores / rationales / conflicts)
        ├── RecommendationReport   (skeleton + validated refs)
        ├── RecommendationSummary  (counts = 0 + assembly limitations)
        └── AssemblyResult (status + warnings)
```

## Reference validation

Requires **all** of: Decision, Comparison, Portfolio, Risk, Research,
Quantitative Risk. Rejects broken digests/ids, duplicate report references,
disagreeing Decision instrument symbols (foreign ownership), and duplicate
recommendation identities in `assemble_many`.

## Ownership boundaries

Assembler owns construction of Recommendation artifacts only. Upstream reports
remain cite-only. Engine (G1.2) owns synthesis of options / scores / rationales /
conflicts. Reporter (G1.3) owns presentation.

## Future engine handoff

Engine (G1.2) — **DONE** · see [G1.2](G1_2_RECOMMENDATION_ENGINE.md).
Consumes `AssemblyResult`, populates options / scores / rationales / conflicts.

## Non-goals (this phase)

Recommendation generation, scoring, confidence, trade-offs, conflicts, ranking,
optimization, trading, workflow, persistence.
