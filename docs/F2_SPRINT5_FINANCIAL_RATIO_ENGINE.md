# F2.5 — Financial Ratio Engine

**Package:** `financial` **`0.5.0`** · **Domain payload:** `0.5.0-financial` · **Engine:** `0.5.0-ratios`

**Scope:** Canonical cross-statement financial ratios composed from Income / Balance / Cash Flow Intelligence.

**Mode:** Domain-only · **No forecasting · No valuation · No provider integrations · No market data · No `/api/v1` changes**

**Note:** Phase 1 Valuation Suite remains frozen. No git milestone until Phase 2 completes (through F2.7).

---

## Objective

Compose F2.2–F2.4 intelligence outputs into one standardized, explainable ratio analysis layer for Research, Risk, EQI, and Decision consumers.

---

## Package layout

```text
packages/financial/src/financial/intelligence/
  ratio_engine.py
  ratio_models.py
  ratio_validation.py
  ratio_explainability.py
```

## API

```python
from financial import FinancialEngine

engine = FinancialEngine()
analysis = engine.analyze_financial_ratios(statements)   # one period triad
analysis = engine.analyze_financial_ratios(snapshot)     # multi-period
```

Inputs: `FinancialStatements`, `FinancialSnapshot`, normalized dict, or a sequence of statements.

## Ratio families

| Family | Examples |
|---|---|
| Profitability | Gross/Op/EBIT/EBITDA/Net margins, ROA, ROE, ROCE, ROIC |
| Liquidity | Current, Quick, Cash, Working Capital Ratio |
| Leverage | D/E, D/A, Equity Ratio, Net Debt, Net Debt/EBITDA, Interest Coverage, Financial Leverage |
| Efficiency | Asset / Inventory / Receivable / Payable / WC / Fixed Asset Turnover |
| Cash flow | OCF Ratio/Margin, FCF Margin, Cash Conversion, Capex/OCF, Dividend & Debt Coverage, Cash Interest Coverage |
| Shareholder | BVPS, TBVPS, RE Ratio, Dividend Payout / Retention |
| Capital allocation | Capex discipline, dividend/buyback sustainability, debt reduction quality, composite score |

Each ratio includes value, benchmark class, trend, confidence, interpretation, risk notes, and full explainability.

## Next

**F2.6 — Trend & Time-Series Intelligence** — completed; see [F2_SPRINT6_TREND_INTELLIGENCE.md](F2_SPRINT6_TREND_INTELLIGENCE.md).

**Next:** F2.7 — Financial Statement Aggregator
