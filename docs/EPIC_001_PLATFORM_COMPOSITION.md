# EPIC-001 — Platform Composition Layer (Phase 1)

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | **Complete** — awaiting approval |
| **Last updated** | 2026-07-26 |
| **Package** | `dsp_platform` **0.7.0** |
| **Pipeline** | `COMPOSITION_PIPELINE_VERSION` = `1.0.0-epic-001` |
| **ADR** | [ADR-EPIC-001-001](adr/ADR-EPIC-001-001-platform-composition.md) |
| **Docs Suite** | **1.3.31** |

---

## Executive Summary

EPIC-001 adds an internal orchestration pipeline to `dsp_platform` that composes
FEATURE packages (financial → valuation → domain engines → aggregator →
recommendation → committee) using **public APIs only**. No new scoring, no
recommendation/committee overrides, no `/api/v1` changes, no frontend/mobile/persistence changes.

The platform is the execution pipeline for completed analytical packages.
Domain engines remain the sole owners of financial logic.

---

## Platform Architecture

```text
Application / tests
        │
        ▼
DSPPlatform.compose_intelligence(CompositionRequest)
        │
        ▼
PlatformOrchestrator
        │
        ▼
ExecutionPipeline (deterministic EXECUTION_ORDER)
        │
        ├── DependencyResolver
        ├── ExecutionContext
        ├── TimingCollector / EvidenceCollector
        └── public package engines only
                │
                ▼
        PipelineResult → PlatformResult envelope
```

**Rules preserved:** public interfaces only · no package internals · no score /
recommendation / committee overrides · no circular dependencies · ASI allowlists
updated for FEATURE orchestration only.

---

## Pipeline Flow / Execution Sequence

```text
1. financial
2. valuation
3. economic_moat
4. management_quality
5. financial_strength
6. earnings_quality
7. growth_quality
8. business_quality_aggregator
9. investment_recommendation
10. investment_committee
        │
        ▼
Unified PipelineResult
```

Order is fixed in `EXECUTION_ORDER` / `DependencyResolver`. Stages 3–7 run in
listed sequence (deterministic; not parallel).

---

## Dependency Graph (composition)

```text
financial_statements
        → FinancialEngine
        → Valuation (signals / overall / snapshot+price)
        → Moat / MQ / FS / EQ / GQ (FA + optional BQ)
        → BusinessQualityAggregatorEngine
        → InvestmentRecommendationEngine
        → InvestmentCommitteeEngine
```

See also [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md).

---

## Integration Guide

```python
from dsp_platform import DSPPlatform, CompositionRequest
from investment_recommendation import ValuationSignals

platform = DSPPlatform()
envelope = platform.compose_intelligence(
    CompositionRequest(
        financial_statements=statements,
        valuation_signals=ValuationSignals(
            intrinsic_value_per_share=100.0,
            current_market_price=70.0,
        ),
    )
)
assert envelope.ok
result = envelope.payload  # PipelineResult
print(result.investment_committee.decision)
print(result.metadata.pipeline_version)
print(result.timings)
```

Or call `PlatformOrchestrator().execute(request)` directly in tests.

**Inputs:** `CompositionRequest` (statements required; valuation via
`overall_valuation` / `valuation_signals` / snapshot+price / price-only degraded path).

**Outputs:** typed `PipelineResult` with all stage payloads, metadata, timings,
evidence counts, warnings, limitations, failed stage (if any).

---

## Extension Guide

1. Add a new package with a public engine API.
2. Register it only after an approved epic + ADR.
3. Append a `PipelineStage` in `composition/pipeline.py` (preserve order rules).
4. Update `DependencyResolver` prerequisites if needed.
5. Extend `PipelineResult` / `CompositionRequest` with typed fields.
6. Expand architecture allowlist + composition tests.
7. Do **not** re-implement scoring inside `dsp_platform`.

---

## Error Handling

- Stage failures raise/capture `CompositionStageError` with stage identity.
- Completed upstream outputs are preserved on `PipelineResult`.
- First failed stage is sticky (`failed_stage`); no partial corruption of prior stages.
- Downstream stages skip when prerequisites missing (graceful degradation where safe).

---

## Files Created

| Path |
|---|
| `packages/dsp_platform/src/dsp_platform/composition/__init__.py` |
| `packages/dsp_platform/src/dsp_platform/composition/versions.py` |
| `packages/dsp_platform/src/dsp_platform/composition/models.py` |
| `packages/dsp_platform/src/dsp_platform/composition/config.py` |
| `packages/dsp_platform/src/dsp_platform/composition/context.py` |
| `packages/dsp_platform/src/dsp_platform/composition/errors.py` |
| `packages/dsp_platform/src/dsp_platform/composition/resolver.py` |
| `packages/dsp_platform/src/dsp_platform/composition/collectors.py` |
| `packages/dsp_platform/src/dsp_platform/composition/pipeline.py` |
| `packages/dsp_platform/src/dsp_platform/composition/orchestrator.py` |
| `packages/dsp_platform/tests/test_composition_pipeline.py` |
| `docs/EPIC_001_PLATFORM_COMPOSITION.md` |
| `docs/adr/ADR-EPIC-001-001-platform-composition.md` |

## Files Modified

| Path |
|---|
| `packages/dsp_platform/pyproject.toml` (0.7.0 + FEATURE deps) |
| `packages/dsp_platform/src/dsp_platform/platform.py` |
| `packages/dsp_platform/src/dsp_platform/__init__.py` |
| `packages/dsp_platform/src/dsp_platform/configuration.py` |
| `packages/dsp_platform/tests/test_architecture.py` |
| `packages/dsp_platform/README.md` |
| `docs/DSP_STATUS.md` · `DSP_CHANGELOG.md` · `VERSION_MATRIX.md` |
| `docs/DEPENDENCY_GRAPH.md` · `PACKAGE_OWNERSHIP_MATRIX.md` · `PACKAGE_TESTING_MATRIX.md` |
| `docs/DSP_DECISION_RECORDS.md` |
| `docs/asi/TECHNICAL_DEBT_REGISTER.md` · `ENGINEERING_METRICS_DASHBOARD.md` |

---

## Architecture Impact

- `dsp_platform` **0.6.0 → 0.7.0**
- ASI `_FORBIDDEN` allowlists FEATURE packages for platform orchestration
- Frozen `ai_committee` / G1.3 `recommendation` paths unchanged
- `/api/v1` unchanged · no frontend · no mobile · no persistence redesign
- No new financial / scoring / recommendation logic

---

## Execution Pipeline Summary

| Stage | Public entry |
|---|---|
| financial | `FinancialEngine` |
| valuation | Valuation public APIs / signals |
| economic_moat … growth_quality | Domain engines |
| business_quality_aggregator | `BusinessQualityAggregatorEngine` |
| investment_recommendation | IR engine |
| investment_committee | Committee engine |

Collectors: `TimingCollector`, `EvidenceCollector`.  
Result: `PipelineResult` + `ExecutionMetadata` + trace.

---

## Integration Test Results

Composition suite + platform architecture tests: **PASS** (see run log for this epic).

---

## Performance Summary

Pipeline is in-process sequential orchestration; performance smoke covered by
composition e2e (order + determinism strip timings). No new network I/O.

---

## Remaining Technical Debt

- **TD-E001** — `/api/v1` exposure of composition results
- **TD-E002** — richer ValuationEngine snapshot auto-wiring from FinancialAnalysis
- TD-F012 / TD-F014 / TD-F016 provider / veto tunables
- Prior domain provider gaps TD-F001…F010

Resolved by EPIC-001: TD-F011, TD-F013, TD-F015 (platform-internal).

---

## Updated Repository Health

**Overall / Platform Health Score: 91 / 100**

Docs Suite **1.3.31** · `dsp_platform` **0.7.0** · FEATURE 001–008 composed internally.

---

## Recommendation for next epic

**API Integration Epic** — expose composition behind `/api/v1` with explicit approval.

### STOP

Do **not** begin:

- `/api/v1` integration
- frontend / mobile integration
- deployment changes
- authentication
- persistence redesign

Await approval before the API Integration Epic.
