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
│   ├── __init__.py                 # v0.12.0 — + Overall Valuation Aggregator
│   ├── core/                       # V1.5 shared infrastructure (no methodology)
│   │   ├── result_models.py
│   │   ├── confidence_engine.py
│   │   ├── sensitivity_engine.py
│   │   ├── scenario_engine.py
│   │   ├── explainability_engine.py
│   │   ├── validation_engine.py
│   │   ├── metadata.py
│   │   ├── quality_flags.py
│   │   ├── errors.py
│   │   └── interfaces.py
│   ├── exceptions.py
│   ├── enums.py
│   ├── assumptions.py              # multi-method ValuationAssumptions
│   ├── models.py
│   ├── aggregation.py
│   ├── registry.py
│   ├── dcf_intelligence/           # V1.2 domain DCF engine (explainable)
│   │   ├── engine.py
│   │   ├── wacc.py
│   │   ├── forecast.py
│   │   ├── terminal.py
│   │   ├── present_value.py
│   │   ├── equity.py
│   │   ├── margin.py
│   │   └── sensitivity.py
│   ├── reverse_dcf/                # V1.3 Reverse DCF (independent)
│   │   ├── reverse_dcf_engine.py
│   │   ├── reverse_dcf_models.py
│   │   ├── reverse_dcf_validation.py
│   │   └── reverse_dcf_explainability.py
│   ├── residual_income/            # V1.4 Residual Income (independent)
│   │   ├── residual_income_engine.py
│   │   ├── residual_income_models.py
│   │   ├── residual_income_validation.py
│   │   └── residual_income_explainability.py
│   ├── epv/                        # V1.6 Earnings Power Value (zero growth)
│   │   ├── epv_engine.py
│   │   ├── epv_models.py
│   │   ├── epv_validation.py
│   │   └── epv_explainability.py
│   ├── graham/                     # V1.7 Graham Intrinsic Value (heuristic)
│   │   ├── graham_engine.py
│   │   ├── graham_models.py
│   │   ├── graham_validation.py
│   │   └── graham_explainability.py
│   ├── ddm/                        # V1.8 Dividend Discount Model
│   │   ├── ddm_engine.py
│   │   ├── ddm_models.py
│   │   ├── ddm_validation.py
│   │   └── ddm_explainability.py
│   ├── asset_based/                # V1.9 Asset-Based & Liquidation
│   │   ├── asset_engine.py
│   │   ├── asset_models.py
│   │   ├── asset_validation.py
│   │   └── asset_explainability.py
│   ├── relative/                   # V1.10 Relative Valuation Suite
│   │   ├── relative_engine.py
│   │   ├── relative_models.py
│   │   ├── relative_validation.py
│   │   └── relative_explainability.py
│   ├── consensus/                  # V1.11 Cross-Method Consensus
│   │   ├── consensus_engine.py
│   │   ├── consensus_models.py
│   │   ├── consensus_validation.py
│   │   └── consensus_explainability.py
│   ├── overall/                    # V1.12 Overall Valuation Aggregator
│   │   ├── overall_engine.py
│   │   ├── overall_models.py
│   │   ├── overall_validation.py
│   │   └── overall_explainability.py
│   ├── methods/
│   │   ├── base.py
│   │   ├── dcf.py                  # legacy multi-method runner (unchanged API)
│   │   ├── owner_earnings.py
│   │   ├── earnings_multiple.py
│   │   ├── book_value.py
│   │   └── residual_income.py      # legacy closed-form method (unchanged)
│   └── engine/
│       └── service.py              # ValuationEngine (+ … / consensus / overall)
└── tests/
    ├── test_core/
    ├── test_epv.py
    ├── test_graham.py
    ├── test_ddm.py
    ├── test_asset_based.py
    ├── test_relative.py
    ├── test_consensus.py
    └── test_overall.py
```

## Valuation Core Framework (V1.5 / 0.5.0)

Shared research infrastructure for all future valuation methods. Does **not**
introduce a new methodology. Existing DCF / Reverse DCF / Residual Income math
is unchanged.

```python
from valuation import (
    ValuationResult,
    ConfidenceEngine,
    ValidationEngine,
    SensitivityEngine,
    ScenarioEngine,
    ExplainabilityEngine,
    QualityFlag,
)

detail = ConfidenceEngine().score({"data_completeness": 1.0, "solver_accuracy": 1.0})
assert detail.level in {"high", "medium", "low"}
```

See [V1_SPRINT5_VALUATION_CORE.md](../../docs/V1_SPRINT5_VALUATION_CORE.md).

## Earnings Power Value (V1.6 / 0.6.0)

Zero-growth capitalization of normalized owner earnings (Greenwald EPV).
Uses Valuation Core for confidence, validation, scenarios, sensitivity, and
explainability. Does **not** enable Overall Valuation.

```python
from valuation import ValuationEngine, EpvInputs, NormalizationMethod

result = ValuationEngine().analyze_epv(
    EpvInputs(
        revenue=1000,
        ebit=100,
        tax_rate=0.25,
        maintenance_capex=40,
        depreciation=40,
        cost_of_capital=0.10,
        shares_outstanding=100,
        cash=50,
        debt=100,
        current_market_price=5,
        normalization_method=NormalizationMethod.MANUAL_OVERRIDE,
    )
)
assert result.enterprise_epv.value == 750.0
```

See [V1_SPRINT6_EPV.md](../../docs/V1_SPRINT6_EPV.md).

## Graham Intrinsic Value (V1.7 / 0.7.0)

Benjamin Graham heuristics (original + modern yield-adjusted). Research-only;
assumptions stated explicitly. Does **not** enable Overall Valuation.

```python
from valuation import ValuationEngine, GrahamInputs, GrahamFormula

result = ValuationEngine().analyze_graham(
    GrahamInputs(
        eps_trailing=2.0,
        growth_rate=7.0,
        aaa_bond_yield=0.044,
        formula=GrahamFormula.ORIGINAL,
        shares_outstanding=100,
        current_market_price=30,
    )
)
assert result.intrinsic_value_per_share.value == 45.0
```

See [V1_SPRINT7_GRAHAM.md](../../docs/V1_SPRINT7_GRAHAM.md).

## Dividend Discount Model (V1.8 / 0.8.0)

Zero-growth, Gordon, two-stage, and multi-stage DDM on Valuation Core.
Research-only; does **not** enable Overall Valuation.

```python
from valuation import ValuationEngine, DdmInputs, DdmMethod

result = ValuationEngine().analyze_ddm(
    DdmInputs(
        current_dps=2.0,
        cost_of_equity=0.10,
        expected_dividend_growth=0.03,
        method=DdmMethod.GORDON,
        shares_outstanding=100,
        current_market_price=30,
    )
)
assert result.intrinsic_value_per_share.value is not None
```

See [V1_SPRINT8_DDM.md](../../docs/V1_SPRINT8_DDM.md).

## Asset-Based Valuation (V1.9 / 0.9.0)

Book value, tangible book, NAV, adjusted NAV, liquidation, conservative
liquidation, and replacement cost. Research-only; does **not** enable Overall Valuation.

```python
from valuation import ValuationEngine, AssetBasedInputs, AssetMethod

result = ValuationEngine().analyze_asset_based(
    AssetBasedInputs(
        cash=100,
        ppe=400,
        long_term_debt=200,
        shares_outstanding=100,
        method=AssetMethod.BOOK_VALUE,
    )
)
assert result.book_value.value is not None
```

See [V1_SPRINT9_ASSET_BASED.md](../../docs/V1_SPRINT9_ASSET_BASED.md).

## Relative Valuation Suite (V1.10 / 0.10.0)

Company vs industry / sector / peer / historical multiples (P/E, PEG, P/B,
EV/EBITDA, dividend yield, and more). Benchmarks are **injected** — no market
API dependency. Research-only; does **not** enable Overall Valuation.

```python
from valuation import (
    ValuationEngine,
    RelativeInputs,
    RelativeMultiple,
    BenchmarkScope,
    BenchmarkMultiples,
)

result = ValuationEngine().analyze_relative(
    RelativeInputs(
        current_market_price=100,
        shares_outstanding=10,
        eps=5.0,
        method=RelativeMultiple.PE,
        benchmark_scope=BenchmarkScope.INDUSTRY,
        industry=BenchmarkMultiples(median=15.0, count=12),
        peer=BenchmarkMultiples(median=13.0, count=6),
    )
)
assert result.implied_share_price.value is not None
```

See [V1_SPRINT10_RELATIVE.md](../../docs/V1_SPRINT10_RELATIVE.md).

## Cross-Method Consensus (V1.11 / 0.11.0)

Compares standardized `ValuationResult` / V2 payloads across methods.
Does **not** call valuation engines. Does **not** enable Overall Valuation.

```python
from valuation import ValuationEngine, ConsensusInputs, WeightingMode

result = ValuationEngine().analyze_consensus(
    ConsensusInputs(
        methods=[dcf_result, relative_result, asset_result],
        weighting_mode=WeightingMode.AUTOMATIC,
    )
)
assert result.consensus_per_share.value is not None
```

See [V1_SPRINT11_CONSENSUS.md](../../docs/V1_SPRINT11_CONSENSUS.md).

## Overall Valuation Aggregator (V1.12 / 0.12.0)

Assembles Consensus + method outputs into Overall Intrinsic Value, MoS,
research labels, and scores. **Does not re-execute engines.** Research labels
are educational — not investment recommendations.

```python
from valuation import ValuationEngine, OverallInputs

overall = ValuationEngine().analyze_overall(
    OverallInputs(
        current_market_price=50.0,
        consensus=consensus_result,
        methods=[dcf_vr, relative_vr],
    )
)
assert overall.overall_valuation_enabled is True
```

See [V1_SPRINT12_OVERALL.md](../../docs/V1_SPRINT12_OVERALL.md).

## DCF Intelligence (V1.2)

Domain-first FCFF engine with CAPM WACC, Gordon / exit-multiple terminal value,
equity bridge, MoS research posture, sensitivity matrix, and per-field
explainability.

```python
from valuation import (
    ValuationEngine,
    DcfAnalysisInputs,
    DcfForecastAssumptions,
    CapmInputs,
    CostOfDebtInputs,
    CapitalStructure,
)

result = ValuationEngine().analyze_dcf(
    DcfAnalysisInputs(
        forecast=DcfForecastAssumptions(
            base_revenue=1000,
            revenue_growth=0.05,
            operating_margin=0.20,
            tax_rate=0.25,
            depreciation_pct_of_revenue=0.04,
            capex_pct_of_revenue=0.06,
            nwc_pct_of_revenue=0.10,
            forecast_years=10,
        ),
        capm=CapmInputs(0.04, 1.0, 0.05),
        cost_of_debt=CostOfDebtInputs(0.06),
        capital_structure=CapitalStructure(equity_weight=0.7, debt_weight=0.3),
    )
)
assert result.present_value.enterprise_value.value is not None
```

MoS bands (`strong_buy` / `buy` / `hold` / `overvalued`) are **research postures**,
not trade recommendations. Multi-method `analyze()` is unchanged.

## Reverse DCF Intelligence (V1.3)

Independent research engine: *what growth is implied by the market price?*

```python
from valuation import ValuationEngine, ReverseDcfInputs

result = ValuationEngine().analyze_reverse_dcf(
    ReverseDcfInputs(
        current_share_price=50,
        shares_outstanding=10,
        cash=20,
        debt=30,
        minority_interest=0,
        investments=0,
        current_revenue=200,
        current_ebit=40,
        current_fcff=25,
        current_operating_margin=0.20,
        tax_rate=0.25,
        reinvestment_rate=0.30,
        forecast_years=10,
        terminal_growth=0.02,
        wacc=0.09,
    )
)
assert result.implied_revenue_cagr.value is not None
assert result.solver.converged
```

Binary-search solver (±0.01%, max 200 iters). Bear/Base/Bull scenarios +
WACC / terminal-growth / price sensitivity. Does **not** modify DCF Intelligence
or enable Overall Valuation. See [V1_SPRINT3_REVERSE_DCF.md](../../docs/V1_SPRINT3_REVERSE_DCF.md).

## Residual Income Valuation (V1.4 / 0.4.1)

Independent multi-period clean-surplus RIV with ROE path models, quality flags,
clean-surplus checks, and `to_v2_aggregate_payload()` for future aggregation.

```python
from valuation import ValuationEngine, ResidualIncomeInputs, RoeForecastModel

result = ValuationEngine().analyze_residual_income(
    ResidualIncomeInputs(
        current_book_value=1000,
        roe_forecast=0.15,
        cost_of_equity=0.10,
        dividend_payout_ratio=0.40,
        forecast_years=10,
        terminal_growth=0.02,
        shares_outstanding=100,
        current_market_price=12,
        roe_model=RoeForecastModel.CONSTANT,
    )
)
assert result.clean_surplus_ok
assert "research and educational" in result.disclaimer.lower()
```

See [V1_SPRINT4_RESIDUAL_INCOME.md](../../docs/V1_SPRINT4_RESIDUAL_INCOME.md).

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

`0.12.0`
