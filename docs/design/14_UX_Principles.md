# 14 — UX Principles

**System:** DSP AI Indicator Institutional Design System  
**Programme:** P9.0 · EPIC-001  
**Version:** 1.0.0  
**Status:** Approved  
**Upstream:** Product Design Standard V2 · User Trust Standard · Research Mode  

---

## 1. Purpose

Define UX principles that every interface — website, dashboard, research, portfolio, reports, mobile, admin, AI panels — must satisfy.

---

## 2. Constitution priority (UX lens)

Trust → Correctness → Explainability → Consistency → Accessibility → Performance → Visual Polish → Feature Completeness

Never ship polish that reduces trust.

---

## 3. Four Questions (mandatory)

Every screen and every insight block must answer:

1. **What is happening?**  
2. **Why is it happening?**  
3. **Why should I care?**  
4. **What should I do next?** (investigation step)

Metric cards follow Product Design Standard V2 fields: Title · Rating · Value · Plain English · Why it matters · Takeaway.

---

## 4. Trust UX principles

| Principle | UX implication |
|---|---|
| Traceable | Source chip / source line on insights |
| Explainable | Four Questions visible or one tap away |
| Consistent | Same ratings, colors, order, VLIS tokens |
| Actionable | Next investigation always present |
| Honest | Epistemic category; no fabricated certainty |
| Transparent AI | Separate raw · calculated · AI · consensus · user |
| Research first | Research Mode labels unless flags unlock |

---

## 5. Interaction principles

1. **Summary first, details later** — progressive disclosure.  
2. **One primary action** per region.  
3. **Server decides** — UI presents frozen `/api/v1` outcomes; no client-side valuation/recommendation reasoning.  
4. **Empty is honest** — unavailable beats fake zeros.  
5. **AI is assistive** — oversight and disclosure always reachable.  
6. **Keyboard and touch parity** for critical paths.  
7. **Performance is UX** — skeletons over blank; virtualize long lists.

---

## 6. Research Mode UX

| Allowed | Forbidden (default) |
|---|---|
| Categorical research ratings | BUY / SELL / HOLD chrome |
| Watch / investigate language | Target price as advice chrome |
| Caution / High risk text | Red “Sell” styling as recommendation |
| Confidence labels | Hidden uncertainty |

When SEBI-gated flags unlock recommendation presentation, use Governance / Decision Framework vocabulary (GV/DF), still with disclosures.

---

## 7. Surface intents

| Surface | Primary job |
|---|---|
| Website | Brand + credible entry |
| Dashboard | Orient + route to work |
| Research Workspace | Deep analysis with trust |
| Portfolio | Multi-position monitoring context |
| Reports | Portable explained narrative |
| Mobile | Same jobs, stacked |
| Admin | Safe control density |
| AI Panels | Explain & challenge with citations |

---

## 8. Anti-patterns

- Tip-app urgency banners  
- Color-only decisions  
- Card-in-card nesting without need  
- Uncaptioned charts  
- Parallel glossaries fighting REP-002  
- Dashboard-first marketing heroes  

---

## 9. Definition of done (UX)

A view is not done until Four Questions, trust chips (where applicable), empty/loading/error, a11y keyboard pass, and Design System tokens are satisfied.
