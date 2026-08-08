# 13 — Responsive Guidelines

**System:** DSP AI Indicator Institutional Design System  
**Programme:** P9.0 · EPIC-001  
**Version:** 1.0.0  
**Status:** Approved  
**Upstream:** `docs/RESPONSIVE_GUIDELINES.md` (PR1.2)

---

## 1. Purpose

Define intentional breakpoints and mobile adaptation for all DSP surfaces.

---

## 2. Breakpoints

| Name | Min width | Intent |
|---|---|---|
| `xs` | 0 | Narrow phones |
| `sm` | 640px | Large phones / small tablets |
| `md` | 768px | Tablets |
| `lg` | 1024px | Laptops; dual-pane ok |
| `xl` | 1280px | Desktop workspace + rails |
| `2xl` | 1536px | Wide monitors; still respect 72rem content max |

Gutters: 16px below `lg`; 24px at `lg+`.

---

## 3. Adaptation patterns

| Pattern | Mobile | Desktop |
|---|---|---|
| Navigation | Menu sheet | Topbar + sidebar |
| Dashboard widgets | 1 column | 2–3 columns |
| Research TOC | Drawer | Fixed ~15rem |
| AI panel | Full-screen sheet | Docked 22–28rem |
| Tables | Horizontal scroll or stacked rows | Full table |
| Filters | Bottom sheet | Inline / side |
| Reports | Single column | Single column (max 72rem) |

---

## 4. Mobile-first rules

1. Design the stacked reading path first.  
2. Do not hide trust-critical labels to save space — abbreviate carefully.  
3. Keep primary investigation CTA reachable without horizontal pan.  
4. Touch targets ≥ 44×44px.  
5. Avoid hover-only affordances; provide tap equivalents.  
6. Sticky toolbars must not cover content permanently without dismiss/skip.

---

## 5. Surface-specific notes

### Website

Hero remains one composition; secondary sections stack cleanly. No multi-column hero on small screens.

### Dashboard

Priority: summary → primary widgets → secondary. Collapse customization panels into sheets.

### Research Workspace

Section order preserved; progressive disclosure for long analysis.

### Portfolio

Holdings usable via scroll; detail as sheet.

### Admin

Prefer tables with horizontal scroll over unusable shrink; expose critical actions as icon+label.

---

## 6. Orientation & safe areas

Respect `env(safe-area-inset-*)` on notched devices. Landscape: prefer usable charts with reduced chrome.

---

## 7. Do / Don’t

| Do | Don’t |
|---|---|
| Intentional collapse | Tiny desktop UI scaled down |
| Local table scroll | Whole-page horizontal trap |
| Sheet patterns for AI/nav | Hover-only mega-menus on touch |
