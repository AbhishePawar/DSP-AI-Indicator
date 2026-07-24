# Phase E1.4 — Risk Integration

**Status:** Implemented · Coordination / aggregation only

## Integration philosophy

`RiskIntegrator` is the canonical **coordination** layer for qualitative Risk
artifacts. It aggregates an existing `RiskProfile`, assessment, summary,
coverage, and report into an `IntegratedRiskContext`.

It does not create analysis, does not perform monitoring, does not assign
`RiskLevel`, does not compute quantitative risk, and does not recommend actions.

## Ownership

Integrator owns only the coordinated bundle (`IntegratedRiskContext` via
`RiskIntegrationResult`). It does not own Portfolio, Monitoring execution,
DecisionPack, Evidence, Comparison, or analysis logic.

## Dependencies

Consumes existing Risk artifacts only:

- `RiskProfile`
- `RiskAssessment` (or latest on the profile)
- `RiskSummary`
- `RiskCoverage`
- `RiskReport`

Does not import or invoke `RiskAnalyzer`, `RiskReporter`, or Portfolio
Monitoring services.

## Integration flow

```text
RiskProfile (+ assessment / summary / coverage / report)
        ↓
validate ownership / references / duplicate artifacts
        ↓
resolve and combine qualitative artifacts
        ↓
IntegratedRiskContext
  (reporting_inputs_ready / monitoring_inputs_ready)
        ↓
RiskIntegrationResult (status COMPLETE | PARTIAL | EMPTY)
```

## Completeness status

| Status   | Meaning |
|----------|---------|
| COMPLETE | Assessment, summary, coverage, and report all present |
| PARTIAL  | Some but not all qualitative artifacts present |
| EMPTY    | Profile only — no assessment, summary, coverage, or report |

## Validation

Rejects:

- invalid `RiskProfile`
- foreign ownership (assessment / report `risk_id` or `portfolio_id`)
- duplicate artifacts (assessment already on profile; duplicate coverage kinds)
- broken references (citation digests; report↔assessment id mismatch;
  summary count mismatch vs assessment)

## Prepared downstream inputs

- **Reporting:** `reporting_inputs_ready` when assessment + summary are present
- **Monitoring:** `monitoring_inputs_ready` when portfolio citation is present;
  Monitoring citation is noted if attached — never interpreted

## Non-goals

Monitoring implication engines, VaR, beta, Sharpe, Sortino, alpha,
probability, expected loss, stress testing, optimization, trading,
recommendations, observation generation, evidence reinterpretation,
RiskLevel assignment.
