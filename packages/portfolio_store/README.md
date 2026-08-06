# portfolio_store

**Status: Production · Additive (RC1 Milestone 3)**

Server-side, user-owned persistence for **Portfolio**, **Holdings**,
**Transactions**, and **Watchlist** — replacing browser-`localStorage`-only
storage without redesigning any existing engine.

## Why this package exists (and what it does not do)

This package is a **persistence store only**. It never computes portfolio
analytics — that remains exclusively `packages/portfolio_analytics`
(Sharpe/Sortino/Beta/…) and `dsp_platform.portfolio_intelligence`
(research-object linkage). `portfolio_store` only records *what a user
declared* (holdings, transactions, watchlist symbols, a selected benchmark
symbol) so it survives across sessions/devices — the same records that were
previously trapped in browser `localStorage`.

- **Holdings** are declared in the exact shape
  `portfolio_analytics.PositionInput`/`portfolio_analytics.PortfolioAnalyticsHolding`
  already expects (`symbol`, `weight`, optional `units`/`cost_basis_per_unit`/
  `purchase_date`/`sector`/`country`/`exchange`/factor-proxy scores) — so a
  persisted holding can be handed straight to the existing Portfolio
  Analytics endpoints with zero translation and zero duplicated modeling.
- **Transactions** are an **append-only ledger** (buy/sell/dividend/bonus/
  split/rights/fee/tax/cash_deposit/cash_withdrawal) — a record of what
  happened, not a reconciliation engine. This package does **not** derive
  holdings/weights from transactions automatically; that would be new
  business logic outside this milestone's scope (recorded as a remaining
  gap, not silently invented).

## Architecture (mirrors `packages/enterprise`'s established pattern exactly)

```
PortfolioService (ownership checks: user_id must own portfolio_id)
        ↓
PortfolioStorePort (Protocol)
        ├── InMemoryPortfolioStore   — test / process-local default
        └── DatabasePortfolioStore   — hydrates from / flushes to DatabasePort
                                        (production_platform.DatabasePort,
                                        same duck-typed port enterprise uses;
                                        no import dependency added)
```

`DatabasePortfolioStore` stores one JSON snapshot row per portfolio
(`portfolio_snapshots`, keyed by `portfolio_id`) for the mutable
Portfolio/Holdings/Watchlist working set, and true append-only SQL rows for
`portfolio_transactions` (never updated or deleted by `flush()` — only
inserted), exactly mirroring `enterprise.db_store`'s
snapshot-row + append-only-audit-log pattern.

## Ownership model

Every `Portfolio` belongs to `user_id` (the authenticated principal via
`DSPPlatform.auth_current_user` — the existing institutional auth, EPIC-A009
— never a new auth scheme). `Portfolio.org_id` is carried as an optional,
currently-unused field so **Organization ownership can be layered on later
without a schema migration or redesign** — it is not wired to any
authorization check in this milestone.

A user may have **multiple portfolios**; exactly one is `is_default=True`
at a time (enforced by the service, not by the caller).

## Testing

- `tests/test_models.py` — model validation / `to_dict()` shape.
- `tests/test_service.py` — CRUD, ownership enforcement, multi-portfolio,
  default-portfolio invariants, transaction types, watchlist, benchmark,
  migration idempotency.
- `tests/test_db_store.py` — durability round-trip via
  `production_platform.InMemoryDatabasePort` (rehydrate after restart).
- `tests/test_architecture.py` — dependency/import boundary (no
  `data_engine`/`dsp_platform`/`api_platform`/`contracts` imports; zero
  package dependencies, matching `enterprise`'s convention).
