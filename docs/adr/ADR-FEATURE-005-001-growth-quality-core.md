# ADR-FEATURE-005-001: Growth Quality Core Domain (Phase 1)

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **Epic** | FEATURE-005 |
| **Related** | FEATURE-001…004 · `packages/growth_quality/` |

## Title

Introduce top-level `growth_quality` package (FEATURE-005); defer platform
composition and concentration / deal-attribution providers.

## Decision

Create `growth_quality` **0.1.0** with six explainable dimensions consuming FA + BQ.
Register in monorepo tooling. Do not wire platform/API/frontend/AI Committee.
Growth risk is scored inverted (higher = safer) with confidence capped without
customer-concentration feeds.

## Consequences

- Package-only surface: `from growth_quality import GrowthQualityEngine`
- Concentration, market saturation, and organic-vs-acquisition attribution deferred (TD-F009 / TD-F010)

## Rollback

Unregister and remove/revert `packages/growth_quality/`.
