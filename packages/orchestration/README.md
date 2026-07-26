<!-- ASI-005-PACKAGE-CARD -->
# orchestration

> ASI-005 standard package card. Detailed historical notes follow in the appendix.

## 1. Package Purpose

DSP orchestration — single official analysis pipeline (flow only)

## 2. Responsibilities

Provide the stable `orchestration` public façade; keep domain logic inside this package’s ownership boundaries.

## 3. Package Status

**Production · Frozen (flow only)** · Version **0.2.0** · [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

`__all__` exports (8): `AnalysisRequest`, `InvestmentAnalysisService`, `OrchestrationError`, `RecommendationMapper`, `to_economic_context`, `to_fundamental_context`, `to_technical_context`, `to_valuation_context`

## 5. Package Structure

`packages/orchestration/src/orchestration/` · `packages/orchestration/tests/` · local `pyproject.toml` when present.

## 6. Dependencies

`ai_committee`, `contracts`, `core`, `data_engine`, `dsp`, `economic`, `fundamental`, `recommendation`, `snapshot_bridge`, `valuation`

## 7. Architecture Notes

Architecture allowlists / freeze policy apply. See appendix and [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
import orchestration
print(orchestration.__version__)
```

Worked examples live in `packages/orchestration/tests/`.

## 9. Testing

```bash
pytest packages/orchestration/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

[PACKAGE_OWNERSHIP_MATRIX.md](../../docs/PACKAGE_OWNERSHIP_MATRIX.md) · [PACKAGE_GOVERNANCE.md](../../docs/PACKAGE_GOVERNANCE.md)

## 11. Limitations

This card describes **current** implementation only. Epic freeze docs under `docs/` remain authoritative for certified behaviour.

## 12. Future Extensions (future only)

New features require an approved epic + ADR. **Not implemented here.**

---

## Appendix — Detailed package notes

# Orchestration

Sprint 7.0 — thin **application layer** that owns the single official
execution pipeline of the DSP AI Indicator platform.

## Responsibilities

Coordinate completed packages into one path:

```
Instrument
  → Market Data → DSP Engine
  → Financial Bridge → Fundamental Engine
                     → Valuation Engine
  → Economic Bridge → Economic Engine
  → CommitteeInput → InvestmentCommittee
  → CommitteeReport
```

## Non-responsibilities

- Indicator / fundamental / economic calculations
- Voting / aggregation logic
- Provider HTTP, parsing, normalization
- Snapshot construction (delegated to `snapshot_bridge`)

## Package Structure

```
packages/orchestration/
├── README.md
├── src/orchestration/
│   ├── __init__.py              # public API
│   ├── exceptions.py            # OrchestrationError
│   ├── models.py                # AnalysisRequest
│   └── service.py               # InvestmentAnalysisService
└── tests/
    ├── test_models.py
    └── test_service.py
```

## Dependency Diagram

```
orchestration
    ├── contracts
    ├── core
    ├── data_engine
    ├── snapshot_bridge
    ├── dsp
    ├── fundamental
    ├── economic
    ├── valuation
    ├── ai_committee
    └── recommendation
```

No package imports `orchestration` (no reverse dependencies).

## Execution Pipeline

1. Validate `AnalysisRequest`
2. Fetch price series → `IndicatorEngine.analyze` → `AnalysisResult`
3. Optionally fetch financial snapshot once (for fundamentals and/or valuation)
4. Optionally run `FundamentalEngine.analyze` / `ValuationEngine.analyze`
5. Optionally fetch economics → bridge → `EconomicEngine.analyze`
6. Build `CommitteeInput` → dynamic committee (T + F? + E? + V?) → deliberate
7. Optionally map via `analyze_recommendation()` → `contracts.Recommendation`

## Sequence Diagram

```
Caller                    InvestmentAnalysisService
  │ analyze(request)                │
  │────────────────────────────────▶│ MarketDataService.get_price_series
  │                                 │ IndicatorEngine.analyze
  │                                 │ FinancialBridgeService.get_snapshot
  │                                 │ FundamentalEngine.analyze
  │                                 │ EconomicBridgeService.get_snapshot
  │                                 │ EconomicEngine.analyze
  │                                 │ InvestmentCommittee.deliberate
  │◀──── CommitteeReport            │
```

## Public API

```python
from datetime import date

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from orchestration import AnalysisRequest, InvestmentAnalysisService

service = InvestmentAnalysisService(
    market_data=market_data,
    financial_bridge=financial_bridge,
    economic_bridge=economic_bridge,
)
report = service.analyze(
    AnalysisRequest(
        instrument=Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD"),
        start=date(2024, 1, 1),
        end=date(2024, 6, 30),
    )
)
```

## Partial Failure Policy

| Stage | Default |
|---|---|
| Market / DSP | Always required — failure → `OrchestrationError` |
| Fundamentals | Optional when `allow_partial=True` — skip Fundamental member |
| Economics | Optional when `allow_partial=True` — skip Economic member |
| `include_fundamentals=False` | Skip fundamentals stage entirely |
| `include_economic=False` | Skip economics stage entirely |
| `include_valuation=False` | Skip valuation stage entirely |

## Architecture Decisions

1. **Thin by construction** — only sequencing and error translation.
2. **Dynamic committee roster** when no committee is injected — members
   match available analyses so missing optional data cannot break
   deliberation.
3. **Injected committee is strict** — caller owns roster completeness.
4. **All failures become `OrchestrationError`** — no provider exceptions
   leak to callers.
5. **Instrument is already resolved** — master-data / ticker resolution
   remains outside this package.
6. **Sprint 7.1** — `analyze_recommendation()` maps the report through
   `recommendation.RecommendationMapper` to `contracts.Recommendation`
   without changing `analyze()`'s return type.

## Version

`0.1.1`
