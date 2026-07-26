# ADR-FEATURE-006-001: Business Quality Aggregator (Phase 1)

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **Epic** | FEATURE-006 |
| **Related** | FEATURE-001…005 · `packages/business_quality_aggregator/` |

## Title

Introduce top-level `business_quality_aggregator` package (FEATURE-006) as a
cross-domain composition layer; keep distinct from F3.7
`business_quality.BusinessQualityAggregator`; defer platform composition.

## Decision

Create `business_quality_aggregator` **0.1.0** that consumes only public
analysis objects from the five FEATURE domain engines. Register in monorepo
tooling. Do not wire platform/API/frontend/AI Committee. Place aggregator
outside `business_quality` to avoid circular dependencies
(`business_quality` is an *input* to domain engines).

## Consequences

- Public class: `BusinessQualityAggregatorEngine` (not `BusinessQualityAggregator`)
- Conflict resolution is deterministic and explainable (TD-F011 / TD-F012 deferred providers)

## Rollback

Unregister and remove/revert `packages/business_quality_aggregator/`.
