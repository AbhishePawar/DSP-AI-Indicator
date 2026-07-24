# Analyst Consensus UX

**Epic:** PR1.1 · PXB  
**Sections:** Market Analyst Consensus · DSP vs Street  
**Data:** Ports only today (`compliance.analyst_consensus`) — providers later.

---

## 1. Goals

- Show Street posture without turning DSP into a tip mirror.  
- Make disagreement between DSP View and Street visible and explainable.  
- Empty-state gracefully when no provider.

---

## 2. UX blocks — Market Analyst Consensus

| Block | Content | Interaction |
|---|---|---|
| **Consensus** | Aggregate rating + coverage count | Tooltip → terminology |
| **Distribution** | Rating distribution bars/pie | Hover counts |
| **Timeline** | Consensus rating over time | Range selector 1Y/3Y |
| **Target Changes** | Recent target revisions | Table + sparkline |
| **Rating Changes** | Up/down/maintains | Filter chips |
| **Bull vs Bear** | Narrative cards | Expand |
| **Market Agreement** | Dispersion / agreement score | Plain-English |
| **AI Summary** | Backend summary of Street | “Ask AI” refine |

Research Mode: Street “target” labeled carefully (e.g. “Street average target”) — distinct from DSP **Estimated Intrinsic Value Range**.

---

## 3. UX blocks — DSP vs Street

| Block | Content |
|---|---|
| DSP View | Research Conclusion label |
| Street Consensus | Mapped research-safe wording |
| Gap callout | Agree / Mild diverge / Strong diverge |
| Drivers | Top 3 reasons for gap (cite-backed when available) |
| AI Consensus Analysis | Challenge-aware comparison |

---

## 4. Wireframe (desktop)

```text
## Market Analyst Consensus
┌ Consensus chip ┐ ┌ Coverage n ┐ ┌ Agreement ┐
┌ Rating distribution chart + interpretation ──────────────┐
┌ Timeline ────────────────────────────────────────────────┐
┌ Target changes │ Rating changes ─────────────────────────┤
┌ Bull case ───────────────┬ Bear case ────────────────────┤
┌ AI Summary ──────────────────────────────────────────────┤

## DSP vs Street
┌ DSP View │ Street │ Gap │ AI Analysis │ [Challenge] ─────┤
```

---

## 5. Empty state copy

> Street consensus is not connected yet. DSP research continues without sell-side
> feeds. Intrinsic value range above is DSP’s model band — not a Street target.

---

## 6. Accessibility

- Charts have text summary table alternative.  
- Color + pattern for up/down revisions.  
- Timeline keyboard scrubbable.  
