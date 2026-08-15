<!-- ASI-005-PACKAGE-CARD -->
# dsp_platform

> ASI-005 standard package card. Detailed historical notes follow in the appendix.

## 1. Package Purpose

DSP Platform façade — composition entry point and application import boundaries

## 2. Responsibilities

Provide the stable `dsp_platform` public façade; keep domain logic inside this package’s ownership boundaries.

## 3. Package Status

**Active · EPIC-V100 Production Certification** · Version **1.0.0** · [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

`DSPPlatform`, `PlatformOrchestrator`, `CompositionRequest`, `PipelineResult`, plus existing façade exports.

## 5. Package Structure

`packages/dsp_platform/src/dsp_platform/` including `composition/` · `packages/dsp_platform/tests/`

## 6. Dependencies

Epic K peers plus FEATURE composition packages: `financial`, `valuation`, `business_quality`, `economic_moat`, `management_quality`, `financial_strength`, `earnings_quality`, `growth_quality`, `business_quality_aggregator`, `investment_recommendation`, `investment_committee`

## 7. Architecture Notes

EPIC-001 internal orchestration only — public package APIs, no score overrides, no `/api/v1` changes.

## 8. Usage Examples

```python
from dsp_platform import DSPPlatform, CompositionRequest
from investment_recommendation import ValuationSignals

platform = DSPPlatform()
result = platform.compose_intelligence(
    CompositionRequest(
        financial_statements=statements,
        valuation_signals=ValuationSignals(
            intrinsic_value_per_share=100.0,
            current_market_price=70.0,
        ),
    )
)
print(result.ok, result.payload.investment_committee.decision)
```

## Pipeline flow

```
financial → valuation → moat/MQ/FS/EQ/GQ → aggregator → recommendation → committee
```

## 9. Testing

```bash
pytest packages/dsp_platform/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

[PACKAGE_OWNERSHIP_MATRIX.md](../../docs/PACKAGE_OWNERSHIP_MATRIX.md) · [PACKAGE_GOVERNANCE.md](../../docs/PACKAGE_GOVERNANCE.md)

## 11. Limitations

This card describes **current** implementation only. Epic freeze docs under `docs/` remain authoritative for certified behaviour.

## 12. Future Extensions (future only)

New features require an approved epic + ADR. **Not implemented here.**

---

## Appendix — Detailed package notes

# DSP Platform

Sprint 7.3 — **public façade + configuration + integration gates**.

External applications should import **only** `dsp_platform` and
`contracts`. The import name avoids shadowing Python's stdlib
`platform` module.

## Public architecture

```
Application
    │
    ├─ DSPPlatform.analyze(request) ───────────────▶ Recommendation
    │
    └─ DSPPlatform.analyze_decision_pack(request) ▶ Decision Pack
            │
            ├─ Recommendation
            ├─ Decision Brief
            └─ Assurance Assessment
```

```
Application
    │
    ▼
DSPPlatform.analyze(AnalysisRequest)
    │
    ▼
InvestmentAnalysisService.analyze_recommendation
    │
    ▼
RecommendationMapper
    │
    ▼
contracts.Recommendation
```

## Package Structure

```
packages/dsp_platform/
├── README.md
├── PERFORMANCE.md
├── src/dsp_platform/
│   ├── __init__.py       # public API
│   ├── exceptions.py     # PlatformError
│   ├── config.py         # immutable configuration
│   ├── facade.py         # DSPPlatform
│   ├── wiring.py         # composition root (from_config)
│   ├── health.py         # offline health / readiness
│   ├── loaders.py        # optional env config loaders
│   └── boundaries.py     # application import contracts
└── tests/
    ├── conftest.py       # offline E2E factory
    ├── samples/          # import-boundary samples
    ├── test_e2e.py
    ├── test_health.py
    ├── test_loaders.py
    ├── test_boundaries.py
    └── test_performance.py
```

## Dependency Diagram

```
dsp_platform
    ├── contracts          (public output types)
    ├── core
    ├── orchestration      (analyze path)
    ├── recommendation     (via orchestration)
    ├── data_engine        (wiring / health registry only)
    └── snapshot_bridge    (wiring only)
```

`analyze()` never calls providers, engines, or the committee directly.

## Public API

```python
from datetime import date

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from dsp_platform import (
    DSPPlatform,
    PlatformConfig,
    PlatformSecrets,
    PlatformHealthService,
    Environment,
    load_platform_config,
)

instrument = Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")

# DI (tests / custom wiring) or composition root
platform = DSPPlatform.from_config(
    PlatformConfig(
        environment=Environment.PRODUCTION,
        secrets=PlatformSecrets(fred_api_key="…"),  # inject — never hardcode
    )
)

# Optional: load from environment
# platform = DSPPlatform.from_config(load_platform_config())

request = platform.make_request(instrument, date(2024, 1, 1), date(2024, 6, 30))
recommendation = platform.analyze(request)  # backward compatible

# Preferred investor artifact (Phase B2)
pack = platform.analyze_decision_pack(request)
assert pack.recommendation.action is recommendation.action
assert pack.brief.headline
assert pack.assurance.investor_guidance.stance

# Offline readiness (no live HTTP)
report = PlatformHealthService(config=PlatformConfig(), platform=platform).check()
assert report.ready
```

## Health checks

`PlatformHealthService` validates:

| Check | Behaviour |
|---|---|
| configuration | Reconstruct / validate `PlatformConfig` |
| feature_flags | Feature flag model present |
| provider_settings | Enabled provider ids listed |
| provider_registry | Required ids registered (if registry injected) |
| composition_pipeline | Canonical `compose_intelligence` path importable and enabled |
| investment_data_provider | Production resolves authenticated investment connectors (P1-03); skipped elsewhere |
| dependency_wiring | Legacy `DSPPlatform.analysis_service` present; skipped when the canonical composition path serves analysis |

Never performs network I/O.

## Import boundaries

Applications may import only:

- `dsp_platform`
- `contracts`

Use `assert_application_imports(source)` (or CI) to reject imports of
`data_engine`, `snapshot_bridge`, `dsp`, `fundamental`, `economic`,
`valuation`, `ai_committee`, `orchestration`, `recommendation`, `core`.

Sibling packages must import each other only via public `__init__`
façades. Enforce with `assert_public_sibling_imports`.

## Configuration

| Model / helper | Purpose |
|---|---|
| `PlatformConfig` | Immutable root (DI primary) |
| `FeatureFlags` | Defaults for fund / econ / valuation / partial |
| `load_platform_config` | Optional env → config |
| `load_secrets_from_environ` | Optional secret injection |

No global mutable state. Secrets are never hardcoded.

## Integration strategy

Offline E2E tests wire fake market / bridges / engines into the **real**
`InvestmentAnalysisService` and exercise `DSPPlatform.analyze()` end to
end — covering BUY / SELL / HOLD, partial data, provider failure,
configuration failure, committee disagreement, determinism, and
`PlatformError` translation. No live HTTP.

## Sequence Diagram

```
App                     DSPPlatform              InvestmentAnalysisService
 │ analyze(request)          │                            │
 │──────────────────────────▶│ analyze_recommendation     │
 │                           │───────────────────────────▶│ … orchestration …
 │                           │◀── Recommendation          │
 │◀── Recommendation         │                            │
```

## Design Decisions

1. **Import name `dsp_platform`** — avoids stdlib collision.
2. **DI-first constructor** — tests inject a fake or offline orchestrator.
3. **Wiring is the only adapter-aware module** — keeps the façade thin.
4. **`PlatformError` only** — internal exceptions never escape.
5. **Health is offline** — registry inspection, not live pings.
6. **Import boundaries as code** — enforceable without a separate linter binary.

## Performance

See [PERFORMANCE.md](PERFORMANCE.md).

## Version

`0.2.1`
