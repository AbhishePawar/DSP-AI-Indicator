# business_quality_aggregator

## 1. Package Purpose

Cross-domain Business Quality Aggregator — combines Economic Moat, Management
Quality, Financial Strength, Earnings Quality, and Growth Quality into one
explainable assessment (FEATURE-006 Phase 1).

**Distinct from** F3.7 `business_quality.BusinessQualityAggregator` (which only
packages an existing F3.6 `BusinessQualityAnalysis`).

## 2. Responsibilities

- Weighted aggregation of five public domain-engine outputs.
- Deterministic conflict resolution with explained penalties.
- Overall Business Quality Score / Rating with evidence and confidence.
- Cross-domain strengths, weaknesses, risks, and investment observations.

## 3. Package Status

**Active · Phase 1 cross-domain layer** · Version **0.1.0**

## 4. Public API

- `BusinessQualityAggregatorEngine` — `validate` / `analyze` / `analyze_from_inputs` / `explain`
- `BusinessQualityAggregation`, component/evidence/conflict types
- `AggregatorComponent`, `BusinessQualityAggregatorRating`, `BusinessQualityAggregatorWeights`

## 5. Package Structure

```
packages/business_quality_aggregator/
├── README.md · pyproject.toml
├── src/business_quality_aggregator/
│   (engine, adapters, conflicts, scoring, models, …)
└── tests/
```

## 6. Dependencies

- `core` · `financial` · `business_quality`
- `economic_moat` · `management_quality` · `financial_strength`
- `earnings_quality` · `growth_quality`

## 7. Architecture Notes

- Domain-layer only — not composed into platform / API / frontend / orchestration / AI Committee.
- No circular dependency with `business_quality` analytics modules beyond consuming public FA/BQ for the convenience path.
- Does not recalculate financial metrics owned by domain engines.

## 8. Aggregation & Weighting Methodology

| Engine | Default weight |
|---|---|
| Economic Moat | 25% |
| Management Quality | 20% |
| Financial Strength | 20% |
| Earnings Quality | 20% |
| Growth Quality | 15% |

Weights are configurable via `BusinessQualityAggregatorWeights` (must sum to 1.0).

**Ratings:** `<40` poor · `≥40` below_average · `≥55` average · `≥70` good · `≥80` excellent · `≥90` exceptional

## 9. Conflict Resolution Rules

Deterministic penalties (capped) when conflicting signals appear, e.g.:

- Strong moat + weak balance sheet
- Excellent management + weak earnings quality
- Strong growth + poor cash generation
- High profitability + weak capital allocation
- Strong strength + weak liquidity
- Outstanding growth + deteriorating margins

Each adjustment records rule id, engines, metrics, and reasoning.

## 10. Usage Examples

```python
from business_quality_aggregator import BusinessQualityAggregatorEngine

# Convenience: run five public engines then compose
result = BusinessQualityAggregatorEngine().analyze_from_inputs(fa, bq)

# Or compose precomputed public analyses
result = BusinessQualityAggregatorEngine().analyze(
    economic_moat=em,
    management_quality=mq,
    financial_strength=fs,
    earnings_quality=eq,
    growth_quality=gq,
)
print(result.overall_business_quality_rating, result.score.value)
```

## 11. Testing

```bash
pytest packages/business_quality_aggregator/tests -q --import-mode=importlib -p no:cov
```

## 12. Governance

- [FEATURE_006_BUSINESS_QUALITY_AGGREGATOR.md](../../docs/FEATURE_006_BUSINESS_QUALITY_AGGREGATOR.md)
- [ADR-FEATURE-006-001](../../docs/adr/ADR-FEATURE-006-001-business-quality-aggregator.md)

## 13. Limitations

- Conflict rules are heuristic; not a forecast or recommendation engine
- Does not replace F3.6/F3.7 BQ packaging layer
- Research-only

## 14. Future Extensions

- Additional conflict rules · configurable penalty schedules · platform composition (deferred)
