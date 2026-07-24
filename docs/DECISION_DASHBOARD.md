# Decision Dashboard Blueprint

**Epic:** PR1.1 · PXB  
**Placement:** Company Analysis section **Decision Dashboard** (after Copilot, before Evidence)  
**Also:** May deep-link from sticky “Jump to Decision Dashboard” in TOC.

---

## 1. Purpose

One screen that answers the four questions for the whole company:

1. What is DSP’s overall Investment Assessment?  
2. Why (score stack + drivers)?  
3. Why care (opportunity / risk / suitability)?  
4. What next (horizon, monitor list, Challenge Mode link)?

Research Mode labels only — no Buy/Sell/Hold/Official Target Price.

---

## 2. Frozen fields

| Field | Type | Research Mode presentation | Notes |
|---|---|---|---|
| **Research Conclusion** | Enum-like label | Attractive / Fairly Valued / Caution / … | Via terminology map |
| **Estimated Intrinsic Value Range** | Range string | Low–High + currency | Not “Target Price” |
| **Business Score** | 0–100 + band | Metric card | |
| **Financial Score** | 0–100 + band | Metric card | |
| **Growth Score** | 0–100 + band | Metric card | |
| **Valuation Score** | 0–100 + band | Metric card | |
| **Risk Score** | 0–100 + band | Higher may mean more risk — label clearly | |
| **Management Score** | 0–100 + band | | |
| **Capital Allocation** | Rating + blurb | | |
| **Moat** | Rating + blurb | Wide / Narrow / None / Unclear | |
| **Predictability** | Rating + blurb | | |
| **Analyst Confidence** | Band | Street coverage confidence when available | Empty if no provider |
| **AI Confidence** | Band | Explainability / evidence completeness — not price prediction | |
| **Top Opportunity** | Short text | One primary upside theme | |
| **Biggest Risk** | Short text | One primary risk theme | |
| **Research Horizon** | Text | e.g. 12–36 months framing | Not a guarantee period |
| **Suitable Investor** | Text | Temperament / horizon fit — educational | |

All numeric scores still require Meaning / Why / Takeaway when expanded.

---

## 3. Layout (desktop)

```text
┌ Research Conclusion (DSP View)     Intrinsic Value Range     ┐
├──────────────────────────────────────────────────────────────┤
│ Score hex/row: Business Fin Growth Val Risk Mgmt             │
├────────────────────────────┬─────────────────────────────────┤
│ Capital Allocation · Moat  │ Predictability                  │
│ Analyst Conf · AI Conf     │                                 │
├────────────────────────────┴─────────────────────────────────┤
│ Top Opportunity          │ Biggest Risk                      │
│ Research Horizon         │ Suitable Investor                 │
├──────────────────────────────────────────────────────────────┤
│ [Open AI Challenge]  [Ask Copilot]  [View Evidence]          │
└──────────────────────────────────────────────────────────────┘
```

### Mobile

Single column; scores as compact chips → expand to Metric Cards; CTAs sticky bottom.

---

## 4. Empty / partial states

| Condition | UX |
|---|---|
| Scores missing | Skeleton chips + “Awaiting backend envelope” |
| No consensus | Analyst Confidence = Unavailable |
| Challenge not built | CTA disabled with explanation |

---

## 5. Flag behaviour

| Flag | Effect |
|---|---|
| Research Mode | DSP View labels; intrinsic range wording |
| ShowBuySell + SEBI | May show official action labels (future) |
| ShowTargetPrice + SEBI | May rename range to Official Target Price (future) |

---

## 6. Non-goals

- No client-side score math  
- No portfolio optimization  
- No order tickets  
