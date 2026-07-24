# Responsive Guidelines

**Epic:** PR1.2 · VLIS  
**Principle:** No component may merely shrink — each breakpoint has **intentional** behaviour.

---

## 1. Breakpoints

| Name | Width | Intent |
|---|---|---|
| Mobile | `< 768px` | One column; drawer; sheets; accordion Analysis |
| Tablet | `768–1023px` | Collapsible sidebar; 1–2 columns; optional TOC |
| Desktop | `≥ 1024px` | Persistent sidebar; TOC + main; rails |

Aligns with [MOBILE_UX.md](MOBILE_UX.md).

---

## 2. Shell behaviour

| Element | Mobile | Tablet | Desktop |
|---|---|---|---|
| Sidebar | Hidden → drawer | Collapsible | Persistent / collapsible |
| Topbar | Menu + title + account | + collapse | + breadcrumbs full |
| Content width | Fluid 16px gutter | 24px gutter | max 72rem centered |
| Copilot | Bottom sheet | Collapsible rail | Right rail |
| TOC | Accordion headers | Optional left mini | Sticky left |

---

## 3. Component adaptations (mandatory)

| Component | Must not | Must do |
|---|---|---|
| Metric Card | Shrink typography unreadably | Stack fields; optional collapse Meaning+ |
| Decision Dashboard | Tiny 6-col score grid | Chip row → sheet details |
| Tables | Cramped columns | Horizontal scroll + sticky first col optional |
| Charts | Micro-legends overlapping | Legend above; fewer ticks |
| KG | Unusable mini-canvas | List-first; full-screen graph |
| Forms | Side-by-side squeezes | Single column |
| Quick Actions | 4 tiny buttons | 2×2 grid ≥ 44px |
| Nav labels | Icon-only without names | Visible labels in drawer |

---

## 4. Typography responsive

| Level | Mobile | Desktop |
|---|---|---|
| Page title | ~1.75rem | ~2.25rem |
| Section | ~1.25rem | ~1.5rem |
| Body | 0.875–1rem | 1rem |

Do not scale display font below readability to “fit.”

---

## 5. Touch vs pointer

- Mobile/tablet touch: tap tooltips, larger hit areas  
- Desktop pointer: hover previews allowed  
- Hybrid devices: support both; never hover-only critical actions  

---

## 6. Orientation

- Portrait primary for mobile Analysis  
- Landscape: allow two-pane Copilot only if height sufficient; else keep sheet  

---

## 7. Container queries (L1.2+ recommendation)

Prefer container queries for Metric Card / Dashboard widgets inside grids so behaviour follows **slot width**, not only viewport.

---

## 8. QA matrix

For each major screen verify:

| Check | M | T | D |
|---|---|---|---|
| Primary CTA reachable | ☐ | ☐ | ☐ |
| No horizontal page scroll (except tables/charts) | ☐ | ☐ | ☐ |
| Focus order sensible | ☐ | ☐ | ☐ |
| Four questions still answerable above fold or via summary | ☐ | ☐ | ☐ |
