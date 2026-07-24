# Phase C4.1 — Portfolio Domain Models

**Status:** Implemented · Structure only · No assembly / monitoring / calculations

## Aggregate root

`Portfolio` is the aggregate root. It owns:

- `PortfolioIdentity`
- `PortfolioHolding` (citations only)
- `PortfolioConstraint`
- `PortfolioSnapshot`

It does not own engines, IEF interpreters, or Comparison logic.

## Ownership

| Model | Role |
|---|---|
| PortfolioIdentity | Metadata facet |
| PortfolioHolding | Position + DecisionPack citation (+ optional evidence/comparison refs) |
| PortfolioSnapshot | Immutable as-of freeze |
| PortfolioAllocation | Descriptive weights only |
| PortfolioConstraint | Policy descriptors (unevaluated) |
| PortfolioObservation | Qualitative note |
| PortfolioSummary / PortfolioReport | Presentation / citation surface |

## Immutability

All models are `@dataclass(frozen=True, slots=True)`.

## Dependency rules

Allowed: `contracts`, `core`, `decision_intelligence`, `industry`, `comparison`, `universe`

Forbidden: analysis engines, providers, interpreters, valuation/technical/fundamental packages, `dsp_platform`

Holdings cite via `DecisionPackReference` / `EvidenceBundleReference` /
`ComparisonReportReference` — payloads are never embedded.

## Non-goals (still deferred)

Assembler, monitoring, constraint evaluation, allocation logic, optimization,
risk, persistence, report generation pipelines.
