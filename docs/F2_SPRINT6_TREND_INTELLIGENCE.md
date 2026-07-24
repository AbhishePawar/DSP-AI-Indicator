# F2.6 — Trend & Time-Series Intelligence

**Package:** `financial` **`0.6.0`** · **Domain payload:** `0.6.0-financial` · **Engine:** `0.6.0-trend`

**Scope:** Canonical multi-period trend layer composed from Income / Balance / Cash Flow / Ratio Intelligence.

**Mode:** Domain-only · **No forecasting · No valuation · No provider integrations · No market data · No `/api/v1` changes**

**Note:** Phase 1 Valuation Suite remains frozen. No git milestone until Phase 2 completes (through F2.7).

---

## Objective

Analyze ordered historical reporting periods to detect business direction, consistency, stability, and financial evolution — without duplicating F2.2–F2.5 line-item or ratio math.

---

## Package layout

```text
packages/financial/src/financial/intelligence/
  trend_engine.py
  trend_models.py
  trend_validation.py
  trend_explainability.py
```

## API

```python
from financial import FinancialEngine, FinancialStatementsHistory

engine = FinancialEngine()
analysis = engine.analyze_trends(history)     # FinancialStatementsHistory
analysis = engine.analyze_trends(snapshot)    # FinancialSnapshot (ordered)
analysis = engine.analyze_trends(statements)  # sequence of FinancialStatements
```

**Inputs:** `FinancialStatementsHistory`, ordered `FinancialSnapshot`, normalized dict, or sequence of statements.

**Minimum:** 2 periods · **Recommended:** 3–10 · **Maximum:** 20

## Families

| Family | Examples |
|---|---|
| Revenue | Growth, CAGR, consistency, acceleration, stability |
| Profitability | Gross / operating / net margins, EBIT, EBITDA, ROE, ROA, ROIC |
| Cash flow | OCF, FCF, conversion, Capex, dividends, stability |
| Balance sheet | Net debt, cash, equity, WC, assets, book value |
| Ratios | Liquidity, leverage, efficiency, profitability, capital allocation |
| Consistency | Consistency / volatility / stability / persistence / predictability |

## Classification

`strongly_improving` · `improving` · `stable` · `weakening` · `strongly_weakening` · `highly_volatile`

## Quality flags

Consistent Compounder · Improving / Deteriorating Business · Margin Expansion / Compression · Cash Flow Improving · Debt Increasing / Reducing · High Volatility · Stable Compound Growth

## Design rules

- Reuses F2.2–F2.5 engines per period; trend math (growth, CAGR, stability, flags) lives only here
- Deterministic · immutable models · shared explainability + validation
- Performance target: **&lt;40 ms** for a 10-period history (uninstrumented)

## Next

**F2.7 — Financial Statement Aggregator** — completed; see [F2_SPRINT7_FINANCIAL_AGGREGATOR.md](F2_SPRINT7_FINANCIAL_AGGREGATOR.md).

Phase 2 Financial Statement Intelligence (F2.1–F2.7) is complete.
