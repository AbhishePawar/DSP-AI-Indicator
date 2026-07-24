# Financial Terminology Library

**Epic:** PR1.1 · PXB  
**Use:** Tooltips, Learn More drawers, Copilot grounding.

---

## 1. Term schema

| Field | Description |
|---|---|
| `id` | Stable key (`debt_to_equity`) |
| `term` | Display name |
| `definition` | Plain-English definition |
| `why_it_matters` | Investor relevance |
| `healthy_range` | Illustrative guidance — **not advice**; cite methodology later |
| `dsp_interpretation` | How DSP frames the term in Research Mode |
| `suggested_ai_questions` | Copilot starters |

---

## 2. Core terms (v1 library)

### debt_to_equity

| | |
|---|---|
| **Term** | Debt to Equity |
| **Definition** | How much debt the company uses compared with shareholders’ equity. |
| **Why it matters** | High leverage can amplify losses when business conditions worsen. |
| **Healthy range** | Industry-dependent; many non-financials are watched more carefully above ~1.0–1.5 (illustrative only). |
| **DSP interpretation** | Shown as Debt Level metric with peer context; Research Mode never labels “Sell” for high debt alone. |
| **AI questions** | What does this D/E mean for risk? · How does it compare to peers? · What cash flow covers the debt? |

### roic

| | |
|---|---|
| **Term** | Return on Invested Capital (ROIC) |
| **Definition** | How well the company turns invested capital into after-tax operating profit. |
| **Why it matters** | Persistently high ROIC often signals a durable advantage. |
| **Healthy range** | Often compared to cost of capital; above WACC is a common quality signal (illustrative). |
| **DSP interpretation** | Feeds Business Quality / capital efficiency narratives. |
| **AI questions** | Is ROIC durable? · What drives ROIC here? · How cyclical is it? |

### free_cash_flow

| | |
|---|---|
| **Term** | Free Cash Flow (FCF) |
| **Definition** | Cash left after operating needs and sustaining/growth capex (definition per methodology note). |
| **Why it matters** | Supports dividends, buybacks, debt paydown, and resilience. |
| **Healthy range** | Positive and stable relative to earnings is generally preferred; sector norms vary. |
| **DSP interpretation** | Financial Strength + Valuation context; volatility called out in Risk. |
| **AI questions** | How reliable is FCF? · What capex is discretionary? · Any working-capital traps? |

### intrinsic_value_range

| | |
|---|---|
| **Term** | Estimated Intrinsic Value Range |
| **Definition** | Model-based estimate band of business value under stated assumptions — **not** an Official Target Price in Research Mode. |
| **Why it matters** | Frames whether market price appears rich/cheap **relative to DSP assumptions**. |
| **Healthy range** | N/A — range width reflects uncertainty. |
| **DSP interpretation** | Labeled Estimated Intrinsic Value Range until SEBI `ShowTargetPrice` unlocks official wording. |
| **AI questions** | What assumptions drive the range? · What breaks the bull case? · How wide is uncertainty? |

### moat

| | |
|---|---|
| **Term** | Economic Moat / Competitive Advantage |
| **Definition** | Structural reasons a firm can sustain returns above competitors. |
| **Why it matters** | Moats support long-term Research Conclusions more than one-year noise. |
| **Healthy range** | Qualitative (wide / narrow / none) with evidence. |
| **DSP interpretation** | Competitive Advantage section + Decision Dashboard Moat field. |
| **AI questions** | What is the moat? · Is it eroding? · How do customers switch? |

### interest_coverage

| | |
|---|---|
| **Term** | Interest Coverage |
| **Definition** | Operating earnings relative to interest expense. |
| **Why it matters** | Thin coverage raises refinancing and downturn risk. |
| **Healthy range** | Higher is generally safer; thresholds are sector-specific (illustrative). |
| **DSP interpretation** | Financial Strength + Risk. |
| **AI questions** | Can they service debt in a downturn? · What is the maturity wall? |

### cagr

| | |
|---|---|
| **Term** | Compound Annual Growth Rate (CAGR) |
| **Definition** | Smoothed annualized growth between two points in time. |
| **Why it matters** | Summarizes growth without over-weighting a single year. |
| **Healthy range** | Context vs industry and cycle. |
| **DSP interpretation** | Growth section; always show period and base/end years. |
| **AI questions** | Is growth volume or price? · How cyclical? · Sustainable? |

### beta_context

| | |
|---|---|
| **Term** | Beta (market sensitivity) |
| **Definition** | Historical sensitivity of returns versus a market benchmark (when provided by quant context). |
| **Why it matters** | Helps set expectations for volatility — not a Buy/Sell signal alone. |
| **Healthy range** | Depends on investor temperament; DSP reports, does not prescribe. |
| **DSP interpretation** | Risk context; Suitable Investor field may reference volatility tolerance. |
| **AI questions** | What drives beta here? · How did it behave in past stress? |

### research_conclusion

| | |
|---|---|
| **Term** | Research Conclusion |
| **Definition** | DSP’s synthesized Investment Assessment in Research Mode (Attractive / Fairly Valued / Caution, etc.). |
| **Why it matters** | Anchors the page; always paired with AI Challenge Mode. |
| **Healthy range** | N/A |
| **DSP interpretation** | Not a SEBI recommendation until flags unlock. |
| **AI questions** | Why this conclusion? · What would flip it? · Strongest counterargument? |

### market_consensus

| | |
|---|---|
| **Term** | Market Analyst Consensus |
| **Definition** | Aggregated sell-side views (when providers connected). |
| **Why it matters** | Shows Street posture vs DSP View — disagreement is informative. |
| **Healthy range** | N/A |
| **DSP interpretation** | Separate from DSP intrinsic range; DSP vs Street section. |
| **AI questions** | Where do we disagree with Street? · How dispersed are targets? |

---

## 3. Extension process

1. Add term with full schema before shipping a metric that references it.  
2. Keep `healthy_range` explicitly **illustrative** + link methodology.  
3. Never embed Buy/Sell in definitions under Research Mode.  
