# financial_strength

## 1. Package Purpose

Financial Strength & Balance Sheet Quality Intelligence — Buffett-aligned,
evidence-backed assessment of fortress balance sheets and cash durability
(FEATURE-003 Phase 1).

## 2. Responsibilities

- Evaluate six financial-strength dimensions with explainable scoring.
- Compose overall score and rating (`very_weak` → `exceptional`).
- Accept only public `FinancialAnalysis` + `BusinessQualityAnalysis` inputs.
- Expose a stable public API via `__all__`.

## 3. Package Status

**Active · Phase 1 core analytics** · Version **0.1.0**

## 4. Public API

- `FinancialStrengthEngine` — `validate` / `analyze` / `explain`
- `FinancialStrengthAnalysis`, `FinancialStrengthComponentScore`, evidence/score types
- `FinancialStrengthDimension`, `FinancialStrengthRating`, `FinancialStrengthWeights`

## 5. Package Structure

```
packages/financial_strength/
├── README.md
├── pyproject.toml
├── src/financial_strength/
│   ├── engine.py · rules.py · scoring.py · signals.py
│   ├── models.py · explainability.py · validation.py
│   ├── metadata.py · exceptions.py
└── tests/
```

## 6. Dependencies

- `core` · `financial` · `business_quality`

## 7. Architecture Notes

- Not composed into `dsp_platform`, API, frontend, orchestration, or AI Committee.
- Debt maturity profiles and full stress histories are Phase 1 limitations.
- Forbidden imports enforced by architecture tests.

## 8. Usage Examples

```python
from financial_strength import FinancialStrengthEngine

engine = FinancialStrengthEngine()
analysis = engine.analyze(financial_analysis, business_quality_analysis)
print(analysis.overall_strength_rating, analysis.score.value)
```

## 9. Testing

```bash
pytest packages/financial_strength/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

- [FEATURE_003_FINANCIAL_STRENGTH.md](../../docs/FEATURE_003_FINANCIAL_STRENGTH.md)
- [ADR-FEATURE-003-001](../../docs/adr/ADR-FEATURE-003-001-financial-strength-core.md)

## 11. Limitations

- No debt maturity schedule / committed facilities
- Limited multi-cycle stress history
- Research-only — not a credit rating

## 12. Future Extensions

- Maturity / covenant / facility providers (new ADR)
- Platform composition (allowlist ADR required)
- AI evidence enrichment (same contracts)
