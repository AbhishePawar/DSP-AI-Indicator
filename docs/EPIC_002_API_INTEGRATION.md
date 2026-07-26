# EPIC-002 — /api/v1 Integration (Phase 1)

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | **Complete** — awaiting approval |
| **Last updated** | 2026-07-26 |
| **API package** | `api_platform` **0.2.0** |
| **Platform** | `dsp_platform` **0.7.1** |
| **Docs Suite** | **1.3.32** |
| **ADR** | [ADR-EPIC-002-001](adr/ADR-EPIC-002-001-api-composition.md) |

## Executive Summary

EPIC-002 exposes the EPIC-001 composition pipeline through `/api/v1` as a
presentation boundary only. The API talks exclusively to `dsp_platform` public
APIs (`compose_intelligence`, `build_composition_request`, capability helpers).
No analytical engines, recommendation rules, or committee logic were changed.

## Endpoint Summary

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/analyse` | Execute composition → public PipelineResult DTO |
| `POST` | `/api/v1/validate` | Validate payload only (no execution) |
| `GET` | `/api/v1/health` | Status + platform + pipeline versions |
| `GET` | `/api/v1/version` | Package / pipeline / docs / API versions |
| `GET` | `/api/v1/capabilities` | Modules, reports, stages, metadata |

Root aliases (`/analyse`, `/health`, …) remain mounted for backward compatibility.

## Files Created

| Path |
|---|
| `packages/dsp_platform/src/dsp_platform/composition/adapters.py` |
| `packages/api_platform/src/api_platform/api/composition_schemas.py` |
| `packages/api_platform/src/api_platform/api/validation.py` |
| `packages/api_platform/src/api_platform/api/mappers.py` |
| `packages/api_platform/src/api_platform/api/routers/composition.py` |
| `packages/api_platform/src/api_platform/api/routers/meta.py` |
| `packages/api_platform/tests/test_composition_api.py` |
| `docs/EPIC_002_API_INTEGRATION.md` |
| `docs/API_V1_COMPOSITION.md` |
| `docs/adr/ADR-EPIC-002-001-api-composition.md` |

## Files Modified

| Path |
|---|
| `packages/api_platform/` app, schemas, health, `__init__`, pyproject, README, arch tests, `test_api.py` |
| `packages/dsp_platform/` composition exports, versions **0.7.1**, README |
| `docs/DSP_STATUS.md` · `DSP_CHANGELOG.md` · `VERSION_MATRIX.md` · ownership/testing/dependency matrices |
| `docs/asi/TECHNICAL_DEBT_REGISTER.md` · `ENGINEERING_METRICS_DASHBOARD.md` · `DSP_DECISION_RECORDS.md` |

## Architecture Impact

- `api_platform` **0.1.0 → 0.2.0**
- `dsp_platform` **0.7.0 → 0.7.1** (JSON → `CompositionRequest` adapter only)
- FEATURE packages remain forbidden imports in `api_platform`
- Existing `/analyze/company` and other K1.1 routes unchanged
- No frontend / mobile / auth redesign / persistence / deployment

## Endpoint Summary

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/analyse` | Execute composition → public PipelineResult DTO |
| `POST` | `/api/v1/validate` | Validate payload only (no execution) |
| `GET` | `/api/v1/health` | Status + platform + pipeline versions |
| `GET` | `/api/v1/version` | Package / pipeline / docs / API versions |
| `GET` | `/api/v1/capabilities` | Modules, reports, stages, metadata |

Root aliases (`/analyse`, `/health`, …) remain mounted for backward compatibility.

## API Test Results

`packages/api_platform/tests` + composition/platform arch + monorepo smoke: **61 PASS** · integrity **PASS**

## OpenAPI Coverage

Live schema: `/openapi.json` · Swagger: `/docs` · ReDoc: `/redoc`

Documented models: `AnalyseRequest`, `AnalyseResponse`, `ValidateResponse`,
`VersionResponse`, `CapabilitiesResponse`, `CompositionErrorBody`, `HealthResponse`.

See [API_V1_COMPOSITION.md](API_V1_COMPOSITION.md) for examples and error catalogue.

## Remaining Technical Debt

- TD-E002 richer ValuationEngine snapshot auto-wiring
- TD-E003 authenticated composition rate limits / quotas (future)
- Prior domain provider gaps TD-F001…F010, F012, F014, F016

Resolved: **TD-E001** (composition via `/api/v1`)

## Updated Repository Health

**Overall / API Health Score: 91 / 100**

## Recommendation for next epic

**Frontend Integration Epic** — consume `/api/v1/analyse` and related meta routes.

### STOP

Do **not** begin frontend, mobile, authentication redesign, deployment, or
persistence redesign without explicit unlock.
