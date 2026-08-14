# 05 — Grid System

**System:** DSP AI Indicator Institutional Design System  
**Programme:** P9.0 · EPIC-001  
**Version:** 1.0.0  
**Status:** Approved  

---

## 1. Purpose

Define layout grids for dashboard, research, report, AI panel, and marketing compositions.

---

## 2. Foundations

| Token | Value |
|---|---|
| Content max width | 72rem |
| Gutter mobile | 16px |
| Gutter desktop | 24px |
| Column mental model | 4 / 8 / 12 responsive |
| Alignment | Left-aligned research content; centered only for auth/marketing heroes |

---

## 3. Breakpoint columns

| Breakpoint | Columns | Typical use |
|---|---|---|
| < 640px | 4 | Mobile stack |
| ≥ 640px | 8 | Tablet |
| ≥ 1024px | 12 | Desktop workspace |
| ≥ 1280px | 12 + optional rail | Dashboard / analysis with TOC |

Exact breakpoint tokens: see [13_Responsive_Guidelines.md](13_Responsive_Guidelines.md).

---

## 4. Surface layouts

### 4.1 Dashboard

| Zone | Grid behaviour |
|---|---|
| Shell | Topbar full width; sidebar collapsible |
| Main | 1 → 2 → 3 widget columns (`sm` / `xl`) |
| Widget | Span 1–2 columns; avoid nested card-in-card |

### 4.2 Research Workspace

| Zone | Spec |
|---|---|
| TOC / section nav | ~15rem fixed on desktop; drawer on mobile |
| Main analysis | Fluid remainder; single reading column for prose |
| Evidence / AI rail | Optional right rail ≥1280px; stacks below on smaller |

Preserve analysis section order from Product Design Standard V2.

### 4.3 Portfolio

| Zone | Spec |
|---|---|
| Summary strip | Full width, one composition |
| Holdings table | Full width with horizontal scroll on small screens |
| Detail drawer | Overlay / split ≥1024px |

### 4.4 Reports

| Zone | Spec |
|---|---|
| Print / PDF logical width | Prefer single column prose + full-width figures |
| Screen report | Max 72rem; charts captioned beneath |

### 4.5 AI Panels

| Zone | Spec |
|---|---|
| Docked panel | 22–28rem width desktop |
| Mobile | Full-screen sheet |
| Internal layout | Header · message stream · composer · disclosure footer |

### 4.6 Marketing / Website

First viewport: one composition — brand, one headline, one supporting sentence, one CTA group, one dominant visual plane. No stat strips or card grids in the hero.

### 4.7 Admin

Dense but bordered tables; 12-column forms with 6+6 paired fields on desktop; stacked on mobile.

---

## 5. Alignment rules

- Align text columns and metric columns consistently within a view.
- Do not center-align long research prose.
- Keep primary CTA alignment stable in toolbars.

---

## 6. Do / Don’t

| Do | Don’t |
|---|---|
| Intentional column spans | Random masonry for research |
| One primary reading path | Competing equal columns of equal noise |
| Collapse rails on small screens | Horizontal pan of entire workspace as default |
