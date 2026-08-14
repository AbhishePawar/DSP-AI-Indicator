# 10 — Motion Guidelines

**System:** DSP AI Indicator Institutional Design System  
**Programme:** P9.0 · EPIC-001  
**Version:** 1.0.0  
**Status:** Approved  
**Upstream:** `docs/ANIMATION_GUIDELINES.md` (PR1.2)

---

## 1. Purpose

Motion explains state changes. It never celebrates, distracts, or implies certainty.

---

## 2. Philosophy

| Principle | Meaning |
|---|---|
| Purposeful | Open/close, load, stream, expand |
| Short | 150–300ms typical |
| Calm easing | Standard ease-out |
| Interruptible | User actions cancel pending motion |
| Accessible | Honor `prefers-reduced-motion: reduce` |

Under reduced motion: instant transitions or opacity-only; no position/scale choreography.

---

## 3. Allowed motion catalogue

| Pattern | Duration | Notes |
|---|---|---|
| Fade in content | 150–200ms | Prefer for enter |
| Expand/collapse section | 200–300ms | Height + fade |
| Drawer / sheet enter | 200–300ms | From edge |
| Dropdown | 150ms | Opacity + slight Y |
| Skeleton shimmer | Optional | Pause under reduced-motion |
| AI stream token appear | Opacity | No bouncing |
| Toast enter/exit | 200ms | — |

---

## 4. Forbidden motion

- Confetti / success fireworks for research conclusions  
- Perpetual neon pulses on AI  
- Parallax noise in research workspace  
- Chart series that “race” to imply urgency  
- Multi-element staggered hero spam in authenticated tools  

Marketing surfaces may use 2–3 intentional motions for presence; research tools stay quieter.

---

## 5. Surface guidance

| Surface | Motion budget |
|---|---|
| Website | 2–3 intentional motions max in first experiences |
| Dashboard | Widget load fade; avoid constant animation |
| Research | Expand sections; chart draw optional & subtle |
| AI Panels | Streaming opacity only |
| Mobile | Prefer system sheet transitions |
| Reports | Minimal; print has none |

---

## 6. Performance

Prefer CSS transforms/opacity; avoid layout thrash; pause offscreen animations.

---

## 7. Certification hooks

UI Certification Checklist requires reduced-motion verification before PASS.
