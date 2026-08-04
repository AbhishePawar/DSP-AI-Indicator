# Enterprise Multi-Provider Authentication Platform

Production-architecture identity layer for DSP AI Indicator. Extends **A009 RBAC** and **EPIC-016** HttpOnly cookie sessions. Does **not** modify valuation engines, REP-002, research methodology, or analytical APIs.

## 1. Database schema

Users remain A008 persistence metadata entities (`auth-user-*`) with enterprise fields in `metadata`:

| Field | Storage | Notes |
|-------|---------|-------|
| id / user_id | payload | UUID |
| name / display_name | payload | Display name |
| username | payload | Unique |
| email | payload | Unique, case-insensitive |
| mobile | metadata.mobile | E.164 India `+91…` |
| passwordHash | payload.password_hash | `bcrypt$…` preferred; `pbkdf2$…` fallback |
| provider | metadata.provider | `EMAIL`, `GOOGLE`, `MICROSOFT`, `FACEBOOK`, `PHONE`, `USERNAME`, `MAGIC_LINK` |
| avatar | metadata.avatar | URL from IdP |
| role / roles | payload.roles | Permission-based RBAC |
| status | payload | `active` \| `disabled` |
| emailVerified | metadata.email_verified | |
| phoneVerified | metadata.phone_verified | |
| linkedProviders | metadata.linked_providers | Account linking by email |
| createdAt / updatedAt | payload | ISO-8601 |
| lastLogin | payload.last_login | |

Additional metadata entities:

- `auth-access-{id}` — enterprise access requests  
- `auth-invite-{token}` — invitations after approval  
- `auth-login-hist-{id}` — login history / device hints  
- `auth-email-verify-{token}`, `auth-pwd-reset-{token}`, `auth-magic-{token}`  
- `auth-session-{id}` — sessions (EPIC-A009 / EPIC-016)

SQL reference (PEP-001 `identity_users`) remains available for the parallel security_platform path; the web primary path is A009 metadata.

## 2. Auth configuration

| Component | Location |
|-----------|----------|
| Platform service | `packages/auth/src/auth/enterprise_platform.py` |
| Models / providers | `packages/auth/src/auth/enterprise_models.py` |
| Password hashing | `packages/auth/src/auth/hashing.py` (bcrypt → PBKDF2) |
| OTP | `packages/auth/src/auth/otp.py` |
| SMS adapters | `packages/auth/src/auth/sms.py` |
| OAuth adapters | `packages/auth/src/auth/oauth_providers.py` |
| API router | `packages/api_platform/.../enterprise_auth_platform.py` |
| Web client | `apps/web/src/lib/api/enterpriseAuth.ts` |
| Login UI | `apps/web/src/app/(auth)/login/LoginForm.tsx` |

Primary login stack: Enterprise platform → A009 sessions/JWT → EPIC-016 cookies + CSRF.

## 3. OAuth configuration

Env-gated real OAuth2 authorization-code flows:

| Provider | Authorize | Token | UserInfo |
|----------|-----------|-------|----------|
| Google | `accounts.google.com/o/oauth2/v2/auth` | `oauth2.googleapis.com/token` | OIDC userinfo |
| Microsoft Entra | `login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize` | token endpoint | Graph `/me` |
| Facebook | `facebook.com/v19.0/dialog/oauth` | Graph token | Graph `/me` |

When client id/secret are absent:

- `GET /auth/enterprise/providers` reports `available: false`
- Login buttons are **disabled** with honest messaging
- `POST /auth/enterprise/oauth/begin` returns **503** with clear detail

First login: auto-create user (verified email required), import name/avatar, link by email to prevent duplicates.

Callback URL (web): `{origin}/oauth/callback`

## 4. Environment variables

See root `.env.example` and `apps/web/.env.example`. Key variables:

```
# Core
DSP_ENVIRONMENT=development
DSP_JWT_SECRET=
DSP_AUTH_JWT_SECRET=
DSP_COOKIE_AUTH=true
DSP_CSRF_ENABLED=true
DSP_PASSWORD_HASHER=bcrypt
DSP_SEED_ADMIN_PASSWORD=Admin@123
DSP_FORCE_ADMIN_SEED=0

# Google
DSP_GOOGLE_CLIENT_ID=
DSP_GOOGLE_CLIENT_SECRET=

# Microsoft Entra / Azure AD
DSP_MICROSOFT_CLIENT_ID=
DSP_MICROSOFT_CLIENT_SECRET=
DSP_MICROSOFT_TENANT_ID=common

# Facebook
DSP_FACEBOOK_APP_ID=
DSP_FACEBOOK_APP_SECRET=

# SMS / OTP
DSP_SMS_PROVIDER=dev
DSP_TWILIO_ACCOUNT_SID=
DSP_TWILIO_AUTH_TOKEN=
DSP_TWILIO_FROM_NUMBER=
DSP_MSG91_AUTH_KEY=
DSP_MSG91_SENDER_ID=DSPAI
DSP_MSG91_TEMPLATE_ID=
DSP_FIREBASE_API_KEY=

# Web
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
NEXT_PUBLIC_COOKIE_AUTH=true
```

## 5. API routes

All under `/api/v1` (and root aliases):

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/auth/enterprise/schema` | Schema + feature flags |
| GET | `/auth/enterprise/providers` | OAuth/SMS availability |
| POST | `/auth/enterprise/register` | Email registration |
| POST | `/auth/enterprise/verify-email` | Activate account |
| POST | `/auth/enterprise/login` | Email/username + password |
| POST | `/auth/enterprise/password/forgot` | Reset request |
| POST | `/auth/enterprise/password/reset` | Confirm reset |
| POST | `/auth/enterprise/password/change` | Authenticated change |
| GET | `/auth/enterprise/password/strength` | Strength meter |
| POST | `/auth/enterprise/oauth/begin` | Start OAuth |
| POST | `/auth/enterprise/oauth/callback` | Complete OAuth + session |
| POST | `/auth/enterprise/otp/request` | Send India mobile OTP |
| POST | `/auth/enterprise/otp/verify` | Verify OTP + session |
| POST | `/auth/enterprise/magic-link/request` | Optional magic link |
| POST | `/auth/enterprise/magic-link/consume` | Consume magic link |
| POST | `/auth/enterprise/access-requests` | Submit enterprise request |
| GET | `/auth/enterprise/access-requests` | Admin list |
| POST | `/auth/enterprise/access-requests/{id}/decide` | Approve/reject |
| POST | `/auth/enterprise/invitations/accept` | Create password |
| GET | `/auth/enterprise/admin/users` | List users |
| POST | `/auth/enterprise/admin/users/{id}/status` | Enable/disable |
| POST | `/auth/enterprise/admin/users/{id}/reset-password` | Admin reset |
| PUT | `/auth/enterprise/admin/users/{id}/roles` | Assign roles |
| GET | `/auth/enterprise/admin/login-history` | Login history |
| GET | `/auth/enterprise/admin/sessions` | Active sessions |

Existing `/auth/rbac/*` remains for compatibility.

## 6. Middleware

- **CSRF** (`CsrfMiddleware`) — double-submit on mutating requests when access cookie present  
- **Rate limits** — platform `RateLimitHookMiddleware` + in-service buckets (login/OTP/register/reset)  
- **Security headers** — `SecurityHeadersMiddleware`  
- **Optional SecurityMiddleware** — when `DSP_ENABLE_SECURITY=true`  
- Next.js `middleware.ts` — CSP only (auth enforcement remains client `AuthGuard` + API)

Cookies (EPIC-016): `dsp_access`, `dsp_refresh`, `dsp_csrf`, `dsp_session` — HttpOnly where applicable; remember-me extends max-age.

## 7. Admin panel

Admin console **Identity** section adds:

- Enterprise access request approve/reject  
- Login history (provider, device, success)  
- Existing users / roles / sessions (A010)

Roles (product → RBAC permissions, no hardcoded UI checks):

| Product role | A009 role id | Permissions (summary) |
|--------------|--------------|------------------------|
| Administrator | `administrator` | Full |
| Research Analyst | `research_analyst` | Research create/edit/submit |
| Portfolio Manager | `portfolio_manager` | Read + audit + submit |
| Viewer | `viewer` | `read_research` |
| Enterprise Client | `enterprise_client` | `read_research`, `view_audit` |

## 8. OTP / SMS abstraction

`SmsProviderPort` adapters:

- **DevSmsAdapter** — local default; returns `debug_code` (never external send)  
- **NullSmsAdapter** — honest unavailable  
- **TwilioSmsAdapter** / **Msg91SmsAdapter** — live when credentials present  
- **FirebaseSmsAdapter** — documents client-SDK requirement; honest server unavailable  

OTP rules: India `+91` mobiles, 6-digit code, 5-minute expiry, 30s resend cooldown, hourly send cap, max 5 verify attempts, IP failure tracking.

## 9. Workflows

### Self-service email

Register → verify email → login (password / remember me) → `/dashboard`

### Enterprise request access

Submit → Admin approve → Invitation token → `/invite` create password → login  

Coexists with `/register`.

### OAuth

Begin → IdP → `/oauth/callback` → session cookies → `/dashboard`

### Mobile OTP

Request → SMS (or Dev debug) → Verify → session

### Dev seed

If no administrator exists (non-production unless `DSP_FORCE_ADMIN_SEED=1`):

- email: `admin@dspai.local`  
- username: `admin`  
- password: `Admin@123` (or `DSP_SEED_ADMIN_PASSWORD`)  
- role: Administrator  

## 10. Security summary

- Passwords: bcrypt (when installed) or PBKDF2-SHA256; never plaintext  
- Sessions: JWT access + refresh; HttpOnly cookies; CSRF; remember-me TTLs  
- Rate limiting on auth hot paths  
- Login history + device labels  
- Disabled users lose sessions  
- Honest unavailable messaging when OAuth/SMS secrets missing  
- CV-001: no fabricated auth success without real verification  

## 11. Testing

```powershell
cd packages/auth; python -m pytest tests/test_enterprise_auth_platform.py -q
cd apps/web; npm test -- --run src/lib/auth/auth.test.ts
```

Coverage: registration, login, OTP+Dev SMS, account linking, admin seed, rate limits / brute-force OTP.
