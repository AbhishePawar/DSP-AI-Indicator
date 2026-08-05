# Enterprise Authentication Platform

| Field | Value |
|---|---|
| **Status** | Production-ready extension of frozen PEP-001 identity |
| **Stack** | `packages/auth` + `security_platform` + FastAPI `/api/v1` |
| **Client** | Next.js thin client (`apps/web`) — **no Auth.js / NextAuth** |
| **Sessions** | Single session layer (A009 JWT + refresh + HttpOnly cookies) |

## Architecture

All authentication logic lives in Python (`packages/auth`, `security_platform`). The web app only calls `/api/v1` and never holds OAuth client secrets or issues sessions.

```text
Browser → /api/v1/auth/* → EnterpriseAuthPlatform → AuthService / OAuth / OTP / MFA ports
                         → HttpOnly cookies + JWT access + rotating refresh
                         → /dashboard
```

## Providers

| Provider | Env credentials | Intentional disable |
|---|---|---|
| Google | `DSP_GOOGLE_CLIENT_ID/SECRET` | `DSP_AUTH_PROVIDER_GOOGLE=disabled` → `coming_soon` |
| Microsoft Entra | `DSP_MICROSOFT_*` + `DSP_MICROSOFT_TENANT_ID` | `DSP_AUTH_PROVIDER_MICROSOFT=disabled` |
| Facebook | `DSP_FACEBOOK_CLIENT_ID/SECRET` (or legacy `DSP_FACEBOOK_APP_ID/SECRET`) | `DSP_AUTH_PROVIDER_FACEBOOK=disabled` |
| Mobile OTP (India) | `DSP_SMS_PROVIDER` (+ Twilio/MSG91/Fast2SMS) | `DSP_AUTH_PROVIDER_OTP=disabled` |
| Email / Username | always available | — |
| Magic link | `DSP_AUTH_MAGIC_LINK=true` | default Coming Soon |

Google, Microsoft, and Facebook all share one `OAuthProviderAdapter` implementation (`packages/auth/src/auth/oauth_providers.py`) — provider-specific behavior (Microsoft's per-tenant issuer, Facebook's lack of an OIDC `id_token`) is isolated to small, explicit branches, not separate OAuth stacks. Each provider additionally has four dedicated browser-navigable routes (`GET /auth/{provider}`, `GET /auth/{provider}/callback`, `POST /auth/{provider}/link`, `POST /auth/{provider}/unlink`) alongside the generic SPA popup routes below — see [ENTERPRISE_AUTH_PLATFORM.md](security/ENTERPRISE_AUTH_PLATFORM.md) §§3, 3a, 3b for the full per-provider security details.

`GET /auth/providers` (alias `/auth/enterprise/providers`) returns:

```json
{ "id": "google", "provider": "GOOGLE", "status": "available|unavailable|coming_soon", "available": true }
```

UI rules:

- `unavailable` → **hide** button (missing credentials)
- `coming_soon` → show **Coming Soon**
- `available` → show active CTA
- Mobile OTP mode **never** shows a password field

OAuth uses **PKCE (S256)** + CSRF `state`. Account linking merges by verified email.

## Roles

| Product | Role id |
|---|---|
| Super Admin | `super_admin` |
| Administrator | `administrator` |
| Research Analyst | `research_analyst` |
| Portfolio Manager | `portfolio_manager` |
| Enterprise Client | `enterprise_client` |
| Read Only Viewer | `read_only` |

Dev seed (only if no Super Admin / Administrator exists):

- Email: `admin@dspai.local`
- Username: `admin`
- Password: `Admin@123` (override `DSP_SEED_ADMIN_PASSWORD`)
- Role: `super_admin`

## Security controls

- **Argon2id** password hashing (`DSP_PASSWORD_HASHER=argon2id`); legacy PBKDF2/bcrypt verified and upgraded on login
- JWT access tokens + **refresh rotation with automatic reuse detection** (every refresh mints a new token and immediately kills the old one; presenting an already-rotated token revokes the whole session) — see below and [ENTERPRISE_AUTH_PLATFORM.md §3e](security/ENTERPRISE_AUTH_PLATFORM.md)
- HttpOnly Secure cookies (`DSP_COOKIE_AUTH`)
- CSRF for cookie-mode mutations
- PKCE for OAuth
- Rate limiting + brute-force counters
- Account lockout (`DSP_AUTH_LOCKOUT_THRESHOLD`, `DSP_AUTH_LOCKOUT_SECONDS`)
- Session expiry + Remember Me TTL
- Login audit logs + device management + **expiring** trusted devices (`DSP_AUTH_TRUSTED_DEVICE_DAYS`, default 30 — "remember this device" always lapses, never trusted forever)
- MFA implemented (TOTP enrollment/verify/enable/disable, encrypted-at-rest secrets, recovery codes with status + regeneration, enrollment/verify rate limiting, forced re-authentication on disable/regenerate) and WebAuthn/Passkey implemented (registration + authentication, discoverable credentials) — both gated by `DSP_AUTH_MFA=true`; login contracts stay additive-stable (`mfa_required` + `mfa_token` + `methods` only appear when a factor is actually enrolled)

## Key API routes

| Area | Paths |
|---|---|
| Discovery | `GET /auth/providers` |
| Email | `POST /auth/register`, `/auth/verify-email`, `/auth/forgot-password`, `/auth/reset-password` |
| Login | `POST /auth/enterprise/login` (+ `/auth/rbac/login`) |
| Refresh | `POST /auth/rbac/refresh` (rotates + reuse-detects; also `POST /auth/refresh` on the separate PEP-001/cookie identity stack) |
| OAuth | `GET /auth/oauth/{provider}/start\|callback`; plus dedicated `GET/POST /auth/{google\|microsoft\|facebook}/{,callback,link,unlink}` |
| OTP | `POST /auth/otp/request\|verify\|resend` |
| Account | `GET/PATCH/DELETE /auth/me`, change-password/email, unlink, devices, login-history, sessions/revoke-all |
| Access requests | `POST/GET /auth/enterprise/access-requests`, invitations/accept |
| MFA | `POST /auth/mfa/{enroll,enable,verify,disable}`, `GET /auth/mfa/recovery-codes`, `POST /auth/mfa/recovery-codes/regenerate` (canonical); `POST /auth/mfa/totp/{enroll,enroll/confirm,verify,disable}` (pre-existing aliases, unchanged); `POST /auth/mfa/webauthn/{register,register/complete,authenticate,authenticate/complete,credentials/remove}`, `GET /auth/mfa/webauthn/credentials` — all `DSP_AUTH_MFA=true` |
| Passkey (primary login) | `POST /auth/passkey/{register/begin,register/complete,login/begin,login/complete}`, `GET /auth/passkey`, `DELETE /auth/passkey/{credential_id}` — `DSP_AUTH_MFA=true` |
| Admin | provision, status, unlock, force reset, roles, revoke sessions, login history |

## SMS / Email adapters

- SMS: `console`/`dev` (local OTP echo), `null`, Twilio, MSG91, Firebase stub
- Email: `console` (dev tokens), `null`

## MFA

`MfaGateway.evaluate(session, device_trusted)` runs after primary auth (password, OAuth, OTP, magic link, passkey). When `DSP_AUTH_MFA=true` and a user is enrolled in TOTP and/or a WebAuthn passkey, the login response adds `mfa_required: true` + a short-lived `mfa_token` + `methods: ["totp", "webauthn", ...]` alongside the session tokens (additive, non-blocking); the client then calls `/auth/mfa/verify` (or `/auth/mfa/webauthn/authenticate*`) with that `mfa_token` to complete step-up. Unenrolled users, and all logins while `DSP_AUTH_MFA=false`, are unaffected — this never breaks existing clients.

TOTP enrollment is two-phase and encrypted at rest: `POST /auth/mfa/enroll` issues a secret + QR held only in memory until `POST /auth/mfa/enable` verifies a live code from the authenticator app, at which point the secret is encrypted (`auth.secret_box`, AES via `cryptography.fernet`, key-rotation-ready) before being persisted and 10 salted+hashed recovery codes are returned once. `GET /auth/mfa/recovery-codes` reports remaining-code counts (never the codes themselves); `POST /auth/mfa/recovery-codes/regenerate` and `POST /auth/mfa/disable` both **require the current password** (forced re-authentication) so a hijacked access token alone cannot strip or rotate a second factor. Enrollment and step-up are rate-limited to blunt 6-digit brute forcing. "Remember this device" (`remember_device` + `device_id` on `/auth/mfa/verify`) records the device as trusted for `DSP_AUTH_TRUSTED_DEVICE_DAYS` days (default 30) — trust always expires and is re-checked on every login, never permanent. Every step of the lifecycle (`mfa.enroll.begin/success/failure`, `mfa.enable`, `mfa.disable`, `mfa.verify.success/failure`, `mfa.recovery.used/regenerated`) is recorded in the audit trail. See [ENTERPRISE_AUTH_PLATFORM.md §3d](security/ENTERPRISE_AUTH_PLATFORM.md) for the full sequence diagrams and security model.

## Refresh token rotation & reuse detection

`POST /auth/rbac/refresh` (and `EnterpriseAuthPlatform.refresh_session`, a
thin bridge over the same `AuthenticationService.refresh` used by that
endpoint) rotates the refresh token on every call: the presented token is
invalidated in the same atomic write that mints its replacement, so a
refresh token can only ever be used once. Presenting a token that has
already been rotated away — replay, forgery, or a losing concurrent
request — revokes the entire session (the refresh-token family, since one
A009 session has exactly one active refresh-token lineage) rather than
just rejecting the one bad token. `refresh.issued`, `refresh.rotated`,
`refresh.reused`, `refresh.revoked`, and `session.revoked` are recorded in
the same audit trail as every other authentication event. See
[ENTERPRISE_AUTH_PLATFORM.md §3e](security/ENTERPRISE_AUTH_PLATFORM.md) for
the full design, sequence diagrams, and security model.

## Passkey (WebAuthn) — primary, passwordless sign-in

The same `WebAuthnAdapter`/credential store used for MFA step-up above also powers a fully passwordless, primary sign-in path under `/auth/passkey/*` (`GET /auth/enterprise/providers` → `passkey.available`). `login/begin` requests a *discoverable* ("usernameless") credential challenge — no identifier required, the browser's own account picker supplies it — and `login/complete` verifies the assertion and issues a full session (HttpOnly cookies + JWT) exactly like password/OAuth/OTP login. A credential registered via either `/auth/mfa/webauthn/register*` or `/auth/passkey/register/*` works for both entry points. See [ENTERPRISE_AUTH_PLATFORM.md §3c](security/ENTERPRISE_AUTH_PLATFORM.md) for ceremony sequence diagrams, the full security model (challenge/origin/RP-ID/signature/counter validation), recovery strategy (device migration), and browser/deployment requirements.

## Non-goals

- No Auth.js / NextAuth
- No duplicated Next.js session store
- No Prisma identity rewrite
