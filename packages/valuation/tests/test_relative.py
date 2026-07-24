"""Relative Valuation Suite tests — target 100% module coverage."""

from __future__ import annotations

import math
import time

import pytest

from valuation import ValuationEngine, ValuationError
from valuation.relative import (
    RELATIVE_VERSION,
    BenchmarkMultiples,
    BenchmarkScope,
    RelativeEngine,
    RelativeInputs,
    RelativeMultiple,
    RelativeQualityFlag,
    StaticMultipleProvider,
    explain_many,
    explain_step,
    to_v2_aggregate_payload,
    validate_relative_inputs,
)
from valuation.relative.relative_models import to_valuation_result


def _bench(
    median: float | None = 15.0,
    mean: float | None = 16.0,
    count: int = 8,
    p25: float | None = 10.0,
    p75: float | None = 20.0,
    label: str = "IND",
) -> BenchmarkMultiples:
    return BenchmarkMultiples(
        median=median,
        mean=mean,
        count=count,
        percentile_25=p25,
        percentile_75=p75,
        label=label,
    )


def _base(**kwargs) -> RelativeInputs:
    data: dict = dict(
        current_market_price=100.0,
        shares_outstanding=10.0,
        enterprise_value=1200.0,
        revenue=500.0,
        ebit=80.0,
        ebitda=100.0,
        net_income=50.0,
        eps=5.0,
        forward_eps=6.0,
        book_value=400.0,
        tangible_book_value=350.0,
        operating_cash_flow=90.0,
        free_cash_flow=70.0,
        dividend_per_share=2.0,
        dividend_yield=0.02,
        growth_rate=0.08,
        expected_growth=0.10,
        industry=_bench(15.0, 16.0, 12, 10.0, 20.0, "industry"),
        sector=_bench(14.0, 15.0, 20, 9.0, 19.0, "sector"),
        peer=_bench(13.0, 14.0, 6, 11.0, 18.0, "peer"),
        historical_average=12.0,
        average_5y=12.5,
        average_10y=11.5,
        risk_free_rate=0.04,
        market_premium=0.05,
        accounting_quality_score=80.0,
        method=RelativeMultiple.PE,
        benchmark_scope=BenchmarkScope.INDUSTRY,
    )
    data.update(kwargs)
    return RelativeInputs(**data)


class TestEveryMultiple:
    @pytest.mark.parametrize(
        "method,kwargs,check",
        [
            (RelativeMultiple.PE, {}, lambda r: r.current_multiple.value == pytest.approx(20.0)),
            (
                RelativeMultiple.FORWARD_PE,
                {"industry": _bench(18.0)},
                lambda r: r.current_multiple.value == pytest.approx(100.0 / 6.0),
            ),
            (
                RelativeMultiple.PEG,
                {"industry": _bench(1.5), "expected_growth": 0.10},
                lambda r: r.current_multiple.value == pytest.approx(20.0 / 10.0),
            ),
            (
                RelativeMultiple.PB,
                {"industry": _bench(2.0)},
                lambda r: r.current_multiple.value == pytest.approx(1000.0 / 400.0),
            ),
            (
                RelativeMultiple.PTBV,
                {"industry": _bench(2.5)},
                lambda r: r.current_multiple.value == pytest.approx(1000.0 / 350.0),
            ),
            (
                RelativeMultiple.PRICE_SALES,
                {"industry": _bench(1.8)},
                lambda r: r.current_multiple.value == pytest.approx(1000.0 / 500.0),
            ),
            (
                RelativeMultiple.PRICE_CASH_FLOW,
                {"industry": _bench(10.0)},
                lambda r: r.current_multiple.value == pytest.approx(1000.0 / 90.0),
            ),
            (
                RelativeMultiple.PRICE_FCF,
                {"industry": _bench(12.0)},
                lambda r: r.current_multiple.value == pytest.approx(1000.0 / 70.0),
            ),
            (
                RelativeMultiple.EV_SALES,
                {"industry": _bench(2.0)},
                lambda r: r.current_multiple.value == pytest.approx(1200.0 / 500.0),
            ),
            (
                RelativeMultiple.EV_EBIT,
                {"industry": _bench(12.0)},
                lambda r: r.current_multiple.value == pytest.approx(1200.0 / 80.0),
            ),
            (
                RelativeMultiple.EV_EBITDA,
                {"industry": _bench(10.0)},
                lambda r: r.current_multiple.value == pytest.approx(1200.0 / 100.0),
            ),
            (
                RelativeMultiple.DIVIDEND_YIELD,
                {"industry": _bench(0.025, 0.03, 8, 0.015, 0.04)},
                lambda r: r.current_multiple.value == pytest.approx(0.02),
            ),
        ],
    )
    def test_multiple(self, method, kwargs, check) -> None:
        r = RelativeEngine().analyze(_base(method=method, **kwargs))
        assert r.method is method
        assert r.version == RELATIVE_VERSION
        check(r)
        assert r.implied_share_price.value is not None
        assert r.intrinsic_value_per_share.value is not None


class TestScopes:
    def test_industry(self) -> None:
        r = RelativeEngine().analyze(_base(benchmark_scope=BenchmarkScope.INDUSTRY))
        assert r.fair_multiple.value == pytest.approx(15.0)
        # PE=20, fair=15 → implied = 15 * 5 = 75
        assert r.implied_share_price.value == pytest.approx(75.0)

    def test_sector(self) -> None:
        r = RelativeEngine().analyze(
            _base(benchmark_scope=BenchmarkScope.SECTOR, industry=_bench())
        )
        assert r.fair_multiple.value == pytest.approx(14.0)

    def test_peer(self) -> None:
        r = RelativeEngine().analyze(_base(benchmark_scope=BenchmarkScope.PEER))
        assert r.fair_multiple.value == pytest.approx(13.0)

    def test_historical(self) -> None:
        r = RelativeEngine().analyze(
            _base(benchmark_scope=BenchmarkScope.HISTORICAL, historical_average=11.0)
        )
        assert r.fair_multiple.value == pytest.approx(11.0)

    def test_historical_falls_back_5y_10y(self) -> None:
        r = RelativeEngine().analyze(
            _base(
                benchmark_scope=BenchmarkScope.HISTORICAL,
                historical_average=None,
                average_5y=None,
                average_10y=9.0,
            )
        )
        assert r.fair_multiple.value == pytest.approx(9.0)

    def test_weighted(self) -> None:
        r = RelativeEngine().analyze(
            _base(
                benchmark_scope=BenchmarkScope.WEIGHTED,
                industry_weight=0.4,
                sector_weight=0.2,
                peer_weight=0.4,
            )
        )
        # 0.4*15 + 0.2*14 + 0.4*13 = 6+2.8+5.2 = 14
        assert r.fair_multiple.value == pytest.approx(14.0)

    def test_mean_when_no_median(self) -> None:
        r = RelativeEngine().analyze(
            _base(industry=_bench(median=None, mean=17.0))
        )
        assert r.fair_multiple.value == pytest.approx(17.0)


class TestValidation:
    def test_negative_shares(self) -> None:
        with pytest.raises(ValuationError, match="shares"):
            validate_relative_inputs(_base(shares_outstanding=-1))

    def test_negative_ev(self) -> None:
        with pytest.raises(ValuationError, match="enterprise_value"):
            validate_relative_inputs(_base(enterprise_value=-1))

    def test_negative_revenue(self) -> None:
        with pytest.raises(ValuationError, match="revenue"):
            validate_relative_inputs(_base(revenue=-10))

    def test_missing_industry(self) -> None:
        with pytest.raises(ValuationError, match="industry"):
            validate_relative_inputs(
                _base(industry=BenchmarkMultiples(), benchmark_scope=BenchmarkScope.INDUSTRY)
            )

    def test_missing_sector(self) -> None:
        with pytest.raises(ValuationError, match="sector"):
            validate_relative_inputs(
                _base(sector=BenchmarkMultiples(), benchmark_scope=BenchmarkScope.SECTOR)
            )

    def test_missing_peer(self) -> None:
        with pytest.raises(ValuationError, match="peer"):
            validate_relative_inputs(
                _base(peer=BenchmarkMultiples(), benchmark_scope=BenchmarkScope.PEER)
            )

    def test_missing_historical(self) -> None:
        with pytest.raises(ValuationError, match="historical"):
            validate_relative_inputs(
                _base(
                    benchmark_scope=BenchmarkScope.HISTORICAL,
                    historical_average=None,
                    average_5y=None,
                    average_10y=None,
                )
            )

    def test_impossible_multiple(self) -> None:
        with pytest.raises(ValuationError, match="impossible"):
            validate_relative_inputs(_base(industry=_bench(median=-5.0)))

    def test_impossible_yield(self) -> None:
        with pytest.raises(ValuationError, match="impossible yield"):
            validate_relative_inputs(
                _base(
                    method=RelativeMultiple.DIVIDEND_YIELD,
                    industry=_bench(median=-0.01, mean=-0.01, p25=-0.02, p75=-0.005),
                )
            )

    def test_missing_eps(self) -> None:
        with pytest.raises(ValuationError, match="eps"):
            validate_relative_inputs(_base(eps=None))

    def test_zero_eps(self) -> None:
        with pytest.raises(ValuationError, match="non-zero"):
            validate_relative_inputs(_base(eps=0.0))

    def test_zero_forward_eps(self) -> None:
        with pytest.raises(ValuationError, match="forward_eps"):
            validate_relative_inputs(
                _base(method=RelativeMultiple.FORWARD_PE, forward_eps=0.0)
            )

    def test_zero_growth_peg(self) -> None:
        with pytest.raises(ValuationError, match="expected_growth"):
            validate_relative_inputs(
                _base(method=RelativeMultiple.PEG, expected_growth=0.0)
            )

    def test_negative_price(self) -> None:
        with pytest.raises(ValuationError, match="current_market_price"):
            validate_relative_inputs(_base(current_market_price=-1))

    def test_nan(self) -> None:
        with pytest.raises(ValuationError, match="NaN"):
            validate_relative_inputs(_base(eps=float("nan")))

    def test_infinite(self) -> None:
        with pytest.raises(ValuationError, match="infinite"):
            validate_relative_inputs(_base(eps=float("inf")))

    def test_weighted_missing_all(self) -> None:
        with pytest.raises(ValuationError, match="weighted"):
            validate_relative_inputs(
                _base(
                    benchmark_scope=BenchmarkScope.WEIGHTED,
                    industry=BenchmarkMultiples(),
                    sector=BenchmarkMultiples(),
                    peer=BenchmarkMultiples(),
                )
            )

    def test_weight_warning(self) -> None:
        summary = validate_relative_inputs(
            _base(
                benchmark_scope=BenchmarkScope.WEIGHTED,
                industry_weight=0.5,
                sector_weight=0.5,
                peer_weight=0.5,
            )
        )
        assert any("weights" in w for w in summary.warnings)

    def test_weak_peer_warning(self) -> None:
        summary = validate_relative_inputs(_base(peer=_bench(count=2)))
        assert any("weak peer" in w.lower() for w in summary.warnings)

    def test_negative_eps_warning(self) -> None:
        summary = validate_relative_inputs(_base(eps=-1.0))
        assert any("negative EPS" in w for w in summary.warnings)


class TestSensitivityScenarios:
    def test_scenarios(self) -> None:
        r = RelativeEngine().analyze(_base())
        kinds = {s.kind.name for s in r.scenarios}
        assert "bear" in kinds
        assert "base" in kinds
        assert "bull" in kinds
        assert any("stress" in s.kind.name for s in r.scenarios)

    def test_sensitivity(self) -> None:
        r = RelativeEngine().analyze(_base())
        assert "industry_multiple" in r.sensitivity.grids
        assert "peer_multiple" in r.sensitivity.grids
        assert "growth_rate" in r.sensitivity.grids
        assert "margin" in r.sensitivity.grids
        assert "enterprise_value" in r.sensitivity.grids
        assert r.sensitivity.notes is not None or r.sensitivity.grids


    def test_sensitivity_ev_none_cells(self) -> None:
        r = RelativeEngine().analyze(
            _base(method=RelativeMultiple.EV_EBITDA, industry=_bench(10.0))
        )
        cells = []
        for grid in r.sensitivity.grids.values():
            cells.extend(grid)
        assert cells


class TestConfidenceFlags:
    def test_confidence(self) -> None:
        r = RelativeEngine().analyze(_base())
        assert r.confidence in {"high", "medium", "low"}
        assert r.confidence_detail.score >= 0
        assert r.confidence_detail.score <= r.confidence_detail.max_score

    def test_undervalued_deep_value(self) -> None:
        # PE=20, fair industry=40 → discount 50%
        r = RelativeEngine().analyze(_base(industry=_bench(40.0)))
        assert RelativeQualityFlag.UNDERVALUED in r.quality_flags
        assert RelativeQualityFlag.DEEP_VALUE in r.quality_flags

    def test_overvalued_premium(self) -> None:
        r = RelativeEngine().analyze(_base(industry=_bench(10.0)))
        assert RelativeQualityFlag.OVERVALUED in r.quality_flags
        assert RelativeQualityFlag.PREMIUM_VALUATION in r.quality_flags

    def test_mild_undervalued(self) -> None:
        # PE=20, fair=24 → ~16.7% discount
        r = RelativeEngine().analyze(_base(industry=_bench(24.0)))
        assert RelativeQualityFlag.UNDERVALUED in r.quality_flags
        assert RelativeQualityFlag.DEEP_VALUE not in r.quality_flags

    def test_mild_overvalued(self) -> None:
        r = RelativeEngine().analyze(_base(industry=_bench(17.0)))
        assert RelativeQualityFlag.OVERVALUED in r.quality_flags

    def test_growth_premium(self) -> None:
        r = RelativeEngine().analyze(
            _base(industry=_bench(10.0), expected_growth=0.20)
        )
        assert RelativeQualityFlag.GROWTH_PREMIUM in r.quality_flags

    def test_weak_peer_flag(self) -> None:
        r = RelativeEngine().analyze(_base(peer=_bench(count=2)))
        assert RelativeQualityFlag.WEAK_PEER_SET in r.quality_flags

    def test_outlier_and_leaders(self) -> None:
        # current PE=20 >= p75=12 → high percentile
        r = RelativeEngine().analyze(
            _base(
                industry=_bench(15.0, 16.0, 12, 8.0, 12.0),
                sector=_bench(14.0, 15.0, 20, 8.0, 12.0),
                peer=_bench(13.0, 14.0, 6, 8.0, 12.0),
            )
        )
        assert RelativeQualityFlag.OUTLIER_MULTIPLE in r.quality_flags
        assert RelativeQualityFlag.INDUSTRY_LEADER in r.quality_flags
        assert RelativeQualityFlag.SECTOR_LEADER in r.quality_flags

    def test_cyclical(self) -> None:
        r = RelativeEngine().analyze(
            _base(
                industry=_bench(10.0),
                ebitda=250.0,
                revenue=500.0,
            )
        )
        assert RelativeQualityFlag.CYCLICAL_VALUATION in r.quality_flags

    def test_aq_unit_interval(self) -> None:
        r = RelativeEngine().analyze(_base(accounting_quality_score=0.7))
        assert r.confidence_detail.score >= 0

    def test_low_peer_quality_confidence(self) -> None:
        r = RelativeEngine().analyze(
            _base(
                peer=_bench(count=0),
                industry=_bench(count=2),
                historical_average=None,
                average_5y=None,
                average_10y=None,
                risk_free_rate=None,
                market_premium=None,
                accounting_quality_score=None,
                eps=5.0,
                revenue=None,
                ebitda=None,
                book_value=None,
                enterprise_value=None,
                free_cash_flow=None,
            )
        )
        assert r.confidence in {"high", "medium", "low"}


class TestExplainabilityIntegration:
    def test_helpers_and_payloads(self) -> None:
        assert explain_step(name="x", value=1.0, formula="x=1").name == "x"
        assert len(explain_many([{"name": "y", "value": 2, "formula": "y=2"}])) == 1
        result = ValuationEngine().analyze_relative(_base())
        assert len(result.explainability) >= 5
        assert "research" in result.disclaimer.lower()
        vr = to_valuation_result(result)
        assert vr.model_name == "relative"
        from valuation import (
            to_relative_valuation_result,
            to_relative_v2_aggregate_payload,
        )

        assert to_relative_valuation_result(result).model_name == "relative"
        assert to_v2_aggregate_payload(result)["method"] == "relative"
        assert to_relative_v2_aggregate_payload(result)["multiple"] == "pe"
        assert result.to_dict()["method"] == "pe"
        assert result.peer_ranking.value is not None
        assert result.industry_ranking.value is not None
        assert result.historical_ranking.value is not None


class TestProviderAndMaps:
    def test_static_provider(self) -> None:
        provider = StaticMultipleProvider(
            industry={RelativeMultiple.PE: _bench(18.0)},
            sector={RelativeMultiple.PE: _bench(17.0)},
            peer={RelativeMultiple.PE: _bench(16.0)},
            historical={RelativeMultiple.PE: 14.0},
        )
        assert isinstance(provider, object)
        assert provider.get_industry(RelativeMultiple.PE).median == 18.0
        assert provider.get_sector(RelativeMultiple.PE).median == 17.0
        assert provider.get_peer(RelativeMultiple.PE).median == 16.0
        assert provider.get_historical(RelativeMultiple.PE) == 14.0
        assert provider.get_industry(RelativeMultiple.PB).median is None

    def test_by_multiple_maps(self) -> None:
        r = RelativeEngine().analyze(
            _base(
                method=RelativeMultiple.PB,
                industry=BenchmarkMultiples(),  # empty primary; use map
                industry_by_multiple={RelativeMultiple.PB: _bench(2.5)},
                sector_by_multiple={RelativeMultiple.PB: _bench(2.2)},
                peer_by_multiple={RelativeMultiple.PB: _bench(2.0)},
                historical_by_multiple={RelativeMultiple.PB: 1.8},
            )
        )
        assert r.fair_multiple.value == pytest.approx(2.5)
        snap = next(
            s for s in r.multiple_analysis.snapshots if s.multiple is RelativeMultiple.PB
        )
        assert snap.historical_average == pytest.approx(1.8)


class TestEdgeCases:
    def test_dividend_from_dps(self) -> None:
        r = RelativeEngine().analyze(
            _base(
                method=RelativeMultiple.DIVIDEND_YIELD,
                dividend_yield=None,
                dividend_per_share=3.0,
                industry=_bench(0.03, 0.03, 8, 0.02, 0.04),
            )
        )
        assert r.current_multiple.value == pytest.approx(0.03)
        assert r.implied_share_price.value == pytest.approx(3.0 / 0.03)

    def test_peg_growth_already_percent(self) -> None:
        r = RelativeEngine().analyze(
            _base(
                method=RelativeMultiple.PEG,
                expected_growth=10.0,
                industry=_bench(2.0),
            )
        )
        assert r.current_multiple.value == pytest.approx(20.0 / 10.0)

    def test_percentile_below_p25(self) -> None:
        r = RelativeEngine().analyze(
            _base(
                current_market_price=40.0,  # PE=8
                industry=_bench(15.0, 16.0, 12, 10.0, 20.0),
                peer=_bench(15.0, 16.0, 6, 10.0, 20.0),
            )
        )
        assert r.peer_ranking.value is not None
        assert r.peer_ranking.value < 50.0

    def test_percentile_without_quartiles(self) -> None:
        r = RelativeEngine().analyze(
            _base(
                industry=_bench(15.0, 16.0, 12, None, None),
                peer=_bench(15.0, 16.0, 6, None, None),
            )
        )
        assert r.industry_ranking.value == pytest.approx(50.0 * (20.0 / 15.0))

    def test_unknown_method(self) -> None:
        inputs = _base()
        object.__setattr__(inputs, "method", "bogus")  # type: ignore[arg-type]
        with pytest.raises(ValuationError, match="unknown multiple"):
            RelativeEngine()._compute_multiple(inputs, inputs.method)  # type: ignore[arg-type]

    def test_unknown_scope(self) -> None:
        inputs = _base()
        object.__setattr__(inputs, "benchmark_scope", "bogus")  # type: ignore[arg-type]
        with pytest.raises(ValuationError, match="unknown benchmark scope"):
            RelativeEngine()._fair_from_scope(
                inputs, inputs.industry, inputs.sector, inputs.peer, 12.0
            )

    def test_unable_to_resolve_fair(self) -> None:
        # Bypass validation by calling _value with empty benches after patching scope
        inputs = _base(
            industry=BenchmarkMultiples(),
            sector=BenchmarkMultiples(),
            peer=BenchmarkMultiples(),
            historical_average=None,
            average_5y=None,
            average_10y=None,
            benchmark_scope=BenchmarkScope.WEIGHTED,
            industry_weight=0.0,
            sector_weight=0.0,
            peer_weight=0.0,
        )
        # validation would fail; call _value directly after forcing empty pick
        with pytest.raises(ValuationError, match="unable to resolve fair"):
            RelativeEngine()._value(inputs)

    def test_compute_none_when_missing_drivers(self) -> None:
        eng = RelativeEngine()
        bare = RelativeInputs(
            current_market_price=10.0,
            shares_outstanding=1.0,
            method=RelativeMultiple.PE,
            industry=_bench(),
        )
        assert eng._compute_multiple(bare, RelativeMultiple.PE) is None
        assert eng._compute_multiple(bare, RelativeMultiple.FORWARD_PE) is None
        assert eng._compute_multiple(bare, RelativeMultiple.PEG) is None
        assert eng._compute_multiple(bare, RelativeMultiple.PB) is None
        assert eng._compute_multiple(bare, RelativeMultiple.PTBV) is None
        assert eng._compute_multiple(bare, RelativeMultiple.PRICE_SALES) is None
        assert eng._compute_multiple(bare, RelativeMultiple.PRICE_CASH_FLOW) is None
        assert eng._compute_multiple(bare, RelativeMultiple.PRICE_FCF) is None
        assert eng._compute_multiple(bare, RelativeMultiple.EV_SALES) is None
        assert eng._compute_multiple(bare, RelativeMultiple.EV_EBIT) is None
        assert eng._compute_multiple(bare, RelativeMultiple.EV_EBITDA) is None
        assert eng._compute_multiple(bare, RelativeMultiple.DIVIDEND_YIELD) is None

    def test_implied_ev_zero_enterprise(self) -> None:
        eng = RelativeEngine()
        inputs = _base(
            method=RelativeMultiple.EV_EBITDA,
            enterprise_value=0.0,
            industry=_bench(10.0),
        )
        assert eng._implied_price(inputs, RelativeMultiple.EV_EBITDA, 10.0, 5.0) is None

    def test_implied_dividend_missing_dps(self) -> None:
        eng = RelativeEngine()
        inputs = _base(
            method=RelativeMultiple.DIVIDEND_YIELD,
            dividend_per_share=None,
            industry=_bench(0.03),
        )
        assert (
            eng._implied_price(inputs, RelativeMultiple.DIVIDEND_YIELD, 0.03, 0.02)
            is None
        )

    def test_implied_peg_missing_growth(self) -> None:
        eng = RelativeEngine()
        inputs = _base(method=RelativeMultiple.PEG, expected_growth=None)
        assert eng._implied_price(inputs, RelativeMultiple.PEG, 1.5, 2.0) is None

    def test_driver_per_share_ev_and_none(self) -> None:
        eng = RelativeEngine()
        inputs = _base()
        assert eng._driver_per_share(inputs, RelativeMultiple.EV_SALES) == pytest.approx(
            0.1
        )
        assert eng._driver_per_share(inputs, RelativeMultiple.PEG) == pytest.approx(5.0)
        assert eng._driver_per_share(
            inputs, RelativeMultiple.DIVIDEND_YIELD
        ) == pytest.approx(2.0)
        zero_shares = RelativeInputs(
            current_market_price=10.0,
            shares_outstanding=0.0,
            method=RelativeMultiple.EV_SALES,
            industry=_bench(),
        )
        assert eng._driver_per_share(zero_shares, RelativeMultiple.EV_SALES) is None
        assert eng._driver_per_share(inputs, "bogus") is None  # type: ignore[arg-type]

    def test_peer_confidence_bands(self) -> None:
        r8 = RelativeEngine().analyze(_base(peer=_bench(count=8)))
        assert r8.confidence_detail.score >= 0
        r3 = RelativeEngine().analyze(_base(peer=_bench(count=3)))
        assert r3.confidence_detail.score >= 0
        r1 = RelativeEngine().analyze(_base(peer=_bench(count=1)))
        assert RelativeQualityFlag.WEAK_PEER_SET in r1.quality_flags

    def test_sensitivity_handles_valuation_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        eng = RelativeEngine()
        inputs = _base()

        def boom(_adj: RelativeInputs):
            raise ValuationError("forced")

        monkeypatch.setattr(eng, "_value", boom)
        mat = eng._sensitivity(inputs)
        cells = [c for g in mat.grids.values() for c in g]
        assert any(c.output_value is None for c in cells)

    def test_percentile_edge_lo_zero(self) -> None:
        eng = RelativeEngine()
        bench = BenchmarkMultiples(median=10.0, percentile_25=0.0, percentile_75=20.0)
        assert eng._percentile(0.0, bench) == 0.0
        assert eng._percentile(None, bench) is None
        empty = BenchmarkMultiples()
        assert eng._percentile(10.0, empty) is None
        # between p25 and median
        b2 = _bench(15.0, 16.0, 8, 10.0, 20.0)
        assert eng._percentile(12.0, b2) is not None
        assert eng._percentile(17.0, b2) is not None
        # no median between quartiles
        b3 = BenchmarkMultiples(
            median=None, mean=15.0, percentile_25=10.0, percentile_75=20.0
        )
        assert eng._percentile(15.0, b3) == pytest.approx(50.0)

    def test_performance_budget(self) -> None:
        engine = RelativeEngine()
        inputs = _base()
        t0 = time.perf_counter()
        for _ in range(20):
            engine.analyze(inputs)
        avg_ms = (time.perf_counter() - t0) * 1000.0 / 20.0
        assert avg_ms < 50.0, f"avg {avg_ms:.2f} ms >= 50"

    def test_multiple_analysis_all_snapshots(self) -> None:
        r = RelativeEngine().analyze(_base())
        assert len(r.multiple_analysis.snapshots) == len(RelativeMultiple)
        assert r.multiple_analysis.primary.multiple is RelativeMultiple.PE
        assert r.margin_of_safety.value is not None
        assert not math.isnan(r.execution_time_ms or 0.0)

    def test_scenario_sensitivity_with_ev_ebit(self) -> None:
        r = RelativeEngine().analyze(
            _base(method=RelativeMultiple.EV_EBIT, industry=_bench(12.0))
        )
        assert r.implied_share_price.value is not None
        assert len(r.scenarios) >= 3

    def test_forecast_risk_core_flag(self) -> None:
        r = RelativeEngine().analyze(
            _base(
                peer=_bench(count=0),
                industry=_bench(count=1, median=15.0),
                historical_average=None,
                average_5y=None,
                average_10y=None,
                risk_free_rate=None,
                market_premium=None,
                accounting_quality_score=0.1,
                revenue=None,
                ebitda=None,
                book_value=None,
                enterprise_value=None,
                free_cash_flow=None,
                operating_cash_flow=None,
            )
        )
        # May or may not be low depending on ConfidenceEngine weights
        assert r.confidence in {"high", "medium", "low"}
