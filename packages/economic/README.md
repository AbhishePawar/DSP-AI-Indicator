<!-- ASI-005-PACKAGE-CARD -->
# economic

> ASI-005 standard package card. Detailed historical notes follow in the appendix.

## 1. Package Purpose

Economic Engine — macroeconomic analysis for DSP AI Indicator

## 2. Responsibilities

Provide the stable `economic` public façade; keep domain logic inside this package’s ownership boundaries.

## 3. Package Status

**Production · Frozen** · Version **0.1.1** · [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

`__all__` exports (7): `EconomicAssessment`, `EconomicCondition`, `EconomicEngine`, `EconomicError`, `EconomicSignal`, `EconomicSnapshot`, `Recommendation`

## 5. Package Structure

`packages/economic/src/economic/` · `packages/economic/tests/` · local `pyproject.toml` when present.

## 6. Dependencies

`contracts`, `core`

## 7. Architecture Notes

Architecture allowlists / freeze policy apply. See appendix and [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
import economic
print(economic.__version__)
```

Worked examples live in `packages/economic/tests/`.

## 9. Testing

```bash
pytest packages/economic/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

[PACKAGE_OWNERSHIP_MATRIX.md](../../docs/PACKAGE_OWNERSHIP_MATRIX.md) · [PACKAGE_GOVERNANCE.md](../../docs/PACKAGE_GOVERNANCE.md)

## 11. Limitations

This card describes **current** implementation only. Epic freeze docs under `docs/` remain authoritative for certified behaviour.

## 12. Future Extensions (future only)

New features require an approved epic + ADR. **Not implemented here.**

---

## Appendix — Detailed package notes

# Economic — Macroeconomic Analysis Engine

`economic` is the platform's **Economic Engine** (Section 3.6 of
`docs/DSP_AI_INDICATOR_ARCHITECTURE.md`): it analyzes a point-in-time
macroeconomic snapshot and produces a deterministic regime assessment
for downstream engines (Valuation, Portfolio, Risk, and eventually the
AI Investment Committee).

**Sprint 6.0 — architecture only.** No forecasting. No LLM. No ML.

```
EconomicSnapshot
     │
     ▼
EconomicEngine.analyze()
     │
     ├─ GdpAnalyzer
     ├─ InflationAnalyzer
     ├─ InterestRateAnalyzer
     ├─ PmiAnalyzer
     └─ LiquidityAnalyzer
     │
     ▼
EconomicSignal × N
     │
     ▼
aggregate_signals()
     │
     ▼
EconomicAssessment
  ├─ overall_condition
  ├─ recommendation
  ├─ reasoning
  ├─ evidence
  └─ detected_signals
```

## Purpose

Establish a clean, independent macro analysis layer that:

1. Accepts structured macro inputs (`EconomicSnapshot`).
2. Runs single-responsibility analyzers.
3. Emits deterministic `EconomicSignal` observations.
4. Aggregates into an explainable `EconomicAssessment`.

The AI Investment Committee will consume `EconomicAssessment` in a
future sprint via an `EconomicMember` — this package does **not**
depend on `ai_committee`.

## Architecture

Analyzers own thresholds. The engine owns orchestration. Aggregation
owns the BUY/HOLD/SELL and regime classification rules. Evidence is
emitted as `contracts.Evidence` with
`EngineSource.ECONOMIC_ENGINE` for explainability.

## Folder Structure

```
packages/economic/
├── README.md
├── pyproject.toml
├── src/economic/
│   ├── __init__.py
│   ├── enums.py              # EconomicCondition, Recommendation
│   ├── exceptions.py         # EconomicError
│   ├── models.py             # Snapshot, Signal, Assessment
│   ├── aggregation.py        # signal → condition + recommendation
│   ├── registry.py           # analyzer registry
│   ├── analyzers/
│   │   ├── base.py
│   │   ├── gdp.py
│   │   ├── inflation.py
│   │   ├── interest_rate.py
│   │   ├── pmi.py
│   │   └── liquidity.py
│   └── engine/
│       └── service.py        # EconomicEngine
└── tests/
```

## Public APIs

| Symbol | Role |
|---|---|
| `EconomicEngine` | `analyze(snapshot) -> EconomicAssessment` |
| `EconomicSnapshot` | Point-in-time macro inputs |
| `EconomicAssessment` | Full engine output |
| `EconomicSignal` | One deterministic observation |
| `EconomicCondition` | EXPANSION / SLOWING / CONTRACTION / RECOVERY |
| `Recommendation` | BUY / HOLD / SELL (engine-local) |

Analyzers and the registry are intentional internals (not in `__all__`).

## Usage Example

```python
from datetime import date
from economic import EconomicEngine, EconomicSnapshot

engine = EconomicEngine()
assessment = engine.analyze(
    EconomicSnapshot(
        as_of=date(2024, 6, 15),
        gdp_growth=0.04,
        cpi_inflation=0.015,
        interest_rate=0.025,
        interest_rate_change=0.0,
        pmi=58.0,
        liquidity_indicator=0.75,
    )
)

print(assessment.overall_condition)   # EconomicCondition.EXPANSION
print(assessment.recommendation)      # Recommendation.BUY
print(assessment.reasoning)
```

## Initial Decision Rules

| Scenario | Signals | Assessment |
|---|---|---|
| High GDP + Low Inflation + Accommodative/Stable Rates + Strong PMI + Ample Liquidity | Broadly bullish | **BUY** / EXPANSION |
| High Inflation + Rapid Rate Hikes + Weak GDP + Contraction PMI + Tight Liquidity | Broadly bearish | **SELL** / CONTRACTION |
| Mixed / balanced bullish vs bearish | Mixed | **HOLD** / SLOWING |

Member-level thresholds (examples):

- GDP ≥ 3% → Strong Growth (bullish); < 1% → Weak (bearish)
- CPI ≤ 2% → Low Inflation (bullish); > 4% → High (bearish)
- Rate change ≥ 75 bps → Rapid Hikes (bearish)
- PMI ≥ 50 → Expansion (bullish); < 45 → Contraction (bearish)
- Liquidity ≥ 0.6 → Ample (bullish); < 0.4 → Tight (bearish)

## Dependency Diagram

```
contracts
    ▲
core
    ▲
economic
```

**Allowed:** `contracts`, `core`.

**Forbidden:** `dsp`, `fundamental`, `ai_committee`, `data_engine`
(architecture table *permits* `data_engine`, but this foundation
consumes an already-built `EconomicSnapshot` and adds no unused
dependency — same discipline as `dsp` / `fundamental`).

## Sequence Diagram

```
Caller
  │ analyze(EconomicSnapshot)
  ▼
EconomicEngine
  │
  ├─ registry.get("gdp").analyze(snapshot) → EconomicSignal
  ├─ registry.get("inflation")...
  ├─ registry.get("interest_rate")...
  ├─ registry.get("pmi")...
  └─ registry.get("liquidity")...
  │
  ├─ aggregate_signals([...])
  │     → EconomicCondition + Recommendation + reasoning
  │
  └─ EconomicAssessment(+ contracts.Evidence trail)
```

## Design Decisions

1. **`EconomicSnapshot` is point-in-time**, not `contracts.EconomicSeries`.
   Series → snapshot normalization belongs to Data Engine later.
2. **`Recommendation` is engine-local**, distinct from
   `contracts.RecommendationAction` (no STRONG_*).
3. **Unemployment / currency_trend** are on the snapshot for future
   analyzers but unused by Sprint 6.0 analyzers.
4. **Rapid rate hikes take precedence** over absolute rate level when
   `interest_rate_change` is present.
5. **Missing inputs → neutral signal**, not omission — every analyzer
   always returns at least one signal.

## Future Roadmap

- Yield-curve / unemployment / currency analyzers
- Multi-period trend from `contracts.EconomicSeries`
- Data Engine adapter producing `EconomicSnapshot`
- `EconomicMember` for the AI Investment Committee
- Promote shared types into Contracts when cross-engine consumers land

## Tests

```bash
pytest packages/economic -q
pytest -q
```
