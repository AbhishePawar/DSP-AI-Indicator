# comparison

## 1. Package Purpose

Qualitative peer comparison engine (AIMF C2.5 + C3.7 evidence citations) — no rankings or scores

## 2. Responsibilities

- Provide the `comparison` domain façade for DSP AI Indicator.
- Expose stable public exports via `__all__`.
- Remain within architecture allowlists (ASI-003).

## 3. Package Status

**Production · Frozen**  
Version: **0.2.0**  
Canonical versions → [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

- Package version: `0.2.0`
- `ComparisonDimensionResult`
- `ComparisonError`
- `ComparisonEvidenceSummary`
- `ComparisonExplanation`
- `ComparisonLimitation`
- `ComparisonObservation`
- `ComparisonReport`
- `ComparisonRequest`
- `ComparisonResult`
- `ComparisonStatus`
- `QualitativeComparisonEngine`
- `compare_universe_result`

Import the package root only for public use unless tests intentionally exercise internals.

## 5. Package Structure

```
packages/comparison/
├── README.md
├── pyproject.toml (if present)
├── src/comparison/
│   └── …
└── tests/
```

## 6. Dependencies

Declared in `pyproject.toml`:

- `contracts`
- `core`
- `decision_intelligence`
- `universe`
- `industry`

## 7. Architecture Notes

- Feature freeze: do not add product behaviour under ASI documentation tasks.
- Forbidden imports are enforced by `tests/test_architecture.py` where present.
- Thin-client / platform rules → [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
from comparison import QualitativeComparisonEngine

# See package tests for worked examples against frozen façades.
_ = QualitativeComparisonEngine
```

## 9. Testing

```bash
pytest packages/comparison/tests -q --import-mode=importlib -p no:cov
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
