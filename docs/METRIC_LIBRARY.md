# Metric Explanation Library

**Epic:** PR1.1 · PXB  
**Schema frozen for all metrics in Analysis / Portfolio / Compare.**

---

## 1. Standard schema

Every metric explanation object:

| Field | Required | Description |
|---|---|---|
| `title` | yes | Human metric name |
| `rating` | yes | Categorical band (e.g. HIGH / MEDIUM / LOW / ATTRACTIVE) |
| `actual_value` | yes | Concrete number or short fact |
| `meaning` | yes | Plain-English “what this means” |
| `why_it_matters` | yes | Investor consequence |
| `investor_takeaway` | yes | What to watch / do next (non-tip) |
| `learn_more` | yes | Link key into Terminology Library or long-form note |
| `ai_prompts` | yes | 2–4 Copilot starter prompts for this metric |

Research Mode: ratings use research vocabulary (not Buy/Sell).

---

## 2. JSON shape (implementation contract for L1.2 UI)

```json
{
  "id": "debt_to_equity",
  "title": "Debt Level",
  "rating": "HIGH",
  "actual_value": "Debt to Equity 1.87",
  "meaning": "Company relies more on debt than many peers.",
  "why_it_matters": "Higher debt increases financial risk during downturns.",
  "investor_takeaway": "Monitor cash flow and debt servicing.",
  "learn_more": "term:debt_to_equity",
  "ai_prompts": [
    "Explain this company's debt in plain English",
    "What would make this debt level safer?",
    "How does this debt compare to peers?"
  ]
}
```

---

## 3. Starter catalog (representative — expand in L1.2)

### Business Quality

| id | title | example rating focus |
|---|---|---|
| `roic` | Return on Invested Capital | Capital efficiency |
| `gross_margin_trend` | Gross Margin Trend | Pricing / mix durability |
| `revenue_quality` | Revenue Quality | Recurring vs cyclical |

### Financial Strength

| id | title |
|---|---|
| `debt_to_equity` | Debt Level |
| `interest_coverage` | Interest Coverage |
| `current_ratio` | Liquidity |
| `fcf_stability` | Free Cash Flow Stability |

### Growth

| id | title |
|---|---|
| `revenue_cagr` | Revenue Growth |
| `eps_growth` | Earnings Growth |
| `reinvestment_rate` | Reinvestment Rate |

### Valuation

| id | title | Research Mode label notes |
|---|---|---|
| `intrinsic_range` | Estimated Intrinsic Value Range | Never “Target Price” unless SEBI flags |
| `earnings_multiple` | Earnings Multiple Context | Peer-relative |
| `cash_flow_yield` | Cash Flow Yield | |

### Risk

| id | title |
|---|---|
| `business_risk` | Business Risk |
| `financial_risk` | Financial Risk |
| `drawdown_context` | Historical Stress Context |

### Management / Moat

| id | title |
|---|---|
| `capital_allocation` | Capital Allocation |
| `moat_strength` | Competitive Advantage |
| `predictability` | Outcome Predictability |

---

## 4. Scoring display metrics (Decision Dashboard)

Scores use the same schema; `actual_value` may be `72/100` with meaning describing band.

See [DECISION_DASHBOARD.md](DECISION_DASHBOARD.md).

---

## 5. Authoring rules

1. Meaning ≤ 2 sentences.  
2. Takeaway is observational (“monitor…”, “compare…”), not order language.  
3. Always attach `learn_more` term id.  
4. Always attach ≥ 2 AI prompts.  
5. If data missing → Empty State, do not invent values in UI.  
