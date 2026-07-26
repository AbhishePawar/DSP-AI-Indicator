# management_quality

## 1. Package Purpose

Management Quality & Capital Allocation Intelligence — Buffett/Munger-aligned,
evidence-backed assessment of management behaviour (FEATURE-002 Phase 1).

## 2. Responsibilities

- Evaluate six management dimensions with explainable, rule-based scoring.
- Compose an overall management score and ordinal rating (`poor` → `excellent`).
- Accept only public `FinancialAnalysis` + `BusinessQualityAnalysis` inputs.
- Expose a stable public API via `__all__`.
- Remain within architecture allowlists (ASI-003).

## 3. Package Status

**Active · Phase 1 core analytics**  
Version: **0.1.0**  
Canonical versions → [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

- Package version: `0.1.0`
- `ManagementEngine` — `validate` / `analyze` / `explain`
- `ManagementAnalysis`, `ManagementComponentScore`, `ManagementEvidence`
- `ManagementDimension`, `ManagementRating`, `ManagementWeights`
- `management_rating_from_score`, `validate_weights`

## 5. Package Structure

```
packages/management_quality/
├── README.md
├── pyproject.toml
├── src/management_quality/
│   ├── engine.py
│   ├── rules.py
│   ├── scoring.py
│   ├── signals.py
│   ├── models.py
│   ├── explainability.py
│   ├── validation.py
│   ├── metadata.py
│   └── exceptions.py
└── tests/
```

## 6. Dependencies

- `core`
- `financial`
- `business_quality`

## 7. Architecture Notes

- Does **not** import `dsp_platform`, API, frontend, or orchestration.
- Not composed into platform in Phase 1.
- Forbidden imports enforced by `tests/test_architecture.py`.
- Governance dimension is confidence- and score-capped without board data.

## 8. Usage Examples

```python
from management_quality import ManagementEngine

engine = ManagementEngine()
analysis = engine.analyze(financial_analysis, business_quality_analysis)
print(analysis.overall_management_rating, analysis.score.value)
for component in analysis.components:
    print(component.dimension, component.score.value)
```

## 9. Testing

```bash
pytest packages/management_quality/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

- [FEATURE_002_MANAGEMENT_QUALITY.md](../../docs/FEATURE_002_MANAGEMENT_QUALITY.md)
- [ADR-FEATURE-002-001](../../docs/adr/ADR-FEATURE-002-001-management-quality-core.md)

## 11. Limitations

- No board independence, promoter ownership, RPT, or auditor feeds.
- Guidance reliability and regulatory actions deferred.
- Research-only — not investment advice.

## 12. Future Extensions (future only)

- Governance / filings / compensation providers (new ADR)
- Platform composition into `dsp_platform` (allowlist ADR required)
- AI-assisted evidence enrichment (same contracts)
