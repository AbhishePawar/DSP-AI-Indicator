# portfolio_analytics

**Status: Production · Additive (new package)**

Pure-computation quantitative analytics engine for the Portfolio Intelligence
workspace. Ports & Adapters: this package performs **no I/O** — it accepts
already-fetched price/return history and portfolio composition, and returns
immutable, honestly-empty-when-unavailable result models.

## Scope

- **Performance**: Sharpe, Sortino, Treynor, Jensen's Alpha, Beta, Tracking
  Error, Information Ratio. Maximum Drawdown is **reused** from
  `quantitative_risk.QuantitativeRiskEngine` (never recomputed here).
- **Risk**: Correlation Matrix, Portfolio Heatmap, Risk Attribution, Factor
  Exposure (weighted rollup of caller-supplied per-security signals only).
- **Allocation**: Sector Allocation, Country Allocation.
- **Simulation**: Monte Carlo (bootstrap resampling), Efficient Frontier
  (mean-variance random-weight sampling) — both explicitly documented as
  approximations.
- **Stress**: Scenario Analysis (caller-defined shocks), Stress Testing
  (historical crash-window replay).
- **Constraints**: Position Limits (breach detection), Rebalancing (drift +
  suggested deltas — analysis only, never a trade instruction).
- **Tax**: unrealized gain/loss, holding-period classification, tax-loss
  harvesting candidates.

## Why this package exists (and not `portfolio` or `quantitative_risk`)

Both `packages/portfolio` (EPIC-A002) and `packages/quantitative_risk`
(E2.2/E2.3) are marked **Production · Frozen** — see their own READMEs. This
package is additive: it reuses `quantitative_risk.QuantitativeRiskEngine` for
Maximum Drawdown via its public `calculate()` API (a small in-process
`MarketDataPort`/`HistoricalReturnsPort`/`BenchmarkDataPort` shim, not a
reimplementation), and never modifies either frozen package.

## Data honesty (CV-001 / CV-005)

Every public function returns `None` (or a result field explicitly marked
unavailable) when it cannot compute a metric from the inputs it was given —
insufficient history, a missing benchmark, or missing cost-basis data. No
value is ever fabricated or defaulted to zero to "fill a gap".

## Dependencies

`core` (exceptions/validation) and `quantitative_risk` (Maximum Drawdown
reuse only). No `data_engine`, `dsp_platform`, `contracts`, or `api_platform`
imports — enforced by `tests/test_architecture.py`.
