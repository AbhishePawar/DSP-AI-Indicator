# Production Security Guide (EPIC-016)

Commercial GA security foundation for DSP AI Indicator. Architecture freeze preserved — no valuation/research engine changes.

## Principles

1. **CV-001** — Never fabricate security or billing state; return honest unavailable messages.
2. **HttpOnly sessions** — Browser-readable token storage is not the production path.
3. **Defense in depth** — Cookies + CSRF + security headers + rate limits + RBAC.
4. **Ports over vendors** — OAuth2/OIDC/SSO/billing adapters are interfaces first; wire vendors later.

## Environment controls

| Variable | Purpose | Production |
|---|---|---|
| `DSP_ENABLE_SECURITY` | Enable SecurityBundle | `true` |
| `DSP_JWT_SECRET` | JWT signing secret (non-default) | required |
| `DSP_COOKIE_AUTH` | HttpOnly cookie session mode | `true` (default) |
| `DSP_CSRF_ENABLED` | Double-submit CSRF enforcement | `true` |
| `DSP_COOKIE_SECURE` | Secure cookie flag | `true` in production |
| `DSP_COOKIE_SAMESITE` | `lax` / `strict` / `none` | `lax` |
| `DSP_RATE_LIMIT_ENABLED` | API rate limiting | `true` |
| `DSP_CORS_ORIGINS` | Explicit allow-list | required |
| `DSP_DATABASE_URL` | Durable enterprise + identity | Postgres URL |
| `DSP_BILLING_PROVIDER` | `null` / `stripe` / `razorpay` / `paddle` | chosen vendor |
| `NEXT_PUBLIC_COOKIE_AUTH` | Web prefers cookie mode | `true` |

## Cookie session (production)

Cookies issued on login/refresh:

- `dsp_access` — HttpOnly, Secure (prod), SameSite
- `dsp_refresh` — HttpOnly, Secure (prod), SameSite
- `dsp_session` — HttpOnly session id
- `dsp_csrf` — **not** HttpOnly (double-submit CSRF)

Mutating requests with an access cookie must send `X-CSRF-Token` matching `dsp_csrf`.

Bearer tokens remain accepted for API clients and tests. The SPA production path must not persist JWTs in `localStorage`.

## Headers

API responses set:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` (camera/mic/geo disabled)
- `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'`
- `Cache-Control: no-store`

Web CSP remains in `apps/web/next.config.ts` (includes `'unsafe-inline'` / `'unsafe-eval'` trade-offs for Next.js — tracked as residual risk).

## Identity architecture

See [SESSION_ARCHITECTURE.md](./SESSION_ARCHITECTURE.md).

Ports (no vendor wiring required for GA architecture close):

- OAuth2 authorization server port
- OIDC client port
- SSO provider port
- Device/session management port
- Password reset + email verification (IdentityService)
- RBAC (enterprise + institutional)

## Billing

See [BILLING_ARCHITECTURE.md](./BILLING_ARCHITECTURE.md). Adapters always return **Billing provider unavailable.** until live credentials + webhook verification are configured.

## Audit

See [AUDIT_ARCHITECTURE.md](./AUDIT_ARCHITECTURE.md). Append-only enterprise audit with actor, action, resource, before/after, IP, correlation ID.

## Residual risks (honest)

- Live IdP (Okta/Azure AD/Google) not wired
- Live Stripe/Razorpay/Paddle checkout/webhooks not executed
- Multi-replica rate limits need Redis edge configuration
- Web CSP still allows unsafe-inline/eval for Next.js bundling
- Enterprise route actor binding via `X-User-Id` still needs JWT-subject hardening in a follow-up
