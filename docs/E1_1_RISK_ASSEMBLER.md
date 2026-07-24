# Phase E1.1 — Risk Assembler

**Status:** Implemented · Construction / orchestration only

## Construction philosophy

`RiskAssembler` is the canonical constructor for immutable `RiskProfile`
aggregates. It attaches citations and emits a **structural** `RiskReport`
with empty observations / descriptors / assessments.

## Assembly flow

```text
Validate inputs
        ↓
Validate ownership (Portfolio / Monitoring)
        ↓
Validate citation references
        ↓
Construct immutable RiskProfile
        ↓
Construct empty structural RiskReport
        ↓
RiskAssemblyResult
```

## Ownership

Assembler owns **construction**. It does not own qualitative analysis,
coverage posture evaluation, monitoring interpretation, scoring, or
recommendations.

## Dependency rules

Consumes: `PortfolioReference`, optional `MonitoringReference`, Decision /
Evidence / Comparison citation refs, optional unevaluated `RiskConstraint`
descriptors.

Never embeds upstream payloads. Never imports engines / providers /
interpreters.

## Validation

Rejects: duplicate references, foreign Monitoring ownership, broken
citations, invalid identities, duplicate `risk_id` in `assemble_many`.

## Status

| Status | Meaning |
|---|---|
| `COMPLETE` | Valid assembly with MonitoringReference attached |
| `PARTIAL` | Valid assembly without MonitoringReference |

## Non-goals

Risk Analyzer, observations, descriptors, coverage evaluation, monitoring
implications, calculations, VaR/Sharpe/beta, recommendations, trading.
