# Phase G1.0 — Recommendation Intelligence Domain Models

**Status:** Implemented · Structure only · No assembler / engine / reporter  

**Package:** `packages/recommendation/` **0.1.0**  
**Freeze:** [G0.0A](G0_0A_RECOMMENDATION_ARCHITECTURE_FREEZE.md)

## Ownership

Recommendation owns **only**:

| Model | Role |
|---|---|
| `RecommendationIdentity` | Session identity |
| `RecommendationProfile` | Aggregate root |
| `RecommendationOption` | Action posture candidate |
| `RecommendationScore` | Transparent confidence (Decimal) |
| `RecommendationRationale` | Cite-backed explanation |
| `RecommendationConflict` | Declared upstream / option tension |
| `RecommendationSummary` | Counts / limitations |
| `RecommendationReport` | Immutable presentation snapshot |

Upstream Decision / Comparison / Portfolio / Risk / Research / Quantitative Risk
remain **reference-only**.

**Legacy:** Sprint 7.1 `RecommendationMapper` remains exported as a committee →
`contracts.Recommendation` adapter and is **not** the G domain engine.

## Reference models

| Reference | Cites |
|---|---|
| `DecisionReference` | DecisionPack |
| `ComparisonReference` | ComparisonReport |
| `PortfolioReference` | Portfolio |
| `RiskReference` | Qualitative RiskReport |
| `ResearchReference` | ResearchReport |
| `QuantitativeRiskReference` | QuantitativeRiskReport |

Citation keys use `kind:id` (e.g. `research:dsp.research.demo`) for option /
rationale / conflict report refs.

## Option contract

Every `RecommendationOption` requires: `option_id`, `option_type`, `title`,
`description`, `supporting_rationale_refs`, `supporting_report_refs`,
`confidence_reference` (score_id), `priority`.

## Score contract

Every `RecommendationScore` requires: `score_id`, `score_type`, Decimal `value`,
`unit`, `method_id`, non-empty `provenance`, `calculation_timestamp`.  
Optional `confidence_level`. Score never replaces rationale.

## Numeric policy

Scores use `decimal.Decimal` only. Floats rejected. No implicit rounding in
domain constructors.

## Validation rules

Duplicate options / scores / rationales / conflicts; broken rationale /
confidence / conflict / preferred-option links; unknown report citation keys;
missing provenance / method_id / unit; non-Decimal scores; immutable frozen
dataclasses.

## Extension guidance

- **G1.1** Assembler — **DONE** ([G1.1](G1_1_RECOMMENDATION_ASSEMBLER.md))
- **G1.2** Engine — option / conflict / confidence synthesis  
- **G1.3** Reporter  
- Optimizer / OMS / Workflow remain external consumers  

## Non-goals (this phase)

Synthesis, scoring algorithms, ranking, optimization, execution, trading,
workflow, persistence.
