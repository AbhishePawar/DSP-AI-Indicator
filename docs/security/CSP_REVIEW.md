# CSP REVIEW — EPIC-019A

| Field | Value |
|---|---|
| Date | 2026-08-04 |
| Product | DSP AI Indicator 2.0.0-rc.1 |
| Branch | `cursor/p6-1-commercial-readiness` |
| Scope | Next.js web CSP hardening (Architecture Freeze) |

## Summary

Production script CSP no longer uses `'unsafe-inline'` or `'unsafe-eval'`. Per-request nonces are issued from `apps/web/src/middleware.ts`. Static CSP was removed from `next.config.ts` headers to avoid conflicting dual policies.

| Directive | Production | Development | Notes |
|---|---|---|---|
| `script-src` | `'self' 'nonce-…' 'strict-dynamic'` | same + `'unsafe-eval'` | Dev retains `'unsafe-eval'` for Next HMR only |
| `style-src` | `'self' 'unsafe-inline'` | same | **Unavoidable residual** — next-themes / CSS variable injection / Next font styles without full style-nonce migration |
| `default-src` | `'self'` | same | — |
| `object-src` | `'none'` | same | — |
| `frame-ancestors` | `'none'` | same | — |
| API CSP | unchanged hardened | — | `packages/api_platform/.../ops_middleware.py` |

## Removed (production)

- `script-src 'unsafe-inline'`
- `script-src 'unsafe-eval'`

## Documented exceptions (not PASS as fully locked CSP)

1. **`style-src 'unsafe-inline'`** — required for current Next App Router + `next-themes` appearance applicator without redesigning style injection. Tracked residual (AUD-013 partial closure).
2. **Dev `'unsafe-eval'`** — Next.js HMR only; must not ship in production builds (`NODE_ENV=production`).
3. **`connect-src https:`** — allows HTTPS API hosts; tighten to explicit origins at deploy time (ops).

## Verification

- Middleware matcher applies CSP on HTML navigations.
- Root layout reads `x-nonce` for Next script association (`data-csp-nonce`).
- Re-audit after any Next major upgrade.

## Status

| Claim | Result |
|---|---|
| Production script unsafe-inline removed | **PASS** |
| Production script unsafe-eval removed | **PASS** |
| Style unsafe-inline removed | **FAIL / ACCEPTED residual** (documented) |
| Full CSP lockdown (no exceptions) | **PARTIAL** |
