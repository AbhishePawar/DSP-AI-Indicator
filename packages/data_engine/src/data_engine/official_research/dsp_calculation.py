"""Deterministic DSP calculations from verified facts + accepted assumptions.

Does not replace valuation.methods.dcf or dcf_intelligence. It applies the
DSP-gate DCF formula (DcfMethod) to SIMPLE-17 FCF using Decimal math.

Canonical DcfMethod (packages/valuation/methods/dcf.py):
    FCF₀ = OCF − CapEx
    FCFₜ = FCF₀(1+g)ᵗ
    TV = FCFₙ(1+gₜ)/(r−gₜ)
    IV = Σ FCFₜ/(1+r)ᵗ + TV/(1+r)ⁿ

SIMPLE-17 / financial FORMULA_FCF uses abs(capex), so FCF₀ here is the
already-derived FCF (CFO − |Capex|). DcfMethod FCF is after-interest cash
flow, so the present value is equity value. Net debt is not subtracted again.

DCF Intelligence (FCFF = EBIT(1−t)+D&A−CapEx−ΔNWC; CAPM WACC; EV − debt + cash)
remains a separate engine. It is not invoked here because VerifiedDataset does
not carry CAPM / NWC / D&A drivers. Mixing the two formulas is forbidden.

MoS uses the existing per-share formula:
    MoS = (IV/share − Price) / IV/share
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from typing import Any, Mapping

from data_engine.official_research.assumption_contract import (
    CanonicalAssumption,
    DATA_CLASS_DERIVED,
)
from data_engine.official_research.assumption_validator import (
    validate_assumption_pack,
)
from data_engine.official_research.derived_fields import (
    DerivedFieldSet,
    derive_dsp_fields,
)
from data_engine.official_research.extraction import (
    VALUATION_SHARE_SEMANTIC,
    canonicalize_period,
    normalize_numeric_to_actual,
    periods_comparable,
)
from data_engine.official_research.research_plan import classify_research_capability
from data_engine.official_research.verified_dataset import VerifiedDataset
from data_engine.security_master.models import SecurityListing, UNSUPPORTED_SECURITY_TYPES

__all__ = [
    "BUFFETT_FORMULA",
    "CANONICAL_DCF",
    "DCF_INTELLIGENCE_FORMULA",
    "DCF_METHOD_FORMULA",
    "FORMULA_VERSIONS",
    "MOAT_WEIGHTS",
    "MOS_FORMULA",
    "QUALITY_WEIGHTS",
    "SENSITIVITY_GROWTH_DELTAS",
    "SENSITIVITY_TERMINAL_DELTAS",
    "SENSITIVITY_WACC_DELTAS",
    "CalculationResult",
    "DspCalculationSet",
    "ScoreAggregationResult",
    "SensitivityCell",
    "accepted_only",
    "aggregate_moat_scores",
    "aggregate_quality_scores",
    "buffett_market_gdp",
    "ignore_ai_valuation",
    "presentation_round",
    "run_dsp_calculations",
    "scenario_pack",
]

DCF_METHOD_FORMULA = (
    "FCF0 = OCF - abs(CapEx); "
    "FCFt = FCF0*(1+g)^t; "
    "TV = FCFn*(1+gt)/(r-gt); "
    "IV = sum FCFt/(1+r)^t + TV/(1+r)^n"
)
DCF_INTELLIGENCE_FORMULA = (
    "FCFF=EBIT(1-t)+DA-CapEx-dNWC; "
    "EV=sum PV(FCFF)+PV(TV); "
    "Equity=EV-Debt-Minority+Cash+Investments; "
    "IV/share=Equity/Shares"
)
CANONICAL_DCF = "valuation.methods.dcf"
MOS_FORMULA = "(intrinsic_value_per_share - market_price_per_share) / intrinsic_value_per_share"
BUFFETT_FORMULA = "total_market_cap / gdp"
FORMULA_VERSIONS = {
    "dcf": "valuation.methods.dcf",
    "fcf": "fcf",
    "net_debt": "net_debt",
    "market_cap": "official_research.derived.market_cap.v1",
    "enterprise_value": "official_research.derived.enterprise_value.v1",
    "margin_of_safety": "valuation.dcf_intelligence.margin.v1",
    "quality": "business_quality.compose_overall_score",
    "moat": "economic_moat.DEFAULT_MOAT_WEIGHTS",
    "buffett_market_gdp": "buffett_indicator.market_cap_to_gdp.unimplemented_in_dsp_engine",
}

# Existing DEFAULT_BUSINESS_QUALITY_WEIGHTS
QUALITY_WEIGHTS: dict[str, Decimal] = {
    "earnings_quality": Decimal("0.30"),
    "capital_allocation": Decimal("0.30"),
    "business_characteristics": Decimal("0.20"),
    "competitive_position": Decimal("0.20"),
}

# Existing DEFAULT_MOAT_WEIGHTS
MOAT_WEIGHTS: dict[str, Decimal] = {
    "brand": Decimal("0.20"),
    "network_effects": Decimal("0.15"),
    "switching_costs": Decimal("0.20"),
    "cost_advantage": Decimal("0.15"),
    "intangible_assets": Decimal("0.15"),
    "efficient_scale": Decimal("0.15"),
}

# Existing DcfSensitivitySpec defaults
SENSITIVITY_GROWTH_DELTAS = (Decimal("-0.02"), Decimal("0"), Decimal("0.02"))
SENSITIVITY_WACC_DELTAS = (Decimal("-0.01"), Decimal("0"), Decimal("0.01"))
SENSITIVITY_TERMINAL_DELTAS = (Decimal("-0.005"), Decimal("0"), Decimal("0.005"))

_INTERNAL_PREC = 28
_PRESENTATION_MONEY = 2


@dataclass(frozen=True, slots=True)
class CalculationResult:
    field: str
    value: Decimal | None
    status: str
    formula_version: str
    formula: str
    scenario: str
    input_fields: tuple[str, ...]
    input_evidence_ids: tuple[str, ...]
    assumption_ids: tuple[str, ...]
    calculated_at: datetime
    detail: str
    extras: dict[str, Any] | None = None

    def to_public_dict(self) -> dict[str, Any]:
        payload = {
            "derived_field": self.field,
            "value": None if self.value is None else str(self.value),
            "calculation_status": self.status,
            "formula_version": self.formula_version,
            "formula": self.formula,
            "scenario": self.scenario,
            "input_fields": list(self.input_fields),
            "input_evidence_ids": list(self.input_evidence_ids),
            "assumption_ids": list(self.assumption_ids),
            "calculated_at": self.calculated_at.isoformat(),
            "detail": self.detail,
            "data_class": DATA_CLASS_DERIVED,
            "is_source_evidence": False,
        }
        if self.extras:
            payload["extras"] = {
                key: (str(val) if isinstance(val, Decimal) else val)
                for key, val in self.extras.items()
            }
        return payload


@dataclass(frozen=True, slots=True)
class SensitivityCell:
    dimension: str
    delta: Decimal
    parameter_value: Decimal
    intrinsic_value_per_share: Decimal | None
    status: str


@dataclass(frozen=True, slots=True)
class ScoreAggregationResult:
    overall: Decimal | None
    status: str
    components: dict[str, Decimal | None]
    weights: dict[str, Decimal]
    formula_version: str
    detail: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "overall": None if self.overall is None else str(self.overall),
            "status": self.status,
            "components": {
                key: None if val is None else str(val) for key, val in self.components.items()
            },
            "weights": {key: str(val) for key, val in self.weights.items()},
            "formula_version": self.formula_version,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class DspCalculationSet:
    derived: DerivedFieldSet
    dcf: CalculationResult
    intrinsic_value: CalculationResult
    intrinsic_value_per_share: CalculationResult
    margin_of_safety: CalculationResult
    quality: ScoreAggregationResult
    moat: ScoreAggregationResult
    risk: ScoreAggregationResult
    buffett: CalculationResult
    overall: ScoreAggregationResult
    sensitivity: tuple[SensitivityCell, ...]
    scenarios: dict[str, CalculationResult]
    calculated_at: datetime
    formula_catalog: dict[str, str]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "derived": self.derived.to_public_dict(),
            "dcf": self.dcf.to_public_dict(),
            "intrinsic_value": self.intrinsic_value.to_public_dict(),
            "intrinsic_value_per_share": self.intrinsic_value_per_share.to_public_dict(),
            "margin_of_safety": self.margin_of_safety.to_public_dict(),
            "quality": self.quality.to_public_dict(),
            "moat": self.moat.to_public_dict(),
            "risk": self.risk.to_public_dict(),
            "buffett": self.buffett.to_public_dict(),
            "overall": self.overall.to_public_dict(),
            "sensitivity": [
                {
                    "dimension": cell.dimension,
                    "delta": str(cell.delta),
                    "parameter_value": str(cell.parameter_value),
                    "intrinsic_value_per_share": (
                        None
                        if cell.intrinsic_value_per_share is None
                        else str(cell.intrinsic_value_per_share)
                    ),
                    "status": cell.status,
                }
                for cell in self.sensitivity
            ],
            "scenarios": {name: item.to_public_dict() for name, item in self.scenarios.items()},
            "calculated_at": self.calculated_at.isoformat(),
            "formula_catalog": dict(self.formula_catalog),
        }


def presentation_round(value: Decimal, *, places: int = _PRESENTATION_MONEY) -> Decimal:
    quant = Decimal("1").scaleb(-places)
    return value.quantize(quant)


def ignore_ai_valuation(_payload: Any) -> None:
    """AI DCF/IV numbers are never inputs. DSP calculates independently."""
    return None


def accepted_only(
    items: tuple[CanonicalAssumption, ...], *, scenario: str
) -> dict[str, CanonicalAssumption]:
    chosen: dict[str, CanonicalAssumption] = {}
    for item in items:
        if item.scenario != scenario:
            continue
        if item.validation_status != "ACCEPTED":
            continue
        chosen[item.field] = item
    return chosen


def scenario_pack(
    items: tuple[CanonicalAssumption, ...], scenario: str
) -> tuple[CanonicalAssumption, ...]:
    return tuple(item for item in items if item.scenario == scenario)


def _blocked(
    field: str,
    *,
    status: str,
    detail: str,
    now: datetime,
    scenario: str = "BASE",
    formula_version: str = CANONICAL_DCF,
    formula: str = DCF_METHOD_FORMULA,
    inputs: tuple[str, ...] = (),
    evidence_ids: tuple[str, ...] = (),
    assumption_ids: tuple[str, ...] = (),
) -> CalculationResult:
    return CalculationResult(
        field=field,
        value=None,
        status=status,
        formula_version=formula_version,
        formula=formula,
        scenario=scenario,
        input_fields=inputs,
        input_evidence_ids=evidence_ids,
        assumption_ids=assumption_ids,
        calculated_at=now,
        detail=detail,
    )


def _rate(item: CanonicalAssumption | None) -> Decimal | None:
    if item is None or item.value is None:
        return None
    return Decimal(item.value)


def _dcf_core(
    *,
    fcf0: Decimal,
    wacc: Decimal,
    growth: Decimal,
    terminal: Decimal,
    years: int,
) -> tuple[Decimal, Decimal, Decimal] | str:
    """Return (pv_fcf, pv_tv, equity_iv) or a block reason."""
    if years < 1 or years > 30:
        return "forecast periods invalid"
    if wacc <= 0:
        return "WACC must be > 0"
    if terminal >= wacc:
        return "WACC must exceed terminal growth"
    if fcf0 <= 0:
        return "FCF inputs invalid"
    with localcontext() as ctx:
        ctx.prec = _INTERNAL_PREC
        one = Decimal("1")
        present = Decimal("0")
        fcf_n = fcf0
        for t in range(1, years + 1):
            fcf_t = fcf0 * (one + growth) ** t
            discount = (one + wacc) ** t
            if discount == 0:
                return "discount factors invalid"
            present += fcf_t / discount
            fcf_n = fcf_t
            if fcf_t.is_nan() or fcf_t.is_infinite() or present.is_infinite():
                return "NaN/infinity"
        spread = wacc - terminal
        if spread <= 0:
            return "WACC must exceed terminal growth"
        tv = fcf_n * (one + terminal) / spread
        pv_tv = tv / ((one + wacc) ** years)
        equity = present + pv_tv
        if any(x.is_nan() or x.is_infinite() for x in (present, pv_tv, equity, tv)):
            return "NaN/infinity"
        return present, pv_tv, equity


def _capability_for(listing: SecurityListing | None, capability: str | None) -> str:
    if capability:
        return capability
    if listing is None:
        return "equity"
    if listing.security_type in UNSUPPORTED_SECURITY_TYPES:
        return listing.security_type
    return classify_research_capability(listing)


def _run_dcf(
    dataset: VerifiedDataset,
    derived: DerivedFieldSet,
    assumptions: dict[str, CanonicalAssumption],
    *,
    now: datetime,
    scenario: str,
    capability: str,
) -> CalculationResult:
    inputs = ("fcf", "discount_rate", "fcf_growth_rate", "terminal_growth_rate", "shares")
    if capability in UNSUPPORTED_SECURITY_TYPES:
        return _blocked(
            "dcf",
            status="BLOCKED",
            detail=f"unsupported security type {capability}",
            now=now,
            scenario=scenario,
            inputs=inputs,
        )
    if capability != "equity":
        return _blocked(
            "dcf",
            status="BLOCKED",
            detail=f"{capability} is not forced through ordinary-equity DCF",
            now=now,
            scenario=scenario,
            inputs=inputs,
        )
    fcf = derived.fcf
    if fcf.status != "CALCULATED" or fcf.value is None:
        status = "STALE_INPUT" if fcf.status == "STALE_INPUT" else (
            "CONFLICT_INPUT" if fcf.status == "CONFLICT_INPUT" else "BLOCKED"
        )
        if fcf.status == "CALCULATION_BLOCKED":
            status = "CALCULATION_BLOCKED"
        return _blocked(
            "dcf",
            status=status,
            detail=f"FCF status={fcf.status}",
            now=now,
            scenario=scenario,
            inputs=inputs,
        )
    wacc_row = assumptions.get("wacc") or assumptions.get("discount_rate")
    growth_row = assumptions.get("fcf_growth_rate")
    terminal_row = assumptions.get("terminal_growth_rate")
    years_row = assumptions.get("projection_years")
    if wacc_row is None or growth_row is None or terminal_row is None:
        return _blocked(
            "dcf",
            status="BLOCKED",
            detail="required DCF assumptions are not ACCEPTED",
            now=now,
            scenario=scenario,
            inputs=inputs,
        )
    wacc = _rate(wacc_row)
    growth = _rate(growth_row)
    terminal = _rate(terminal_row)
    years = 5 if years_row is None or years_row.value is None else int(years_row.value)
    if wacc is None or growth is None or terminal is None:
        return _blocked(
            "dcf",
            status="BLOCKED",
            detail="required DCF assumptions are not numeric",
            now=now,
            scenario=scenario,
            inputs=inputs,
        )
    if dataset.identity is not None and derived.fcf.currency and dataset.identity.currency:
        if derived.fcf.currency != dataset.identity.currency:
            return _blocked(
                "dcf",
                status="CALCULATION_BLOCKED",
                detail="currency mismatch",
                now=now,
                scenario=scenario,
                inputs=inputs,
            )
    core = _dcf_core(fcf0=fcf.value, wacc=wacc, growth=growth, terminal=terminal, years=years)
    if isinstance(core, str):
        return _blocked(
            "dcf",
            status="BLOCKED",
            detail=core,
            now=now,
            scenario=scenario,
            inputs=inputs,
            assumption_ids=(wacc_row.assumption_id, growth_row.assumption_id, terminal_row.assumption_id),
        )
    pv_fcf, pv_tv, equity = core
    evidence = fcf.input_evidence_ids
    return CalculationResult(
        field="dcf",
        value=equity,
        status="CALCULATED",
        formula_version=CANONICAL_DCF,
        formula=DCF_METHOD_FORMULA,
        scenario=scenario,
        input_fields=inputs,
        input_evidence_ids=evidence,
        assumption_ids=(
            wacc_row.assumption_id,
            growth_row.assumption_id,
            terminal_row.assumption_id,
        ),
        calculated_at=now,
        detail="DcfMethod equity IV from verified FCF and ACCEPTED assumptions",
        extras={
            "fcf0": fcf.value,
            "pv_forecast_fcf": pv_fcf,
            "pv_terminal": pv_tv,
            "terminal_value_undiscounted": None,
            "wacc": wacc,
            "fcf_growth_rate": growth,
            "terminal_growth_rate": terminal,
            "projection_years": Decimal(years),
        },
    )


def _per_share(
    dcf: CalculationResult,
    dataset: VerifiedDataset,
    *,
    now: datetime,
    scenario: str,
) -> tuple[CalculationResult, CalculationResult]:
    equity = CalculationResult(
        field="intrinsic_value",
        value=dcf.value,
        status=dcf.status,
        formula_version=dcf.formula_version,
        formula=dcf.formula,
        scenario=scenario,
        input_fields=dcf.input_fields,
        input_evidence_ids=dcf.input_evidence_ids,
        assumption_ids=dcf.assumption_ids,
        calculated_at=now,
        detail=dcf.detail,
        extras=dcf.extras,
    )
    shares = dataset.shares
    if dcf.status != "CALCULATED" or dcf.value is None:
        return equity, _blocked(
            "intrinsic_value_per_share",
            status=dcf.status if dcf.status != "CALCULATED" else "BLOCKED",
            detail="DCF blocked",
            now=now,
            scenario=scenario,
            formula= "IV/share = Equity / TOTAL_OUTSTANDING",
            inputs=("intrinsic_value", "shares_outstanding"),
        )
    if dataset.shares_status != "VERIFIED" or shares is None or shares.shares <= 0:
        status = "STALE_INPUT" if dataset.shares_status == "REFRESH_REQUIRED" else "BLOCKED"
        if dataset.shares_status == "CONFLICT":
            status = "CONFLICT_INPUT"
        return equity, _blocked(
            "intrinsic_value_per_share",
            status=status,
            detail=f"shares status={dataset.shares_status}",
            now=now,
            scenario=scenario,
            formula="IV/share = Equity / TOTAL_OUTSTANDING",
            inputs=("intrinsic_value", "shares_outstanding"),
        )
    if shares.semantic_type != VALUATION_SHARE_SEMANTIC:
        return equity, _blocked(
            "intrinsic_value_per_share",
            status="BLOCKED",
            detail=f"shares semantic={shares.semantic_type} cannot be the DCF denominator",
            now=now,
            scenario=scenario,
            formula="IV/share = Equity / TOTAL_OUTSTANDING",
            inputs=("intrinsic_value", "shares_outstanding"),
        )
    per_share = dcf.value / shares.shares
    return equity, CalculationResult(
        field="intrinsic_value_per_share",
        value=per_share,
        status="CALCULATED",
        formula_version=CANONICAL_DCF,
        formula="IV/share = Equity / TOTAL_OUTSTANDING",
        scenario=scenario,
        input_fields=("intrinsic_value", "shares_outstanding"),
        input_evidence_ids=dcf.input_evidence_ids + shares.evidence_ids,
        assumption_ids=dcf.assumption_ids,
        calculated_at=now,
        detail="verified TOTAL_OUTSTANDING only",
    )


def _mos(
    ivps: CalculationResult,
    dataset: VerifiedDataset,
    *,
    now: datetime,
    scenario: str,
) -> CalculationResult:
    if ivps.status != "CALCULATED" or ivps.value is None:
        return _blocked(
            "margin_of_safety",
            status="BLOCKED" if ivps.status == "CALCULATED" else ivps.status,
            detail="intrinsic value blocked",
            now=now,
            scenario=scenario,
            formula_version=FORMULA_VERSIONS["margin_of_safety"],
            formula=MOS_FORMULA,
            inputs=("intrinsic_value_per_share", "price"),
        )
    if ivps.value == 0:
        return _blocked(
            "margin_of_safety",
            status="BLOCKED",
            detail="intrinsic value per share is zero",
            now=now,
            scenario=scenario,
            formula_version=FORMULA_VERSIONS["margin_of_safety"],
            formula=MOS_FORMULA,
            inputs=("intrinsic_value_per_share", "price"),
        )
    if dataset.price_status != "VERIFIED" or dataset.price is None:
        status = "STALE_INPUT" if dataset.price_status == "REFRESH_REQUIRED" else "BLOCKED"
        if dataset.price_status == "CONFLICT":
            status = "CONFLICT_INPUT"
        return _blocked(
            "margin_of_safety",
            status=status,
            detail=f"price status={dataset.price_status}",
            now=now,
            scenario=scenario,
            formula_version=FORMULA_VERSIONS["margin_of_safety"],
            formula=MOS_FORMULA,
            inputs=("intrinsic_value_per_share", "price"),
        )
    if dataset.identity is not None and dataset.price.currency != dataset.identity.currency:
        return _blocked(
            "margin_of_safety",
            status="CALCULATION_BLOCKED",
            detail="currency mismatch",
            now=now,
            scenario=scenario,
            formula_version=FORMULA_VERSIONS["margin_of_safety"],
            formula=MOS_FORMULA,
            inputs=("intrinsic_value_per_share", "price"),
        )
    ratio = (ivps.value - dataset.price.price) / ivps.value
    return CalculationResult(
        field="margin_of_safety",
        value=ratio,
        status="CALCULATED",
        formula_version=FORMULA_VERSIONS["margin_of_safety"],
        formula=MOS_FORMULA,
        scenario=scenario,
        input_fields=("intrinsic_value_per_share", "price"),
        input_evidence_ids=ivps.input_evidence_ids,
        assumption_ids=ivps.assumption_ids,
        calculated_at=now,
        detail="research posture ratio; not a trade recommendation",
    )


def _sensitivity(
    dataset: VerifiedDataset,
    derived: DerivedFieldSet,
    assumptions: dict[str, CanonicalAssumption],
    *,
    now: datetime,
    capability: str,
) -> tuple[SensitivityCell, ...]:
    cells: list[SensitivityCell] = []
    wacc_row = assumptions.get("wacc") or assumptions.get("discount_rate")
    growth_row = assumptions.get("fcf_growth_rate")
    terminal_row = assumptions.get("terminal_growth_rate")
    if wacc_row is None or growth_row is None or terminal_row is None:
        return ()
    base_wacc = _rate(wacc_row)
    base_g = _rate(growth_row)
    base_t = _rate(terminal_row)
    if base_wacc is None or base_g is None or base_t is None:
        return ()

    def _ivps_for(wacc: Decimal, growth: Decimal, terminal: Decimal) -> CalculationResult:
        pack = dict(assumptions)
        pack["discount_rate"] = replace(wacc_row, value=wacc, field="discount_rate")
        pack["wacc"] = replace(wacc_row, value=wacc, field="wacc")
        pack["fcf_growth_rate"] = replace(growth_row, value=growth)
        pack["terminal_growth_rate"] = replace(terminal_row, value=terminal)
        dcf = _run_dcf(dataset, derived, pack, now=now, scenario="BASE", capability=capability)
        _, ivps = _per_share(dcf, dataset, now=now, scenario="BASE")
        return ivps

    for delta in SENSITIVITY_GROWTH_DELTAS:
        g = base_g + delta
        ivps = _ivps_for(base_wacc, g, base_t)
        cells.append(
            SensitivityCell(
                dimension="fcf_growth_rate",
                delta=delta,
                parameter_value=g,
                intrinsic_value_per_share=None if ivps is None else ivps.value,
                status="CALCULATED" if ivps is not None and ivps.status == "CALCULATED" else "BLOCKED",
            )
        )
    for delta in SENSITIVITY_WACC_DELTAS:
        w = base_wacc + delta
        ivps = _ivps_for(w, base_g, base_t)
        cells.append(
            SensitivityCell(
                dimension="wacc",
                delta=delta,
                parameter_value=w,
                intrinsic_value_per_share=None if ivps is None else ivps.value,
                status="CALCULATED" if ivps is not None and ivps.status == "CALCULATED" else "BLOCKED",
            )
        )
    for delta in SENSITIVITY_TERMINAL_DELTAS:
        t = base_t + delta
        ivps = _ivps_for(base_wacc, base_g, t)
        cells.append(
            SensitivityCell(
                dimension="terminal_growth_rate",
                delta=delta,
                parameter_value=t,
                intrinsic_value_per_share=None if ivps is None else ivps.value,
                status="CALCULATED" if ivps is not None and ivps.status == "CALCULATED" else "BLOCKED",
            )
        )
    return tuple(cells)


def _weighted(
    components: Mapping[str, Decimal | None],
    weights: Mapping[str, Decimal],
    *,
    formula_version: str,
    require_all: bool,
) -> ScoreAggregationResult:
    missing = [name for name in weights if components.get(name) is None]
    if require_all and missing:
        return ScoreAggregationResult(
            overall=None,
            status="BLOCKED",
            components=dict(components),
            weights=dict(weights),
            formula_version=formula_version,
            detail=f"missing components: {', '.join(missing)}",
        )
    present: list[tuple[Decimal, Decimal]] = []
    for name, weight in weights.items():
        value = components.get(name)
        if value is None:
            continue
        present.append((value, weight))
    if not present:
        return ScoreAggregationResult(
            overall=None,
            status="BLOCKED",
            components=dict(components),
            weights=dict(weights),
            formula_version=formula_version,
            detail="no component scores",
        )
    total_w = sum(weight for _, weight in present)
    if total_w == 0:
        return ScoreAggregationResult(
            overall=None,
            status="BLOCKED",
            components=dict(components),
            weights=dict(weights),
            formula_version=formula_version,
            detail="weights sum to zero",
        )
    overall = sum(value * weight for value, weight in present) / total_w
    return ScoreAggregationResult(
        overall=overall,
        status="CALCULATED",
        components=dict(components),
        weights=dict(weights),
        formula_version=formula_version,
        detail="weighted mean of provided engine scores; AI narrative ignored",
    )


def aggregate_quality_scores(
    components: Mapping[str, Decimal | None] | None,
    *,
    ai_narrative: str | None = None,
) -> ScoreAggregationResult:
    _ = ai_narrative
    if not components:
        return ScoreAggregationResult(
            overall=None,
            status="BLOCKED",
            components={name: None for name in QUALITY_WEIGHTS},
            weights=dict(QUALITY_WEIGHTS),
            formula_version=FORMULA_VERSIONS["quality"],
            detail="quality scores missing; AI narrative cannot create them",
        )
    return _weighted(
        components,
        QUALITY_WEIGHTS,
        formula_version=FORMULA_VERSIONS["quality"],
        require_all=True,
    )


def aggregate_moat_scores(
    components: Mapping[str, Decimal | None] | None,
    *,
    ai_score: Decimal | None = None,
) -> ScoreAggregationResult:
    _ = ai_score
    if not components:
        return ScoreAggregationResult(
            overall=None,
            status="BLOCKED",
            components={name: None for name in MOAT_WEIGHTS},
            weights=dict(MOAT_WEIGHTS),
            formula_version=FORMULA_VERSIONS["moat"],
            detail="moat dimension scores missing; AI moat rating is ignored",
        )
    return _weighted(
        components,
        MOAT_WEIGHTS,
        formula_version=FORMULA_VERSIONS["moat"],
        require_all=True,
    )


def _risk_result(*, observations: tuple[str, ...] = (), ai_score: Decimal | None = None) -> ScoreAggregationResult:
    _ = ai_score
    if not observations:
        return ScoreAggregationResult(
            overall=None,
            status="BLOCKED",
            components={"qualitative_risk": None},
            weights={},
            formula_version="risk.RiskAnalyzer",
            detail="risk engine is qualitative; numeric AI risk is ignored; no observations",
        )
    return ScoreAggregationResult(
        overall=None,
        status="CALCULATED",
        components={"qualitative_risk": None},
        weights={},
        formula_version="risk.RiskAnalyzer",
        detail="qualitative observations accepted; no quantitative risk score exists",
    )


def buffett_market_gdp(
    *,
    total_market_cap: Decimal | None,
    gdp: Decimal | None,
    market_cap_status: str | None,
    gdp_status: str | None,
    market_period: str | None,
    gdp_period: str | None,
    market_currency: str | None,
    gdp_currency: str | None,
    now: datetime,
) -> CalculationResult:
    inputs = ("total_market_cap", "gdp")
    if market_cap_status != "VERIFIED" or gdp_status != "VERIFIED":
        return _blocked(
            "buffett_indicator",
            status="BLOCKED",
            detail="Buffett market/GDP requires verified total market cap and GDP",
            now=now,
            formula_version=FORMULA_VERSIONS["buffett_market_gdp"],
            formula=BUFFETT_FORMULA,
            inputs=inputs,
        )
    if total_market_cap is None or gdp is None or gdp == 0:
        return _blocked(
            "buffett_indicator",
            status="BLOCKED",
            detail="missing market cap or GDP",
            now=now,
            formula_version=FORMULA_VERSIONS["buffett_market_gdp"],
            formula=BUFFETT_FORMULA,
            inputs=inputs,
        )
    if not market_currency or not gdp_currency or market_currency != gdp_currency:
        return _blocked(
            "buffett_indicator",
            status="CALCULATION_BLOCKED",
            detail="currency mismatch",
            now=now,
            formula_version=FORMULA_VERSIONS["buffett_market_gdp"],
            formula=BUFFETT_FORMULA,
            inputs=inputs,
        )
    left = canonicalize_period(market_period)
    right = canonicalize_period(gdp_period)
    if left is None or right is None or not periods_comparable(left, right):
        return _blocked(
            "buffett_indicator",
            status="CALCULATION_BLOCKED",
            detail="market cap and GDP periods are not compatible",
            now=now,
            formula_version=FORMULA_VERSIONS["buffett_market_gdp"],
            formula=BUFFETT_FORMULA,
            inputs=inputs,
        )
    return CalculationResult(
        field="buffett_indicator",
        value=total_market_cap / gdp,
        status="CALCULATED",
        formula_version=FORMULA_VERSIONS["buffett_market_gdp"],
        formula=BUFFETT_FORMULA,
        scenario="BASE",
        input_fields=inputs,
        input_evidence_ids=(),
        assumption_ids=(),
        calculated_at=now,
        detail="classic market-cap/GDP; company market cap is not the market",
    )


def run_dsp_calculations(
    dataset: VerifiedDataset,
    *,
    assumptions: tuple[CanonicalAssumption, ...] = (),
    listing: SecurityListing | None = None,
    capability: str | None = None,
    quality_components: Mapping[str, Decimal | None] | None = None,
    moat_components: Mapping[str, Decimal | None] | None = None,
    risk_observations: tuple[str, ...] = (),
    ai_valuation: Decimal | None = None,
    ai_quality_narrative: str | None = None,
    ai_moat_score: Decimal | None = None,
    ai_risk_score: Decimal | None = None,
    gdp: tuple[Decimal | None, str | None, str | None, str | None] | None = None,
    total_market_cap: tuple[Decimal | None, str | None, str | None, str | None] | None = None,
    calculated_at: datetime | None = None,
) -> DspCalculationSet:
    """Run derived fields + DCF/MOS/scores. AI valuation payload is ignored."""
    now = calculated_at or datetime.now(tz=UTC)
    ignore_ai_valuation(ai_valuation)
    derived = derive_dsp_fields(dataset, calculated_at=now)
    cap = _capability_for(listing, capability)
    validated = validate_assumption_pack(assumptions)
    accepted_rows = tuple(item.assumption for item in validated if item.accepted)

    base_assumps = accepted_only(accepted_rows, scenario="BASE")
    dcf = _run_dcf(dataset, derived, base_assumps, now=now, scenario="BASE", capability=cap)
    equity, ivps = _per_share(dcf, dataset, now=now, scenario="BASE")
    mos = _mos(ivps, dataset, now=now, scenario="BASE")
    sensitivity = _sensitivity(dataset, derived, base_assumps, now=now, capability=cap)

    scenario_dcf: dict[str, CalculationResult] = {"BASE": dcf}
    for name in ("BEAR", "BULL"):
        pack = accepted_only(accepted_rows, scenario=name)
        if not pack:
            scenario_dcf[name] = _blocked(
                "dcf",
                status="BLOCKED",
                detail=f"no ACCEPTED {name} assumptions",
                now=now,
                scenario=name,
            )
            continue
        scenario_dcf[name] = _run_dcf(
            dataset, derived, pack, now=now, scenario=name, capability=cap
        )

    quality = aggregate_quality_scores(quality_components, ai_narrative=ai_quality_narrative)
    moat = aggregate_moat_scores(moat_components, ai_score=ai_moat_score)
    risk = _risk_result(observations=risk_observations, ai_score=ai_risk_score)

    gdp_row = gdp or (None, None, None, None)
    mkt_row = total_market_cap or (None, None, None, None)
    buffett = buffett_market_gdp(
        total_market_cap=mkt_row[0],
        gdp=gdp_row[0],
        market_cap_status=mkt_row[1],
        gdp_status=gdp_row[1],
        market_period=mkt_row[2],
        gdp_period=gdp_row[2],
        market_currency=mkt_row[3],
        gdp_currency=gdp_row[3],
        now=now,
    )

    overall = ScoreAggregationResult(
        overall=None,
        status="BLOCKED",
        components={
            "quality": quality.overall,
            "moat": moat.overall,
            "valuation_ivps": ivps.value,
            "buffett": buffett.value,
        },
        weights={},
        formula_version="official_research.dsp_calculation.no_hidden_overall_mix",
        detail=(
            "No new overall mix is invented. Quality, moat, DCF, and Buffett stay "
            "separate. AI prose cannot create an overall score."
        ),
    )

    return DspCalculationSet(
        derived=derived,
        dcf=dcf,
        intrinsic_value=equity,
        intrinsic_value_per_share=ivps,
        margin_of_safety=mos,
        quality=quality,
        moat=moat,
        risk=risk,
        buffett=buffett,
        overall=overall,
        sensitivity=sensitivity,
        scenarios=scenario_dcf,
        calculated_at=now,
        formula_catalog={
            **FORMULA_VERSIONS,
            "dcf_intelligence_documented": DCF_INTELLIGENCE_FORMULA,
            "dcf_method_canonical": DCF_METHOD_FORMULA,
        },
    )


def units_are_not_guessed(amount: str, left_unit: str, right_unit: str) -> bool:
    left = normalize_numeric_to_actual(amount, left_unit)
    right = normalize_numeric_to_actual(amount, right_unit)
    return left != right
