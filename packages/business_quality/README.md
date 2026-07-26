# business_quality

## 1. Package Purpose

Canonical Business Quality Intelligence for DSP AI Indicator (Phase 3)

## 2. Responsibilities

- Provide the `business_quality` domain façade for DSP AI Indicator.
- Expose stable public exports via `__all__`.
- Remain within architecture allowlists (ASI-003).

## 3. Package Status

**Production · Frozen** · Phase 3  
Version: **0.7.0**  
Canonical versions → [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

- Package version: `0.7.0`
- `BUSINESS_CHARACTERISTICS_DISCLAIMER`
- `BUSINESS_CHARACTERISTICS_VERSION`
- `BUSINESS_QUALITY_AGGREGATOR_DISCLAIMER`
- `BUSINESS_QUALITY_AGGREGATOR_VERSION`
- `BUSINESS_QUALITY_ENGINE_DISCLAIMER`
- `BUSINESS_QUALITY_ENGINE_VERSION`
- `BUSINESS_QUALITY_VERSION`
- `CAPITAL_ALLOCATION_DISCLAIMER`
- `CAPITAL_ALLOCATION_VERSION`
- `COMPETITIVE_POSITION_DISCLAIMER`
- `COMPETITIVE_POSITION_VERSION`
- `DEFAULT_BUSINESS_QUALITY_WEIGHTS`
- `EARNINGS_QUALITY_DISCLAIMER`
- `EARNINGS_QUALITY_VERSION`
- `FRAMEWORK_VERSION`
- `RESEARCH_DISCLAIMER`
- `AggregatedFlag`
- `AggregatedFlags`
- `Assessment`
- `BusinessCharacteristicsAnalysis`
- `BusinessCharacteristicsEngine`
- `BusinessCharacteristicsFlag`
- `BusinessCharacteristicsValidationError`
- `BusinessQualityAggregator`
- `BusinessQualityAnalysis`
- … and 66 more (see `__all__` in package `__init__.py`)

Import the package root only for public use unless tests intentionally exercise internals.

## 5. Package Structure

```
packages/business_quality/
├── README.md
├── pyproject.toml (if present)
├── src/business_quality/
│   └── …
└── tests/
```

## 6. Dependencies

Declared in `pyproject.toml`:

- `core`
- `financial`

## 7. Architecture Notes

- Feature freeze: do not add product behaviour under ASI documentation tasks.
- Forbidden imports are enforced by `tests/test_architecture.py` where present.
- Thin-client / platform rules → [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
from business_quality import BusinessCharacteristicsEngine

# See package tests for worked examples against frozen façades.
_ = BusinessCharacteristicsEngine
```

## 9. Testing

```bash
pytest packages/business_quality/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

- Ownership → [PACKAGE_OWNERSHIP_MATRIX.md](../../docs/PACKAGE_OWNERSHIP_MATRIX.md)
- Governance standard → [PACKAGE_GOVERNANCE.md](../../docs/PACKAGE_GOVERNANCE.md)
- ASI framework → [ASI_IMPLEMENTATION_FRAMEWORK.md](../../docs/ASI_IMPLEMENTATION_FRAMEWORK.md)

## 11. Limitations

- Documents **current** implementation only.
- Does not embed upstream report payloads or re-run foreign domain math.
- Not a substitute for epic freeze docs under `docs/`.

## 12. Future Extensions (future only)

Any new analytics, providers, or API shapes require an approved epic and ADR. **Not implemented in this package README.**
