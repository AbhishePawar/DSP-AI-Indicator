# portfolio_intelligence_engine

**RC1 Milestone 4 — the "Portfolio Intelligence Engine".**

A pure-Python **combination/scoring layer**. It performs **zero I/O, zero
provider calls, zero valuation/risk/AI computation**. It only *combines*
numbers that other, already-frozen engines have already computed.

## What this package is

An orchestration layer that takes **already-computed signals** — one
`HoldingSignal` per portfolio position, plus already-computed portfolio-level
aggregates (performance ratios, Monte Carlo, correlation matrix, sector /
country allocation, risk attribution) — and *combines* them into
portfolio-level intelligence:

1. Portfolio Health Score (0–100)
2. Concentration Analysis
3. Valuation Heatmap (classification only — reuses caller-supplied MoS)
4. Risk Summary (aggregation + highlighting only)
5. AI Recommendations (rule-based combination, never a new model)
6. Sector & Style Drift
7. Diversification Score
8. Portfolio Opportunity Finder (ranking only)
9. Portfolio Scenario / Committee Summary (Bull/Base/Bear band)

## What this package is **not**

- **Not** a valuation engine. It never computes intrinsic value, fair value,
  or margin of safety — those numbers must already exist (produced by the
  frozen `valuation` engine, surfaced via Research Objects /
  `dsp_platform.evaluate_portfolio_intelligence`, EPIC-A002).
- **Not** a risk engine. Beta, volatility, max drawdown, tracking error, VaR
  proxy, Monte Carlo, and stress tests are all computed by
  `portfolio_analytics` (RC1 Milestone 1/Portfolio Analytics module,
  frozen) and passed in as-is.
- **Not** an AI Committee. It never runs a new LLM/committee vote; the
  "Portfolio Scenario Summary" is a transparent, disclosed weighted
  aggregation of already-computed per-holding valuation/committee signals
  plus the portfolio's own historical volatility/drawdown (from
  `portfolio_analytics`).
- **Not** a data connector. It never calls a market-data or fundamentals
  provider.

## Data honesty (CV-001 / CV-005)

Every function returns an explicit `status` (`complete` / `partial` /
`unavailable`) and a `limitations` tuple. When a required upstream signal is
missing (e.g. no linked valuation for a holding, no caller-declared cash
weight, no caller-declared industry/style), the corresponding sub-result is
`None`/omitted with an honest reason — **never fabricated, never
interpolated, never guessed**.

Two derived metrics are intentionally *labelled as proxies*, not as new
calculations of their own:

- **Value at Risk (95%)** is the 5th-percentile terminal return already
  produced by `portfolio_analytics.compute_monte_carlo` (bootstrap
  resampling), simply relabelled/negated. **Conditional VaR / Expected
  Shortfall is reported as unavailable** — no engine in the platform exposes
  the full tail distribution needed to compute it honestly, and this
  package does not invent one.
- **"Expected CAGR"** and **"worst-case drawdown"** in the Portfolio
  Scenario Summary are the portfolio's own **trailing realized** annualized
  return and max drawdown (from `portfolio_analytics.evaluate_portfolio_performance`
  / stress tests) — clearly documented as historical, not a forecast. No
  single-company forward-looking equity CAGR exists anywhere in the frozen
  engines, so this package does not synthesize one.

## Where the orchestration happens

This package holds **only** the combination logic. The actual calls into
`portfolio_analytics` (quantitative) and `dsp_platform.evaluate_portfolio_intelligence`
(EPIC-A002, qualitative/research-linked) happen one layer up, in
`dsp_platform.portfolio_intelligence_engine_facade`, which builds the
`HoldingSignal` tuple this package consumes. See
`docs/PORTFOLIO_GUIDE.md` §"Portfolio Intelligence Engine" for the full data
flow diagram.
