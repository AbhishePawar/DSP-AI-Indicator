# ADR-EPIC-002-001: /api/v1 Composition Integration

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-07-26 |
| **Epic** | EPIC-002 |
| **Related** | EPIC-001 · `api_platform` · `dsp_platform` 0.7.1 |

## Title

Expose platform composition through `/api/v1` DTOs that depend only on
`dsp_platform` public APIs.

## Decision

1. Add composition routes (`/analyse`, `/validate`, `/version`, `/capabilities`)
   and enrich `/health` with pipeline metadata.
2. Keep API free of FEATURE package imports; use
   `build_composition_request` / `pipeline_result_public_dict` on the platform.
3. Return stable Pydantic DTOs; never serialize raw domain objects.
4. Map failures to structured error bodies (code, message, stage, validation
   errors, correlation id, timestamp) without leaking internal exceptions.

## Consequences

- `api_platform` bumps to **0.2.0**; `dsp_platform` to **0.7.1** (adapter only)
- Analytical engines and decision rules remain untouched
- Frontend/mobile/auth/deploy deferred

## Rollback

Revert `api_platform` composition routers/schemas and platform adapter exports;
restore versions 0.1.0 / 0.7.0.
