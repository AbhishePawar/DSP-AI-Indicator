# F2.3 — Balance Sheet Intelligence

**Package:** `financial` **`0.3.0`** · **Domain payload:** `0.3.0-financial` · **Engine:** `0.3.0-balance`

**Scope:** Pure domain analysis of normalized `BalanceSheet` series — liquidity, leverage, assets, liabilities, equity, working capital, quality flags, trends, explainability.

**Mode:** Domain-only · **No forecasting · No valuation · No provider integrations · No market data · No `/api/v1` changes**

**Note:** Phase 1 Valuation Suite remains frozen. No git milestone until Phase 2 completes (through F2.7).

---

## Objective

Build analytical intelligence on top of the F2.1 Financial Data Domain so Research, Moat, Risk, and Decision modules can later consume standardized balance-sheet insights.

---

## Package layout

```text
packages/financial/src/financial/intelligence/
  balance_engine.py
  balance_models.py
  balance_validation.py
  balance_explainability.py
```

## API

```python
from financial import FinancialEngine, BalanceSheet

engine = FinancialEngine()
analysis = engine.analyze_balance_sheet(balance)       # single period
analysis = engine.analyze_balance_sheet(snapshot)      # multi-period
analysis = engine.analyze_balance_sheet(payload_dict)  # normalized JSON/dict
```

Optional `history=` and `allow_negative_equity=` for growth context / insolvency research cases.

## Capabilities

| Area | Outputs |
|---|---|
| Liquidity | Current / Quick / Cash ratios, Working Capital, Net WC, WC trend |
| Leverage | D/E, D/A, Equity ratio, Net debt, Net D/E, capital structure summary |
| Assets | Composition, concentrations, goodwill %, intangibles %, quality score |
| Liabilities | Current/LT mix, debt structure, lease & deferred-tax exposure |
| Equity | Book / tangible book, RE ratio, treasury impact, equity growth, capital quality |
| Working capital & quality | Cash position, inventory efficiency, receivable dependence, strength composites |
| Flags | Strong/Weak Liquidity, Excessive Leverage, Conservative Capital, High Goodwill/Intangibles, WC Pressure, Strong/Weak Equity, Healthy / Warning |
| Trends | Liquidity, Leverage, Asset Quality, Capital Structure, Working Capital → Improving / Stable / Weakening |

## Validation

Hard failures raise `BalanceAnalysisError`:

- Missing / negative / zero total assets
- Negative equity (unless `allow_negative_equity=True`)
- Assets ≠ Liabilities + Equity
- Duplicate periods / NaN / Infinity

Reuses Financial Domain `validate_statements` when a full period triad is supplied.

## Next

**F2.4 — Cash Flow Intelligence** — completed; see [F2_SPRINT4_CASHFLOW_INTELLIGENCE.md](F2_SPRINT4_CASHFLOW_INTELLIGENCE.md).

**Next:** F2.5 — Financial Ratio Engine.
