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
| dependency_wiring | `DSPPlatform.analysis_service` present |

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
