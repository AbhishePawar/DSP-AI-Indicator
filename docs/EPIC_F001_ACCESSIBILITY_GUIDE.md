# EPIC-F001 — Accessibility Guide

Target: **WCAG AA**

| Requirement | Implementation |
|---|---|
| Keyboard navigation | Radix primitives + focus-visible rings |
| Focus states | `--accent` ring + offset `--bg` |
| Screen reader labels | `aria-label` on IconButton / ThemeSwitcher / Sidebar |
| High contrast | `prefers-contrast: more` token overrides |
| Reduced motion | `prefers-reduced-motion` disables animations |
| Empty / error honesty | EmptyState default copy; no fabricated metrics |

## Testing
Vitest + Testing Library cover render + theme switcher pressed state.
Manual keyboard checks recommended before F002 page wiring.
