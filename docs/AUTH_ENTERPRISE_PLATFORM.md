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
| Facebook | `DSP_FACEBOOK_APP_ID/SECRET` | `DSP_AUTH_PROVIDER_FACEBOOK=disabled` |
| Mobile OTP (India) | `DSP_SMS_PROVIDER` (+ Twilio/MSG91) | `DSP_AUTH_PROVIDER_OTP=disabled` |
| Email / Username | always available | — |
| Magic link | `DSP_AUTH_MAGIC_LINK=true` | default Coming Soon |

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
- JWT access tokens + **refresh rotation**
- HttpOnly Secure cookies (`DSP_COOKIE_AUTH`)
- CSRF for cookie-mode mutations
- PKCE for OAuth
- Rate limiting + brute-force counters
- Account lockout (`DSP_AUTH_LOCKOUT_THRESHOLD`, `DSP_AUTH_LOCKOUT_SECONDS`)
- Session expiry + Remember Me TTL
- Login audit logs + device management + trusted devices
- MFA ports (TOTP / WebAuthn) reserved — `DSP_AUTH_MFA=false`; login contracts stay additive-stable

## Key API routes

| Area | Paths |
|---|---|
| Discovery | `GET /auth/providers` |
| Email | `POST /auth/register`, `/auth/verify-email`, `/auth/forgot-password`, `/auth/reset-password` |
| Login | `POST /auth/enterprise/login` (+ `/auth/rbac/login`) |
| OAuth | `GET /auth/oauth/{provider}/start\|callback` |
| OTP | `POST /auth/otp/request\|verify\|resend` |
| Account | `GET/PATCH/DELETE /auth/me`, change-password/email, unlink, devices, login-history, sessions/revoke-all |
| Access requests | `POST/GET /auth/enterprise/access-requests`, invitations/accept |
| MFA reserved | `/auth/mfa/totp/*`, `/auth/mfa/webauthn/*` → 501 |
| Admin | provision, status, unlock, force reset, roles, revoke sessions, login history |

## SMS / Email adapters

- SMS: `console`/`dev` (local OTP echo), `null`, Twilio, MSG91, Firebase stub
- Email: `console` (dev tokens), `null`

## MFA extension plan

`MfaGateway.evaluate(session, device_trusted)` runs after primary auth. Today it always proceeds. When `DSP_AUTH_MFA=true` and a user is enrolled, responses may add `mfa_required` + `mfa_token` without breaking existing clients. Trusted devices can skip step-up later.

## Non-goals

- No Auth.js / NextAuth
- No duplicated Next.js session store
- No Prisma identity rewrite
- No live TOTP/Passkeys UX in this release (ports only)
