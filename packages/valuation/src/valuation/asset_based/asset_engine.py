"""Asset-Based & Liquidation Valuation Engine — research-only.

Methods: book value, tangible book, NAV, adjusted NAV, liquidation,
conservative liquidation, replacement cost.

Integrates Valuation Core without modifying Core or other valuation methods.
"""

from __future__ import annotations

import time
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, Mapping

from valuation.asset_based.asset_explainability import explain_many, explain_step
from valuation.asset_based.asset_models import (
    ASSET_BASED_VERSION,
    AssetAdjustment,
    AssetBasedInputs,
    AssetMethod,
    AssetQuality,
    AssetQualityFlag,
    AssetValuationResult,
    HaircutSchedule,
)
from valuation.asset_based.asset_validation import validate_asset_based_inputs
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

__all__ = ["AssetBasedEngine", "ASSET_BASED_VERSION"]

_METHODOLOGY = (
    "Asset-based valuation (research only): Book Value, Tangible Book, "
    "NAV, Adjusted NAV, Liquidation, Conservative Liquidation, Replacement Cost. "
    "Equity claim = Assets − Liabilities − Minority Interest − Preferred. "
    "Haircuts and fair-value overlays are research assumptions. "
    "Not investment advice."
)

_LIMITATIONS = (
    RESEARCH_DISCLAIMER,
    "Carrying amounts may diverge from economic value",
    "Liquidation haircuts are judgment-sensitive",
    "Does not enable Overall Valuation",
    "Independent of DCF / Reverse DCF / RIV / EPV / Graham / DDM",
)


class AssetBasedEngine:
    """Compute research-only asset-based valuations."""

    def analyze(self, inputs: AssetBasedInputs) -> AssetValuationResult:
        """Run asset-based analysis (selected method as primary IV)."""
        t0 = time.perf_counter()
        validation = validate_asset_based_inputs(inputs)
        base = self._value(inputs)

        scenarios = self._scenarios(inputs)
        sensitivity = self._sensitivity(inputs)
        quality = self._asset_quality(inputs, base)
        confidence = self._confidence(inputs, quality)
        flags, core_flags = self._quality_flags(inputs, base, quality)

        explain_records = [
            base["bv_exp"],
            base["bvps_exp"],
            base["tbv_exp"],
            base["tbvps_exp"],
            base["nav_exp"],
            base["navps_exp"],
            base["anav_exp"],
            base["anavps_exp"],
            base["liq_exp"],
            base["liqps_exp"],
            base["cons_exp"],
            base["repl_exp"],
            base["iv_exp"],
            base["ivps_exp"],
            base["mos_exp"],
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
            model_name="asset_based",
            engine_version=ASSET_BASED_VERSION,
            methodology=_METHODOLOGY,
            formula_references=(
                "Book / Tangible Book equity",
                "NAV / ANAV fair-value overlays",
                "Liquidation haircut schedules",
            ),
            assumption_summary={
                "method": inputs.method.value,
                "haircuts": inputs.haircut_schedule.as_mapping(),
                "hidden_assets": inputs.hidden_assets,
            },
            research_mode=True,
            calculation_timestamp=datetime.now(UTC).isoformat(),
            execution_time_ms=elapsed_ms,
            core_version=VALUATION_CORE_VERSION,
        )

        return AssetValuationResult(
            version=ASSET_BASED_VERSION,
            currency=inputs.currency,
            disclaimer=RESEARCH_DISCLAIMER,
            methodology=_METHODOLOGY,
            method_used=inputs.method,
            book_value=base["bv_exp"],
            book_value_per_share=base["bvps_exp"],
            tangible_book_value=base["tbv_exp"],
            tangible_book_value_per_share=base["tbvps_exp"],
            nav=base["nav_exp"],
            nav_per_share=base["navps_exp"],
            adjusted_nav=base["anav_exp"],
            adjusted_nav_per_share=base["anavps_exp"],
            liquidation_value=base["liq_exp"],
            liquidation_value_per_share=base["liqps_exp"],
            conservative_liquidation_value=base["cons_exp"],
            replacement_cost_value=base["repl_exp"],
            intrinsic_value=base["iv_exp"],
            intrinsic_value_per_share=base["ivps_exp"],
            margin_of_safety=base["mos_exp"],
            asset_quality=quality,
            haircuts_applied=base["haircuts"],
            adjustments=base["adjustments"],
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

    def _sum_assets(self, inputs: AssetBasedInputs) -> float:
        return (
            inputs.cash
            + inputs.cash_equivalents
            + inputs.investments
            + inputs.receivables
            + inputs.inventory
            + inputs.biological_assets
            + inputs.ppe
            + inputs.investment_property
            + inputs.intangible_assets
            + inputs.goodwill
            + inputs.deferred_tax_assets
            + inputs.other_assets
        )

    def _operating_liabilities(self, inputs: AssetBasedInputs) -> float:
        return (
            inputs.accounts_payable
            + inputs.short_term_debt
            + inputs.long_term_debt
            + inputs.lease_liabilities
            + inputs.deferred_tax_liabilities
            + inputs.other_liabilities
        )

    def _claims(self, inputs: AssetBasedInputs) -> float:
        return inputs.minority_interest + inputs.preferred_equity

    def _common_equity(self, gross_equity: float, inputs: AssetBasedInputs) -> float:
        return gross_equity - self._claims(inputs)

    def _fv(self, carrying: float, fair: float | None) -> float:
        return float(fair) if fair is not None else carrying

    def _apply_haircuts(
        self,
        inputs: AssetBasedInputs,
        schedule: HaircutSchedule,
        *,
        property_mult: float = 1.0,
    ) -> tuple[float, dict[str, float], tuple[AssetAdjustment, ...]]:
        rates = schedule.as_mapping()
        components = {
            "cash": inputs.cash,
            "cash_equivalents": inputs.cash_equivalents,
            "investments": self._fv(inputs.investments, inputs.fv_investments),
            "receivables": self._fv(inputs.receivables, inputs.fv_receivables),
            "inventory": self._fv(inputs.inventory, inputs.fv_inventory),
            "biological_assets": self._fv(
                inputs.biological_assets, inputs.fv_biological_assets
            ),
            "ppe": self._fv(inputs.ppe, inputs.fv_ppe) * property_mult,
            "investment_property": self._fv(
                inputs.investment_property, inputs.fv_investment_property
            )
            * property_mult,
            "intangible_assets": inputs.intangible_assets,
            "goodwill": inputs.goodwill,
            "deferred_tax_assets": inputs.deferred_tax_assets,
            "other_assets": inputs.other_assets,
        }
        recovered = 0.0
        adjustments: list[AssetAdjustment] = []
        for name, carrying in components.items():
            rate = rates[name]
            adj_val = carrying * rate
            recovered += adj_val
            adjustments.append(
                AssetAdjustment(
                    name=name,
                    carrying_value=carrying,
                    adjusted_value=adj_val,
                    delta=adj_val - carrying,
                    rationale=f"liquidation recovery {rate:.0%}",
                )
            )
        recovered += inputs.hidden_assets + inputs.off_balance_sheet_assets
        liab = (
            self._operating_liabilities(inputs)
            + inputs.off_balance_sheet_liabilities
        )
        equity = self._common_equity(recovered - liab, inputs)
        return equity, rates, tuple(adjustments)

    def _value(self, inputs: AssetBasedInputs) -> dict[str, Any]:
        conf = "medium"
        assets = self._sum_assets(inputs)
        liab = self._operating_liabilities(inputs)
        book = self._common_equity(assets - liab, inputs)
        tbv = self._common_equity(
            assets - inputs.goodwill - inputs.intangible_assets - liab,
            inputs,
        )

        # NAV: fair-value assets − liabilities − claims (+ OBS)
        nav_assets = (
            inputs.cash
            + inputs.cash_equivalents
            + self._fv(inputs.investments, inputs.fv_investments)
            + self._fv(inputs.receivables, inputs.fv_receivables)
            + self._fv(inputs.inventory, inputs.fv_inventory)
            + self._fv(inputs.biological_assets, inputs.fv_biological_assets)
            + self._fv(inputs.ppe, inputs.fv_ppe)
            + self._fv(inputs.investment_property, inputs.fv_investment_property)
            + inputs.intangible_assets
            + inputs.goodwill
            + inputs.deferred_tax_assets
            + inputs.other_assets
            + inputs.off_balance_sheet_assets
        )
        nav = self._common_equity(
            nav_assets - liab - inputs.off_balance_sheet_liabilities,
            inputs,
        )

        # ANAV: NAV + hidden + private + real estate appreciation + appraisal delta
        anav_adjustments: list[AssetAdjustment] = []
        anav = nav + inputs.hidden_assets + inputs.private_holdings_adjustment
        if inputs.real_estate_appreciation != 0:
            anav += inputs.real_estate_appreciation
            anav_adjustments.append(
                AssetAdjustment(
                    name="real_estate_appreciation",
                    carrying_value=0.0,
                    adjusted_value=inputs.real_estate_appreciation,
                    delta=inputs.real_estate_appreciation,
                    rationale="ANAV real-estate / property overlay",
                )
            )
        if inputs.hidden_assets:
            anav_adjustments.append(
                AssetAdjustment(
                    name="hidden_assets",
                    carrying_value=0.0,
                    adjusted_value=inputs.hidden_assets,
                    delta=inputs.hidden_assets,
                    rationale="Hidden / unrecorded assets",
                )
            )
        if inputs.private_holdings_adjustment:
            anav_adjustments.append(
                AssetAdjustment(
                    name="private_holdings",
                    carrying_value=0.0,
                    adjusted_value=inputs.private_holdings_adjustment,
                    delta=inputs.private_holdings_adjustment,
                    rationale="Private holdings fair-value overlay",
                )
            )
        if inputs.independent_appraisal is not None:
            delta = inputs.independent_appraisal - (
                self._fv(inputs.ppe, inputs.fv_ppe)
                + self._fv(inputs.investment_property, inputs.fv_investment_property)
            )
            anav += delta
            anav_adjustments.append(
                AssetAdjustment(
                    name="independent_appraisal",
                    carrying_value=0.0,
                    adjusted_value=inputs.independent_appraisal,
                    delta=delta,
                    rationale="Independent appraisal vs carrying PPE/IP",
                )
            )

        # Standard liquidation uses provided schedule
        liq, haircuts, liq_adj = self._apply_haircuts(inputs, inputs.haircut_schedule)

        # Conservative: floor intangibles/goodwill/DTA at 0 recovery already in defaults
        cons_sched = HaircutSchedule(
            cash=min(inputs.haircut_schedule.cash, 1.0),
            cash_equivalents=min(inputs.haircut_schedule.cash_equivalents, 1.0),
            investments=inputs.haircut_schedule.investments,
            receivables=min(inputs.haircut_schedule.receivables, 0.90),
            inventory=min(inputs.haircut_schedule.inventory, 0.80),
            biological_assets=min(inputs.haircut_schedule.biological_assets, 0.50),
            ppe=min(inputs.haircut_schedule.ppe, 0.60),
            investment_property=min(inputs.haircut_schedule.investment_property, 0.60),
            intangible_assets=0.0,
            goodwill=0.0,
            deferred_tax_assets=0.0,
            other_assets=min(inputs.haircut_schedule.other_assets, 0.30),
        )
        cons, _, cons_adj = self._apply_haircuts(inputs, cons_sched)

        # Replacement cost of operating assets − liabilities − claims
        if inputs.replacement_cost is not None:
            repl_assets = inputs.replacement_cost + inputs.cash + inputs.cash_equivalents
        else:
            repl_assets = (
                inputs.cash
                + inputs.cash_equivalents
                + self._fv(inputs.investments, inputs.fv_investments)
                + self._fv(inputs.receivables, inputs.fv_receivables)
                + self._fv(inputs.inventory, inputs.fv_inventory)
                + self._fv(inputs.biological_assets, inputs.fv_biological_assets)
                + self._fv(inputs.ppe, inputs.fv_ppe)
                + self._fv(inputs.investment_property, inputs.fv_investment_property)
                + inputs.other_assets
            )
        replacement = self._common_equity(repl_assets - liab, inputs)

        method = inputs.method
        method_map = {
            AssetMethod.BOOK_VALUE: book,
            AssetMethod.TANGIBLE_BOOK: tbv,
            AssetMethod.NAV: nav,
            AssetMethod.ADJUSTED_NAV: anav,
            AssetMethod.LIQUIDATION: liq,
            AssetMethod.CONSERVATIVE_LIQUIDATION: cons,
            AssetMethod.REPLACEMENT_COST: replacement,
        }
        if method not in method_map:
            raise ValuationError(f"unknown asset method: {method!r}")
        intrinsic = method_map[method]
        shares = inputs.shares_outstanding
        ivps = intrinsic / shares
        bvps = book / shares
        tbvps = tbv / shares
        navps = nav / shares
        anavps = anav / shares
        liqps = liq / shares

        mos: float | None = None
        if inputs.current_market_price is not None and ivps != 0:
            mos = (ivps - inputs.current_market_price) / ivps

        all_adj = tuple(anav_adjustments) + liq_adj

        bv_exp = explain_step(
            name="book_value",
            value=book,
            formula="BV = Assets − Operating Liabilities − MI − Preferred",
            inputs={"assets": assets, "liabilities": liab},
            intermediates={"claims": self._claims(inputs)},
            confidence=conf,
        )
        bvps_exp = explain_step(
            name="book_value_per_share",
            value=bvps,
            formula="BVPS = BV / Shares",
            inputs={"book_value": book, "shares": shares},
            intermediates={},
            confidence=conf,
        )
        tbv_exp = explain_step(
            name="tangible_book_value",
            value=tbv,
            formula="TBV = BV − Goodwill − Intangibles (via asset exclusion)",
            inputs={
                "goodwill": inputs.goodwill,
                "intangible_assets": inputs.intangible_assets,
            },
            intermediates={},
            confidence=conf,
            notes="Excludes goodwill and intangible assets",
        )
        tbvps_exp = explain_step(
            name="tangible_book_value_per_share",
            value=tbvps,
            formula="TBVPS = TBV / Shares",
            inputs={"tbv": tbv, "shares": shares},
            intermediates={},
            confidence=conf,
        )
        nav_exp = explain_step(
            name="nav",
            value=nav,
            formula="NAV = FV(Assets) − Liabilities − OBS Liab − Claims",
            inputs={"nav_assets": nav_assets},
            intermediates={},
            confidence=conf,
        )
        navps_exp = explain_step(
            name="nav_per_share",
            value=navps,
            formula="NAVPS = NAV / Shares",
            inputs={"nav": nav, "shares": shares},
            intermediates={},
            confidence=conf,
        )
        anav_exp = explain_step(
            name="adjusted_nav",
            value=anav,
            formula="ANAV = NAV + Hidden + Private + RE overlay ± Appraisal",
            inputs={
                "nav": nav,
                "hidden_assets": inputs.hidden_assets,
                "private_holdings_adjustment": inputs.private_holdings_adjustment,
            },
            intermediates={"adjustments": len(anav_adjustments)},
            confidence=conf,
        )
        anavps_exp = explain_step(
            name="adjusted_nav_per_share",
            value=anavps,
            formula="ANAVPS = ANAV / Shares",
            inputs={"anav": anav, "shares": shares},
            intermediates={},
            confidence=conf,
        )
        liq_exp = explain_step(
            name="liquidation_value",
            value=liq,
            formula="LV = Σ (Asset × Haircut) − Liabilities − Claims",
            inputs=dict(haircuts),
            intermediates={},
            confidence=conf,
            notes="Category-specific liquidation discounts applied",
        )
        liqps_exp = explain_step(
            name="liquidation_value_per_share",
            value=liqps,
            formula="LVPS = LV / Shares",
            inputs={"liquidation_value": liq, "shares": shares},
            intermediates={},
            confidence=conf,
        )
        cons_exp = explain_step(
            name="conservative_liquidation_value",
            value=cons,
            formula="Conservative LV with capped recoveries; intangibles/goodwill=0",
            inputs=cons_sched.as_mapping(),
            intermediates={"adjustments": len(cons_adj)},
            confidence=conf,
        )
        repl_exp = explain_step(
            name="replacement_cost",
            value=replacement,
            formula="Replacement equity ≈ Replacement operating assets − Liab − Claims",
            inputs={"replacement_cost_input": inputs.replacement_cost},
            intermediates={"repl_assets": repl_assets},
            confidence=conf,
        )
        iv_exp = explain_step(
            name="intrinsic_value",
            value=intrinsic,
            formula=f"Primary IV from method={method.value}",
            inputs={"method": method.value},
            intermediates={},
            confidence=conf,
        )
        ivps_exp = explain_step(
            name="intrinsic_value_per_share",
            value=ivps,
            formula="IV/share = Intrinsic / Shares",
            inputs={"intrinsic": intrinsic, "shares": shares},
            intermediates={},
            confidence=conf,
        )
        mos_exp = explain_step(
            name="margin_of_safety",
            value=mos,
            formula="MoS = (IV/share − Price) / IV/share",
            inputs={"ivps": ivps, "price": inputs.current_market_price},
            intermediates={},
            confidence="low" if mos is None else conf,
            notes="Research posture only — not a recommendation",
        )

        return {
            "book": book,
            "tbv": tbv,
            "nav": nav,
            "anav": anav,
            "liq": liq,
            "cons": cons,
            "replacement": replacement,
            "intrinsic": intrinsic,
            "ivps": ivps,
            "haircuts": haircuts,
            "adjustments": all_adj,
            "assets": assets,
            "liab": liab,
            "bv_exp": bv_exp,
            "bvps_exp": bvps_exp,
            "tbv_exp": tbv_exp,
            "tbvps_exp": tbvps_exp,
            "nav_exp": nav_exp,
            "navps_exp": navps_exp,
            "anav_exp": anav_exp,
            "anavps_exp": anavps_exp,
            "liq_exp": liq_exp,
            "liqps_exp": liqps_exp,
            "cons_exp": cons_exp,
            "repl_exp": repl_exp,
            "iv_exp": iv_exp,
            "ivps_exp": ivps_exp,
            "mos_exp": mos_exp,
        }

    def _scale_haircuts(
        self, schedule: HaircutSchedule, delta: float
    ) -> HaircutSchedule:
        def clamp(x: float) -> float:
            return max(0.0, min(1.0, x + delta))

        m = schedule.as_mapping()
        return HaircutSchedule(**{k: clamp(v) for k, v in m.items()})

    def _scenarios(self, inputs: AssetBasedInputs) -> tuple[ScenarioOutcome, ...]:
        engine = ScenarioEngine()
        specs = (
            ScenarioSpec(
                ScenarioKind.bear(),
                {
                    "haircut_delta": inputs.bear_haircut_delta,
                    "property_delta": inputs.bear_property_delta,
                },
            ),
            ScenarioSpec(
                ScenarioKind.base(),
                {"haircut_delta": 0.0, "property_delta": 0.0},
            ),
            ScenarioSpec(
                ScenarioKind.bull(),
                {
                    "haircut_delta": inputs.bull_haircut_delta,
                    "property_delta": inputs.bull_property_delta,
                },
            ),
            ScenarioSpec(
                ScenarioKind.custom("stress_liq", "Stress Liquidation"),
                {"haircut_delta": -0.15, "property_delta": -0.10},
            ),
        )

        def evaluator(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
            h_delta = float(ctx.get("haircut_delta", 0.0))
            p_delta = float(ctx.get("property_delta", 0.0))
            adj = replace(
                inputs,
                haircut_schedule=self._scale_haircuts(
                    inputs.haircut_schedule, h_delta
                ),
                real_estate_appreciation=inputs.real_estate_appreciation
                + (inputs.ppe + inputs.investment_property) * p_delta,
                method=(
                    AssetMethod.LIQUIDATION
                    if inputs.method
                    not in {
                        AssetMethod.LIQUIDATION,
                        AssetMethod.CONSERVATIVE_LIQUIDATION,
                        AssetMethod.ADJUSTED_NAV,
                    }
                    else inputs.method
                ),
            )
            out = self._value(adj)
            return {
                "intrinsic_value": out["intrinsic"],
                "equity_value": out["intrinsic"],
                "intrinsic_value_per_share": out["ivps"],
                "notes": f"haircut_delta={h_delta}, property_delta={p_delta}",
                "extras": {"liq": out["liq"], "anav": out["anav"]},
            }

        return engine.scenarios({}, specs=specs, evaluator=evaluator)

    def _sensitivity(self, inputs: AssetBasedInputs) -> SensitivityMatrix:
        recv = inputs.haircut_schedule.receivables
        inv = inputs.haircut_schedule.inventory
        prop_appr = inputs.real_estate_appreciation
        debt = inputs.long_term_debt
        hidden = inputs.hidden_assets
        ppe_h = inputs.haircut_schedule.ppe

        axes = (
            SensitivityAxis("asset_haircuts", (ppe_h - 0.1, ppe_h, ppe_h + 0.1)),
            SensitivityAxis(
                "property_appreciation",
                (prop_appr - 50.0, prop_appr, prop_appr + 50.0),
            ),
            SensitivityAxis("inventory_discounts", (inv - 0.1, inv, inv + 0.1)),
            SensitivityAxis("receivable_recovery", (recv - 0.1, recv, recv + 0.1)),
            SensitivityAxis("debt_adjustments", (debt - 50.0, debt, debt + 50.0)),
            SensitivityAxis("hidden_asset_value", (hidden - 50.0, hidden, hidden + 50.0)),
        )

        def evaluator(ctx: Mapping[str, Any]) -> float | None:
            sched = inputs.haircut_schedule
            adj = inputs
            if "asset_haircuts" in ctx and ctx["asset_haircuts"] != ppe_h:
                rate = max(0.0, min(1.0, float(ctx["asset_haircuts"])))
                sched = replace(sched, ppe=rate, investment_property=rate)
                adj = replace(adj, haircut_schedule=sched, method=AssetMethod.LIQUIDATION)
            if "property_appreciation" in ctx and ctx["property_appreciation"] != prop_appr:
                adj = replace(
                    adj,
                    real_estate_appreciation=float(ctx["property_appreciation"]),
                    method=AssetMethod.ADJUSTED_NAV,
                )
            if "inventory_discounts" in ctx and ctx["inventory_discounts"] != inv:
                rate = max(0.0, min(1.0, float(ctx["inventory_discounts"])))
                adj = replace(
                    adj,
                    haircut_schedule=replace(adj.haircut_schedule, inventory=rate),
                    method=AssetMethod.LIQUIDATION,
                )
            if "receivable_recovery" in ctx and ctx["receivable_recovery"] != recv:
                rate = max(0.0, min(1.0, float(ctx["receivable_recovery"])))
                adj = replace(
                    adj,
                    haircut_schedule=replace(adj.haircut_schedule, receivables=rate),
                    method=AssetMethod.LIQUIDATION,
                )
            if "debt_adjustments" in ctx and ctx["debt_adjustments"] != debt:
                new_debt = max(0.0, float(ctx["debt_adjustments"]))
                adj = replace(adj, long_term_debt=new_debt)
            if "hidden_asset_value" in ctx and ctx["hidden_asset_value"] != hidden:
                adj = replace(
                    adj,
                    hidden_assets=max(0.0, float(ctx["hidden_asset_value"])),
                    method=AssetMethod.ADJUSTED_NAV,
                )
            try:
                return float(self._value(adj)["ivps"])
            except ValuationError:
                return None

        context = {
            "asset_haircuts": ppe_h,
            "property_appreciation": prop_appr,
            "inventory_discounts": inv,
            "receivable_recovery": recv,
            "debt_adjustments": debt,
            "hidden_asset_value": hidden,
        }
        return SensitivityEngine().sensitivity(
            context,
            axes=axes,
            evaluator=evaluator,
            output_name="intrinsic_value_per_share",
        )

    def _asset_quality(
        self, inputs: AssetBasedInputs, base: Mapping[str, Any]
    ) -> AssetQuality:
        assets = float(base["assets"])
        if assets <= 0:
            return AssetQuality.WEAK
        cash_q = (inputs.cash + inputs.cash_equivalents) / assets
        recv_q = 1.0 - min(1.0, inputs.receivables / assets)
        inv_q = 1.0 - min(1.0, inputs.inventory / assets)
        intang = (inputs.goodwill + inputs.intangible_assets) / assets
        debt = inputs.short_term_debt + inputs.long_term_debt
        coverage = assets / debt if debt > 0 else 2.0
        score = (
            min(1.0, cash_q * 2) * 0.25
            + recv_q * 0.15
            + inv_q * 0.15
            + max(0.0, 1.0 - intang) * 0.25
            + min(1.0, coverage / 2.0) * 0.20
        )
        if score >= 0.75:
            return AssetQuality.EXCELLENT
        if score >= 0.55:
            return AssetQuality.GOOD
        if score >= 0.35:
            return AssetQuality.AVERAGE
        return AssetQuality.WEAK

    def _confidence(self, inputs: AssetBasedInputs, quality: AssetQuality):
        q_map = {
            AssetQuality.EXCELLENT: 1.0,
            AssetQuality.GOOD: 0.75,
            AssetQuality.AVERAGE: 0.5,
            AssetQuality.WEAK: 0.25,
        }
        bs_quality = q_map[quality]
        aq = inputs.accounting_quality_score
        if aq is None:
            accounting = 0.6
        else:
            accounting = aq / 100.0 if aq > 1.0 else float(aq)
            accounting = max(0.0, min(1.0, accounting))

        verification = 0.5
        if inputs.independent_appraisal is not None:
            verification += 0.3
        if inputs.fv_investments is not None or inputs.fv_ppe is not None:
            verification += 0.2
        verification = min(1.0, verification)

        completeness = 0.4
        if inputs.total_assets is not None:
            completeness += 0.1
        if inputs.current_market_price is not None:
            completeness += 0.15
        if inputs.replacement_cost is not None:
            completeness += 0.15
        if inputs.hidden_assets > 0 or inputs.off_balance_sheet_assets > 0:
            completeness += 0.1
        completeness = min(1.0, completeness)

        adj_reliability = 0.7 if inputs.method in {
            AssetMethod.BOOK_VALUE,
            AssetMethod.TANGIBLE_BOOK,
        } else 0.55

        return ConfidenceEngine().score(
            {
                "accounting_quality": accounting,
                "forecast_reliability": adj_reliability,  # adjustment reliability
                "data_completeness": completeness,
                "business_stability": bs_quality,
                "capital_allocation": verification,
                "model_assumptions": adj_reliability,
            }
        )

    def _quality_flags(
        self,
        inputs: AssetBasedInputs,
        base: Mapping[str, Any],
        quality: AssetQuality,
    ) -> tuple[tuple[AssetQualityFlag, ...], tuple[QualityFlag, ...]]:
        flags: list[AssetQualityFlag] = []
        core: list[QualityFlag] = []
        assets = float(base["assets"])
        book = float(base["book"])

        if assets > 0:
            cash_ratio = (inputs.cash + inputs.cash_equivalents) / assets
            if cash_ratio >= 0.20:
                flags.append(AssetQualityFlag.CASH_RICH)
            if book / assets >= 0.50 and book > 0:
                flags.append(AssetQualityFlag.ASSET_RICH)
            intang = (inputs.goodwill + inputs.intangible_assets) / assets
            if intang >= 0.30:
                flags.append(AssetQualityFlag.HIGH_INTANGIBLE_RISK)
                core.append(QualityFlag.ACCOUNTING_WARNING)
            if inputs.goodwill / assets >= 0.20:
                flags.append(AssetQualityFlag.GOODWILL_HEAVY)
            if inputs.inventory / assets >= 0.30:
                flags.append(AssetQualityFlag.INVENTORY_HEAVY)
            debt = inputs.short_term_debt + inputs.long_term_debt
            if debt / assets >= 0.50:
                flags.append(AssetQualityFlag.HIGH_LEVERAGE)
            if debt > 0 and assets / debt < 1.25:
                flags.append(AssetQualityFlag.WEAK_ASSET_COVERAGE)

        if inputs.hidden_assets > 0 or inputs.off_balance_sheet_assets > 0:
            flags.append(AssetQualityFlag.HIDDEN_ASSETS)
        if (
            inputs.real_estate_appreciation > 0
            or (
                inputs.fv_investment_property is not None
                and inputs.fv_investment_property > inputs.investment_property
            )
        ):
            flags.append(AssetQualityFlag.REAL_ESTATE_UPSIDE)
        if book < 0:
            flags.append(AssetQualityFlag.NEGATIVE_EQUITY)

        if quality is AssetQuality.WEAK and AssetQualityFlag.WEAK_ASSET_COVERAGE not in flags:
            flags.append(AssetQualityFlag.WEAK_ASSET_COVERAGE)

        return tuple(flags), tuple(core)
