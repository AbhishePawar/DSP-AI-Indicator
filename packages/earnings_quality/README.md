# earnings_quality

## 1. Package Purpose

Earnings Quality & Predictability Intelligence — Buffett-aligned, evidence-backed
assessment of earnings quality, consistency, and sustainability (FEATURE-004 Phase 1).

## 2. Responsibilities

- Evaluate six earnings-quality dimensions with explainable scoring.
- Compose overall score and rating (`very_poor` → `excellent`).
- Accept only public `FinancialAnalysis` + `BusinessQualityAnalysis` inputs.
- Remain distinct from `business_quality.EarningsQualityEngine` (F3.2 module).

## 3. Package Status

**Active · Phase 1 core analytics** · Version **0.1.0**

## 4. Public API

- `EarningsQualityEngine` — `validate` / `analyze` / `explain`
- `EarningsQualityAnalysis`, component/evidence/score types
- `EarningsQualityDimension`, `EarningsQualityRating`, `EarningsQualityWeights`

## 5. Package Structure

```
packages/earnings_quality/
├── README.md · pyproject.toml
├── src/earnings_quality/ (engine, rules, scoring, models, …)
└── tests/
```

## 6. Dependencies

- `core` · `financial` · `business_quality`

## 7. Architecture Notes

- Not composed into platform / API / frontend / orchestration / AI Committee.
- Distinct import path: `from earnings_quality import EarningsQualityEngine`
- Restatement feeds and forward forecast models deferred.

## 8. Usage Examples

```python
from earnings_quality import EarningsQualityEngine

engine = EarningsQualityEngine()
analysis = engine.analyze(financial_analysis, business_quality_analysis)
print(analysis.overall_earnings_rating, analysis.score.value)
```

## 9. Testing

```bash
pytest packages/earnings_quality/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

- [FEATURE_004_EARNINGS_QUALITY.md](../../docs/FEATURE_004_EARNINGS_QUALITY.md)
- [ADR-FEATURE-004-001](../../docs/adr/ADR-FEATURE-004-001-earnings-quality-core.md)

## 11. Limitations

- No restatement registry / forensic audit
- Predictability is historical-stability based (not a forecast model)
- Research-only

## 12. Future Extensions

- Restatement / disclosure providers · forward estimate providers · platform composition
