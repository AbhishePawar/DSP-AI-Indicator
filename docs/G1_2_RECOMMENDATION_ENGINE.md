# Phase G1.2 — Recommendation Engine

**Status:** Implemented · Cite-backed baseline synthesis · No primary analysis  

**Package:** `packages/recommendation/` **0.3.0**  
**Freeze:** [G0.0A](G0_0A_RECOMMENDATION_ARCHITECTURE_FREEZE.md)  
**Assembler:** [G1.1](G1_1_RECOMMENDATION_ASSEMBLER.md)

## Engine architecture

```text
AssemblyResult / RecommendationProfile
  + caller-declared SignalPosture overlays
        │
        ▼
RecommendationEngine.synthesize
        │
        ├── aggregate citation keys (provenance)
        ├── detect RecommendationConflict[]
        ├── select preferred + alternate RecommendationOption
        ├── assign RecommendationScore + ConfidenceLevel
        ├── write RecommendationRationale[] (cite-backed)
        ├── RecommendationSummary
        └── RecommendationReport (updated)
```

APIs: `RecommendationEngine`, `EngineContext`, `EngineResult`, `EngineStatus`,
`SignalPosture`.

Method id: `dsp.recommendation.method.baseline_rules.v1`

## Decision flow

1. Validate assembled refs (Decision, Comparison, Portfolio, Risk, Research, Quant).  
2. Aggregate opaque citation keys from refs.  
3. Detect explicit conflicts from declared postures.  
4. Select preferred + alternate option types by transparent rules.  
5. Assign confidence from agreement / conflict / coverage / consistency.  
6. Emit rationales that restate postures + conflict titles + citations.  
7. Populate summary and updated report / profile.

## Conflict policy

| Pattern | Severity | Typical preferred |
|---|---|---|
| Qualitative SUPPORTIVE vs Quant ADVERSE/CAUTIONARY | HIGH | HOLD (alt REDUCE) |
| Valuation SUPPORTIVE vs portfolio fit ADVERSE/CAUTIONARY | MEDIUM | WATCH (alt HOLD) |
| ≥2 UNKNOWN postures | HIGH | INSUFFICIENT_EVIDENCE (alt WATCH) |

Conflicts are first-class `RecommendationConflict` objects with report + option refs.

## Confidence policy

Reflects **evidence agreement**, **conflict severity**, **coverage completeness**,
and **consistency** — **not** market prediction.

| Condition | Level | Decimal |
|---|---|---|
| HIGH conflict or ≥2 UNKNOWN | LOW | 0.35 |
| MEDIUM conflict or 1 UNKNOWN | MEDIUM | 0.55 |
| Full coverage, mixed known postures | HIGH | 0.75 |
| Full coverage + full agreement | VERY_HIGH | 0.90 |

## Evidence policy

- Every option and rationale must cite assembled report citation keys.  
- Signal postures are **caller-declared**, cite-backed overlays — engine never
  re-opens Decision / Risk / Research / Quant engines.  
- No hidden reasoning: rationale body enumerates postures and conflict titles.

## Validation rules

Missing rationales / citations; duplicate options / scores; broken report or
rationale refs; invalid confidence; orphan conflict option refs; profile vs
assembly identity mismatch; duplicate identities in `synthesize_many`.

## Future extension strategy

Additive methods / method_ids for richer posture taxonomies, Research gap
coupling, or Quant metric thresholds — only via freeze amendment. Optimizer,
OMS, LLM, and ML remain outside this package.

**Next:** [G1.3 Reporter](G1_3_RECOMMENDATION_REPORTER.md) — **DONE**.

## Non-goals (this phase)

Portfolio optimization, execution, trading, workflow, LLM reasoning, ML,
Monte Carlo, market forecasting, persistence, legacy mapper use.
