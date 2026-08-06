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

## Portfolio Store API (RC1 Milestone 3)

Server-side, user-owned persistence for Portfolio/Holdings/Transactions/
Watchlist/Benchmark — replaces browser-only `localStorage`. Thin routers
over `dsp_platform.portfolio_store_facade` / `packages/portfolio_store`; no
business logic, analytics, or valuation here (see
[PORTFOLIO_GUIDE.md](PORTFOLIO_GUIDE.md) for the full architecture and
[PORTFOLIO_ANALYTICS.md](PORTFOLIO_ANALYTICS.md) for the separate quant
engine). Every route below requires authentication
(`Authorization: Bearer <access_token>` or the RBAC session cookie — the
exact same `GET /auth/rbac/me` resolution, no new auth scheme) and enforces
per-user ownership server-side.

Base: `/api/v1`

| Method | Path | Purpose |
|---|---|---|
| GET | `/portfolio/schema` | Schema descriptor (transaction types, capabilities, rules) — no auth required |
| GET | `/portfolio` | List the authenticated user's portfolios (default first) |
| POST | `/portfolio` | Create a portfolio (`name`, `is_default?`, `benchmark_symbol?`, `metadata?`) |
| GET | `/portfolio/{id}` | Get one portfolio (403 if not owned, 404 if missing) |
| PUT | `/portfolio/{id}` | Update `name` / `is_default` / `metadata` |
| DELETE | `/portfolio/{id}` | Delete a portfolio (cascades holdings + watchlist) |
| PUT | `/portfolio/{id}/benchmark` | Set or clear (`null`) the selected benchmark symbol |
| GET | `/portfolio/{id}/holdings` | List holdings |
| POST | `/portfolio/{id}/holdings` | Upsert a holding by `symbol` (create or update in place) |
| DELETE | `/portfolio/{id}/holdings/{symbol}` | Remove a holding |
| GET | `/portfolio/{id}/transactions` | List transactions (`?symbol=`, `?limit=`, newest first) |
| POST | `/portfolio/{id}/transactions` | Record a transaction (append-only ledger) |
| GET | `/portfolio/{id}/watchlist` | List watched symbols |
| POST | `/portfolio/{id}/watchlist` | Add a watched symbol (idempotent) |
| DELETE | `/portfolio/{id}/watchlist/{symbol}` | Remove a watched symbol |
| POST | `/portfolio/migrate` | Local → server migration (see below) |

### Transaction types

`buy`, `sell`, `dividend`, `bonus`, `split`, `rights`, `fee`, `tax`,
`cash_deposit`, `cash_withdrawal`. Transactions are an **append-only
ledger** — a record of what happened, not a reconciliation engine; holdings
are managed independently via the Holdings routes above.

### `POST /portfolio/migrate` — local → server migration

Idempotent: if the authenticated user already has a default portfolio on
the server, the request body is ignored and `migrated: false` is returned
— the server never gets overwritten by a stray retry, and the caller's
local copy is never assumed stale. Only when the user has **no** portfolio
yet does this create one from the supplied snapshot (`migrated: true`).

Request:

```json
{
  "name": "My Portfolio",
  "holdings": [{ "symbol": "AAPL", "weight": 0.6 }, { "symbol": "MSFT", "weight": 0.4 }],
  "watchlist": [{ "symbol": "NVDA" }],
  "benchmark_symbol": "SPY"
}
```

Response (`200`):

```json
{ "ok": true, "result": { "migrated": true, "portfolio": { "portfolio_id": "pf_...", "...": "..." } }, "message": null }
```

### Errors

| HTTP | Meaning |
|---|---|
| 401 | Not authenticated (missing/invalid Bearer token or session cookie) |
| 403 | Authenticated, but does not own the requested portfolio |
| 404 | Portfolio not found |
| 400 | Validation error (e.g. unsupported `transaction_type`, empty `name`) |

## Portfolio Intelligence Engine API (RC1 Milestone 4)

Orchestration layer that combines `portfolio_analytics` (quantitative,
frozen) and EPIC-A002's Research-Object linker into portfolio-level
insights (Health Score, Concentration, Valuation Heatmap, Risk Summary,
Recommendations, Drift, Diversification, Opportunity Finder, Scenario
Summary). Thin routers over `dsp_platform.portfolio_intelligence_engine`;
**no valuation, risk, or AI computation happens in `api_platform`** — see
[PORTFOLIO_GUIDE.md](PORTFOLIO_GUIDE.md#portfolio-intelligence-engine-rc1-milestone-4)
for the full reuse/data-honesty contract.

Stateless — mirrors `/portfolio/analytics/*`: the caller supplies portfolio
holdings (and, optionally, linked Research Objects) in the request body.
Nothing here is persisted server-side. No authentication is required (same
trust boundary as `/portfolio/analytics/*` and `/portfolio/intelligence`).

**Not** the same endpoint as `POST /portfolio/intelligence` (EPIC-A002) —
that endpoint only summarizes caller-linked Research Objects with
`engines_called: false`; this one orchestrates `portfolio_analytics` plus
those same linked Research Objects into new composite scores.

Base: `/api/v1`

| Method | Path | Purpose |
|---|---|---|
| POST | `/portfolio/insights` | Every capability at once |
| POST | `/portfolio/insights/health` | Portfolio Health Score only |
| POST | `/portfolio/insights/recommendations` | AI Recommendations only |
| POST | `/portfolio/insights/opportunities` | Portfolio Opportunity Finder only |
| POST | `/portfolio/insights/scenario` | AI Committee / Scenario Summary only |
| GET | `/portfolio/insights/health-check` | Service health (versions only) |

### Request body

```json
{
  "portfolio": {
    "holdings": [
      { "symbol": "AAPL", "weight": 0.6, "sector": "Information Technology", "country": "US" },
      { "symbol": "XOM", "weight": 0.4, "sector": "Energy", "country": "US" }
    ]
  },
  "research_objects": {
    "AAPL": {
      "metadata": { "ticker": "AAPL" },
      "margin_of_safety": { "available": true, "payload": { "margin_of_safety": 0.22 } },
      "recommendation": { "available": true, "payload": { "confidence": 0.71, "margin_of_safety": 0.22 } },
      "business_quality": { "available": true, "payload": { "score": 78 } }
    }
  },
  "benchmark_symbol": "SPY",
  "window_days": 252,
  "cash_weight": 0.05,
  "as_of": "2024-01-11"
}
```

`research_objects` (and `reports`/`snapshots`/`snapshot_ids`) are
**optional** and use the exact same shape `POST /portfolio/intelligence`
already accepts (EPIC-A002 pass-through). When omitted, valuation/quality/
committee-dependent fields are honestly `null`/empty with a `limitations`
message; Risk Summary, Diversification Score, and Concentration Analysis
remain fully available from `portfolio_analytics` alone. `cash_weight` and
`stress_window_ids` are only accepted by `/portfolio/insights` and
`/portfolio/insights/health` (cash allocation only affects the Health
Score).

### Response (`POST /portfolio/insights`, `200`)

```json
{
  "ok": true,
  "available": true,
  "message": null,
  "service_version": "1.0.0",
  "holding_count": 2,
  "health_score": { "status": "partial", "score": 62.4, "components": [ "..." ], "limitations": [] },
  "concentration": { "status": "complete", "largest_holdings": [ "..." ], "flags": [], "limitations": [] },
  "valuation_heatmap": { "status": "partial", "rows": [ "..." ], "limitations": [] },
  "risk_summary": { "status": "partial", "beta": null, "value_at_risk_95": 0.18, "value_at_risk_method": "...", "conditional_value_at_risk_95": null, "limitations": [] },
  "recommendations": [ { "symbol": "AAPL", "action": "increase", "reason": "...", "confidence": 0.71 } ],
  "drift": { "status": "partial", "sector_drift": [ "..." ], "missing_sectors": [ "..." ], "limitations": [] },
  "diversification": { "status": "partial", "score": 55.2, "explanation": [ "..." ], "limitations": [] },
  "opportunities": { "status": "partial", "highest_margin_of_safety": [ "..." ], "highest_expected_cagr": [], "limitations": [ "Data unavailable. No single-company forward-looking equity CAGR..." ] },
  "scenario": { "status": "partial", "cases": [ "..." ], "expected_cagr_basis": "Trailing realized annualized portfolio return...", "limitations": [] },
  "limitations": []
}
```

When no holdings are supplied, every endpoint returns
`{ "ok": true, "available": false, "message": "Data unavailable.", "limitations": [...] }`
— never a fabricated result.

### Errors

| HTTP | Meaning |
|---|---|
| 503 | Unhandled server-side error computing the result (`available: false`, `message: "Data unavailable."`) |
