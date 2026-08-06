# Portfolio Guide — Server-Side Persistence (RC1 Milestone 3)

Status: **COMPLETE**
Priority: P0 · Portfolio Platform Foundation
Supersedes: browser-`localStorage`-only Portfolio persistence
Related: [PORTFOLIO_ANALYTICS.md](PORTFOLIO_ANALYTICS.md) (quantitative
engine — unaffected, reused as-is), [EPIC_A002_PORTFOLIO_GUIDE.md](EPIC_A002_PORTFOLIO_GUIDE.md)
(read-only research-object linker — unaffected, reused as-is), [API_GUIDE.md](API_GUIDE.md#portfolio-store-api-rc1-milestone-3)
(endpoint reference)

## Goal

Replace the browser-only `localStorage` Portfolio persistence with a
production-grade, server-side persistence layer for **Portfolio**,
**Holdings**, **Transactions**, and **Watchlist/Benchmark** — without
redesigning Portfolio Analytics, Authentication, the Company Workspace, the
Data Connector Framework, the AI Committee, the Risk Engine, the Export
Engine, or the API Architecture. Existing browser users must not lose data.

## Architecture

```
[Web thin client]
   PortfolioProvider / usePersistence()  — SAME public interface as before
        ↓
[apps/web/src/lib/portfolio/repository.ts]  — Repository layer (new)
   maps PortfolioHolding <-> ServerHolding; wraps every api.portfolio* call
        ↓
[apps/web/src/lib/api/client.ts]  — api.portfolio{List,Create,Get,Update,
   Delete,SetBenchmark,ListHoldings,UpsertHolding,RemoveHolding,
   ListTransactions,RecordTransaction,ListWatchlist,AddWatchlistSymbol,
   RemoveWatchlistSymbol,Migrate}
        ↓  (Authorization: Bearer <token> or RBAC session cookie)
[api_platform]  routers/portfolio.py   (thin; no business logic;
                 Depends(get_current_user_id) on every route)
        ↓
[dsp_platform]  DSPPlatform.{create_portfolio, list_portfolios, ...}
        ↓
[dsp_platform.portfolio_store_facade]  thin pass-through
        ↓
[portfolio_store]  (new package) PortfolioService
   ownership-checked CRUD — mirrors packages/enterprise's EXACT pattern
        ↓
PortfolioStorePort (Protocol)
   ├── InMemoryPortfolioStore   — process-local default / tests
   └── DatabasePortfolioStore   — hydrates from / flushes to a DatabasePort
                                   (production_platform.DatabasePort — the
                                   same duck-typed port enterprise already
                                   uses; no new persistence architecture)
```

## Why this reuses `enterprise`'s pattern instead of `packages/persistence`

`packages/persistence` (EPIC-A008) is explicitly scoped to "references and
metadata only — research artifact payloads are never stored" (workflow
records, audit records, citations, provenance) and its storage layer has no
per-user partitioning built in. Portfolio Holdings/Transactions are
business data with a completely different shape and access pattern
(inherently per-user, potentially large transaction histories), so reusing
that package would have meant bending its documented scope.

`packages/enterprise` already solved exactly this class of problem —
durable, ownership-scoped domain records over a `DatabasePort` — via
`EnterpriseStorePort` / `InMemoryEnterpriseStore` / `DatabaseEnterpriseStore`
(JSON snapshot rows + an append-only audit log, hydrated at construction,
flushed on every mutation). `portfolio_store` mirrors this pattern exactly:
`PortfolioStorePort` / `InMemoryPortfolioStore` / `DatabasePortfolioStore`,
with one JSON snapshot row per **portfolio** (not one global blob) plus a
true append-only SQL table for the transaction ledger — the same
snapshot-row + append-only-log design, at a finer grain appropriate to
per-user portfolios. No new persistence architecture was invented.

Like `enterprise`, `portfolio_store` has **zero package dependencies** — it
duck-types the `DatabasePort` (`execute`/`fetchall`) rather than importing
`production_platform`, exactly matching `enterprise.db_store`'s convention.

## Ownership model

Every `Portfolio` belongs to `user_id` — the authenticated principal
resolved via `DSPPlatform.auth_current_user()`, the **existing**
institutional auth (EPIC-A009). `get_current_user_id` (a new FastAPI
dependency in `api_platform.api.dependencies`) performs the exact same
resolution `GET /auth/rbac/me` already does (Bearer token first, RBAC
session cookie fallback) — no new auth scheme, no new login flow.

- **Multiple portfolios**: a user may own any number of portfolios.
- **Default portfolio**: exactly one portfolio per user has `is_default =
  true` at all times — enforced by `PortfolioService`, never by the
  caller. The user's first portfolio is always the default; deleting the
  default promotes the next-oldest remaining portfolio.
- **Personal portfolios**: `Portfolio.org_id` exists on the model today but
  is **unused** — reserved so Organization ownership (e.g. authorizing by
  org membership instead of/alongside `user_id`) can be layered on later
  **without a schema migration or redesign**.
- Every service method enforces ownership: `ForbiddenError` (HTTP 403) if
  `portfolio.user_id != user_id`; `NotFoundError` (HTTP 404) if the
  portfolio doesn't exist at all.

## What is (and is not) stored here

| Stored by `portfolio_store` | Computed by (unmodified) |
|---|---|
| Portfolio name, default flag, benchmark symbol selection | — |
| Holdings: symbol, weight, and the same optional fields `portfolio_analytics.PositionInput` already accepts (`units`, `cost_basis_per_unit`, `purchase_date`, `sector`, `country`, `exchange`, factor-proxy scores) | Sharpe/Sortino/Beta/etc. — `packages/portfolio_analytics` (unchanged) |
| Transactions: an append-only ledger of buy/sell/dividend/bonus/split/rights/fee/tax/cash_deposit/cash_withdrawal events | — |
| Watchlist symbols per portfolio | — |

Holdings are declared in the **exact same shape** the already-shipped
Portfolio Analytics endpoints expect — a persisted holding can be handed
straight to `POST /portfolio/analytics/performance` etc. with zero
translation, and no calculation is duplicated anywhere in this milestone.
Transactions are a **ledger only** — this milestone does not derive
holdings/weights from transaction history automatically (see Remaining
Gaps below); that would be new reconciliation business logic outside this
milestone's scope.

## Migration strategy

On first authenticated load, `PersistenceProvider` (frontend) performs
exactly this decision, once per signed-in user:

```
IF   a server default portfolio already exists
     → use the server copy as the source of truth for holdings
     (local savedAnalyses/copilotConversations/preferences are untouched —
     out of scope for this milestone)

ELSE IF localStorage has a portfolio (holdings, possibly empty)
     → POST /portfolio/migrate with the local snapshot
     → the server creates the user's default portfolio from it
     → the returned portfolio_id becomes the sync target for all
       subsequent holding/watchlist/benchmark mutations

Local data is NEVER deleted by this flow, regardless of outcome. If the
migration call fails (network, server error), the UI keeps serving the
local copy exactly as before this milestone, and simply retries the
reconciliation on the next authenticated load.
```

The backend half (`PortfolioService.migrate_local_portfolio` /
`POST /portfolio/migrate`) is **idempotent**: if the user already has a
default portfolio, the call is a no-op (`migrated: false`) and the
supplied local snapshot is discarded — a retry (e.g. a second browser tab,
a flaky network causing a duplicate request) can never overwrite server
data with a stale local copy.

After the initial reconciliation, `PersistenceProvider.persistPortfolio()`
(unchanged public signature) additionally diffs the new holdings list
against the last-known server state and pushes only the delta (upserts +
removals) to the server — best-effort, never blocking the always-on local
save that already existed before this milestone.

Watchlist and Benchmark follow the identical "server exists → adopt; else
push local up" reconciliation, performed once per resolved
`serverPortfolioId` inside `PortfolioIntelligenceWorkspace` (see
`usePortfolioIntelPrefsStore` for the local session store those two fields
already lived in since RC1 Milestone 1 — unchanged public API, this
milestone only adds a server-sync side effect around it).

## Frontend — preserved public interfaces

No component outside `PersistenceProvider.tsx` and
`PortfolioIntelligenceWorkspace.tsx` needed to change:

- `usePortfolio()` (`PortfolioProvider`) — identical shape
  (`holdings`, `addHolding`, `removeHolding`, …).
- `usePersistence()` (`PersistenceProvider`) — identical existing fields
  (`portfolioView`, `persistPortfolio`, `isLoaded`, …) **plus** three new,
  purely additive fields consumers may ignore:
  `serverPortfolioId`, `portfolioSyncStatus`
  (`idle|syncing|synced|error`), `portfolioSyncError`.
- `usePortfolioIntelPrefsStore` (watchlist/benchmark) — identical actions;
  the server-sync side effects live in the workspace component, not the
  store itself.

## Testing

- `packages/portfolio_store/tests/` — models, service (CRUD, ownership,
  multi-portfolio, default-portfolio invariants, every transaction type,
  watchlist, benchmark, migration idempotency), durability round-trip via
  `production_platform.InMemoryDatabasePort` (rehydrate after simulated
  restart), architecture boundary (zero dependencies, no forbidden
  imports).
- `packages/dsp_platform/tests/test_portfolio_store_facade.py` — façade
  wiring + `DSPPlatform` delegation.
- `packages/api_platform/tests/test_portfolio_api.py` — full endpoint
  coverage: auth-required (401), ownership (403/404), multi-portfolio,
  default-portfolio invariant, every transaction type, migration
  (including idempotent retry), watchlist, benchmark.
- `apps/web/src/lib/portfolio/repository.test.ts` — mapping functions +
  every repository call against a mocked `api` client.
- `apps/web/src/providers/PersistenceProvider.test.tsx` — the full
  migration strategy end-to-end: server-exists → adopt; server-empty →
  migrate (including an empty local portfolio); honest degrade (local data
  preserved) on server failure; unauthenticated → zero server calls;
  migration attempted exactly once per subject.
- `apps/web/src/lib/portfolio-intelligence/portfolio-intelligence.test.tsx`
  — workspace renders correctly with the new sync wiring; watchlist/
  benchmark reconciliation calls the repository as expected.

## Performance

- Holdings sync diffs against the last-known server state and only sends
  the delta (changed/added/removed symbols), not the full holdings list,
  on every `persistPortfolio` call.
- `DatabasePortfolioStore.flush()` rewrites all portfolio snapshot rows on
  each mutation (same trade-off `enterprise.db_store` already makes with
  its single global snapshot) — acceptable at per-user portfolio scale;
  transactions are true append-only inserts, never rewritten.
- All server sync is best-effort and asynchronous relative to the
  always-on local save — a slow or failing network call never blocks the
  UI or loses the local copy.

## Security review

- Every route requires authentication; there is no route that accepts a
  caller-supplied `user_id` — it is always resolved server-side from the
  validated access token/session, so no client can impersonate another
  user's portfolio by guessing an id.
- Ownership is checked on every single operation (get/update/delete
  portfolio; list/upsert/remove holding; record/list transaction; list/
  add/remove watchlist symbol) — verified by dedicated 403 tests for each
  resource family.
- No new secrets, no new token format, no new login flow — reuses
  `DSPPlatform.auth_current_user`, the same JWT/session validation already
  used by `GET /auth/rbac/me`.

## Remaining gaps (recorded honestly, not silently worked around)

- **No transaction → holding reconciliation.** Recording a `buy`
  transaction does not automatically update the corresponding holding's
  `weight`/`units` — Transactions are an independent ledger. Building a
  reconciliation engine (realized/unrealized P&L, lot tracking, wash-sale
  awareness) is a distinct, larger milestone.
- **No bulk holdings endpoint.** The frontend repository reconciles
  holdings via N per-symbol calls (upsert/remove), not a single batch
  request — fine at typical portfolio sizes, but a candidate for a future
  bulk endpoint if portfolios grow very large.
- **`DatabasePort` is in-memory only today** (`InMemoryDatabasePort`) —
  the same limitation `packages/enterprise` already documents; a real
  Postgres-backed `DatabasePort` implementation is a separate,
  infrastructure-level piece of work that both packages will benefit from
  identically once it exists.
- **Multi-portfolio switching UI.** The backend and repository fully
  support multiple portfolios per user (tested), but the existing
  workspace UI still primarily surfaces one "active" portfolio at a time
  (`usePortfolioIntelPrefsStore.activePortfolioId`, cosmetic labels today).
  Wiring a true multi-portfolio switcher to real, distinct server
  portfolios is additional frontend UI work, intentionally out of scope
  here to respect "no redesign."
