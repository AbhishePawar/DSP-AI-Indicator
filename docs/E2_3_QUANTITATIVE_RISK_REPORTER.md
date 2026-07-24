# Phase E2.3 — Quantitative Risk Reporter

**Status:** Implemented · Presentation only · No calculations

**Package:** `packages/quantitative_risk/` **0.3.0**  
**Freeze:** [E2.0A](E2_0A_QUANTITATIVE_RISK_ARCHITECTURE_FREEZE.md)  
**Engine:** [E2.2](E2_2_QUANTITATIVE_RISK_ENGINE.md)

## Reporter architecture

```text
QuantitativeRiskReport  ──┐
EngineResult.report     ──┼──► ReportingContext
                          │
                          ▼
              QuantitativeRiskReporter
                          │
                          ├── MetricCollection (grouped, values unchanged)
                          ├── grouped exposures / concentrations /
                          │   volatilities / drawdowns
                          ├── ReportMetadata + summary sections
                          ├── QuantitativeRiskReport (pass-through + limitations)
                          └── ReportingResult
```

APIs: `QuantitativeRiskReporter`, `ReportingContext`, `ReportingResult`,
`ReportingStatus`, plus `MetricCollection` / `ReportMetadata`.

## Presentation responsibilities

| Responsibility | Behavior |
|---|---|
| Format metric collections | Group by `MetricType` into `MetricCollection` |
| Group exposures | Pass-through ordered exposure tuples |
| Group concentrations | Pass-through concentration tuples |
| Group volatility / drawdown | Pass-through wrapper tuples |
| Build summary sections | Default section keys (overview → limitations) |
| Build report metadata | Counts + ids + `as_of` + section keys |
| Preserve provenance | Metric provenance / method_id / unit untouched |

## Validation rules

Rejects missing report identity, engine↔report id mismatches, broken monitoring
ownership, duplicate metric ids, missing provenance / method_id / units on
metrics, missing method_id on exposures, duplicate summary section keys,
duplicate identities in `report_many`.

## Provenance preservation

Reporter never strips or rewrites `provenance`, `method_id`, `unit`, or
`calculation_timestamp`. Engine artifacts are referenced as-is.

## Formatting policy

- **Preserve** all metric `Decimal` values exactly (object identity retained).  
- **Never** round, quantize, or recalculate.  
- **Never** infer missing metrics or invent recommendations.  
- Presentation may append a limitations note only.

## Future extension guidance

- Charts / UI adapters outside this package  
- Additional section keys additive without changing metric values  
- Deferred metrics (VaR, Sharpe, …) appear only after Engine emits them  
- E2.4 validation & freeze next  

## Non-goals (this phase)

New metrics, VaR/Monte Carlo/Sharpe/Sortino/Beta, optimization, recommendations,
workflow, charts, persistence, provider adapters, engine execution.
