# EPIC-003 — Web Frontend Integration (Phase 1)

| Field | Value |
|---|---|
| **Version** | 1.0.0 |
| **Status** | **Complete** — awaiting approval |
| **Last updated** | 2026-07-26 |
| **Web package** | dsp-web **2.5.0** |
| **Route** | /intelligence |
| **Docs Suite** | **1.3.33** |
| **ADR** | [ADR-EPIC-003-001](adr/ADR-EPIC-003-001-intelligence-workspace.md) |

## Executive Summary

EPIC-003 adds an Intelligence Workspace to pps/web that consumes only
/api/v1 composition endpoints (nalyse, alidate, health, ersion,
capabilities). No backend packages are imported. No local scoring or
recommendation logic. Backend and API contracts are unchanged.

## Files Created

| Path |
|---|
| pps/web/src/app/intelligence/page.tsx |
| pps/web/src/components/intelligence/* |
| pps/web/src/lib/api/compositionTypes.ts |
| pps/web/src/lib/intelligence/* |
| pps/web/src/**/*.test.ts(x) (composition + components + arch) |
| pps/web/vitest.config.ts · itest.setup.ts |
| docs/EPIC_003_FRONTEND_INTEGRATION.md |
| docs/FRONTEND_INTELLIGENCE_WORKSPACE.md |
| docs/adr/ADR-EPIC-003-001-intelligence-workspace.md |

## Files Modified

| Path |
|---|
| pps/web/src/lib/api/client.ts · 	ypes.ts |
| pps/web/src/lib/navigation.ts |
| pps/web/package.json · lockfile |
| Living docs (STATUS, CHANGELOG, VERSION_MATRIX, debt, metrics) |

## Architecture Impact

- Frontend depends only on /api/v1 HTTP
- Vitest architecture scan forbids Python package imports
- Existing /analysis route unchanged
- No mobile / auth redesign / deployment / persistence

## UI Component Summary

AnalysisForm · ValidationBanner · PipelineTimeline · BusinessQualityCard ·
RecommendationCard · CommitteeConsensusCard · EvidencePanel · MetricsPanel ·
ExecutionMetadataPanel · HealthIndicator · VersionCard · CapabilitiesPanel ·
IntelligenceWorkspace

## API Integration Summary

| Endpoint | Usage |
|---|---|
| POST /analyse | Run composition; map to view-model |
| POST /validate | Pre-flight validation |
| GET /health | HealthIndicator |
| GET /version | VersionCard |
| GET /capabilities | CapabilitiesPanel |

## Test Results


pm test in pps/web: **14 PASS** (mapper, API mocks, components, architecture, routing)

## Remaining Technical Debt

- TD-E004 richer statement form UI (replace raw JSON textarea)
- TD-E005 screenshot / visual regression pack
- Prior TD-E002 / TD-E003 / domain providers

## Frontend Health Score

**91 / 100**

## Recommendation for next epic

**EPIC-004** — Mobile application or auth/ops epic per roadmap (await approval).

### STOP

Do not begin mobile, authentication redesign, deployment, persistence redesign,
or new analytical features without unlock.
