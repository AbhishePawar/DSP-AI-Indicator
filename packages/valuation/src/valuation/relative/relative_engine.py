"""Relative Valuation Engine — research-only multiples framework.

Computes company multiples vs injected industry / sector / peer / historical
benchmarks. No network I/O; no hardcoded company names.
"""

from __future__ import annotations

import time
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, Mapping

from valuation.core.confidence_engine import ConfidenceEngine
from valuation.core.metadata import RESEARCH_DISCLAIMER, VALUATION_CORE_VERSION
from valuation.core.quality_flags import QualityFlag
from valuation.core.result_models import (
    ScenarioKind,
    ScenarioOutcome,
    SensitivityMatrix,
    ValuationMetadata,
)
from valuation.core.scenario_engine import ScenarioEngine, ScenarioSpec
from valuation.core.sensitivity_engine import SensitivityAxis, SensitivityEngine
from valuation.exceptions import ValuationError
from valuation.relative.relative_explainability import explain_many, explain_step
from valuation.relative.relative_models import (
    RELATIVE_VERSION,
    BenchmarkMultiples,
    BenchmarkScope,
    MultipleAnalysis,
    MultipleSnapshot,
    RelativeInputs,
    RelativeMultiple,
    RelativeQualityFlag,
    RelativeValuationResult,
)
from valuation.relative.relative_validation import validate_relative_inputs

__all__ = ["RelativeEngine", "RELATIVE_VERSION"]

_METHODOLOGY = (
    "Relative Valuation Suite (research only): compare company multiples "
    "(P/E, Forward P/E, PEG, P/B, P/TBV, P/S, P/CF, P/FCF, EV/Sales, EV/EBIT, "
    "EV/EBITDA, Dividend Yield) to injected industry / sector / peer / "
    "historical benchmarks. Fair value = fair multiple × company driver. "
    "Not investment advice. Independent of market-data APIs."
)

_LIMITATIONS = (
    RESEARCH_DISCLAIMER,
    "Peer / industry multiples must be injected — engine does not fetch data",
    "Multiples ignore capital-structure nuances unless EV-based",
    "Does not enable Overall Valuation",
    "Independent of DCF / Reverse DCF / RIV / EPV / Graham / DDM / Asset-Based",
)

_ALL_MULTIPLES: tuple[RelativeMultiple, ...] = tuple(RelativeMultiple)


class RelativeEngine:
    """Compute research-only relative valuations."""

    def analyze(self, inputs: RelativeInputs) -> RelativeValuationResult:
        """Run relative valuation for the selected primary multiple."""
        t0 = time.perf_counter()
        validation = validate_relative_inputs(inputs)
        base = self._value(inputs)

        scenarios = self._scenarios(inputs)
        sensitivity = self._sensitivity(inputs)
        confidence = self._confidence(inputs, base)
        flags, core_flags = self._quality_flags(inputs, base, confidence.level)

        explain_records = [
            base["current_exp"],
            base["fair_exp"],
            base["implied_exp"],
            base["iv_exp"],
            base["ivps_exp"],
            base["pd_exp"],
            base["mos_exp"],
            base["peer_rank_exp"],
            base["ind_rank_exp"],
            base["hist_rank_exp"],
        ]
        explainability = explain_many(
            [
                {
                    "name": r.name,
                    "value": r.value,
                    "formula": r.formula,
                    "inputs": dict(r.inputs),
                    "intermediates": dict(r.intermediates),
                    "confidence": r.confidence,
                    "notes": r.notes,
                    "warnings": r.warnings,
                }
                for r in explain_records
            ]
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        metadata = ValuationMetadata(
            model_name="relative",
            engine_version=RELATIVE_VERSION,
            methodology=_METHODOLOGY,
            formula_references=(
                "Relative multiples: Price/Driver and EV/Driver",
                "Fair price = Fair Multiple × Driver",
            ),
            assumption_summary={
                "method": inputs.method.value,
                "benchmark_scope": inputs.benchmark_scope.value,
                "industry_weight": inputs.industry_weight,
                "peer_weight": inputs.peer_weight,
            },
            research_mode=True,
            calculation_timestamp=datetime.now(UTC).isoformat(),
            execution_time_ms=elapsed_ms,
            core_version=VALUATION_CORE_VERSION,
        )

        return RelativeValuationResult(
            version=RELATIVE_VERSION,
            currency=inputs.currency,
            disclaimer=RESEARCH_DISCLAIMER,
            methodology=_METHODOLOGY,
            method=inputs.method,
            benchmark_scope=inputs.benchmark_scope,
            current_multiple=base["current_exp"],
            fair_multiple=base["fair_exp"],
            implied_share_price=base["implied_exp"],
            intrinsic_value=base["iv_exp"],
            intrinsic_value_per_share=base["ivps_exp"],
            premium_discount=base["pd_exp"],
            margin_of_safety=base["mos_exp"],
            peer_ranking=base["peer_rank_exp"],
            industry_ranking=base["ind_rank_exp"],
            historical_ranking=base["hist_rank_exp"],
            multiple_analysis=base["analysis"],
            confidence=confidence.level,
            confidence_detail=confidence,
            quality_flags=flags,
            core_quality_flags=core_flags,
            validation_summary=validation,
            scenarios=scenarios,
            sensitivity=sensitivity,
            explainability=explainability,
            limitations=_LIMITATIONS,
            metadata=metadata,
            execution_time_ms=elapsed_ms,
        )

    def _market_cap(self, inputs: RelativeInputs) -> float:
        return inputs.current_market_price * inputs.shares_outstanding

    def _compute_multiple(
        self, inputs: RelativeInputs, multiple: RelativeMultiple
    ) -> float | None:
        price = inputs.current_market_price
        mcap = self._market_cap(inputs)
        ev = inputs.enterprise_value

        if multiple is RelativeMultiple.PE:
            if inputs.eps is None or inputs.eps == 0:
                return None
            return price / inputs.eps
        if multiple is RelativeMultiple.FORWARD_PE:
            if inputs.forward_eps is None or inputs.forward_eps == 0:
                return None
            return price / inputs.forward_eps
        if multiple is RelativeMultiple.PEG:
            pe = self._compute_multiple(inputs, RelativeMultiple.PE)
            g = inputs.expected_growth
            if pe is None or g is None or g == 0:
                return None
            # PEG uses growth in percent units when |g| < 1 (decimal → ×100)
            g_pct = g * 100.0 if abs(g) < 1.0 else g
            return pe / g_pct
        if multiple is RelativeMultiple.PB:
            if not inputs.book_value or inputs.book_value == 0:
                return None
            return mcap / inputs.book_value
        if multiple is RelativeMultiple.PTBV:
            if not inputs.tangible_book_value or inputs.tangible_book_value == 0:
                return None
            return mcap / inputs.tangible_book_value
        if multiple is RelativeMultiple.PRICE_SALES:
            if not inputs.revenue or inputs.revenue == 0:
                return None
            return mcap / inputs.revenue
        if multiple is RelativeMultiple.PRICE_CASH_FLOW:
            if not inputs.operating_cash_flow or inputs.operating_cash_flow == 0:
                return None
            return mcap / inputs.operating_cash_flow
        if multiple is RelativeMultiple.PRICE_FCF:
            if not inputs.free_cash_flow or inputs.free_cash_flow == 0:
                return None
            return mcap / inputs.free_cash_flow
        if multiple is RelativeMultiple.EV_SALES:
            if ev is None or not inputs.revenue or inputs.revenue == 0:
                return None
            return ev / inputs.revenue
        if multiple is RelativeMultiple.EV_EBIT:
            if ev is None or not inputs.ebit or inputs.ebit == 0:
                return None
            return ev / inputs.ebit
        if multiple is RelativeMultiple.EV_EBITDA:
            if ev is None or not inputs.ebitda or inputs.ebitda == 0:
                return None
            return ev / inputs.ebitda
        if multiple is RelativeMultiple.DIVIDEND_YIELD:
            if inputs.dividend_yield is not None:
                return inputs.dividend_yield
            if inputs.dividend_per_share is not None and price > 0:
                return inputs.dividend_per_share / price
            return None
        raise ValuationError(f"unknown multiple: {multiple!r}")

    def _driver_per_share(
        self, inputs: RelativeInputs, multiple: RelativeMultiple
    ) -> float | None:
        """Driver that converts a fair multiple into an implied share price."""
        shares = inputs.shares_outstanding
        if multiple is RelativeMultiple.PE:
            return inputs.eps
        if multiple is RelativeMultiple.FORWARD_PE:
            return inputs.forward_eps
        if multiple is RelativeMultiple.PEG:
            # Implied PE = PEG × g_pct; price = PE × EPS
            return inputs.eps
        if multiple is RelativeMultiple.PB:
            return None if not inputs.book_value else inputs.book_value / shares
        if multiple is RelativeMultiple.PTBV:
            return (
                None
                if not inputs.tangible_book_value
                else inputs.tangible_book_value / shares
            )
        if multiple is RelativeMultiple.PRICE_SALES:
            return None if not inputs.revenue else inputs.revenue / shares
        if multiple is RelativeMultiple.PRICE_CASH_FLOW:
            return (
                None
                if not inputs.operating_cash_flow
                else inputs.operating_cash_flow / shares
            )
        if multiple is RelativeMultiple.PRICE_FCF:
            return (
                None
                if not inputs.free_cash_flow
                else inputs.free_cash_flow / shares
            )
        if multiple in {
            RelativeMultiple.EV_SALES,
            RelativeMultiple.EV_EBIT,
            RelativeMultiple.EV_EBITDA,
        }:
            # Approximate equity price via EV fair / shares (research heuristic)
            return 1.0 / shares if shares else None
        if multiple is RelativeMultiple.DIVIDEND_YIELD:
            # Fair price ≈ DPS / fair yield
            return inputs.dividend_per_share
        return None

    def _resolve_bench(
        self, inputs: RelativeInputs, multiple: RelativeMultiple
    ) -> tuple[BenchmarkMultiples, BenchmarkMultiples, BenchmarkMultiples, float | None]:
        industry = inputs.industry_by_multiple.get(multiple, inputs.industry)
        sector = inputs.sector_by_multiple.get(multiple, inputs.sector)
        peer = inputs.peer_by_multiple.get(multiple, inputs.peer)
        if multiple is inputs.method:
            industry = inputs.industry if _has_bench(inputs.industry) else industry
            sector = inputs.sector if _has_bench(inputs.sector) else sector
            peer = inputs.peer if _has_bench(inputs.peer) else peer
        hist = inputs.historical_by_multiple.get(multiple)
        if hist is None and multiple is inputs.method:
            hist = (
                inputs.historical_average
                or inputs.average_5y
                or inputs.average_10y
            )
        return industry, sector, peer, hist

    def _fair_from_scope(
        self,
        inputs: RelativeInputs,
        industry: BenchmarkMultiples,
        sector: BenchmarkMultiples,
        peer: BenchmarkMultiples,
        historical: float | None,
    ) -> float | None:
        scope = inputs.benchmark_scope

        def pick(b: BenchmarkMultiples) -> float | None:
            if b.median is not None and b.median > 0:
                return b.median
            if b.mean is not None and b.mean > 0:
                return b.mean
            return None

        if scope is BenchmarkScope.INDUSTRY:
            return pick(industry)
        if scope is BenchmarkScope.SECTOR:
            return pick(sector)
        if scope is BenchmarkScope.PEER:
            return pick(peer)
        if scope is BenchmarkScope.HISTORICAL:
            return historical if historical and historical > 0 else None
        if scope is BenchmarkScope.WEIGHTED:
            parts: list[tuple[float, float]] = []
            for w, b in (
                (inputs.industry_weight, industry),
                (inputs.sector_weight, sector),
                (inputs.peer_weight, peer),
            ):
                v = pick(b)
                if v is not None and w > 0:
                    parts.append((w, v))
            if not parts:
                return None
            wsum = sum(w for w, _ in parts)
            return sum(w * v for w, v in parts) / wsum
        raise ValuationError(f"unknown benchmark scope: {scope!r}")

    def _implied_price(
        self,
        inputs: RelativeInputs,
        multiple: RelativeMultiple,
        fair: float,
        current: float | None,
    ) -> float | None:
        if multiple is RelativeMultiple.DIVIDEND_YIELD:
            dps = inputs.dividend_per_share
            if dps is None or fair <= 0:
                return None
            return dps / fair
        if multiple is RelativeMultiple.PEG:
            g = inputs.expected_growth
            if g is None or inputs.eps is None:
                return None
            g_pct = g * 100.0 if abs(g) < 1.0 else g
            implied_pe = fair * g_pct
            return implied_pe * inputs.eps
        if multiple in {
            RelativeMultiple.EV_SALES,
            RelativeMultiple.EV_EBIT,
            RelativeMultiple.EV_EBITDA,
        }:
            # Fair EV = fair multiple × driver; equity ≈ fair EV × (price/EV)
            driver = None
            if multiple is RelativeMultiple.EV_SALES:
                driver = inputs.revenue
            elif multiple is RelativeMultiple.EV_EBIT:
                driver = inputs.ebit
            else:
                driver = inputs.ebitda
            if driver is None or inputs.enterprise_value is None:
                return None
            if inputs.enterprise_value == 0:
                return None
            fair_ev = fair * driver
            # Scale current price by EV ratio (research heuristic)
            return inputs.current_market_price * (fair_ev / inputs.enterprise_value)
        driver = self._driver_per_share(inputs, multiple)
        if driver is None:
            return None
        return fair * driver

    def _percentile(
        self, current: float | None, bench: BenchmarkMultiples
    ) -> float | None:
        if current is None:
            return None
        lo = bench.percentile_25
        hi = bench.percentile_75
        med = bench.median
        if lo is not None and hi is not None and hi > lo:
            # Piecewise linear vs quartiles
            if current <= lo:
                return max(0.0, 25.0 * (current / lo)) if lo else 0.0
            if current >= hi:
                return min(100.0, 75.0 + 25.0 * min(1.0, (current - hi) / hi))
            if med is not None and med > lo:
                if current <= med:
                    return 25.0 + 25.0 * (current - lo) / (med - lo)
                return 50.0 + 25.0 * (current - med) / (hi - med)
            return 25.0 + 50.0 * (current - lo) / (hi - lo)
        ref = bench.median or bench.mean
        if ref is None or ref == 0:
            return None
        # Simple rank proxy: 50 when equal, clipped
        return max(0.0, min(100.0, 50.0 * (current / ref)))

    def _snapshot(
        self, inputs: RelativeInputs, multiple: RelativeMultiple
    ) -> MultipleSnapshot:
        current = self._compute_multiple(inputs, multiple)
        industry, sector, peer, hist = self._resolve_bench(inputs, multiple)
        # For non-primary, still allow empty primary benches from maps
        if multiple is not inputs.method:
            pass
        fair = self._fair_from_scope(inputs, industry, sector, peer, hist)
        gap = None
        pd = None
        if current is not None and fair is not None and fair != 0:
            gap = current - fair
            pd = (current - fair) / fair
        implied = (
            self._implied_price(inputs, multiple, fair, current)
            if fair is not None
            else None
        )
        # Prefer peer then industry for ranking display
        rank_bench = peer if _has_bench(peer) else industry
        pct = self._percentile(current, rank_bench)
        return MultipleSnapshot(
            multiple=multiple,
            current=current,
            industry=industry,
            sector=sector,
            peer=peer,
            historical_average=hist,
            fair_multiple=fair,
            valuation_gap=gap,
            premium_discount=pd,
            percentile_rank=pct,
            implied_price=implied,
        )

    def _value(self, inputs: RelativeInputs) -> dict[str, Any]:
        conf = "medium"
        primary = self._snapshot(inputs, inputs.method)
        snapshots = [self._snapshot(inputs, m) for m in _ALL_MULTIPLES]
        analysis = MultipleAnalysis(
            snapshots=tuple(snapshots),
            primary=primary,
        )

        current = primary.current
        fair = primary.fair_multiple
        implied = primary.implied_price
        if fair is None:
            raise ValuationError("unable to resolve fair multiple from benchmarks")
        # P1-04 — never substitute market price for an unresolved implied IV.
        if implied is None:
            raise ValuationError(
                "relative valuation unavailable: implied price could not be "
                "derived from the fair multiple (missing required fundamentals)"
            )

        ivps = float(implied)
        intrinsic = ivps * inputs.shares_outstanding
        pd = primary.premium_discount
        mos = None
        if ivps != 0:
            mos = (ivps - inputs.current_market_price) / ivps

        peer_rank = self._percentile(current, primary.peer)
        ind_rank = self._percentile(current, primary.industry)
        hist_rank = None
        if current is not None and primary.historical_average:
            hist_rank = max(
                0.0,
                min(100.0, 50.0 * (current / primary.historical_average)),
            )

        current_exp = explain_step(
            name="current_multiple",
            value=current,
            formula=f"Current {inputs.method.value} from company fundamentals",
            inputs={"method": inputs.method.value, "price": inputs.current_market_price},
            intermediates={},
            confidence=conf,
        )
        fair_exp = explain_step(
            name="fair_multiple",
            value=fair,
            formula=f"Fair multiple from scope={inputs.benchmark_scope.value}",
            inputs={
                "scope": inputs.benchmark_scope.value,
                "industry_median": primary.industry.median,
                "peer_median": primary.peer.median,
                "sector_median": primary.sector.median,
            },
            intermediates={},
            confidence=conf,
            notes="Peers/industry are injected abstractions — not fetched",
        )
        implied_exp = explain_step(
            name="implied_share_price",
            value=implied,
            formula="Implied Price = Fair Multiple × Driver (or EV scale)",
            inputs={"fair_multiple": fair},
            intermediates={},
            confidence=conf,
        )
        ivps_exp = explain_step(
            name="intrinsic_value_per_share",
            value=ivps,
            formula="IV/share = Implied Share Price from relative multiple",
            inputs={"implied": implied},
            intermediates={},
            confidence=conf,
        )
        iv_exp = explain_step(
            name="intrinsic_value",
            value=intrinsic,
            formula="Equity IV = IV/share × Shares",
            inputs={"ivps": ivps, "shares": inputs.shares_outstanding},
            intermediates={},
            confidence=conf,
        )
        pd_exp = explain_step(
            name="premium_discount",
            value=pd,
            formula="Premium/Discount = (Current Multiple − Fair) / Fair",
            inputs={"current": current, "fair": fair},
            intermediates={},
            confidence=conf,
        )
        mos_exp = explain_step(
            name="margin_of_safety",
            value=mos,
            formula="MoS = (IV/share − Price) / IV/share",
            inputs={"ivps": ivps, "price": inputs.current_market_price},
            intermediates={},
            confidence=conf,
            notes="Research posture only — not a recommendation",
        )
        peer_rank_exp = explain_step(
            name="peer_ranking",
            value=peer_rank,
            formula="Percentile rank vs peer distribution (injected)",
            inputs={"peer_count": primary.peer.count},
            intermediates={},
            confidence=conf if primary.peer.count >= 3 else "low",
            warnings=(
                ("Weak peer set (count < 3)",)
                if primary.peer.count > 0 and primary.peer.count < 3
                else ()
            ),
        )
        ind_rank_exp = explain_step(
            name="industry_ranking",
            value=ind_rank,
            formula="Percentile rank vs industry distribution (injected)",
            inputs={"industry_label": primary.industry.label},
            intermediates={},
            confidence=conf,
        )
        hist_rank_exp = explain_step(
            name="historical_ranking",
            value=hist_rank,
            formula="Rank proxy vs historical average multiple",
            inputs={"historical_average": primary.historical_average},
            intermediates={},
            confidence=conf,
        )

        return {
            "current": current,
            "fair": fair,
            "implied": implied,
            "ivps": ivps,
            "intrinsic": intrinsic,
            "premium_discount": pd,
            "mos": mos,
            "analysis": analysis,
            "primary": primary,
            "current_exp": current_exp,
            "fair_exp": fair_exp,
            "implied_exp": implied_exp,
            "iv_exp": iv_exp,
            "ivps_exp": ivps_exp,
            "pd_exp": pd_exp,
            "mos_exp": mos_exp,
            "peer_rank_exp": peer_rank_exp,
            "ind_rank_exp": ind_rank_exp,
            "hist_rank_exp": hist_rank_exp,
        }

    def _scenarios(self, inputs: RelativeInputs) -> tuple[ScenarioOutcome, ...]:
        engine = ScenarioEngine()
        specs = (
            ScenarioSpec(
                ScenarioKind.bear(),
                {
                    "multiple_delta": inputs.bear_multiple_delta,
                    "growth_delta": inputs.bear_growth_delta,
                },
            ),
            ScenarioSpec(
                ScenarioKind.base(),
                {"multiple_delta": 0.0, "growth_delta": 0.0},
            ),
            ScenarioSpec(
                ScenarioKind.bull(),
                {
                    "multiple_delta": inputs.bull_multiple_delta,
                    "growth_delta": inputs.bull_growth_delta,
                },
            ),
            ScenarioSpec(
                ScenarioKind.custom("stress_peer", "Stress Peer"),
                {"multiple_delta": -0.20, "growth_delta": -0.03},
            ),
        )

        def evaluator(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
            m_delta = float(ctx.get("multiple_delta", 0.0))
            g_delta = float(ctx.get("growth_delta", 0.0))
            ind = inputs.industry
            if ind.median is not None:
                ind = replace(ind, median=max(1e-9, ind.median * (1.0 + m_delta)))
            if ind.mean is not None:
                ind = replace(ind, mean=max(1e-9, ind.mean * (1.0 + m_delta)))
            peer = inputs.peer
            if peer.median is not None:
                peer = replace(peer, median=max(1e-9, peer.median * (1.0 + m_delta)))
            growth = inputs.expected_growth
            if growth is not None:
                growth = growth + g_delta
            adj = replace(
                inputs,
                industry=ind,
                peer=peer,
                expected_growth=growth,
            )
            out = self._value(adj)
            return {
                "intrinsic_value": out["intrinsic"],
                "equity_value": out["intrinsic"],
                "intrinsic_value_per_share": out["ivps"],
                "notes": f"multiple_delta={m_delta}, growth_delta={g_delta}",
                "extras": {"fair": out["fair"]},
            }

        return engine.scenarios({}, specs=specs, evaluator=evaluator)

    def _sensitivity(self, inputs: RelativeInputs) -> SensitivityMatrix:
        ind_med = inputs.industry.median or inputs.industry.mean or 10.0
        peer_med = inputs.peer.median or inputs.peer.mean or ind_med
        growth = inputs.expected_growth if inputs.expected_growth is not None else 0.05
        # Margin proxy via EBIT/revenue when available
        margin = 0.0
        if inputs.ebit is not None and inputs.revenue and inputs.revenue != 0:
            margin = inputs.ebit / inputs.revenue
        ev = inputs.enterprise_value if inputs.enterprise_value is not None else 0.0

        axes = (
            SensitivityAxis(
                "industry_multiple",
                (ind_med * 0.9, ind_med, ind_med * 1.1),
            ),
            SensitivityAxis(
                "peer_multiple",
                (peer_med * 0.9, peer_med, peer_med * 1.1),
            ),
            SensitivityAxis("growth_rate", (growth - 0.02, growth, growth + 0.02)),
            SensitivityAxis("margin", (margin - 0.02, margin, margin + 0.02)),
            SensitivityAxis(
                "enterprise_value",
                (max(0.0, ev * 0.9), ev, ev * 1.1 if ev else 1.0),
            ),
        )

        def evaluator(ctx: Mapping[str, Any]) -> float | None:
            adj = inputs
            if "industry_multiple" in ctx and ctx["industry_multiple"] != ind_med:
                v = max(1e-9, float(ctx["industry_multiple"]))
                adj = replace(
                    adj,
                    industry=replace(adj.industry, median=v, mean=v),
                )
            if "peer_multiple" in ctx and ctx["peer_multiple"] != peer_med:
                v = max(1e-9, float(ctx["peer_multiple"]))
                adj = replace(adj, peer=replace(adj.peer, median=v, mean=v))
            if "growth_rate" in ctx and ctx["growth_rate"] != growth:
                adj = replace(adj, expected_growth=float(ctx["growth_rate"]))
            if "margin" in ctx and ctx["margin"] != margin and adj.revenue:
                adj = replace(adj, ebit=float(ctx["margin"]) * adj.revenue)
            if "enterprise_value" in ctx and ctx["enterprise_value"] != ev:
                adj = replace(
                    adj, enterprise_value=max(0.0, float(ctx["enterprise_value"]))
                )
            try:
                return float(self._value(adj)["ivps"])
            except ValuationError:
                return None

        context = {
            "industry_multiple": ind_med,
            "peer_multiple": peer_med,
            "growth_rate": growth,
            "margin": margin,
            "enterprise_value": ev,
        }
        return SensitivityEngine().sensitivity(
            context,
            axes=axes,
            evaluator=evaluator,
            output_name="intrinsic_value_per_share",
        )

    def _confidence(self, inputs: RelativeInputs, base: Mapping[str, Any]):
        peer = inputs.peer
        peer_quality = 0.3
        if peer.count >= 8:
            peer_quality = 1.0
        elif peer.count >= 5:
            peer_quality = 0.75
        elif peer.count >= 3:
            peer_quality = 0.55
        elif peer.count > 0:
            peer_quality = 0.35

        industry_q = 0.7 if _has_bench(inputs.industry) else 0.3
        if inputs.industry.count >= 10:
            industry_q = 1.0

        market_stability = 0.6
        if inputs.risk_free_rate is not None:
            market_stability += 0.2
        if inputs.market_premium is not None:
            market_stability += 0.2
        market_stability = min(1.0, market_stability)

        aq = inputs.accounting_quality_score
        if aq is None:
            accounting = 0.6
        else:
            accounting = aq / 100.0 if aq > 1.0 else float(aq)
            accounting = max(0.0, min(1.0, accounting))

        hist = 0.4
        if inputs.historical_average or inputs.average_5y or inputs.average_10y:
            hist = 0.8
        if inputs.average_5y and inputs.average_10y:
            hist = 1.0

        completeness = 0.4
        for attr in (
            "eps",
            "revenue",
            "ebitda",
            "book_value",
            "enterprise_value",
            "free_cash_flow",
        ):
            if getattr(inputs, attr) is not None:
                completeness += 0.1
        completeness = min(1.0, completeness)

        return ConfidenceEngine().score(
            {
                "accounting_quality": accounting,
                "forecast_reliability": hist,
                "data_completeness": completeness,
                "business_stability": market_stability,
                "capital_allocation": peer_quality,
                "model_assumptions": industry_q,
            }
        )

    def _quality_flags(
        self,
        inputs: RelativeInputs,
        base: Mapping[str, Any],
        confidence_level: str,
    ) -> tuple[tuple[RelativeQualityFlag, ...], tuple[QualityFlag, ...]]:
        flags: list[RelativeQualityFlag] = []
        core: list[QualityFlag] = []
        pd = base.get("premium_discount")
        primary: MultipleSnapshot = base["primary"]

        if pd is not None:
            if pd <= -0.30:
                flags.append(RelativeQualityFlag.DEEP_VALUE)
                flags.append(RelativeQualityFlag.UNDERVALUED)
            elif pd <= -0.10:
                flags.append(RelativeQualityFlag.UNDERVALUED)
            elif pd >= 0.30:
                flags.append(RelativeQualityFlag.PREMIUM_VALUATION)
                flags.append(RelativeQualityFlag.OVERVALUED)
            elif pd >= 0.10:
                flags.append(RelativeQualityFlag.OVERVALUED)

        g = inputs.expected_growth or inputs.growth_rate
        if g is not None and g > 0.15 and pd is not None and pd > 0:
            flags.append(RelativeQualityFlag.GROWTH_PREMIUM)

        if primary.percentile_rank is not None:
            if primary.percentile_rank >= 90:
                flags.append(RelativeQualityFlag.OUTLIER_MULTIPLE)
            if primary.percentile_rank >= 75 and _has_bench(inputs.industry):
                flags.append(RelativeQualityFlag.INDUSTRY_LEADER)
            if primary.percentile_rank >= 75 and _has_bench(inputs.sector):
                flags.append(RelativeQualityFlag.SECTOR_LEADER)

        if inputs.peer.count > 0 and inputs.peer.count < 3:
            flags.append(RelativeQualityFlag.WEAK_PEER_SET)
            core.append(QualityFlag.LOW_DATA_QUALITY)

        if (
            inputs.ebitda is not None
            and inputs.revenue
            and inputs.revenue > 0
            and abs(inputs.ebitda / inputs.revenue) > 0.4
        ):
            # High cyclicality proxy when margins extreme vs peers (research)
            if pd is not None and abs(pd) > 0.25:
                flags.append(RelativeQualityFlag.CYCLICAL_VALUATION)

        if confidence_level == "low" and RelativeQualityFlag.WEAK_PEER_SET not in flags:
            core.append(QualityFlag.FORECAST_RISK)

        return tuple(dict.fromkeys(flags)), tuple(dict.fromkeys(core))


def _has_bench(b: BenchmarkMultiples) -> bool:
    return (b.median is not None and b.median > 0) or (
        b.mean is not None and b.mean > 0
    )
