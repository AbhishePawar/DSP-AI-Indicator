# Phase E2.2 — Quantitative Risk Engine

**Status:** Implemented · Initial metric catalog · No reporter

**Package:** `packages/quantitative_risk/` **0.2.0**  
**Freeze:** [E2.0A](E2_0A_QUANTITATIVE_RISK_ARCHITECTURE_FREEZE.md)  
**Models:** [E2.1](E2_1_QUANTITATIVE_RISK_DOMAIN_MODELS.md)

## Engine architecture

```text
EngineContext
  ├── QuantitativeRiskIdentity
  ├── PortfolioReference / MonitoringReference / BenchmarkReference
  ├── MarketDataPort
  ├── HistoricalReturnsPort
  └── BenchmarkDataPort
        │
        ▼
QuantitativeRiskEngine.calculate
        │
        ├── RiskMetric (×4 baseline)
        ├── RiskConcentration / RiskExposure / RiskVolatility / DrawdownProfile
        ├── QuantitativeRiskSummary
        └── QuantitativeRiskReport  (immutable)
        │
        ▼
EngineResult (status + artifacts + warnings)
```

APIs: `QuantitativeRiskEngine`, `EngineContext`, `EngineResult`, `EngineStatus`.

## Port architecture

Package-local Protocols only — no concrete providers, no vendor SDKs:

| Port | Role |
|---|---|
| `MarketDataPort.get_portfolio_weights` | Declared weights for concentration / exposure |
| `HistoricalReturnsPort.get_returns` | Period returns for volatility / drawdown |
| `BenchmarkDataPort.get_returns` | Benchmark series (validated; unused in baseline math) |

DTOs: `WeightPoint`, `ReturnPoint` (`decimal.Decimal` only).

Adapters live **outside** this package.

## Metric pipeline

| # | Metric | Artifacts | Method id |
|---|---|---|---|
| 1 | Top holding weight | `RiskMetric` + `RiskConcentration` | `…concentration.top_weight.v1` |
| 2 | Max single-name exposure + rows | `RiskMetric` + `RiskExposure[]` | `…exposure.weight.v1` |
| 3 | Annualized realized vol | `RiskMetric` + `RiskVolatility` | `…volatility.realized_stdev_daily.v1` |
| 4 | Maximum drawdown | `RiskMetric` + `DrawdownProfile` | `…drawdown.max.v1` |

Volatility: sample stdev of period returns × √252 (method-bound).  
Drawdown: peak-to-trough on compounded equity curve from period returns.

## Validation rules

Rejects: missing/empty market weights, missing/empty historical returns,
missing/empty benchmark returns, foreign monitoring ownership, negative
weights, duplicate instrument weights, duplicate quantitative_risk identities
(`calculate_many`), duplicate metric ids, non-finite Decimals.

Metric contract enforced via domain models: provenance, method_id, unit,
Decimal value, calculation_timestamp.

## Precision policy

Engine-owned (`precision.py`):

| Scale | Quantum |
|---|---|
| Weights | `1e-8` (`WEIGHT_QUANTUM`) |
| Returns | `1e-8` (`RETURN_QUANTUM`) |
| Metrics | `1e-8` (`METRIC_QUANTUM`) |

Rounding: `ROUND_HALF_EVEN`. No float storage. Domain constructors stay
precision-neutral; engine quantizes before constructing artifacts.

## Future metric extension strategy

Additive only under freeze amendment / later E2 phases:

- New `MetricType` values + engine methods  
- VaR, Monte Carlo, Sharpe, Sortino, Beta, factor models  
- Richer use of `BenchmarkDataPort` / `RiskDistribution` / stress scenarios  
- Port promotion to `contracts` when a second context needs the same ports  

No redesign of ownership, dependency direction, or Models → Engine → Reporter.

## Non-goals (this phase)

Reporter UI, persistence, vendor adapters, VaR/Monte Carlo/Sharpe/Sortino/Beta,
optimization, trading, recommendations, LLM reasoning.

**Next:** [E2.3 Reporter](E2_3_QUANTITATIVE_RISK_REPORTER.md) — **DONE**.
