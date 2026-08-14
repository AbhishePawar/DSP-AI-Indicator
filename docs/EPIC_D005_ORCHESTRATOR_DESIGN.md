# EPIC-D005 — Orchestrator Design

## Service

`DataOrchestrator` (`data_engine.data_orchestrator`):

- Accepts fetch/health/resolve callables for D001–D004
- Runs requested sections in parallel (`ThreadPoolExecutor`)
- Maps `None` → unavailable, exceptions → error section status
- Never invents section payloads
- Deterministic `SECTION_ORDER`: market_quote → financial_statements →
  corporate_actions → historical_series

## Request

`DataOrchestratorRequest` — symbol/exchange/currency + include flags +
pass-through limits for statements / actions / history.

## Response (`UnifiedDataBundle`)

| Field | Content |
|---|---|
| identity | Resolved company identity (statements resolve preferred) |
| market_quote / financial_statements / corporate_actions / historical_series | `SectionResult` (status + payload + provenance) |
| provider_metadata | Provider health snapshots |
| provenance | Per-section provenance map (deterministic keys) |
| health | Aggregated provider health |
| retrieval | Timing + ok/unavailable/error section lists + partial flag |

## Platform façade

`dsp_platform.data_orchestrator.get_unified_data_bundle` wires env-backed
D001–D004 façades. Rebuilds request-bound fetch closures per call (tests may
inject a mock orchestrator).

## Forbidden

- Calculations / derived metrics / indicators
- Valuation, scoring, recommendations
- Fabricating missing sections
- Breaking `/analyse`
