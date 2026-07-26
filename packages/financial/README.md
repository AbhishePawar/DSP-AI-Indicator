# financial

## 1. Package Purpose

Canonical Financial Statement Domain for DSP AI Indicator (Phase 2)

## 2. Responsibilities

- Provide the `financial` domain façade for DSP AI Indicator.
- Expose stable public exports via `__all__`.
- Remain within architecture allowlists (ASI-003).

## 3. Package Status

**Production · Frozen** · Phase 2  
Version: **0.7.0**  
Canonical versions → [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

- Package version: `0.7.0`
- `ACCOUNTING_STANDARDS`
- `AGGREGATOR_RESEARCH_DISCLAIMER`
- `BALANCE_RESEARCH_DISCLAIMER`
- `BALANCE_SHEET_FIELDS`
- `CASHFLOW_RESEARCH_DISCLAIMER`
- `CASH_FLOW_FIELDS`
- `FIELD_ALIASES`
- `FINANCIAL_VERSION`
- `INCOME_STATEMENT_FIELDS`
- `RATIO_RESEARCH_DISCLAIMER`
- `RESEARCH_DISCLAIMER`
- `TREND_RESEARCH_DISCLAIMER`
- `AccountingStandard`
- `AggregatedQualityFlag`
- `AssetMetrics`
- `BalanceAnalysisError`
- `BalanceAnalysisMetadata`
- `BalanceQualityFlag`
- `BalanceSheet`
- `BalanceSheetAnalysis`
- `BalanceSheetEngine`
- `BalanceTrendSummary`
- `BenchmarkClass`
- `CapitalAllocationMetrics`
- `CashFlowAnalysis`
- … and 82 more (see `__all__` in package `__init__.py`)

Import the package root only for public use unless tests intentionally exercise internals.

## 5. Package Structure

```
packages/financial/
├── README.md
├── pyproject.toml (if present)
├── src/financial/
│   └── …
└── tests/
```

## 6. Dependencies

Declared in `pyproject.toml`:

- `core`

## 7. Architecture Notes

- Feature freeze: do not add product behaviour under ASI documentation tasks.
- Forbidden imports are enforced by `tests/test_architecture.py` where present.
- Thin-client / platform rules → [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
from financial import BalanceSheetEngine

# See package tests for worked examples against frozen façades.
_ = BalanceSheetEngine
```

## 9. Testing

```bash
pytest packages/financial/tests -q --import-mode=importlib -p no:cov
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
