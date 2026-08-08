# 06 — Spacing System

**System:** DSP AI Indicator Institutional Design System  
**Programme:** P9.0 · EPIC-001  
**Version:** 1.0.0  
**Status:** Approved  

---

## 1. Purpose

Define a single spacing scale so rhythm stays consistent across density modes and surfaces.

---

## 2. Scale

Base: **16px = 1rem**

| Step | px | rem | Common use |
|---|---|---|---|
| 0 | 0 | 0 | Reset |
| 1 | 4 | 0.25 | Icon gaps, hairline stacks |
| 2 | 8 | 0.5 | Compact stacks, inline gaps |
| 3 | 12 | 0.75 | Chip padding, tight lists |
| 4 | 16 | 1 | Default control inset |
| 5 | 24 | 1.5 | Card padding / section gap |
| 6 | 32 | 2 | Section separation |
| 7 | 48 | 3 | Page rhythm |
| 8 | 64 | 4 | Hero / auth breathing |

Tokens: `--space-1` … `--space-8` (see Design Tokens).

---

## 3. Density modes

| Mode | Where | Guidance |
|---|---|---|
| Comfortable | Marketing, onboarding, empty states | Prefer steps 5–7 |
| Default | Research, dashboard | Steps 4–6 |
| Compact | Admin tables, dense monitors | Steps 2–4; never below readable tap targets |

Touch targets remain ≥ 44×44px even in compact mode.

---

## 4. Component spacing recipes

| Component | Padding | Gap |
|---|---|---|
| Button | 8×16 (sm) · 10×16 (md) · 12×20 (lg) | — |
| Input | 8–12 vertical · 12 horizontal | — |
| Card | 24 | Header→body 16 |
| Metric card | 16–24 | Internal stack 8–12 |
| Table cell | 8–12 vertical | — |
| AI message | 12–16 | 8 between messages |
| Page section | — | 32–48 between sections |

---

## 5. Radius companion

Spacing pairs with radius (not a substitute for elevation):

| Element | Radius |
|---|---|
| Buttons, inputs, badges | 6px |
| Cards, panels, table wraps | 8px |
| Modals / sheets | 8–12px |
| Pills / fully round | Avoid by default |

---

## 6. Do / Don’t

| Do | Don’t |
|---|---|
| Use scale steps only | Magic numbers (13px, 27px) |
| Consistent card padding per surface | Alternating random insets |
| Increase space for decision-critical blocks | Cramped Four-Question answers |
