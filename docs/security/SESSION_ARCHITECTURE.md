# Session Architecture (EPIC-016)

## Goals

- Eliminate browser-readable access/refresh token persistence as the production path
- Support session rotation, refresh, device inventory, and invalidation
- Align with OWASP session management guidance

## Components

| Layer | Location | Role |
|---|---|---|
| Cookie helpers | `security_platform.security.cookies` | Issue/clear HttpOnly cookies + CSRF |
| CSRF middleware | `api_platform.api.csrf_middleware` | Enforce double-submit on cookie sessions |
| Auth routes | `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/session` | Cookie + Bearer issuance |
| RBAC routes | `/auth/rbac/*` | Institutional login with cookie attach |
| Token service | `security_platform.security.identity.tokens` | Access JWT + refresh rotation |
| Device sessions | `InMemoryDeviceSessionStore` / `DeviceSessionPort` | Device inventory + revoke |
| Web session | `apps/web` `sessionStore` + `cookieSession` | Metadata only in cookie mode |

## Lifecycle

```text
Login → issue access+refresh JWT
      → Set-Cookie HttpOnly (access/refresh/session)
      → Set-Cookie dsp_csrf (JS-readable)
      → SPA stores metadata + CSRF only (no JWT in localStorage)

Request → credentials: include
        → Authorization Bearer optional (API clients)
        → X-CSRF-Token required for mutating cookie sessions

Refresh → rotate refresh family
        → re-issue cookies

Logout  → revoke server session/refresh
        → clear cookies
```

## Session fixation / rotation

- New `session_id` on login
- Refresh token rotation invalidates prior refresh token
- Device session `rotate()` issues a new session id
- `revoke` / `revoke_all` for forced invalidation

## Password reset / email verification

`IdentityService` provides:

- `request_password_reset` / `confirm_password_reset`
- `issue_email_verification` / `confirm_email_verification`

Delivery is out-of-band (email adapter not vendor-wired in this epic).

## SSO / OIDC

Ports:

- `OAuth2AuthorizationPort` — Null + Local adapters
- `OidcClientPort` — Null + `LocalOidcClientAdapter`
- `SsoProviderPort` — Null + `LocalSsoAdapter`

Production IdP wiring is explicitly out of scope for EPIC-016 architecture close.

## Feature flags

- `DSP_COOKIE_AUTH=true` (API default on)
- `NEXT_PUBLIC_COOKIE_AUTH=true` (web default on)
- Set either to `false` for Bearer/localStorage compatibility during migration
