# Product Design Standard V2

**Epic:** PR1.0  
**Applies to:** all web / mobile research surfaces

---

## Screen completeness test

Every screen must answer:

1. **What is happening?**  
2. **Why is it happening?**  
3. **Why should I care?**  
4. **What should I do next?**

---

## Metric card standard

Every metric uses this shape:

| Field | Purpose |
|---|---|
| Title | Named concept (e.g. Debt Level) |
| Rating | Categorical signal (e.g. HIGH) |
| Actual Value | Concrete figure / ratio |
| Plain-English Explanation | What this means |
| Why It Matters | Risk / opportunity context |
| Investor Takeaway | Practical next attention |

Example:

```text
Debt Level
HIGH
Debt to Equity 1.87
What this means: Company relies more on debt than many peers.
Why it matters: Higher debt increases financial risk during downturns.
Investor Takeaway: Monitor cash flow and debt servicing.
```

Implementation sketch: `apps/web` `MetricCard` · `compliance.metric_presentation`.

---

## Analysis page order

1. Company Snapshot  
2. Research Conclusion  
3. Executive Summary  
4. Market Analyst Consensus  
5. Business Quality  
6. Financial Strength  
7. Growth  
8. Valuation  
9. Risk Analysis  
10. Management  
11. Competitive Advantage  
12. Knowledge Graph  
13. AI Copilot  
14. AI Challenge Mode  
15. Evidence  
16. Export  

Canonical enum: `compliance.analysis_sections.ANALYSIS_PAGE_ORDER`.

---

## UX standards

- Summary first · details later  
- Every chart has interpretation  
- Every financial term has a tooltip  
- Every page has AI assistant entry  
- Progressive disclosure  
- Mobile first · Accessibility first  

See [USER_EXPERIENCE_GUIDELINES.md](USER_EXPERIENCE_GUIDELINES.md).

---

## Terminology

Research Mode forbids hard-coded BUY / SELL / HOLD / Target Price.
Use [RESEARCH_MODE.md](RESEARCH_MODE.md) mappings via `terminology.present_*`.
