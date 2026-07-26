# ADR-EPIC-001-001: Platform Composition Layer (Phase 1)

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **Epic** | EPIC-001 |
| **Related** | FEATURE-001…008 · `packages/dsp_platform/composition/` |

## Title

Compose FEATURE analytical/decision packages into `dsp_platform` as an internal
orchestration pipeline; do not change `/api/v1`, frontend, or domain scoring.

## Decision

Add `dsp_platform.composition` with `PlatformOrchestrator`, deterministic
`EXECUTION_ORDER`, typed `PipelineResult`, timing/evidence collectors, and
stage-isolated error propagation. Bump `dsp_platform` to **0.7.0**. Allowlist
FEATURE packages in platform architecture tests for orchestration-only imports.

## Consequences

- Platform calls public engines only; no score/recommendation overrides
- API/frontend/mobile/persistence remain deferred (TD-E001)

## Rollback

Revert `composition/` module, dependency allowlist, and version to 0.6.0.
