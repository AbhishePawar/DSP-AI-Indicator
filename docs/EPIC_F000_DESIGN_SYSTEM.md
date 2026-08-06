# EPIC-F000 — Design System Freeze

Aligned to **PR1.2 Visual Language** (`docs/VISUAL_LANGUAGE.md`).

## Tokens

TypeScript: `apps/web/src/foundation/tokens/design-tokens.ts`  
CSS vars: `apps/web/src/app/globals.css`

| System | Tokens |
|---|---|
| Colour | bg, fg, muted, surface, accent (teal), semantic danger/warning |
| Typography | Fraunces (display) + Sora (body) |
| Spacing | 0–24 scale (rem) |
| Breakpoints | sm 640 · md 768 · lg 1024 · xl 1280 · 2xl 1536 |
| Radius / z-index | frozen scales |

## Rules

- No purple/magenta brand accents
- Calm institutional research desk — not tip-app neon
- Theme: light / dark / system (existing ThemeProvider; next-themes in F001)

## Component hierarchy

Foundations → primitives (shadcn F001) → patterns → domain → layouts  
See `foundation/components/hierarchy.ts`.
