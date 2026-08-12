# EPIC-A009 — API Guide

Institutional RBAC routes (additive). Legacy `POST /auth/login` unchanged.

Base: `/api/v1`

| Method | Path | Purpose |
|---|---|---|
| GET | `/auth/rbac/schema` | Schema descriptor |
| POST | `/auth/rbac/login` | Login → tokens + session |
| POST | `/auth/rbac/logout` | Revoke session |
| POST | `/auth/rbac/refresh` | Rotate refresh token → new access + refresh tokens |
| GET | `/auth/rbac/me` | Current user (`Authorization: Bearer`) |
| POST | `/auth/rbac/users` | Create user |
| GET | `/auth/rbac/users` | List users |
| GET | `/auth/rbac/users/{id}` | Get user |
| PUT | `/auth/rbac/users/{id}/roles` | Assign roles |
| GET | `/auth/rbac/roles` | List roles |
| POST | `/auth/rbac/roles` | Upsert role |
| GET | `/auth/rbac/permissions` | List permissions |
| POST | `/auth/rbac/evaluate` | Evaluate permission |
| POST | `/auth/rbac/protect?permission=` | Optional bearer+permission guard |

Default platform APIs remain open for backward compatibility. Callers opt into
protection via `/auth/rbac/protect` or `DSPPlatform.protect_with_permission`.

## Refresh token rotation

`POST /auth/rbac/refresh` implements OAuth 2.0 Security BCP rotation, not a
stateless re-issue: the response's `tokens.refresh_token` is a **new**
value on every call, and the token you sent becomes permanently invalid
the instant the response is returned — do not cache or retry with it.

Request:

```json
{ "refresh_token": "<current refresh token>" }
```
(`refresh_token` may be omitted when using cookie auth — the `dsp_refresh`
HttpOnly cookie is read instead. `created_at` / `access_jti` remain
optional, deterministic-testing-only fields, unchanged from before.)

Response (`200`) — identical shape to `/auth/rbac/login`:

```json
{
  "ok": true,
  "result": {
    "user": { "...": "..." },
    "tokens": {
      "access_token": "...",
      "refresh_token": "... (new — the old one is now dead)",
      "token_type": "bearer",
      "expires_in": 3600,
      "session_id": "..."
    },
    "session": { "session_id": "...", "revoked": false, "...": "..." }
  },
  "message": null
}
```

Failure (`401`) — invalid, expired, revoked, or **already-used** refresh
token. A `401` here always means "the client must re-authenticate", never
"retry the request": if the token was rejected because it had already been
rotated away (reuse/replay), the **entire session has been revoked** as a
side effect, so retrying — even with a token from a response that
appeared to succeed moments earlier in a race — will also fail. Clients
should treat this exactly like an expired session: drop local tokens and
send the user back through the login flow.

```json
{ "ok": false, "error": "Refresh token reuse detected; session revoked.", "message": "Data unavailable." }
```

See [SECURITY_GUIDE.md](SECURITY_GUIDE.md#refresh-token-rotation--reuse-detection-oauth-20-security-bcp) and [ENTERPRISE_AUTH_PLATFORM.md §3e](security/ENTERPRISE_AUTH_PLATFORM.md) for the full design, audit event catalogue, and sequence diagrams.

## RC1 Milestone 6 — Enterprise Dashboards

Thin aggregation routes over existing engines. No duplicated calculations.
Full detail: [DASHBOARDS.md](DASHBOARDS.md).

| Method | Path | Purpose |
|---|---|---|
| GET | `/dashboards/schema` | Role list + reuse rules |
| GET | `/dashboards/research` | Research Analyst dashboard |
| GET | `/dashboards/portfolio-manager` | Portfolio Manager dashboard |
| GET | `/dashboards/wealth-advisor` | Wealth Advisor dashboard |
| GET | `/dashboards/family-office` | Family Office dashboard |
| GET | `/dashboards/executive` | Executive / platform KPI dashboard |

Optional query params (role-dependent): `portfolio_id`, `symbols`, `watchlist_id`,
`client_portfolio_ids`, `workflow_id`. Missing sections return
`"message": "Data unavailable."` with `"available": false`.

## RC1 Milestone 7 — AI Research Copilot 2.0

Orchestration / explanation only. Full detail: [COPILOT.md](COPILOT.md).

| Method | Path | Purpose |
|---|---|---|
| GET | `/copilot/schema` | Modes, rules, engine reuse |
| POST | `/copilot/chat` | Conversational router (M7) or legacy `context_ref` |
| POST | `/copilot/company` | Company analysis explanation |
| POST | `/copilot/portfolio` | Portfolio Intelligence explanation |
| POST | `/copilot/valuation` | Valuation / MoS explanation |
| POST | `/copilot/comparison` | Comparison assistant |
| POST | `/copilot/document` | Filings / news / transcripts Q&A |
| GET | `/copilot/history` | List conversations |
| GET | `/copilot/history/{id}` | Conversation turns + context |
| DELETE | `/copilot/history/{id}` | Delete conversation |

Retained: `/copilot/complete`, `/copilot/stream`, `/copilot/providers`.
Missing engine inputs → `"Data unavailable."`

## RC1 Milestone 8 — Research Workspace

Orchestration only (notes / folders / bookmarks / templates / workflow / Copilot).
Full detail: [RESEARCH_WORKSPACE.md](RESEARCH_WORKSPACE.md).

| Method | Path | Purpose |
|---|---|---|
| GET | `/research-workspace` | Workspace dashboard |
| GET | `/research-workspace/schema` | Templates, statuses, reuse rules |
| POST | `/research-workspace/note` | Create note |
| GET | `/research-workspace/note/{id}` | Get note |
| PUT | `/research-workspace/note/{id}` | Update note (creates version) |
| DELETE | `/research-workspace/note/{id}` | Delete note |
| GET | `/research-workspace/note/{id}/versions` | Version history |
| POST | `/research-workspace/note/{id}/restore` | Restore version |
| POST | `/research-workspace/note/{id}/diff` | Diff two versions |
| GET | `/research-workspace/notes` | List notes |
| POST | `/research-workspace/folder` | Create folder |
| PUT | `/research-workspace/folder/{id}` | Rename / move / archive |
| DELETE | `/research-workspace/folder/{id}` | Delete folder |
| GET | `/research-workspace/folders` | List folders |
| POST | `/research-workspace/bookmark` | Create bookmark |
| DELETE | `/research-workspace/bookmark/{id}` | Delete bookmark |
| GET | `/research-workspace/bookmarks` | List bookmarks |
| POST | `/research-workspace/template` | Apply template → note |
| POST | `/research-workspace/comment` | Add comment |
| POST | `/research-workspace/comment/{id}/resolve` | Resolve comment |
| POST | `/research-workspace/share` | Share note with user ids |
| POST | `/research-workspace/publish` | Draft→review→approved→published (workflow) |
| GET | `/research-workspace/search?q=` | Full-text search |
| POST | `/research-workspace/ai` | Copilot 2.0 assist on note |
| POST | `/research-workspace/tag` | Create / update tag |
| DELETE | `/research-workspace/tag/{id}` | Delete tag |

## RC1 Milestone 9 — Commercial SaaS Platform

Orchestration over `packages/enterprise` (orgs, IAM, licenses, API keys, usage,
billing ports). Never fabricates payments. Full detail: [SAAS_PLATFORM.md](SAAS_PLATFORM.md).

| Method | Path | Purpose |
|---|---|---|
| GET | `/saas/schema` | Plans, reuse rules |
| GET | `/saas/dashboard` | Admin SaaS dashboard (honest KPIs) |
| GET | `/saas/plans` | Plan comparison / feature matrix |
| GET | `/saas/organizations` | List organizations |
| POST | `/saas/organization` | Create organization (+ optional trial plan) |
| GET | `/saas/organization/{id}` | Get organization |
| PUT | `/saas/organization/{id}` | Update / rename |
| POST | `/saas/organization/{id}/archive` | Archive |
| DELETE | `/saas/organization/{id}` | Soft-delete / archive |
| GET/PUT | `/saas/organization/{id}/settings` | Branding + workspace prefs |
| POST | `/saas/team` | Create team (IAM) |
| POST | `/saas/organization/{id}/invite` | Invite member |
| POST | `/saas/subscription` | Record subscription + assign license |
| GET | `/saas/organization/{id}/subscription` | Subscription overlay |
| POST | `/saas/license` | Assign license |
| POST | `/saas/license/key` | Issue enterprise license key |
| POST | `/saas/license/activate` | Activate key on org |
| GET | `/saas/organization/{id}/license` | License status |
| POST | `/saas/api-key` | Generate API key |
| POST | `/saas/api-key/rotate` | Rotate |
| POST | `/saas/api-key/revoke` | Revoke |
| POST | `/saas/usage` | Record usage metric |
| GET | `/saas/organization/{id}/usage` | Usage snapshot |
| GET | `/saas/organization/{id}/billing` | BillingPort status |
| GET/PUT | `/saas/organization/{id}/billing-profile` | Tax / GST / VAT profile |
| GET | `/saas/organization/{id}/limits` | Plan feature limits |
| POST | `/saas/coupon` | Coupon metadata |
| POST | `/saas/checkout` | Checkout session (unavailable without provider) |

Existing `/api/v1/enterprise/*` contracts remain unchanged.

## RC1 Milestone 10 — Production Operations

Aggregation only over existing health/metrics/logging/OTel/backup interfaces.
Full detail: [PRODUCTION_OPERATIONS.md](PRODUCTION_OPERATIONS.md).

| Method | Path | Purpose |
|---|---|---|
| GET | `/ops/schema` | Routes + reuse rules |
| GET | `/ops/health` | Aggregate live/ready/startup/dependencies |
| GET | `/ops/health/live` | Liveness |
| GET | `/ops/health/ready` | Readiness |
| GET | `/ops/health/startup` | Startup / lifecycle |
| GET | `/ops/status` | Lifecycle + component snapshot |
| GET | `/ops/version` | Build / version / uptime |
| GET | `/ops/dependencies` | Dependency aggregation |
| GET | `/ops/metrics` | Metrics summary (`?format=prometheus` for text) |
| GET | `/ops/observability` | Logging / OTel / Prometheus pointers |
| GET | `/ops/backup` | BackupPort status (honest unavailable by default) |
| POST | `/ops/backup` | Backup actions via BackupPort |
| GET | `/ops/secrets` | Vault / rotation interface status |
| GET | `/ops/dashboard` | Production ops dashboard aggregate |

Additive health aliases (reuse same aggregation):

| Method | Path |
|---|---|
| GET | `/health/startup` |
| GET | `/health/dependencies` |

Existing `/health`, `/health/live`, `/health/ready`, `/metrics` remain canonical.

## RC1 Milestone 11 — Super Admin Control Center

Configuration Operating System. Overlays only — never executes valuation/AI/risk
engines. Additive to A010 `/admin/*`. Full detail:
[SUPER_ADMIN_CONTROL_CENTER.md](SUPER_ADMIN_CONTROL_CENTER.md).

| Method | Path | Purpose |
|---|---|---|
| GET | `/admin/control-center/schema` | Modules, routes, reuse rules |
| GET | `/admin/control-center/dashboard` | Control Center overview |
| GET | `/admin/configuration/registry` | Full registry (`?module_id=` for one) |
| POST | `/admin/configuration` | Versioned module update |
| GET | `/admin/configuration/history` | Change history |
| POST | `/admin/rollback` | One-click rollback to version |
| POST | `/admin/branding` | Branding overlay |
| POST | `/admin/cms` | CMS page overlay |
| POST | `/admin/feature-flags/overrides` | Feature flag overrides |
| POST | `/admin/valuation/config` | Valuation config overlay |
| POST | `/admin/ai/config` | AI config overlay |
| POST | `/admin/risk/config` | Risk config overlay |
| POST | `/admin/market/config` | Market settings overlay |
| POST | `/admin/connectors/config` | Connector control overlay |
| GET/POST | `/admin/business-rules` | List / upsert rules |
| DELETE | `/admin/business-rules/{id}` | Delete rule |
| POST | `/admin/notifications/config` | Notifications overlay |
| POST | `/admin/dashboard/layout` | Dashboard layout overlay |
| POST | `/admin/security/config` | Security overlay |
| POST | `/admin/templates/config` | Email/report templates overlay |
| POST | `/admin/saas/control` | SaaS defaults + plans façade |
| GET | `/admin/monitoring` | Ops + Admin metrics façade |
| POST | `/admin/backup/control` | BackupPort façade |
| GET | `/admin/release` | Release / environment profiles |
| GET | `/admin/audit/config` | Configuration audit export |
| GET | `/admin/users-orgs` | Users + organizations façade |

A010 `GET /admin/configuration`, `GET /admin/feature-flags`, `GET /admin/audit`
remain unchanged.

