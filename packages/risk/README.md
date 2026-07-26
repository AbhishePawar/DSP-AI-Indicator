# risk

## 1. Package Purpose

DSP Risk Intelligence — qualitative assemble, analyze, report, integrate (E1.0–E1.4)

## 2. Responsibilities

- Provide the `risk` domain façade for DSP AI Indicator.
- Expose stable public exports via `__all__`.
- Remain within architecture allowlists (ASI-003).

## 3. Package Status

**Production · Frozen**  
Version: **0.5.0**  
Canonical versions → [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

- Package version: `0.5.0`
- `IntegratedRiskContext`
- `MonitoringReference`
- `PortfolioReference`
- `RiskAnalysisContext`
- `RiskAnalysisResult`
- `RiskAnalysisStatus`
- `RiskAnalyzer`
- `RiskAssembler`
- `RiskAssemblyContext`
- `RiskAssemblyResult`
- `RiskAssemblyStatus`
- `RiskAssessment`
- `RiskConstraint`
- `RiskConstraintKind`
- `RiskCoverage`
- `RiskCoverageKind`
- `RiskCoverageStatus`
- `RiskDescriptor`
- `RiskError`
- `RiskIdentity`
- `RiskIntegrationContext`
- `RiskIntegrationResult`
- `RiskIntegrationStatus`
- `RiskIntegrator`
- `RiskLevel`
- … and 8 more (see `__all__` in package `__init__.py`)

Import the package root only for public use unless tests intentionally exercise internals.

## 5. Package Structure

```
packages/risk/
├── README.md
├── pyproject.toml (if present)
├── src/risk/
│   └── …
└── tests/
```

## 6. Dependencies

Declared in `pyproject.toml`:

- `core`
- `portfolio`
- `industry`

## 7. Architecture Notes

- Feature freeze: do not add product behaviour under ASI documentation tasks.
- Forbidden imports are enforced by `tests/test_architecture.py` where present.
- Thin-client / platform rules → [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
from risk import RiskAssembler

# See package tests for worked examples against frozen façades.
_ = RiskAssembler
```

## 9. Testing

```bash
pytest packages/risk/tests -q --import-mode=importlib -p no:cov
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
