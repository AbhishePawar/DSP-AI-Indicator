"""P1-04 — valuation method integrity (fail-closed, no fabricated IV)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, StatementPeriodType
from fundamental.models import FinancialSnapshot
from valuation import (
    MarketSnapshot,
    ValuationAssumptions,
    ValuationEngine,
    ValuationError,
)
from valuation.aggregation import aggregate_estimates, confidence_from_count
from valuation.consensus import (
    ConsensusEngine,
    ConsensusInputs,
    ConsensusValidationError,
    WeightingMode,
)
from valuation.core.result_models import (
    ScenarioKind,
    ScenarioOutcome,
    SensitivityCell,
    SensitivityMatrix,
    ValidationSummary,
    ValuationMetadata,
    ValuationResult,
)
from valuation.dcf_intelligence.assumptions import DcfBridgeInputs
from valuation.dcf_intelligence.equity import compute_equity_bridge, validate_equity_bridge
from valuation.ddm import DdmInputs, DdmMethod, validate_ddm_inputs
from valuation.enums import ValuationConfidence, ValuationMethod
from valuation.methods.book_value import BookValueMethod
from valuation.methods.dcf import DcfMethod
from valuation.methods.earnings_multiple import EarningsMultipleMethod
from valuation.methods.residual_income import ResidualIncomeMethod
from valuation.models import IntrinsicValueEstimate
from valuation.overall import OverallEngine, OverallInputs, OverallValuationError
from valuation.relative import (
    BenchmarkMultiples,
    BenchmarkScope,
    RelativeEngine,
    RelativeInputs,
    RelativeMultiple,
)


FIXED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


def _instrument() -> Instrument:
    return Instrument(symbol="TEST", asset_class=AssetClass.EQUITY, currency="USD")


def _snapshot(
    *,
    ocf: float | None = 150.0,
    capex: float | None = 30.0,
    net_income: float | None = 100.0,
    equity: float | None = 1000.0,
) -> FinancialSnapshot:
    inst = _instrument()
    return FinancialSnapshot(
        instrument=inst,
        statements=(
            FundamentalStatement(
                instrument=inst,
                period_end=date(2024, 12, 31),
                period_type=StatementPeriodType.ANNUAL,
                fiscal_year=2024,
                currency="USD",
                operating_cash_flow=ocf,
                capital_expenditures=capex,
                net_income=net_income,
                total_equity=equity,
            ),
        ),
    )


def _sens() -> SensitivityMatrix:
    return SensitivityMatrix(
        grids={
            "x": (
                SensitivityCell("x", 1.0, "ivps", 10.0, 0, 0),
            )
        },
        notes="t",
    )


def _vr(
    method: str,
    *,
    iv: float | None = 1000.0,
    ivps: float | None = 10.0,
    confidence_score: float = 5.0,
) -> ValuationResult:
    return ValuationResult(
        model_name=method,
        version="test",
        methodology=f"{method} test",
        intrinsic_value=iv,
        enterprise_value=None,
        equity_value=iv,
        intrinsic_value_per_share=ivps,
        margin_of_safety=0.1 if ivps else None,
        confidence_score=confidence_score,
        confidence_level="medium",
        quality_flags=(),
        sensitivity_results=_sens(),
        scenario_results=(
            ScenarioOutcome(ScenarioKind.base(), iv, None, ivps),
        ),
        validation_summary=ValidationSummary(ok=True, checks=("ok",), warnings=()),
        explainability=(),
        research_disclaimer="research",
        metadata=ValuationMetadata(
            model_name=method, engine_version="t", methodology="t"
        ),
        currency="USD",
        confidence_explanation="test",
    )


def _bypass_assumptions(
    *,
    discount_rate: float,
    terminal_growth_rate: float,
) -> ValuationAssumptions:
    assumptions = ValuationAssumptions.__new__(ValuationAssumptions)
    object.__setattr__(assumptions, "discount_rate", discount_rate)
    object.__setattr__(assumptions, "fcf_growth_rate", 0.03)
    object.__setattr__(assumptions, "terminal_growth_rate", terminal_growth_rate)
    object.__setattr__(assumptions, "projection_years", 5)
    object.__setattr__(assumptions, "earnings_multiple", 12.0)
    object.__setattr__(assumptions, "owner_earnings_cap_rate", 0.10)
    object.__setattr__(assumptions, "residual_income_required_return", 0.10)
    return assumptions  # type: ignore[return-value]


# --------------------------------------------------------------------------- DCF
def test_dcf_missing_fcf_unavailable() -> None:
    est = DcfMethod().estimate(_snapshot(ocf=None, capex=30.0), ValuationAssumptions())
    assert est.applicable is False
    assert est.intrinsic_value is None


def test_dcf_invalid_discount_runtime() -> None:
    est = DcfMethod().estimate(
        _snapshot(), _bypass_assumptions(discount_rate=0.0, terminal_growth_rate=0.02)
    )
    assert est.applicable is False
    assert "discount_rate" in est.rationale


def test_dcf_terminal_growth_ge_discount_unavailable() -> None:
    est = DcfMethod().estimate(
        _snapshot(), _bypass_assumptions(discount_rate=0.08, terminal_growth_rate=0.08)
    )
    assert est.applicable is False
    assert "terminal_growth" in est.rationale


def test_dcf_valid_deterministic() -> None:
    engine = ValuationEngine(clock=lambda: FIXED)
    a = engine.analyze(_snapshot(), method_names=("dcf",))
    b = engine.analyze(_snapshot(), method_names=("dcf",))
    assert a.estimates[0].applicable is True
    assert a.estimates[0].intrinsic_value == pytest.approx(
        b.estimates[0].intrinsic_value
    )


# --------------------------------------------------------------------------- EV bridge
def test_equity_bridge_applies_adjustments_once() -> None:
    bridge = DcfBridgeInputs(
        cash=100.0,
        total_debt=50.0,
        minority_interest=10.0,
        non_operating_investments=20.0,
        shares_outstanding=10.0,
    )
    result = compute_equity_bridge(enterprise_value=1000.0, bridge=bridge)
    assert result.equity_value.value == pytest.approx(1060.0)
    assert result.intrinsic_value_per_share.value == pytest.approx(106.0)


def test_equity_bridge_rejects_cash_double_count_signal() -> None:
    bridge = DcfBridgeInputs(cash=500.0, non_operating_investments=600.0)
    with pytest.raises(ValuationError, match="double counting"):
        validate_equity_bridge(enterprise_value=100.0, bridge=bridge)


def test_equity_bridge_rejects_negative_ev() -> None:
    with pytest.raises(ValuationError, match="enterprise_value"):
        validate_equity_bridge(enterprise_value=-1.0, bridge=DcfBridgeInputs())


# --------------------------------------------------------------------------- DDM
def test_ddm_missing_dividend_unavailable() -> None:
    with pytest.raises(ValuationError, match="current_dps is zero"):
        validate_ddm_inputs(
            DdmInputs(
                method=DdmMethod.ZERO_GROWTH,
                current_dps=0.0,
                cost_of_equity=0.10,
                shares_outstanding=100.0,
                current_market_price=30.0,
            )
        )


def test_ddm_invalid_cost_of_equity() -> None:
    with pytest.raises(ValuationError, match="cost_of_equity"):
        validate_ddm_inputs(
            DdmInputs(
                method=DdmMethod.ZERO_GROWTH,
                current_dps=2.0,
                cost_of_equity=0.0,
                shares_outstanding=100.0,
                current_market_price=30.0,
            )
        )


# --------------------------------------------------------------------------- Default methods
def test_earnings_multiple_non_positive_unavailable() -> None:
    est = EarningsMultipleMethod().estimate(
        _snapshot(net_income=-10.0), ValuationAssumptions()
    )
    assert est.applicable is False


def test_book_value_non_positive_unavailable() -> None:
    est = BookValueMethod().estimate(_snapshot(equity=-5.0), ValuationAssumptions())
    assert est.applicable is False


def test_residual_income_missing_book_unavailable() -> None:
    est = ResidualIncomeMethod().estimate(
        _snapshot(equity=None), ValuationAssumptions()
    )
    assert est.applicable is False


# --------------------------------------------------------------------------- Relative
def test_relative_no_peers_unavailable() -> None:
    with pytest.raises(ValuationError, match="peer"):
        RelativeEngine().analyze(
            RelativeInputs(
                current_market_price=100.0,
                shares_outstanding=10.0,
                method=RelativeMultiple.PE,
                eps=5.0,
                benchmark_scope=BenchmarkScope.PEER,
                peer=None,
            )
        )


def test_relative_implied_none_not_market_price() -> None:
    eng = RelativeEngine()
    inputs = RelativeInputs(
        current_market_price=100.0,
        shares_outstanding=10.0,
        method=RelativeMultiple.EV_EBITDA,
        enterprise_value=0.0,
        ebitda=50.0,
        industry=BenchmarkMultiples(median=10.0, mean=10.0, count=5, label="ind"),
        benchmark_scope=BenchmarkScope.INDUSTRY,
    )
    with pytest.raises(ValuationError, match="implied price"):
        eng._value(inputs)


# --------------------------------------------------------------------------- Aggregation / consensus
def test_unavailable_methods_not_zero_in_aggregation() -> None:
    estimates = (
        IntrinsicValueEstimate(
            method=ValuationMethod.DCF,
            intrinsic_value=None,
            applicable=False,
            formula="x",
            rationale="missing",
        ),
        IntrinsicValueEstimate(
            method=ValuationMethod.BOOK_VALUE,
            intrinsic_value=1000.0,
            applicable=True,
            formula="x",
            rationale="ok",
        ),
        IntrinsicValueEstimate(
            method=ValuationMethod.EARNINGS_MULTIPLE,
            intrinsic_value=None,
            applicable=False,
            formula="x",
            rationale="missing",
        ),
    )
    vr, mos, conf, _, reasoning = aggregate_estimates(
        estimates, MarketSnapshot(market_cap=800.0)
    )
    assert vr.mid == pytest.approx(1000.0)
    assert conf is ValuationConfidence.LOW
    assert "1 applicable" in reasoning
    assert mos.available is True


def test_confidence_ignores_unavailable_count() -> None:
    assert confidence_from_count(0) is ValuationConfidence.INSUFFICIENT
    assert confidence_from_count(1) is ValuationConfidence.LOW
    assert confidence_from_count(3) is ValuationConfidence.MEDIUM
    assert confidence_from_count(5) is ValuationConfidence.HIGH


def test_consensus_excludes_null_iv_methods() -> None:
    result = ConsensusEngine().analyze(
        ConsensusInputs(
            methods=(
                _vr("dcf", iv=1000.0, ivps=10.0),
                _vr("ddm", iv=None, ivps=None),
                _vr("graham", iv=900.0, ivps=9.0),
            ),
            weighting_mode=WeightingMode.EQUAL,
            current_market_price=8.0,
        )
    )
    by_method = {d.method: d for d in result.method_weights}
    assert by_method["ddm"].included_in_consensus is False
    assert by_method["ddm"].weight == pytest.approx(0.0)
    assert by_method["dcf"].included_in_consensus is True
    assert by_method["graham"].included_in_consensus is True
    assert result.consensus_intrinsic_value.value is not None
    assert result.consensus_intrinsic_value.value > 0


def test_consensus_all_unavailable_fails() -> None:
    with pytest.raises(ConsensusValidationError, match="no usable"):
        ConsensusEngine().analyze(
            ConsensusInputs(
                methods=(_vr("ddm", iv=None, ivps=None),),
                weighting_mode=WeightingMode.EQUAL,
            )
        )


# --------------------------------------------------------------------------- Overall / MOS
def test_overall_rejects_zero_ivps() -> None:
    cons = ConsensusEngine().analyze(
        ConsensusInputs(
            methods=(_vr("book", iv=0.0, ivps=0.0),),
            weighting_mode=WeightingMode.EQUAL,
            current_market_price=5.0,
        )
    )
    with pytest.raises(OverallValuationError, match="zero"):
        OverallEngine().analyze(
            OverallInputs(current_market_price=5.0, consensus=cons)
        )


def test_mos_unavailable_when_no_applicable_methods() -> None:
    estimates = (
        IntrinsicValueEstimate(
            method=ValuationMethod.DCF,
            intrinsic_value=None,
            applicable=False,
            formula="x",
            rationale="missing",
        ),
    )
    _, mos, conf, _, _ = aggregate_estimates(
        estimates, MarketSnapshot(market_cap=100.0)
    )
    assert mos.available is False
    assert mos.ratio is None
    assert conf is ValuationConfidence.INSUFFICIENT


def test_full_analyze_skips_unavailable_no_cross_contamination() -> None:
    snap = _snapshot(ocf=None, capex=None, net_income=None, equity=500.0)
    assessment = ValuationEngine(clock=lambda: FIXED).analyze(snap)
    by_name = {e.method: e for e in assessment.estimates}
    assert by_name[ValuationMethod.DCF].applicable is False
    assert by_name[ValuationMethod.DCF].intrinsic_value is None
    assert by_name[ValuationMethod.BOOK_VALUE].applicable is True
    assert by_name[ValuationMethod.BOOK_VALUE].intrinsic_value == pytest.approx(500.0)
    assert assessment.valuation_range.mid == pytest.approx(500.0)
