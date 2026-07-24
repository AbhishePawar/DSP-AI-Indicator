# F2.1 — Financial Data Domain & Canonical Models

**Package:** `financial` **`0.1.0`** · **Domain:** `0.1.0-financial`  

**Scope:** Canonical Income Statement, Balance Sheet, Cash Flow, Period, Metadata — models / validation / normalization / serialization only.

**Mode:** Domain-only · **No calculations · No ratios · No valuation integration**

**Note:** Phase 1 Valuation Suite remains stable and untouched. No git milestone until Phase 2 completes.

---

## Objective

Create the single source of truth for financial statements used by future Valuation, Moat, Management, Risk, Research, and Decision modules.

---

## Package

```text
packages/financial/src/financial/
  __init__.py
  models.py
  income_statement.py
  balance_sheet.py
  cash_flow.py
  period.py
  currency.py
  validation.py
  normalization.py
  metadata.py
  exceptions.py
  engine.py
```

## API

```python
from datetime import date
from financial import (
    FinancialEngine,
    FinancialPeriod,
    FinancialSnapshot,
    FinancialStatements,
    IncomeStatement,
    BalanceSheet,
    CashFlowStatement,
    PeriodType,
    UnitScale,
    statements_from_raw,
)

period = FinancialPeriod(
    period_type=PeriodType.ANNUAL,
    period_end=date(2024, 12, 31),
    fiscal_year=2024,
)

stmt = statements_from_raw(
    period=period,
    income={"Total Revenue": 1000, "Net Earnings": 120},
    balance={"total_assets": 5000, "total_liabilities": 2000, "total_equity": 3000},
    cash_flow={"CFO": 200, "fcf": 150},
)

snap = FinancialSnapshot(statements=(stmt,))
engine = FinancialEngine()
engine.validate(snap)
normalized = engine.normalize(snap, target_scale=UnitScale.ACTUAL)
payload = engine.serialize(normalized)
```

## Design rules

- Frozen, typed dataclasses
- Provider-agnostic aliases (no NSE/BSE/API code)
- Accounting-equation validation
- Unit-scale normalization (currency metadata retarget only — no FX in F2.1)
- Versioned JSON/dict payloads

## Next

**F2.2 — Income Statement Intelligence** (derived metrics / quality signals — still domain-only). Completed — see [F2_SPRINT2_INCOME_INTELLIGENCE.md](F2_SPRINT2_INCOME_INTELLIGENCE.md).

**Next:** F2.3 — Balance Sheet Intelligence.
