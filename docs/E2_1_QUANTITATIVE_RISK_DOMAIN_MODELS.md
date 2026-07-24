# Phase E2.1 — Quantitative Risk Domain Models

**Status:** Implemented · Structure only · No calculations / engines

**Package:** `packages/quantitative_risk/` **0.1.0**  
**Freeze:** [E2.0A](E2_0A_QUANTITATIVE_RISK_ARCHITECTURE_FREEZE.md)

## Ownership

Quantitative Risk owns **only**:

| Model | Role |
|---|---|
| `QuantitativeRiskIdentity` | Session / profile identity |
| `QuantitativeRiskProfile` | Aggregate root |
| `RiskMetric` | Measurable metric contract (Decimal) |
| `RiskExposure` | Exposure decomposition |
| `RiskConcentration` | Concentration container |
| `RiskCorrelation` | Correlation shell |
| `RiskVolatility` | Volatility container |
| `DrawdownProfile` | Drawdown shell |
| `StressScenario` | Scenario definition |
| `ScenarioResult` | Scenario outcome |
| `RiskDistribution` | Distribution shell |
| `QuantitativeRiskSummary` | Counts / limitations |
| `QuantitativeRiskReport` | Immutable presentation snapshot |

Upstream Portfolio, Monitoring, benchmarks, market/returns series, and Research
remain **reference-only**.

## Reference models

| Reference | Cites |
|---|---|
| `PortfolioReference` | Portfolio |
| `MonitoringReference` | Portfolio Monitoring |
| `BenchmarkReference` | Benchmark identity |
| `MarketDataReference` | Market-data port snapshot |
| `HistoricalReturnsReference` | Historical-returns port snapshot |
| `ResearchReference` | Optional ResearchReport citation |

## Metric contract

Every `RiskMetric` requires:

- `metric_id`, `metric_name`, `metric_type`
- `value` as **`decimal.Decimal`** (floats rejected)
- `unit`, `method_id`
- non-empty `provenance`
- `calculation_timestamp`
- optional `status` (`VALID` / `PARTIAL` / `FAILED`)

## Numeric policy

- Public numeric fields use `Decimal` only.  
- No implicit float coercion.  
- Units and method ids are mandatory on metrics / scenario results.  

## Validation rules

Rejects duplicate metrics/scenarios/results, foreign monitoring ownership,
broken scenario→result links, missing provenance/method/unit, non-Decimal
values, metric-type mismatches on concentration/volatility/drawdown wrappers.

## Extension guidance

- **E2.2** Quantitative Engine — **DONE** ([E2.2](E2_2_QUANTITATIVE_RISK_ENGINE.md))
- **E2.3** Reporter  
- Deferred: VaR, Monte Carlo, Sharpe, Sortino, Beta (additive later)  
- Vendor adapters remain outside this package  

## Non-goals (this phase)

Calculations, engines, reporter, persistence, API adapters, optimization.
