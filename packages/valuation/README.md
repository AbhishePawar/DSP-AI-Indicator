# Valuation Engine

Sprint 8.0 — standalone **Valuation Engine** for the DSP AI Indicator.

Estimates intrinsic equity value from a
`fundamental.FinancialSnapshot` using multiple independent methodologies.
Committee integration is **Sprint 8.1** (complete): `ValuationMember`
maps ``ValuationAssessment`` into the Investment Committee.

## Package Structure

```
packages/valuation/
├── README.md
├── pyproject.toml
├── src/valuation/
│   ├── __init__.py
│   ├── exceptions.py
│   ├── enums.py
│   ├── assumptions.py      # injectable ValuationAssumptions
│   ├── models.py
│   ├── aggregation.py
│   ├── registry.py
│   ├── methods/
│   │   ├── base.py
│   │   ├── dcf.py
│   │   ├── owner_earnings.py
│   │   ├── earnings_multiple.py
│   │   ├── book_value.py
│   │   └── residual_income.py
│   └── engine/
│       └── service.py      # ValuationEngine
└── tests/
```

## Dependency Diagram

```
contracts ← core ← fundamental ← valuation
```

Forbidden: `data_engine`, `snapshot_bridge`, `economic`, `dsp`,
`ai_committee`, `orchestration`, `recommendation`, `dsp_platform`.

## Public API

```python
from datetime import date

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, StatementPeriodType
from contracts.domain.fundamental_statement import FundamentalStatement
from fundamental.models import FinancialSnapshot
from valuation import (
    ValuationEngine,
    ValuationAssumptions,
    MarketSnapshot,
)

instrument = Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")
snapshot = FinancialSnapshot(
    instrument=instrument,
    statements=(FundamentalStatement(
        instrument=instrument,
        period_end=date(2023, 12, 31),
        period_type=StatementPeriodType.ANNUAL,
        fiscal_year=2023,
        currency="USD",
        net_income=100.0,
        total_equity=500.0,
        operating_cash_flow=180.0,
        capital_expenditures=40.0,
    ),),
)

engine = ValuationEngine(
    assumptions=ValuationAssumptions(discount_rate=0.10, earnings_multiple=12.0)
)
assessment = engine.analyze(snapshot, MarketSnapshot(market_cap=1_200.0))

print(assessment.valuation_range.mid)
print(assessment.confidence)
print(assessment.margin_of_safety.ratio)
```

## Valuation Methodology & Formulas

| Method | Formula | Required inputs |
|---|---|---|
| **Book Value** | `IV = total_equity` | `total_equity` |
| **Earnings Multiple** | `IV = net_income × earnings_multiple` | `net_income` |
| **Owner Earnings** | `OE = OCF − CapEx`; `IV = OE / cap_rate` | `operating_cash_flow`, `capital_expenditures` |
| **DCF** | `FCF₀ = OCF − CapEx`; project `N` years at `g`; Gordon TV at `g_terminal`; discount at `r` | OCF, CapEx |
| **Residual Income** | `ROE = NI/Equity`; `RI = (ROE−r)×Equity`; `IV = Equity + RI/r` | `net_income`, `total_equity` |

Missing inputs disable **only that method**. The engine still returns a
`ValuationAssessment`.

### Aggregation

- **Mid** = median of applicable intrinsic values  
- **Range** = (min, median, max)  
- **Confidence** = HIGH (≥4 methods) / MEDIUM (2–3) / LOW (1) / INSUFFICIENT (0)  
- **Margin of safety** = `(mid − market_cap) / mid` when `MarketSnapshot.market_cap` is set  

## Sequence Diagram

```
Caller                ValuationEngine              Methods
  │ analyze(snapshot)      │                          │
  │───────────────────────▶│ estimate() × N           │
  │                        │─────────────────────────▶│
  │                        │◀── IntrinsicValueEstimate│
  │                        │ aggregate_estimates()    │
  │◀── ValuationAssessment │                          │
```

## Design Decisions

1. **Engine-local models** — like `economic`; contracts `Evidence` with
   `EngineSource.VALUATION_ENGINE` for explainability trail.
2. **Injectable assumptions** — no hardcoded market forecasts beyond
   documented conservative defaults.
3. **Graceful degradation** — method-level skip, never engine failure.
4. **Company-level values** — estimates are total equity value in
   statement currency (no shares outstanding on statements today).
5. **No HTTP / committee / orchestration** — pure analytics.

## Limitations

- No shares outstanding → no per-share IV or P/B from price alone.
- Owner earnings approximates Buffett OE without WC change / D&A split.
- DCF uses a single growth rate (no staged fade beyond terminal g).
- Wired into the Investment Committee via `ValuationMember` (Sprint 8.1).
- Not exposed as a separate `DSPPlatform` surface — still flows through
  `platform.analyze()` via orchestration.

## Version

`0.1.0`
