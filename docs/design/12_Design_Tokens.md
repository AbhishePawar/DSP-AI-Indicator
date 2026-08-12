# 12 — Design Tokens

**System:** DSP AI Indicator Institutional Design System  
**Programme:** P9.0 · EPIC-001  
**Version:** 1.0.0  
**Status:** Approved  
**Implementation note:** Tokens are specified here for V2.x; this epic does not edit production CSS.

---

## 1. Purpose

Provide the canonical token catalogue for light and dark themes so engineering and design share one vocabulary.

---

## 2. Color tokens

### 2.1 Core (light)

```text
--bg: #f3efe6
--fg: #1c2421
--muted: #5c6b66
--surface: #fffdf8
--surface-2: #ebe4d6
--border: #d5ccbc
--accent: #0f6e56
--accent-fg: #f4fff9
--accent-soft: #d8f0e6
```

### 2.2 Core (dark)

```text
--bg: #101614
--fg: #e8f0ec
--muted: #9bb0a7
--surface: #18211e
--surface-2: #24302c
--border: #31433d
--accent: #3dba8f
--accent-fg: #06241a
--accent-soft: #1d3b32
```

### 2.3 Semantic

```text
--success: var(--accent)
--success-soft: var(--accent-soft)
--warning-fg-light: #7a5a12
--warning-bg-light: #f7ecd2
--warning-fg-dark: #e6d29a
--warning-bg-dark: #3a3218
--danger: <platform danger token>
--danger-fg: <on-danger text>
--info-border: var(--border)
--info-bg: var(--surface-2)
```

### 2.4 Chart

```text
--chart-1: var(--accent)
--chart-2-light: #3d5a80
--chart-2-dark: #8bb4d9
--chart-3-light: #6b5b4a
--chart-3-dark: #c4b5a5
```

### 2.5 Elevation & focus

```text
--focus-ring: var(--accent)
--focus-offset: var(--bg)
--shadow-sm: 0 8px 24px rgba(16,22,20,0.08)
--overlay-scrim: rgba(0,0,0,0.4)
--glow: teal ambient ≤18% (hero/shell wash only)
```

---

## 3. Typography tokens

```text
--font-display: Fraunces, Georgia, serif
--font-body: Sora, system-ui, sans-serif
--font-mono: ui-monospace, monospace

--text-brand: 1.25rem–1.5rem
--text-h1: 1.875rem–2.25rem
--text-h2: 1.25rem–1.5rem
--text-h3: 1.125rem
--text-body: 0.875rem–1rem
--text-label: 0.75rem
--text-meta: 0.75rem
--text-mono: 0.75rem

--weight-regular: 400
--weight-medium: 500
--weight-semibold: 600
```

---

## 4. Spacing tokens

```text
--space-1: 0.25rem   /* 4 */
--space-2: 0.5rem    /* 8 */
--space-3: 0.75rem   /* 12 */
--space-4: 1rem      /* 16 */
--space-5: 1.5rem    /* 24 */
--space-6: 2rem      /* 32 */
--space-7: 3rem      /* 48 */
--space-8: 4rem      /* 64 */
```

---

## 5. Radius & border

```text
--radius-control: 6px
--radius-panel: 8px
--radius-modal: 10px
--border-width: 1px
```

---

## 6. Layout tokens

```text
--content-max: 72rem
--gutter-mobile: 16px
--gutter-desktop: 24px
--toc-width: 15rem
--ai-panel-width: 24rem
--sidebar-width: 16rem
--sidebar-collapsed: 4rem
```

---

## 7. Motion tokens

```text
--duration-fast: 150ms
--duration-base: 200ms
--duration-slow: 300ms
--easing-standard: ease-out
```

---

## 8. Z-index scale

```text
--z-base: 0
--z-sticky: 100
--z-dropdown: 200
--z-overlay: 300
--z-modal: 400
--z-toast: 500
```

---

## 9. Governance

- New tokens require Design System update + CHANGELOG note in this folder’s future revisions.
- Do not introduce purple accent tokens.
- Semantic aliases must not redefine financial recommendation meaning.
