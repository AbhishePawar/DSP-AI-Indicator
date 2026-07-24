# Company Analysis Blueprint

**Epic:** PR1.1 · PXB  
**Status:** FROZEN screen order for L1.2  
**Supersedes:** PR1.0 `analysis_sections` list for **UI** (align code in L1.2 kickoff)

---

## 1. Frozen order

| # | Section | Primary job |
|---|---|---|
| 1 | Company Snapshot | What business is this? |
| 2 | Research Conclusion | DSP View Investment Assessment |
| 3 | Executive Summary | Short narrative of the whole |
| 4 | Investment Thesis | Why the conclusion could be right |
| 5 | Business Quality | Quality of the enterprise |
| 6 | Financial Strength | Balance sheet / cash resilience |
| 7 | Growth | Growth engine & durability |
| 8 | Valuation | Intrinsic range & multiples context |
| 9 | Risk | What can go wrong |
| 10 | Management | Stewardship & incentives |
| 11 | Competitive Advantage | Moat evidence |
| 12 | Market Analyst Consensus | Street view (empty until providers) |
| 13 | DSP vs Street | Agreement / gap |
| 14 | AI Challenge Mode | Support · against · risks · assumptions · unknowns |
| 15 | Knowledge Graph | Relationship exploration |
| 16 | AI Copilot | Section-aware Q&A |
| 17 | Decision Dashboard | Score stack + suitability summary |
| 18 | Evidence | Citations & artifacts |
| 19 | Export | Download / share envelope |

---

## 2. Section contracts (minimum UX)

Each section must ship with:

- `h2` title + one-line purpose  
- Summary strip (2–3 bullets) before detail  
- Metric cards per [METRIC_LIBRARY.md](METRIC_LIBRARY.md)  
- Chart + interpretation when charts exist  
- Terminology tooltips  
- Copilot prompt chips ([AI_COPILOT_UX.md](AI_COPILOT_UX.md))  
- Four-question self-check  

---

## 3. Section notes

### Investment Thesis (new vs PR1.0)

Narrative block: bull pillars · key assumptions · falsifiers.  
Not a Buy recommendation — thesis behind Research Conclusion.

### Risk

Renamed from “Risk Analysis” for brevity; content includes qualitative + quant citations when API provides them.

### Decision Dashboard

Field freeze: [DECISION_DASHBOARD.md](DECISION_DASHBOARD.md).

### AI Challenge Mode

Mandatory before user treats conclusion as complete; see [AI_CHALLENGE_MODE.md](AI_CHALLENGE_MODE.md).

---

## 4. Chrome

- Desktop: sticky section TOC left  
- Mobile: accordion + progress  
- Persistent Research Mode banner (flag-gated)  
- FAB / bar: Ask AI  

---

## 5. Data rules

- All numbers from `/api/v1` envelopes  
- Missing → Empty / Skeleton — never invent  
- Research Mode terminology for conclusions & ranges  
