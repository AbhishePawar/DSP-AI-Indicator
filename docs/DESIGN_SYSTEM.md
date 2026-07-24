# Design System

**Epic:** PR1.1 · PXB  
**Implementation baseline:** `apps/web` (Fraunces + Sora, teal/slate tokens)  
**Principle:** Professional research tool — not tip-app chrome.

> **PR1.2 refinement:** For the frozen visual operating system (tokens, motion,
> component behaviour, charts, a11y, responsive, performance), see
> [PR1_2_VISUAL_LANGUAGE_AND_INTERACTION_SYSTEM.md](PR1_2_VISUAL_LANGUAGE_AND_INTERACTION_SYSTEM.md).
> This PR1.1 doc remains the PXB summary; VLIS is authoritative for visual detail.

---

## 1. Brand & voice

| Element | Spec |
|---|---|
| Primary tagline | Complex Analysis. Simple Decisions. |
| Secondary | Professional Investment Research for Everyone. |
| Tone | Calm, plain-English, evidence-first |
| Avoid | Hype, tip language in Research Mode, purple-glow AI clichés |

---

## 2. Typography

| Role | Font | Size scale (rem) | Weight |
|---|---|---|---|
| Display / brand | Fraunces (`--font-display`) | 1.5–2.5 | 500–600 |
| Page title | Fraunces | 1.875–2.25 | 500 |
| Section title | Fraunces | 1.25–1.5 | 500 |
| Body | Sora (`--font-body`) | 0.875–1 | 400 |
| Meta / labels | Sora | 0.75 | 500 |
| Code / raw API | ui-monospace | 0.75 | 400 |

Line length: prefer ≤ 72ch for explanatory copy.

---

## 3. Color tokens

Light / dark already defined in `globals.css`:

| Token | Role |
|---|---|
| `--bg` | Page background |
| `--fg` | Primary text |
| `--muted` | Secondary text |
| `--surface` / `--surface-2` | Cards / hover |
| `--border` | Dividers |
| `--accent` / `--accent-fg` / `--accent-soft` | CTA / active |
| `--danger-*` | Errors |

**Rating colors (semantic):**

| Rating band | Use |
|---|---|
| Attractive / Strong / Low risk | accent success soft |
| Fair / Medium | neutral surface-2 |
| Caution / High risk | warning amber (not tip-red for “Sell”) |
| Error / unavailable | danger |

---

## 4. Spacing & grid

| Token | Value |
|---|---|
| Space scale | 4 · 8 · 12 · 16 · 24 · 32 · 48 |
| Content max | 72rem (≈ `max-w-6xl`) |
| Dashboard grid | 1 / 2 / 3 cols (`sm` / `xl`) |
| Analysis | TOC 15rem + fluid main (desktop) |
| Gutter | 16px mobile · 24px desktop |

---

## 5. Components

### 5.1 Cards

- Border + surface; no heavy multi-shadow  
- Header optional title + description + action  
- Used for widgets and metric blocks  

### 5.2 Metric Cards

Schema: [METRIC_LIBRARY.md](METRIC_LIBRARY.md)  
Component target: `MetricCard`  
Always include Learn More + Ask AI affordances when data present.

### 5.3 Buttons

| Variant | Use |
|---|---|
| Primary | One primary action per view |
| Secondary | Alternate actions |
| Ghost | Toolbar / chrome |
| Danger | Destructive (logout confirm rare) |

Sizes: `sm` · `md` · `lg`. Focus ring = accent.

### 5.4 Forms

- Label above control  
- Helper text muted  
- Error via Alert tone danger  
- Date / symbol inputs with clear `aria-invalid`  

### 5.5 Tables

- Sticky header on long lists  
- Horizontal scroll on mobile  
- Empty → Empty State component  

### 5.6 Charts (spec only)

| Rule | Detail |
|---|---|
| Always caption | Chart title + one-sentence interpretation |
| Tooltip | Value + plain-English |
| Color | Token-based; pattern for colorblind |
| Empty | Empty State, never blank axes |

### 5.7 Badges

Neutral · success · warning · danger · accent — for ratings/status only.

### 5.8 Alerts

Info · success · warning · danger. Research Mode banner = info.

### 5.9 Empty / Loading / Skeletons

| State | Pattern |
|---|---|
| Empty | Title + description + optional CTA |
| Loading | Spinner with label OR skeleton matching layout |
| Partial | Skeleton remaining cards; show loaded ones |

### 5.10 Dark mode

`light` · `dark` · `system` via ThemeProvider. Same components; token swap only.

### 5.11 Accessibility

- Focus-visible rings on all controls  
- Contrast ≥ WCAG AA for text  
- Icon buttons need `aria-label`  
- Do not rely on color alone for ratings (text label required)  
- Prefer reduced-motion: respect `prefers-reduced-motion` for spins  

---

## 6. Layout primitives

Already in L1.1: AppLayout · Sidebar · Topbar · ContentArea · WidgetGrid · PageHeader · Breadcrumbs.

L1.2 adds: AnalysisTOC · SectionAnchor · CopilotRail · StickyDecisionSummary (optional).

---

## 7. Motion

Subtle only: sidebar width transition, drawer slide, accordion expand.  
No celebratory confetti; no stock-ticker noise.
