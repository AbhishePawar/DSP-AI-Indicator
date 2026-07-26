# ADR-FEATURE-007-001: Investment Recommendation Engine (Phase 1)

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **Epic** | FEATURE-007 |
| **Related** | FEATURE-001…006 · `packages/investment_recommendation/` |

## Title

Introduce top-level `investment_recommendation` package (FEATURE-007) as
deterministic decision intelligence; keep distinct from G1.3
`recommendation.RecommendationEngine`; defer platform composition.

## Decision

Create `investment_recommendation` **0.1.0** consuming public
`OverallValuationResult` / `ValuationSignals` plus FEATURE domain analyses and
`BusinessQualityAggregation`. Register in monorepo tooling. Do not wire
platform/API/frontend/AI Committee. No LLM/ML.

## Consequences

- Public class: `InvestmentRecommendationEngine`
- MoS gates prevent Strong Buy when materially overvalued (TD-F013 / TD-F014)

## Rollback

Unregister and remove/revert `packages/investment_recommendation/`.
