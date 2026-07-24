# F2.4 — Cash Flow Intelligence

**Package:** `financial` **`0.4.0`** · **Domain payload:** `0.4.0-financial` · **Engine:** `0.4.0-cashflow`

**Scope:** Pure domain analysis of normalized `CashFlowStatement` series — operating / investing / financing / FCF, quality flags, trends, explainability.

**Mode:** Domain-only · **No forecasting · No valuation · No provider integrations · No market data · No `/api/v1` changes**

**Note:** Phase 1 Valuation Suite remains frozen. No git milestone until Phase 2 completes (through F2.7).

---

## Objective

Build analytical intelligence on top of the F2.1 Financial Data Domain so Research, Risk, EQI, and Decision modules can later consume standardized cash-flow insights.

---

## Package layout

```text
packages/financial/src/financial/intelligence/
  cashflow_engine.py
  cashflow_models.py
  cashflow_validation.py
  cashflow_explainability.py
```

## API

```python
from financial import FinancialEngine, CashFlowStatement

engine = FinancialEngine()
analysis = engine.analyze_cash_flow(cash_flow)      # single period
analysis = engine.analyze_cash_flow(snapshot)       # multi-period
analysis = engine.analyze_cash_flow(payload_dict)   # normalized JSON/dict
```

## Capabilities

| Area | Outputs |
|---|---|
| Operating | OCF, growth, earnings quality, conversion, stability, generation trend |
| Investing | Capex, intensity, acquisitions, activity, asset sales, discipline, growth class |
| Financing | Debt issue/repay, dividends, buybacks, issuance, dependence, allocation quality |
| Free cash flow | FCF (reported or OCF−|capex|), growth, margin (needs revenue), stability, owner-earnings placeholder, surplus |
| Quality | Operating / investment / financing quality; cash / dividend / buyback / debt sustainability |
| Flags | Strong/Weak Cash Generation, Negative FCF, Heavy Capex, Aggressive Debt Funding, Healthy Allocation, Shareholder Friendly, Warning, Excellent Cash Quality |
| Trends | OCF, FCF, Capital Allocation, Debt Activity → Improving / Stable / Weakening |

## Validation

Hard failures raise `CashFlowAnalysisError`:

- Missing OCF
- NaN / Infinity
- Invalid FCF vs OCF−|capex| inconsistency
- Duplicate periods

## Next

**F2.5 — Financial Ratio Engine** — completed; see [F2_SPRINT5_FINANCIAL_RATIO_ENGINE.md](F2_SPRINT5_FINANCIAL_RATIO_ENGINE.md).

**Next:** F2.6 — Trend & Time-Series Intelligence.
