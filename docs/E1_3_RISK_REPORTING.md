# Phase E1.3 — Risk Reporting

**Status:** Implemented · Presentation / assembly only

## Report philosophy

`RiskReporter` is the canonical **presentation** layer for qualitative Risk
Intelligence. It assembles existing Risk artifacts into a `RiskReport`.

It never performs analysis, never creates observations, never assigns
`RiskLevel`, never computes quantitative risk, and never recommends actions.

## Ownership

Reporter owns only the assembled presentation artifact (`RiskReport` via
`RiskReportingResult`). It does not own Portfolio, DecisionPack, Evidence,
Comparison, Monitoring, or analysis logic.

## Dependencies

Consumes:

- `RiskProfile` (identity, citations, optional attached assessments)
- `RiskAssessment` (or latest assessment on the profile)
- `RiskSummary`, `RiskObservation`, `RiskDescriptor`, `RiskCoverage`

Does not import or invoke `RiskAnalyzer`. Analysis must already exist.

## Reporting flow

```text
RiskProfile + RiskAssessment (+ optional section overlays)
        ↓
validate ownership / references / duplicate sections
        ↓
organize observations / descriptors / coverage / summary
        ↓
canonical RiskReport
        ↓
RiskReportingResult (status COMPLETE | PARTIAL | EMPTY)
```

## Validation

Rejects:

- invalid `RiskProfile`
- foreign assessment ownership (`risk_id` / `portfolio_id` mismatch)
- duplicate report sections (observation codes, descriptor dimensions,
  coverage kinds)
- broken DecisionPack / EvidenceBundle / Comparison citations
- missing required artifacts (`RiskAssessment`, `RiskSummary`)

## Completeness status

| Status   | Meaning                                              |
|----------|------------------------------------------------------|
| COMPLETE | Observations, descriptors, coverage, and summary populated |
| PARTIAL  | Assessment present but one or more sections incomplete |
| EMPTY    | No observations, descriptors, or coverage            |

## Non-goals

Monitoring implication engines, VaR, beta, Sharpe, Sortino, alpha,
probability, expected loss, stress testing, optimization, trading,
recommendations, observation generation, evidence reinterpretation.
