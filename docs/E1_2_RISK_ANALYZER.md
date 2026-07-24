# Phase E1.2 — Risk Analyzer

**Status:** Implemented · Qualitative interpretation only

## Qualitative philosophy

`RiskAnalyzer` is the canonical **descriptive** interpretation layer for
Risk Intelligence. It reads an assembled `RiskProfile` (and optionally a
`Portfolio` for structure/cash posture) and emits categorical risk artifacts.

It does not compute market risk, probability, returns, or trade advice.

## Categorical descriptors

Allowed levels only: `LOW` · `MODERATE` · `ELEVATED` · `HIGH` · `UNKNOWN`

Dimensions include concentration, diversification, cash, liquidity,
constraint, plus coverage kinds (decision / evidence / comparison).

## Analysis flow

```text
RiskProfile (+ optional Portfolio / Monitoring citation)
        ↓
validate ownership / references
        ↓
build descriptors + coverage + observations
        ↓
RiskAssessment + RiskSummary + RiskReport
        ↓
RiskAnalysisResult (profile with assessment attached)
```

## Ownership

Analyzer owns qualitative risk interpretation artifacts.
It never owns Portfolio, DecisionPack, Evidence, Comparison, or Monitoring.

## Dependencies

Consumes `RiskProfile` and optional `portfolio.Portfolio` for declared
weights/cash. Uses citation counts on the profile when Portfolio is absent.

## Non-goals

VaR, beta, Sharpe, Sortino, alpha, probability, expected loss, stress testing,
returns, trading, optimization, security analysis, evidence reinterpretation,
monitoring-change implication engines (E1.4).
