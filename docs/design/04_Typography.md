# 04 — Typography

**System:** DSP AI Indicator Institutional Design System  
**Programme:** P9.0 · EPIC-001  
**Version:** 1.0.0  
**Status:** Approved  

---

## 1. Purpose

Define typographic hierarchy, pairing, and measure for institutional readability.

---

## 2. Font stack

| Role | Family | CSS token | Fallback |
|---|---|---|---|
| Display / brand / titles | Fraunces | `--font-display` | Georgia, serif |
| Body / UI / labels | Sora | `--font-body` | system-ui, sans-serif |
| Mono / evidence IDs | ui-monospace | `--font-mono` | ui-monospace, monospace |

**Pairing rule:** Fraunces for titles only; never set long body copy in display serif.

Avoid default AI stacks as brand: Inter, Roboto, Arial, system-only as primary brand type.

---

## 3. Hierarchy

| Level | Font | Size | Weight | Tracking | Use |
|---|---|---|---|---|---|
| Brand | Fraunces | 1.25–1.5rem | 500 | tight | Shell wordmark |
| Page title (h1) | Fraunces | 1.875–2.25rem | 500 | tight | Page identity |
| Section (h2) | Fraunces | 1.25–1.5rem | 500 | tight | Section heads |
| Subsection (h3) | Fraunces | 1.125rem | 500 | tight | Card / panel titles |
| Body | Sora | 0.875–1rem | 400 | normal | Explanations |
| Label | Sora | 0.75rem | 500 | optional wide | Field labels, “Why it matters” |
| Meta | Sora | 0.75rem | 400 | normal | Timestamps, breadcrumbs |
| Mono | Mono | 0.75rem | 400 | normal | API keys, evidence IDs |

---

## 4. Measure & leading

| Rule | Spec |
|---|---|
| Explanatory prose measure | ≤ 72ch |
| Body line-height | 1.5–1.65 |
| Title line-height | 1.2–1.3 |
| Paragraph spacing | Use spacing scale step 4–5 |

---

## 5. Numerics

| Context | Treatment |
|---|---|
| Metrics / prices | Tabular nums when available; consistent decimal policy per surface |
| Large KPIs | Sora medium/semibold; never ornamental display for dense tables |
| Delta values | Include sign + text color per Color System |

---

## 6. Research content typography

Four-question blocks and metric explanations use body + label hierarchy:

1. What — body  
2. Why — body  
3. Why care — body  
4. What next — body with clear affordance weight  

AI panel prose uses body; citations and source chips use meta / mono as appropriate.

---

## 7. Do / Don’t

| Do | Don’t |
|---|---|
| Clear title → body cascade | All-caps walls of UI |
| One display face for titles | Mixing three serifs |
| Readable research density | Ultra-thin weights for body |
| Consistent metric labeling | Decorative slogan fonts in workspace |
