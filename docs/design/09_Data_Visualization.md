# 09 — Data Visualization

**System:** DSP AI Indicator Institutional Design System  
**Programme:** P9.0 · EPIC-001  
**Version:** 1.0.0  
**Status:** Approved  
**Upstream:** `docs/CHART_STANDARDS.md` (PR1.2)

---

## 1. Purpose

Charts and tables must inform honestly. Visualization never replaces explanation.

---

## 2. Ethics

1. Start axes honestly; do not crop to manufacture drama without disclosure.
2. Always caption: title + one-sentence interpretation.
3. Tooltip: value + plain-English meaning.
4. Never imply recommendation via chart color alone.
5. Show unavailable data as unavailable — never invent points.
6. Prefer fewer series; max three hues before pattern/dash.

---

## 3. Chart types (institutional defaults)

| Type | Preferred use |
|---|---|
| Line | Time series (price, metrics) |
| Bar | Comparisons across categories |
| Horizontal bar | Ranked lists / factors |
| Area | Cumulative or range bands (valuation ranges) |
| Scatter | Relationship exploration (rare; always explained) |
| Donut / pie | Avoid for research decisions; use only for simple composition with ≤5 slices |

Sparklines: only with accessible full chart alternative or text summary.

---

## 4. Color in charts

Use Color System series tokens.  
Positive/negative deltas: sign + text; patterns for colorblind safety.  
Dark theme: explicit series tokens (do not rely on CSS filter invert).

---

## 5. Tables as visualization

Tables are first-class data displays:

- Numeric alignment right/tabular
- Sticky header
- Sort/filter disclosed
- Row density modes
- Export affordance where policy allows

---

## 6. Valuation & risk visuals

| Visual | Rules |
|---|---|
| Valuation range | Show range + assumptions pointer; confidence label |
| Margin of safety | Distinguish RU risk meaning vs VC valuation expression in labels |
| Risk heat | Prefer ordered categorical labels; amber before danger red |
| Scenario fans | Label base/adverse/favorable; no false precision |

---

## 7. Dashboard widgets

Each chart widget includes:

1. Title  
2. Interpretation sentence  
3. Source / as-of  
4. Link to deeper analysis  

---

## 8. Report figures

Print-safe contrast; captions beneath; page-break avoid inside a figure when possible.

---

## 9. Do / Don’t

| Do | Don’t |
|---|---|
| Caption + interpretation | Naked axes |
| Token colors | Rainbow gradients |
| Disclose gaps | Interpolate silently |
| Text ratings nearby | Green/red “Buy/Sell” chart skins |
