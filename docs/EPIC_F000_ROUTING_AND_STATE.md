# EPIC-F000 — Routing & State

## Route groups (target)

| Group | Purpose |
|---|---|
| `(auth)` | Login / unauthenticated |
| `(app)` | Authenticated research shell |
| `(admin)` | A010 administration |
| `(marketing)` | Optional public |

Structural adoption in F001+ — **do not move** existing `src/app` trees in F000.

## Frozen feature routes (not implemented in F000)

`/dashboard` · `/analysis` · `/portfolio` · `/research` · `/admin` · `/settings` · `/profile`

Source: `foundation/routes/freeze.ts`

## Layout specs

Header · Sidebar · Footer contracts: `foundation/layout/spec.ts`

## State

| Kind | Tool |
|---|---|
| Server | TanStack Query (live) |
| Client UI | Zustand (F001) — shape frozen in `uiStoreDefaults` |
| Forms | RHF + Zod (F001) |
| Auth session | existing `lib/auth` |

**Never** store valuation scores or engine outputs in client stores.
