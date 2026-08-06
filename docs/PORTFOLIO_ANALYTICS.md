# Portfolio Intelligence Analytics Module

Status: **COMPLETE**
Priority: P0 · Institutional Portfolio Analytics
Supports: **CV-001** · **CV-002** · **CV-004** · **CV-005** · **CV-009** · RS compliance (thin client honesty)

## Goal

Add real quantitative portfolio analytics — Performance ratios, Risk
Attribution, Factor Exposure, Sector/Country Allocation, Monte Carlo,
Efficient Frontier, Stress Testing, Scenario Analysis, Position Limits,
Rebalancing, and Tax Optimization — **without** duplicating any existing
engine, without modifying the two frozen packages this effort reuses
(`packages/portfolio`, `packages/quantitative_risk`), and without adding
business logic to API routers.

## Architecture

```
[Web thin client]
   POST /api/v1/portfolio/analytics/{performance|risk|allocation|
        simulation|stress|constraints|tax}
   GET  /api/v1/portfolio/analytics/health
        ↓
[api_platform]  routers/portfolio_analytics.py   (no business logic;
                 validates request shape, delegates, maps to JSON envelope)
        ↓
[dsp_platform]  DSPPlatform.evaluate_portfolio_*() / portfolio_analytics_health()
        ↓
[dsp_platform.portfolio_analytics]
   service.py    parses caller's stateless {"holdings": [...]} payload into
                 PositionInput objects, resolves price history per symbol
                 via the adapter, calls the pure engine, returns an honest
                 public dict
   adapter.py    HistoricalSeriesPriceHistoryAdapter(PriceHistoryPort) —
                 wraps dsp_platform.historical_series (EPIC-D004, reused)
        ↓
[portfolio_analytics]  (new, pure computation, Ports & Adapters)
   ports.py        PriceHistoryPort Protocol — no I/O in this package
   models.py        PositionInput + every result model (frozen dataclasses)
   performance.py   Sharpe/Sortino/Treynor/Alpha/Beta/TE/IR; Max Drawdown
                     delegates to quantitative_risk.QuantitativeRiskEngine
   correlation.py    Correlation matrix + portfolio heatmap
   risk_attribution.py   Per-position risk contribution (reuses correlation.py)
   factor_exposure.py    Weighted rollup of caller-supplied per-security signals
   allocation.py    Sector allocation (parallel impl.) + Country allocation (new)
   simulation.py    Monte Carlo (bootstrap) + Efficient Frontier (random sampling)
   stress.py        Scenario Analysis (beta sensitivity) + Stress Testing (replay)
   constraints.py   Position Limits (breach checks) + Rebalancing (drift/deltas)
   tax.py           Tax Optimization (unrealized gain/loss, loss harvesting)
        ↓ (Max Drawdown reuse only, via public calculate() API)
[quantitative_risk]  (frozen, reused — never modified)
   QuantitativeRiskEngine.calculate() — driven with a small in-process
   MarketDataPort/HistoricalReturnsPort/BenchmarkDataPort shim built from
   the caller's already-resolved return series
```

## Why a new package, and why it does not touch `portfolio` or `quantitative_risk`

- `packages/portfolio` (EPIC-A002) and `packages/quantitative_risk`
  (E2.2/E2.3) are both marked **Production · Frozen** in their own
  READMEs, which explicitly forbid adding new analytics to them without a
  new epic/ADR.
- `dsp_platform.portfolio_intelligence` (the existing "Portfolio
  Intelligence" façade) is a read-only research-object linker by design —
  its own schema declares `no_provider_calls`, `no_valuation_calculations`,
  `no_optimisation`. It is architecturally the wrong place for real
  quantitative math, so it is left untouched and additive.
- `portfolio_analytics` is deliberately **not** named
  `portfolio_intelligence` to avoid confusion with that existing EPIC-A002
  module — the two are separate, additive capabilities.

## Reuse table

| Capability | Source | How |
|---|---|---|
| Maximum Drawdown | `quantitative_risk.QuantitativeRiskEngine` | `performance.compute_max_drawdown_via_quantitative_risk` drives the frozen engine's public `calculate()` with a minimal single-weight/whole-series shim — never reimplements the drawdown formula |
| Price/return history | `dsp_platform.historical_series` (EPIC-D004) | `HistoricalSeriesPriceHistoryAdapter` derives daily returns from authenticated OHLCV close prices; no new provider integration |
| Portfolio/Watchlist holdings shape | `dsp_platform.portfolio_intelligence` (EPIC-A002) | The new endpoints accept the same `{"holdings": [...]}` shape; "Portfolio" and "Watchlist" from the requirements are intentionally not re-implemented as standalone endpoints |
| Sector Allocation | New parallel implementation in `allocation.py` | `packages/portfolio` is frozen, so the weight-grouped-by-sector logic is reimplemented (not imported) in the additive package |

Everything else — Sharpe, Sortino, Treynor, Alpha, Beta, Tracking Error,
Information Ratio, Correlation Matrix, Portfolio Heatmap, Risk Attribution,
Factor Exposure, Country Allocation, Monte Carlo, Efficient Frontier,
Scenario Analysis, Stress Testing, Position Limits, Rebalancing, and Tax
Optimization — is genuinely new: no package anywhere in the platform
computed these before this module (confirmed by a dedicated exploration
pass; `research`/`risk`/`portfolio`'s forbidden-word guards even hard-block
words like "sharpe"/"beta"/"alpha"/"var" from ever appearing in their
qualitative outputs, and `quantitative_risk`'s engine docstring explicitly
lists Sharpe/VaR as "deferred metrics").

## Statelessness

Like `/portfolio/intelligence`, every endpoint is a stateless `POST` — the
caller supplies portfolio holdings (symbol, weight, and optional
`units`/`cost_basis_per_unit`/`purchase_date`/`sector`/`country`/`exchange`/
factor-proxy scores) in the request body. Nothing is persisted server-side
by this module.

## Endpoints (thin routers, no business logic)

| Endpoint | Capabilities |
|---|---|
| `POST /api/v1/portfolio/analytics/performance` | Sharpe, Sortino, Treynor, Alpha, Beta, Tracking Error, Information Ratio, Max Drawdown |
| `POST /api/v1/portfolio/analytics/risk` | Risk Attribution, Factor Exposure, Correlation Matrix, Portfolio Heatmap |
| `POST /api/v1/portfolio/analytics/allocation` | Sector Allocation, Country Allocation |
| `POST /api/v1/portfolio/analytics/simulation` | Monte Carlo, Efficient Frontier |
| `POST /api/v1/portfolio/analytics/stress` | Scenario Analysis, Stress Testing |
| `POST /api/v1/portfolio/analytics/constraints` | Position Limits, Rebalancing |
| `POST /api/v1/portfolio/analytics/tax` | Tax Optimization |
| `GET /api/v1/portfolio/analytics/health` | Price-history source health |

Every handler only calls the matching `state.platform.evaluate_portfolio_*`
method and maps the result to a JSON envelope (`ok`, `available`, per-field
`status`/`"Data unavailable."`, `message`). No aggregation, scoring, or
optimization math lives in `api_platform`.

## Method catalog (method IDs)

| Method ID | Formula |
|---|---|
| `dsp.portfolio_analytics.method.monte_carlo.bootstrap.v1` | Bootstrap resampling of historical daily returns |
| `dsp.portfolio_analytics.method.efficient_frontier.random_weight_sampling.v1` | Mean-variance random-weight sampling, Pareto-filtered |
| `dsp.portfolio_analytics.method.scenario.beta_sensitivity.v1` | `shock_pct × beta` per position |
| `dsp.qrisk.method.drawdown.max.v1` | Reused verbatim from `quantitative_risk` |

Formulas (all operate on aligned daily-return `float` series; `rf` = daily
risk-free rate):

- **Sharpe** = `mean(r − rf) / stdev(r) × √252`
- **Sortino** = `mean(r − rf) / downside_deviation(r − rf) × √252`
- **Beta** = `Cov(portfolio, benchmark) / Var(benchmark)`
- **Treynor** = `annualized(mean(r) − rf) / beta`
- **Jensen's Alpha** = `annualized(r) − [rf + beta × (annualized(benchmark) − rf)]`
- **Tracking Error** = `stdev(r − benchmark) × √252`
- **Information Ratio** = `annualized(r − benchmark) / tracking_error`
- **Correlation** = Pearson correlation of two aligned daily-return series
- **Risk contribution** = `weight × volatility × correlation_to_portfolio`, normalized to sum to 1 across positions
- **Country allocation** = declared `country`, else `exchange → country` lookup table (`EXCHANGE_COUNTRY_TABLE`), else `unclassified` (never guessed)

## Approximation-method disclosures (CV-005 — transparency over confidence)

- **Monte Carlo** bootstrap-resamples the *supplied* historical daily-return
  series with replacement; it assumes future returns are drawn from the
  same historical distribution. Seedable for deterministic tests
  (`seed` parameter).
- **Efficient Frontier** randomly samples weight vectors over the
  historical covariance structure implied by the aligned return series and
  keeps only the Pareto-non-dominated points; it is an approximation, never
  a closed-form quadratic optimization.
- **Stress Testing** replays a named historical crash window
  (`gfc_2008`: 2008-09-01 → 2009-03-09; `covid_2020`: 2020-02-19 →
  2020-03-23) using each holding's **actual** historical returns in that
  window when available, falling back to a beta-scaled estimate of the
  **benchmark's own actual return** during that window (never a fabricated
  constant) only when a position's own history is missing — and always
  discloses `positions_with_history` vs. `positions_beta_scaled`.
- **Rebalancing** is explicitly labeled analysis only — `RebalancingPlan.disclaimer`
  states it is never a trade recommendation or order instruction.

## Honest-empty-state rules (CV-001 / CV-005)

Every public function/endpoint returns `None`/`"Data unavailable."`/an
explicit `status: "unavailable"` (or `"partial"` when some but not all
inputs are present) rather than fabricating a value, specifically:

- No benchmark supplied or benchmark history unavailable → beta, alpha,
  treynor, tracking error, information ratio stay `null`; other metrics
  (Sharpe, Sortino, Max Drawdown) remain available.
- No overlapping authenticated price history across all holdings →
  performance/risk/simulation results are `unavailable`.
- No declared `sector`/`country`/`exchange` → that position falls into
  `unclassified_weight`, never guessed.
- No per-security factor-proxy score (`value_score`, `quality_score`, etc.)
  → that factor's `exposure_value` is `null`, and the position is excluded
  from that factor's weighted average (never defaulted to 0).
- No `cost_basis_per_unit`/`purchase_date`/current price → that position's
  tax lot is `available: false` with an explicit `reason_unavailable`.
- Unknown `stress_window_id` → an honest per-scenario `available: false`
  with `message`, never silently dropped or guessed.

## Limitations

- No wash-sale or multi-lot transaction history — Tax Optimization treats
  each position as a single lot from the caller-supplied cost basis.
- Factor Exposure performs **aggregation only** — it does not compute new
  fundamental scores; callers must supply per-security proxies (e.g. Value
  = margin-of-safety from a Research Object's `ValuationSummary`, Quality =
  business/financial quality label, Momentum = trailing return, Size =
  market-cap bucket, Low-volatility = realized volatility).
- Country Allocation's exchange lookup table is intentionally small and
  explicit (`EXCHANGE_COUNTRY_TABLE` in `allocation.py`) — an unrecognized
  exchange is `unclassified`, never guessed.

## Frontend wiring

`apps/web/src/lib/api/client.ts` exposes
`api.portfolioAnalytics{Performance,Risk,Allocation,Simulation,Stress,
Constraints,Tax,Health}` plus typed payloads. A new
`usePortfolioAnalyticsQueries` hook (`lib/portfolio-intelligence/`) wraps
them behind React Query, and `mapPortfolioAnalytics.ts` maps every payload
into display-ready view objects using the existing honest-`display()`
pattern from `mapPortfolioIntelligence.ts`.

- **Wired into existing sections** (`FlagshipSections.tsx`): `PerformanceSection`
  (full ratio panel), `RiskSection` (Risk Attribution + Factor Exposure
  rollup), `AllocationSection` (weight-based Sector + Country Allocation),
  `RebalancingSection` (rebalancing trades + position-limit breaches).
- **New sections** (`AnalyticsSections.tsx`, no prior placeholder):
  Correlation Matrix (color-scaled table), Efficient Frontier (inline-SVG
  scatter + table, no new chart dependency), Monte Carlo (percentile
  table), Stress Testing, Scenario Analysis, Tax Optimization, Position
  Limits, Factor Exposure — registered in `sections.ts` and the left-nav
  "Analytics" group.

Session holdings (`PortfolioHolding`) only carry `allocationPercent` and
`sector` today, so Country Allocation, Factor Exposure, and Tax
Optimization honestly report unavailable until the session holdings model
gains `exchange`/`country`/factor-score/`cost_basis`/`purchase_date`
fields — the plumbing exists end-to-end and lights up the moment those
inputs are present, exactly like the Data Connector Framework's
"Data unavailable — no data source connected." convention.

### Benchmark selection (RC1 milestone)

`evaluate_portfolio_performance`/`evaluate_portfolio_stress_analytics` have
always accepted an optional `benchmark_symbol`, but the workspace never
collected one from the user — Beta, Jensen's Alpha, Treynor Ratio, Tracking
Error, and Information Ratio were therefore always `"Data unavailable."` in
production even though the backend fully supports them. A `BenchmarkSelector`
component (common presets — `SPY`, `QQQ`, `DIA`, `NIFTYBEES` — plus free-text
custom entry) now lives in the workspace toolbar, backed by a new persisted
`benchmarkSymbol` field on `usePortfolioIntelPrefsStore` (same
Zustand + `localStorage` pattern already used for `watchlist`/`portfolios`).
The selected symbol flows through `usePortfolioAnalyticsQueries` into every
query that accepts a benchmark — no backend change was needed; this was a
pure activation of already-built, already-tested engine capability.

## Testing

- `packages/portfolio_analytics/tests/test_*.py` — pure-function unit
  tests per formula module, verified against closed-form/synthetic cases
  (Beta of a series vs. itself = 1.0, self-correlation = 1.0, Max Drawdown
  round-trips through `quantitative_risk`, deterministic Monte Carlo/
  Efficient Frontier with a fixed seed).
- `packages/dsp_platform/tests/test_portfolio_analytics.py` — façade
  wiring against a seeded `InMemoryAuthenticatedHistoricalAdapter`,
  missing-data honesty.
- `packages/api_platform/tests/test_portfolio_analytics_api.py` —
  endpoint contracts, default-unavailable + populated cases.
- `apps/web/src/lib/portfolio-intelligence/mapPortfolioAnalytics.test.ts`,
  `apps/web/src/components/portfolio-intelligence/AnalyticsSections.test.tsx`,
  and extended `portfolio-intelligence.test.tsx` — mapper honesty, new
  section default/populated rendering, and workspace routing for every new
  section id.

## Compliance

| Rule | Result |
|---|---|
| Ports & Adapters architecture followed | PASS |
| No business logic in API routers | PASS |
| Reuses existing valuation/research/risk engines; no duplicate calculations | PASS |
| Frozen packages (`portfolio`, `quantitative_risk`) left unmodified | PASS |
| Missing data → `"Data unavailable."` / explicit `unavailable` status (never fabricated) | PASS |
| Approximation methods (Monte Carlo, Efficient Frontier) explicitly disclosed | PASS |
| Rebalancing explicitly labeled analysis only — never a trade instruction | PASS |
| No breaking API / engine changes (fully additive) | PASS |
| CV-001 / CV-002 / CV-004 / CV-005 / CV-009 | PASS |

## Final

**PASS** — production-ready, additive Portfolio Intelligence Analytics
module covering Performance, Risk Attribution, Factor Exposure, Sector/
Country Allocation, Monte Carlo, Efficient Frontier, Scenario Analysis,
Stress Testing, Position Limits, Rebalancing, and Tax Optimization, wired
end to end from the pure engine through `dsp_platform`, `api_platform`,
and the Portfolio Intelligence Workspace UI.
