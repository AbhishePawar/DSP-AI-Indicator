# portfolio

## 1. Package Purpose

DSP Portfolio models through monitoring (C4.1–C4.6)

## 2. Responsibilities

- Provide the `portfolio` domain façade for DSP AI Indicator.
- Expose stable public exports via `__all__`.
- Remain within architecture allowlists (ASI-003).

## 3. Package Status

**Production · Frozen**  
Version: **0.5.0**  
Canonical versions → [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

- Package version: `0.5.0`
- `ComparisonReportReference`
- `CoverageSummary`
- `DecisionPackReference`
- `Portfolio`
- `PortfolioAllocation`
- `PortfolioAnalysisContext`
- `PortfolioAnalysisResult`
- `PortfolioAnalysisStatus`
- `PortfolioAnalyzer`
- `PortfolioAssembler`
- `PortfolioAssemblyContext`
- `PortfolioAssemblyResult`
- `PortfolioAssemblyStatus`
- `PortfolioChange`
- `PortfolioChangeType`
- `PortfolioCitationAssembler`
- `PortfolioCitationContext`
- `PortfolioCitationResult`
- `PortfolioCitationStatus`
- `PortfolioCitationSummary`
- `PortfolioConstraint`
- `PortfolioConstraintKind`
- `PortfolioDescriptor`
- `PortfolioError`
- `PortfolioHolding`
- … and 13 more (see `__all__` in package `__init__.py`)

Import the package root only for public use unless tests intentionally exercise internals.

## 5. Package Structure

```
packages/portfolio/
├── README.md
├── pyproject.toml (if present)
├── src/portfolio/
│   └── …
└── tests/
```

## 6. Dependencies

Declared in `pyproject.toml`:

- `contracts`
- `core`
- `decision_intelligence`
- `industry`
- `comparison`
- `universe`

## 7. Architecture Notes

- Feature freeze: do not add product behaviour under ASI documentation tasks.
- Forbidden imports are enforced by `tests/test_architecture.py` where present.
- Thin-client / platform rules → [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
from portfolio import PortfolioAssembler

# See package tests for worked examples against frozen façades.
_ = PortfolioAssembler
```

## 9. Testing

```bash
pytest packages/portfolio/tests -q --import-mode=importlib -p no:cov
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
