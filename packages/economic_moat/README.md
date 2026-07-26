# economic_moat

## 1. Package Purpose

Economic Moat Intelligence engine for DSP AI Indicator — Buffett-aligned,
evidence-backed assessment of durable competitive advantage (FEATURE-001 Phase 1).

## 2. Responsibilities

- Evaluate six moat dimensions with explainable, rule-based scoring.
- Compose an overall moat score and ordinal rating (`no_moat` → `wide`).
- Accept only public `FinancialAnalysis` + `BusinessQualityAnalysis` inputs.
- Expose a stable public API via `__all__`.
- Remain within architecture allowlists (ASI-003).

## 3. Package Status

**Active · Phase 1 core analytics**  
Version: **0.2.0**  
Canonical versions → [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

- Package version: `0.2.0`
- `EconomicEngine` — `validate` / `analyze` / `explain`
- `EconomicAnalysis`, `MoatComponentScore`, `EconomicEvidence`, `EconomicScore`
- `MoatDimension`, `MoatRating`, `MoatWeights`, `DEFAULT_MOAT_WEIGHTS`
- `moat_rating_from_score`, `validate_weights`
- Exceptions / metadata / confidence / validation / explainability types

Import the package root only for public use unless tests intentionally exercise internals.

## 5. Package Structure

```
packages/economic_moat/
├── README.md
├── pyproject.toml
├── src/economic_moat/
│   ├── engine.py          # Public façade
│   ├── rules.py           # Dimension rule engine
│   ├── scoring.py         # Weights, ratings, helpers
│   ├── signals.py         # FA/BQ signal extraction
│   ├── models.py          # Domain models
│   ├── explainability.py
│   ├── validation.py
│   ├── metadata.py
│   └── exceptions.py
└── tests/
```

## 6. Dependencies

Declared in `pyproject.toml`:

- `core`
- `financial`
- `business_quality`

## 7. Architecture Notes

- Does **not** import `dsp_platform`, `economic` (macro), valuation, or peers.
- Forbidden imports enforced by `tests/test_architecture.py`.
- Not composed into `dsp_platform` in Phase 1 (platform allowlist unchanged).
- Web TypeScript EMI (`apps/web`) is a separate presentation stack.

## 8. Usage Examples

```python
from economic_moat import EconomicEngine

engine = EconomicEngine()
analysis = engine.analyze(financial_analysis, business_quality_analysis)
print(analysis.overall_moat_rating, analysis.score.value)
for component in analysis.components:
    print(component.dimension, component.score.value, component.reasoning)
```

## 9. Testing

```bash
pytest packages/economic_moat/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

- Ownership → [PACKAGE_OWNERSHIP_MATRIX.md](../../docs/PACKAGE_OWNERSHIP_MATRIX.md)
- FEATURE-001 → [FEATURE_001_ECONOMIC_MOAT.md](../../docs/FEATURE_001_ECONOMIC_MOAT.md)
- ADR → [adr/ADR-FEATURE-001-001-economic-moat-core.md](../../docs/adr/ADR-FEATURE-001-001-economic-moat-core.md)

## 11. Limitations

- Rule-based proxies only; no brand surveys, patent registries, or HHI.
- Network effects and efficient scale are intentionally confidence-capped.
- Research-only — not investment advice.
- Single-company FA/BQ inputs; no peer universe.

## 12. Future Extensions (future only)

- AI-assisted evidence enrichment (same contracts)
- Optional industry / IP / platform-telemetry providers (new ADR)
- Platform composition into `dsp_platform` (allowlist ADR required)
