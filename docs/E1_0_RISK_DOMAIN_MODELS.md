# Phase E1.0 — Risk Domain Models

**Status:** Implemented · Structure only · No analysis / calculations

## Model philosophy

Risk Intelligence E1.0 defines **immutable qualitative contracts** only.
Models describe posture and coverage. They do not compute risk, score
portfolios, or recommend trades.

## Ownership

| Model | Role |
|---|---|
| `RiskIdentity` | Identity facet of a risk profile / assessment lineage |
| `RiskProfile` | Aggregate root — cites Portfolio / Monitoring; owns Risk artifacts |
| `RiskAssessment` | One qualitative as-of assessment container |
| `RiskObservation` | Qualitative note |
| `RiskDescriptor` | Categorical level (`LOW`…`UNKNOWN`) + dimension |
| `RiskCoverage` | Decision / Evidence / Comparison coverage posture |
| `RiskConstraint` | Risk-policy descriptor (not `PortfolioConstraint`) |
| `RiskSummary` | High-level qualitative summary |
| `RiskReport` | Canonical presentation artifact |

Upstream ownership remains unchanged: Portfolio, DecisionPack, Evidence,
Comparison stay outside Risk.

## Dependencies

Allowed runtime imports: `core`, `portfolio`, `industry`
(`EvidenceBundleReference` + Portfolio citation types).

Forbidden: engines, providers, interpreters, Comparison engine,
`dsp_platform`, DI package internals.

## Validation rules

Rejects:

- invalid / empty identity
- duplicate observations (by code)
- duplicate descriptors (by dimension)
- duplicate constraints (by id)
- duplicate coverage kinds
- foreign Monitoring portfolio_id
- foreign Portfolio ownership on assessments
- broken DecisionPack / Evidence / Comparison citations

Observation / descriptor text rejects attractiveness and quantitative
claim terms (score, rank, sharpe, var, beta, alpha, buy, sell, …).

## Immutability & determinism

All models are `@dataclass(frozen=True, slots=True)`.
Payloads are provider-independent and engine-independent.

## Future extension points

- E1.1 RiskAssembler
- E1.2 qualitative RiskAnalyzer
- E1.3 RiskReport workflows
- E1.4 Monitoring-change implications
- E2.x quantitative risk (separate freeze)

## Non-goals (this phase)

Assembler, analyzer, calculations, percentages, probability, VaR, beta,
Sharpe, Sortino, alpha, stress testing, optimization, trading.
