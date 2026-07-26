# growth_quality

## 1. Package Purpose

Growth Quality & Capital Reinvestment Intelligence — Buffett-aligned,
evidence-backed assessment of growth durability, reinvestment efficiency, and
capital-efficient expansion (FEATURE-005 Phase 1).

## 2. Responsibilities

- Evaluate six growth-quality dimensions with explainable scoring.
- Compose overall Growth Quality Score and rating (`very_weak` → `exceptional`).
- Accept only public `FinancialAnalysis` + `BusinessQualityAnalysis` inputs.
- Prefer sustainable compounding; do not reward leverage- or dilution-driven growth.

## 3. Package Status

**Active · Phase 1 core analytics** · Version **0.1.0**

## 4. Public API

- `GrowthQualityEngine` — `validate` / `analyze` / `explain`
- `GrowthQualityAnalysis`, component/evidence/score types
- `GrowthQualityDimension`, `GrowthQualityRating`, `GrowthQualityWeights`

## 5. Package Structure

```
packages/growth_quality/
├── README.md · pyproject.toml
├── src/growth_quality/ (engine, rules, scoring, models, …)
└── tests/
```

## 6. Dependencies

- `core` · `financial` · `business_quality`

## 7. Architecture Notes

- Not composed into platform / API / frontend / orchestration / AI Committee.
- Customer concentration and organic-vs-acquisition attribution feeds deferred.
- Growth risk score is inverted (higher = safer) with confidence capped without concentration data.

## 8. Usage Examples

```python
from growth_quality import GrowthQualityEngine

engine = GrowthQualityEngine()
analysis = engine.analyze(financial_analysis, business_quality_analysis)
print(analysis.overall_growth_rating, analysis.score.value)
```

## 9. Testing

```bash
pytest packages/growth_quality/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

- [FEATURE_005_GROWTH_QUALITY.md](../../docs/FEATURE_005_GROWTH_QUALITY.md)
- [ADR-FEATURE-005-001](../../docs/adr/ADR-FEATURE-005-001-growth-quality-core.md)

## 11. Limitations

- No customer concentration / market saturation registry
- Organic vs acquisition growth is proxied, not deal-attributed
- Research-only — not a growth forecast

## 12. Future Extensions

- Concentration / saturation providers · deal-attribution feeds · platform composition
