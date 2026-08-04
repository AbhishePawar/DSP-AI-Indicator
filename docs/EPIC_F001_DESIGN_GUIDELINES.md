# EPIC-F001 — Design Guidelines

## Identity
Calm institutional research desk — teal accent (`#0f6e56` / dark `#2cb67d`), Fraunces + Sora.
Never purple/magenta brand accents.

## Tokens
Defined in `globals.css` + `foundation/tokens`:
- Semantic: danger / warning / success / info
- Elevation 0–3 · radius sm–xl · shadows · motion fast/normal/slow
- Reduced motion + high contrast media queries respected

## Composition
Foundations → primitives (`ds/`) → patterns → domain pages (F002+)

## Rules
- Pure UI only — no API / scoring / valuation
- Prefer `@/components/ds` for new work; legacy `@/components/ui` remains until migrated
- Empty research surfaces use **Data unavailable.**
- Focus-visible rings required on interactive controls
