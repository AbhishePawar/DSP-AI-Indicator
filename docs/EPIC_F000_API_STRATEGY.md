# EPIC-F000 — API Strategy

## Contract

- Base: `NEXT_PUBLIC_API_BASE_URL` → `/api/v1`
- Client: `src/lib/api/client.ts` (fetch wrapper)
- Backend: `dsp_platform` **1.0.0** · HTTP **v1.0.0-rc1**

## Auth

| Flow | Endpoint |
|---|---|
| Legacy | `POST /auth/login` |
| Institutional | `/auth/rbac/*` (A009 additive) |

JWT Bearer on authenticated calls. Passwords never stored.

## UX states

`idle | loading | success | empty | error` via `resolveListState`.

Empty/error copy defaults to **"Data unavailable."**

## Strategies

Documented in `foundation/ux/strategies.ts` and `foundation/api/strategy.ts`.

## Explicit prohibitions

No browser engine execution · no provider calls · no fabricated metrics ·
no breaking API contract changes from the frontend.
