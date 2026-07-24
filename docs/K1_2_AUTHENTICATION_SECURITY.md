# Phase K1.2 — Authentication & Security Platform

**Status:** Implemented · AuthN / AuthZ / RBAC only · No business logic  

**Package:** `packages/security_platform/` **0.1.0**  
**Protects:** `api_platform` (optional `SecurityMiddleware` via `create_app(security=...)`)  
**Independent of:** `dsp_platform` (never imports authentication)

This phase adds the Authentication & Security Platform. It authenticates
callers, authorizes permissions, issues JWTs / API keys, rate-limits, and
audits — without financial analysis, recommendation logic, durable databases,
or frontend login screens.

---

## 1. Architecture

```text
HTTP Client
    │
    ▼
SecurityMiddleware   (security_platform)
    │  JWT / API key / guest / OAuth2 port
    │  RBAC · rate limit · audit
    ▼
api_platform routers
    │
    ▼
DSPPlatform          ← remains auth-independent
```

| Component | Role |
|---|---|
| `AuthenticationManager` | JWT · API keys · guest · OAuth2-ready port |
| `AuthorizationManager` | Permission checks |
| `RoleManager` / `PermissionManager` | RBAC catalogs |
| `JWTManager` | HS256 issue / verify (stdlib) |
| `ApiKeyManager` | Hashed in-memory API keys |
| `AuditLogger` | Process-local audit events |
| `RateLimiter` | Sliding-window limits |
| `SecurityContext` | Request-scoped principal |
| `SecurityMiddleware` | Starlette / FastAPI protection |

---

## 2. Roles

`ADMIN` · `ADVISOR` · `CLIENT` · `RESEARCHER` · `API` · (`GUEST` for guest mode)

---

## 3. Permissions

`AnalyzeCompany` · `CompareCompanies` · `RunWorkflow` · `AskCopilot` ·
`ViewReports` · `ManageUsers` · `ManagePlatform`

Default matrix (summary):

| Role | Analyze | Compare | Workflow | Copilot | Reports | Manage* |
|---|---|---|---|---|---|---|
| ADMIN | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ADVISOR | ✓ | ✓ | ✓ | ✓ | ✓ | |
| RESEARCHER | ✓ | ✓ | | ✓ | ✓ | |
| API | ✓ | ✓ | ✓ | ✓ | ✓ | |
| CLIENT | | | | ✓ | ✓ | |
| GUEST | | | | | ✓ | |

---

## 4. Authentication

| Method | Header / material |
|---|---|
| JWT | `Authorization: Bearer <jwt>` |
| API key | `X-Api-Key-Id` + `X-Api-Key-Secret` or `Authorization: ApiKey id.secret` |
| OAuth2 | `OAuth2TokenValidator` protocol — adapter supplies IdP validation |
| Guest | Enabled via `SecuritySettings.allow_guest` |

Public paths (default): `/health`, `/docs`, `/redoc`, `/openapi.json`,
`/api/v1/health`.

---

## 5. API wiring

```python
from security_platform import SecurityBundle, SecuritySettings
from api_platform import create_app

bundle = SecurityBundle.create(SecuritySettings(jwt_secret="..."))
app = create_app(security=bundle)
```

When `security=None` (default), the API behaves as K1.1 (unauthenticated) for
local / regression compatibility.

---

## 6. Non-goals

No business logic · no financial analysis · no recommendation logic · no
database implementation · no frontend login.

User / API key stores are **process-local** — production adapters may replace
them without changing RBAC contracts.

---

## 7. Extension strategy

| Next | Pattern |
|---|---|
| **K1.3 Production Services** | **DONE** · see [K1.3](K1_3_PRODUCTION_SERVICES.md) |
| Durable identity store | Adapter behind `UserStore` / `ApiKeyManager` |
| External IdP (OIDC) | Implement `OAuth2TokenValidator` |
| Distributed rate limits | Adapter replacing `RateLimiter` |
| SIEM audit export | Mirror `AuditLogger` events |

---

## Related documents

| Doc | Role |
|---|---|
| **This file** | K1.2 Authentication & Security |
| [K1_1_API_PLATFORM.md](K1_1_API_PLATFORM.md) | API Platform |
| [K1_0_PLATFORM_INTEGRATION.md](K1_0_PLATFORM_INTEGRATION.md) | Platform integration |

---

## Final question

Is the Authentication & Security Platform complete, stable, and ready for
Production Services (K1.3)?

Answered in the phase RETURN.
