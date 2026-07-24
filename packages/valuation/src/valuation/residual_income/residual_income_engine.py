"""Residual Income Valuation Engine — multi-stage RIV (research-only).

Automatic clean-surplus book projection, ROE path models, quality flags,
and V2-ready aggregate cites.

Independent of ``methods.residual_income``, DCF Intelligence, and Reverse DCF.

References
    Penman clean-surplus residual income model; Ohlson framework (conceptual).
"""

from __future__ import annotations

from dataclasses import replace
from statistics import pstdev

from valuation.exceptions import ValuationError
from valuation.residual_income.residual_income_explainability import RiExplainedValue
from valuation.residual_income.residual_income_models import (
    RESEARCH_DISCLAIMER,
    RESIDUAL_INCOME_VERSION,
    CleanSurplusCheck,
    ResidualIncomeInputs,
    ResidualIncomeResult,
    ResidualIncomeScenario,
    ResidualIncomeYear,
    RiConfidenceDetail,
    RiQualityFlag,
    RiScenarioResult,
    RiSensitivityCell,
    RiSensitivityMatrix,
    RoeForecastModel,
)
from valuation.residual_income.residual_income_validation import (
    validate_residual_income_inputs,
)

__all__ = ["ResidualIncomeEngine", "RESIDUAL_INCOME_VERSION", "verify_clean_surplus"]

_METHODOLOGY = (
    "Multi-stage Residual Income Valuation (clean-surplus): "
    "Stage 1 Explicit: NI_t = ROE_t×BV_{t−1}; Div_t = payout×NI_t; "
    "BV_t = BV_{t−1}+NI_t−Div_t (auto-projected); "
    "RI_t = NI_t − r×BV_{t−1}; "
    "Stage 2 Continuing RI: RI_{n+1}/(r−g); "
    "Stage 3 Terminal PV: CV/(1+r)^n; "
    "IV = BV_0 + Σ PV(RI_t) + PV(CV). Research / educational only."
)

_LIMITATIONS = (
    RESEARCH_DISCLAIMER,
    "Assumes clean-surplus book value evolution (auto-projected)",
    "Terminal RI persistence is assumption-sensitive",
    "Does not enable Overall Valuation",
    "Independent of legacy ResidualIncomeMethod closed form",
)

_CLEAN_SURPLUS_TOL = 1e-8


def verify_clean_surplus(
    *,
    year: int,
    opening_book_value: float,
    net_income: float,
    dividends: float,
    ending_book_value: float,
) -> CleanSurplusCheck:
    """Verify ``BV_{t−1} + NI_t − Div_t = BV_t``.

    Returns a :class:`CleanSurplusCheck`. Engine construction always
    satisfies the identity; this helper also supports research audits.
    """
    implied = opening_book_value + net_income - dividends
    residual = abs(ending_book_value - implied)
    return CleanSurplusCheck(
        year=year,
        opening_book_value=opening_book_value,
        net_income=net_income,
        dividends=dividends,
        ending_book_value=ending_book_value,
        implied_ending=implied,
        residual=residual,
        ok=residual <= _CLEAN_SURPLUS_TOL,
    )


def _retention(inputs: ResidualIncomeInputs) -> float:
    if inputs.retention_ratio is not None:
        return float(inputs.retention_ratio)
    return 1.0 - inputs.dividend_payout_ratio


def _payout(inputs: ResidualIncomeInputs) -> float:
    if inputs.retention_ratio is not None:
        return 1.0 - float(inputs.retention_ratio)
    return inputs.dividend_payout_ratio


def _explained(
    name: str,
    value: float | None,
    formula: str,
    inputs: dict,
    intermediates: dict,
    confidence: str,
    notes: str = "",
) -> RiExplainedValue:
    return RiExplainedValue(
        name=name,
        value=value,
        formula=formula,
        inputs=inputs,
        intermediates=intermediates,
        confidence=confidence,
        notes=notes,
    )


def _roe_path(inputs: ResidualIncomeInputs, *, roe_shift: float = 0.0) -> tuple[float, ...]:
    """Build per-year ROE path for the explicit forecast period."""
    n = inputs.forecast_years
    base = inputs.roe_forecast + roe_shift
    terminal = (
        (inputs.terminal_roe + roe_shift)
        if inputs.terminal_roe is not None
        else base
    )
    long_run = (
        inputs.roe_long_run
        if inputs.roe_long_run is not None
        else terminal
    )

    if inputs.roe_model is RoeForecastModel.CONSTANT:
        return tuple(base for _ in range(n))

    if inputs.roe_model is RoeForecastModel.LINEAR_FADE:
        return tuple(
            base + (terminal - base) * (t / n) for t in range(1, n + 1)
        )

    if inputs.roe_model is RoeForecastModel.MEAN_REVERSION:
        kappa = inputs.mean_reversion_kappa
        path: list[float] = []
        roe = base
        for _ in range(n):
            roe = long_run + (roe - long_run) * (1.0 - kappa)
            path.append(roe)
        return tuple(path)

    # MANUAL
    assert inputs.roe_manual_series is not None
    return tuple(v + roe_shift for v in inputs.roe_manual_series)


def _confidence_detail(
    inputs: ResidualIncomeInputs,
    *,
    clean_surplus_ok: bool,
    years: tuple[ResidualIncomeYear, ...],
) -> RiConfidenceDetail:
    """Score confidence from stability, quality, completeness, clean surplus."""
    factors: dict[str, int] = {}
    # Book value stability
    factors["book_value_stability"] = 1 if inputs.current_book_value > 0 else 0
    if years:
        growth = years[-1].ending_book_value / years[0].opening_book_value - 1.0
        factors["book_value_stability"] += 1 if growth > -0.2 else 0

    # ROE stability
    hist = list(inputs.historical_roe_series)
    if len(hist) >= 2:
        factors["roe_stability"] = 1 if pstdev(hist) < 0.08 else 0
    else:
        factors["roe_stability"] = 1 if 0.0 < inputs.roe_forecast < 0.4 else 0

    # Forecast reliability
    factors["forecast_reliability"] = 0
    if inputs.forecast_years >= 5:
        factors["forecast_reliability"] += 1
    if inputs.roe_model is not RoeForecastModel.MANUAL or (
        inputs.roe_manual_series is not None
    ):
        factors["forecast_reliability"] += 1

    # Accounting quality
    if inputs.accounting_quality_score is None:
        factors["accounting_quality"] = 1
    elif inputs.accounting_quality_score >= 70:
        factors["accounting_quality"] = 2
    elif inputs.accounting_quality_score >= 40:
        factors["accounting_quality"] = 1
    else:
        factors["accounting_quality"] = 0

    # Data completeness
    factors["data_completeness"] = 0
    if inputs.shares_outstanding > 0:
        factors["data_completeness"] += 1
    if inputs.current_market_price is not None:
        factors["data_completeness"] += 1
    if inputs.net_income_forecast is not None:
        factors["data_completeness"] += 1

    # Clean surplus compliance
    factors["clean_surplus_compliance"] = 2 if clean_surplus_ok else 0

    score = sum(factors.values())
    max_score = 12
    if score >= 9:
        level = "high"
    elif score >= 5:
        level = "medium"
    else:
        level = "low"

    rationale = (
        f"Confidence={level} (score {score}/{max_score}). "
        + ", ".join(f"{k}={v}" for k, v in factors.items())
        + (
            ". Clean surplus identity held."
            if clean_surplus_ok
            else ". Clean surplus warnings reduced confidence."
        )
    )
    return RiConfidenceDetail(
        level=level,
        score=score,
        max_score=max_score,
        factors=factors,
        rationale=rationale,
    )


def _quality_flags(
    inputs: ResidualIncomeInputs,
    years: tuple[ResidualIncomeYear, ...],
    *,
    clean_surplus_ok: bool,
    clean_warnings: tuple[str, ...],
) -> tuple[RiQualityFlag, ...]:
    flags: list[RiQualityFlag] = []
    roes = [y.roe for y in years]
    if roes and min(roes) >= 0.15 and inputs.cost_of_equity > 0:
        if min(roes) >= inputs.cost_of_equity + 0.03:
            flags.append(RiQualityFlag.HIGH_ROE_SUSTAINABILITY)
    if len(roes) >= 2 and roes[-1] < roes[0] - 0.01:
        flags.append(RiQualityFlag.DECLINING_ROE)
    if any(y.residual_income < 0 for y in years):
        flags.append(RiQualityFlag.NEGATIVE_RESIDUAL_INCOME)
    if years:
        bv_growth = years[-1].ending_book_value / years[0].opening_book_value - 1.0
        if bv_growth < 0.0:
            flags.append(RiQualityFlag.WEAK_BOOK_VALUE_GROWTH)
    if inputs.accounting_quality_score is not None and inputs.accounting_quality_score < 40:
        flags.append(RiQualityFlag.ACCOUNTING_WARNING)
    if clean_warnings or not clean_surplus_ok:
        flags.append(RiQualityFlag.CLEAN_SURPLUS_WARNING)
        flags.append(RiQualityFlag.ACCOUNTING_WARNING)
    retention = _retention(inputs)
    if retention > 0 and inputs.roe_forecast >= inputs.cost_of_equity:
        # High ROE with retention → capital efficient research flag
        if inputs.roe_forecast >= 0.12:
            flags.append(RiQualityFlag.CAPITAL_EFFICIENT_BUSINESS)
    # dedupe preserve order
    seen: set[RiQualityFlag] = set()
    out: list[RiQualityFlag] = []
    for f in flags:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return tuple(out)


def _run_core(
    inputs: ResidualIncomeInputs,
    *,
    roe_shift: float = 0.0,
    payout_override: float | None = None,
    terminal_roe_override: float | None = None,
) -> tuple[
    tuple[ResidualIncomeYear, ...],
    float,
    float,
    float,
    float,
    bool,
    tuple[str, ...],
]:
    """Explicit RI path + continuing value; auto-projects book value.

    Returns:
        years, PV(RI), continuing CV, PV(CV), intrinsic equity,
        clean_surplus_ok, clean_surplus_warnings
    """
    r = inputs.cost_of_equity
    g = inputs.terminal_growth
    payout = payout_override if payout_override is not None else _payout(inputs)
    n = inputs.forecast_years
    path = _roe_path(inputs, roe_shift=roe_shift)
    years: list[ResidualIncomeYear] = []
    bv = inputs.current_book_value
    pv_ri = 0.0
    last_ri = 0.0
    warnings: list[str] = []
    clean_ok = True
    conf_level = "medium"

    for t, roe_t in enumerate(path, start=1):
        opening = bv
        if (
            t == 1
            and inputs.net_income_forecast is not None
            and abs(roe_shift) < 1e-15
            and inputs.roe_model is RoeForecastModel.CONSTANT
        ):
            ni = float(inputs.net_income_forecast)
        else:
            ni = roe_t * opening
        dividends = payout * ni
        ending = opening + ni - dividends
        cs = verify_clean_surplus(
            year=t,
            opening_book_value=opening,
            net_income=ni,
            dividends=dividends,
            ending_book_value=ending,
        )
        if not cs.ok:
            clean_ok = False
            warnings.append(
                f"Year {t}: clean surplus residual {cs.residual:.3e} "
                f"(BV+NI−Div ≠ ending)"
            )
        if ending <= 0:
            raise ValuationError(
                f"ending book value non-positive at year {t}: {ending}"
            )
        charge = r * opening
        ri = ni - charge
        df = 1.0 / ((1.0 + r) ** t)
        pv = ri * df
        pv_ri += pv
        last_ri = ri
        years.append(
            ResidualIncomeYear(
                year=t,
                roe=roe_t,
                opening_book_value=opening,
                net_income=ni,
                dividends=dividends,
                ending_book_value=ending,
                residual_income=ri,
                cost_of_equity_charge=charge,
                present_value_ri=pv,
                clean_surplus=cs,
                explained=_explained(
                    f"year_{t}",
                    ri,
                    "RI_t = NI_t − r×BV_{t−1}; BV_t = BV_{t−1}+NI_t−Div_t",
                    {
                        "roe_t": roe_t,
                        "cost_of_equity": r,
                        "payout": payout,
                        "opening_bv": opening,
                    },
                    {
                        "net_income": ni,
                        "dividends": dividends,
                        "ending_bv": ending,
                        "cost_of_equity_charge": charge,
                        "discount_factor": df,
                        "pv_ri": pv,
                        "clean_surplus_residual": cs.residual,
                        "clean_surplus_ok": cs.ok,
                    },
                    conf_level,
                    notes=(
                        RESEARCH_DISCLAIMER
                        if cs.ok
                        else f"{RESEARCH_DISCLAIMER} Clean surplus warning."
                    ),
                ),
            )
        )
        bv = ending

    term_roe = (
        terminal_roe_override
        if terminal_roe_override is not None
        else (
            inputs.terminal_roe + roe_shift
            if inputs.terminal_roe is not None
            else path[-1]
        )
    )
    if inputs.terminal_roe is not None or terminal_roe_override is not None:
        ri_next = (term_roe - r) * bv
    else:
        ri_next = last_ri * (1.0 + g)

    if r <= g:
        raise ValuationError("cost_of_equity must exceed terminal_growth for CV")
    continuing = ri_next / (r - g)
    pv_cv = continuing / ((1.0 + r) ** n)
    intrinsic = inputs.current_book_value + pv_ri + pv_cv
    return (
        tuple(years),
        pv_ri,
        continuing,
        pv_cv,
        intrinsic,
        clean_ok,
        tuple(warnings),
    )


def _mos(
    intrinsic_equity: float,
    intrinsic_ps: float | None,
    inputs: ResidualIncomeInputs,
    conf: str,
) -> RiExplainedValue:
    if inputs.current_market_price is None:
        return _explained(
            "margin_of_safety",
            None,
            "MoS = (IV − Market) / IV",
            {"market_price": None},
            {},
            "low",
            notes="Market price not provided. " + RESEARCH_DISCLAIMER,
        )
    price = float(inputs.current_market_price)
    if intrinsic_ps is not None and intrinsic_ps != 0:
        ratio = (intrinsic_ps - price) / intrinsic_ps
        return _explained(
            "margin_of_safety",
            ratio,
            "MoS = (IV/share − Price) / IV/share",
            {
                "intrinsic_value_per_share": intrinsic_ps,
                "current_market_price": price,
            },
            {},
            conf,
            notes=RESEARCH_DISCLAIMER,
        )
    market_cap = price * inputs.shares_outstanding
    if intrinsic_equity == 0:
        return _explained(
            "margin_of_safety",
            None,
            "MoS = (IV − MarketCap) / IV",
            {"intrinsic_equity": intrinsic_equity},
            {},
            "low",
            notes="Intrinsic equity is zero. " + RESEARCH_DISCLAIMER,
        )
    ratio = (intrinsic_equity - market_cap) / intrinsic_equity
    return _explained(
        "margin_of_safety",
        ratio,
        "MoS = (IntrinsicEquity − MarketCap) / IntrinsicEquity",
        {
            "intrinsic_equity": intrinsic_equity,
            "market_cap": market_cap,
        },
        {},
        conf,
        notes=RESEARCH_DISCLAIMER,
    )


def _scenario(
    inputs: ResidualIncomeInputs,
    scenario: ResidualIncomeScenario,
    roe_shift: float,
) -> RiScenarioResult:
    years, pv_ri, continuing, pv_cv, intrinsic, clean_ok, warns = _run_core(
        inputs, roe_shift=roe_shift
    )
    detail = _confidence_detail(inputs, clean_surplus_ok=clean_ok, years=years)
    conf = detail.level
    ivps = intrinsic / inputs.shares_outstanding
    return RiScenarioResult(
        scenario=scenario,
        intrinsic_equity_value=_explained(
            f"intrinsic_equity_{scenario.value}",
            intrinsic,
            "IV = BV_0 + Σ PV(RI) + PV(CV)",
            {"roe_shift": roe_shift, "bv0": inputs.current_book_value},
            {
                "pv_ri": pv_ri,
                "pv_cv": pv_cv,
                "continuing": continuing,
                "clean_surplus_ok": clean_ok,
            },
            conf,
            notes=RESEARCH_DISCLAIMER,
        ),
        intrinsic_value_per_share=_explained(
            f"ivps_{scenario.value}",
            ivps,
            "IV/share = IV / Shares",
            {"intrinsic": intrinsic, "shares": inputs.shares_outstanding},
            {},
            conf,
            notes=RESEARCH_DISCLAIMER,
        ),
        pv_residual_income=_explained(
            f"pv_ri_{scenario.value}",
            pv_ri,
            "Σ RI_t / (1+r)^t",
            {"r": inputs.cost_of_equity, "n": inputs.forecast_years},
            {"years": len(years)},
            conf,
        ),
        continuing_value=_explained(
            f"continuing_{scenario.value}",
            continuing,
            "CV = RI_{n+1} / (r − g)",
            {"r": inputs.cost_of_equity, "g": inputs.terminal_growth},
            {"pv_cv": pv_cv, "warnings": "; ".join(warns) if warns else None},
            conf,
        ),
        margin_of_safety=_mos(intrinsic, ivps, inputs, conf),
        confidence=conf,
    )


def _sensitivity(inputs: ResidualIncomeInputs) -> RiSensitivityMatrix:
    def run_patched(
        patched: ResidualIncomeInputs | None = None,
        *,
        dim: str,
        param: float,
        **kwargs: object,
    ) -> RiSensitivityCell:
        src = patched if patched is not None else inputs
        try:
            (
                _y,
                _pv,
                _cv,
                _pvcv,
                intrinsic,
                _ok,
                _w,
            ) = _run_core(src, **kwargs)  # type: ignore[arg-type]
            ivps = intrinsic / src.shares_outstanding
            return RiSensitivityCell(dim, param, intrinsic, ivps)
        except ValuationError:
            return RiSensitivityCell(dim, param, None, None)

    roe_cells: list[RiSensitivityCell] = []
    for delta in (-0.02, 0.0, 0.02):
        roe = inputs.roe_forecast + delta
        if roe < -0.5 or roe > 1.0:
            roe_cells.append(RiSensitivityCell("roe", roe, None, None))
            continue
        roe_cells.append(run_patched(dim="roe", param=roe, roe_shift=delta))

    r_cells: list[RiSensitivityCell] = []
    for delta in (-0.01, 0.0, 0.01):
        r = inputs.cost_of_equity + delta
        if r <= 0 or r <= inputs.terminal_growth:
            r_cells.append(RiSensitivityCell("cost_of_equity", r, None, None))
            continue
        r_cells.append(
            run_patched(
                replace(inputs, cost_of_equity=r),
                dim="cost_of_equity",
                param=r,
            )
        )

    g_cells: list[RiSensitivityCell] = []
    for delta in (-0.005, 0.0, 0.005):
        g = inputs.terminal_growth + delta
        if inputs.cost_of_equity <= g:
            g_cells.append(RiSensitivityCell("terminal_growth", g, None, None))
            continue
        g_cells.append(
            run_patched(
                replace(inputs, terminal_growth=g),
                dim="terminal_growth",
                param=g,
            )
        )

    payout_cells: list[RiSensitivityCell] = []
    for payout in (0.2, 0.4, 0.6):
        payout_cells.append(
            run_patched(
                replace(inputs, dividend_payout_ratio=payout, retention_ratio=None),
                dim="payout_ratio",
                param=payout,
                payout_override=payout,
            )
        )

    troe_cells: list[RiSensitivityCell] = []
    base_troe = (
        inputs.terminal_roe
        if inputs.terminal_roe is not None
        else inputs.roe_forecast
    )
    for delta in (-0.02, 0.0, 0.02):
        troe = base_troe + delta
        if troe < -0.5 or troe > 1.0:
            troe_cells.append(RiSensitivityCell("terminal_roe", troe, None, None))
            continue
        troe_cells.append(
            run_patched(
                replace(inputs, terminal_roe=troe),
                dim="terminal_roe",
                param=troe,
                terminal_roe_override=troe,
            )
        )

    explained = _explained(
        "sensitivity_matrix",
        float(
            len(roe_cells)
            + len(r_cells)
            + len(g_cells)
            + len(payout_cells)
            + len(troe_cells)
        ),
        "OTAT grids: ROE, cost of equity, terminal growth, payout, terminal ROE",
        {
            "roe_deltas": [-0.02, 0.0, 0.02],
            "r_deltas": [-0.01, 0.0, 0.01],
            "g_deltas": [-0.005, 0.0, 0.005],
            "payouts": [0.2, 0.4, 0.6],
            "terminal_roe_deltas": [-0.02, 0.0, 0.02],
        },
        {},
        "high",
        notes="Deterministic; " + RESEARCH_DISCLAIMER,
    )
    return RiSensitivityMatrix(
        roe=tuple(roe_cells),
        cost_of_equity=tuple(r_cells),
        terminal_growth=tuple(g_cells),
        payout_ratio=tuple(payout_cells),
        terminal_roe=tuple(troe_cells),
        explained=explained,
    )


class ResidualIncomeEngine:
    """Domain Residual Income engine — pure, deterministic, explainable.

    Performance target: &lt; 50 ms per valuation on standard hardware
    (pure Python arithmetic; no I/O).
    """

    version = RESIDUAL_INCOME_VERSION

    def analyze(self, inputs: ResidualIncomeInputs) -> ResidualIncomeResult:
        """Run multi-stage residual income valuation.

        Stages:
            1. Explicit forecast (auto BV projection)
            2. Continuing residual income
            3. Terminal present value → intrinsic equity

        Raises:
            ValuationError: On invalid inputs or non-computable paths.
        """
        validation = validate_residual_income_inputs(inputs)

        years, pv_ri, continuing, pv_cv, intrinsic, clean_ok, cs_warns = _run_core(
            inputs
        )
        # Merge validation warnings (e.g. NI/ROE inconsistency)
        all_cs_warns = tuple(validation.warnings) + cs_warns
        if validation.warnings and clean_ok:
            # Soft accounting warning does not break clean surplus identity
            pass

        detail = _confidence_detail(
            inputs, clean_surplus_ok=clean_ok and not all_cs_warns, years=years
        )
        # Soft warnings reduce confidence one notch if still high
        conf = detail.level
        if all_cs_warns and conf == "high":
            conf = "medium"
            detail = RiConfidenceDetail(
                level=conf,
                score=detail.score,
                max_score=detail.max_score,
                factors=detail.factors,
                rationale=detail.rationale
                + " Reduced to medium due to clean-surplus/accounting warnings.",
            )
        elif all_cs_warns and conf == "medium":
            conf = "low"
            detail = RiConfidenceDetail(
                level=conf,
                score=detail.score,
                max_score=detail.max_score,
                factors=detail.factors,
                rationale=detail.rationale
                + " Reduced to low due to clean-surplus/accounting warnings.",
            )

        flags = _quality_flags(
            inputs,
            years,
            clean_surplus_ok=clean_ok,
            clean_warnings=all_cs_warns,
        )
        ivps = intrinsic / inputs.shares_outstanding

        book = _explained(
            "book_value",
            inputs.current_book_value,
            "BV_0 = current book value; future BV auto-projected via clean surplus",
            {"current_book_value": inputs.current_book_value},
            {
                "retention": _retention(inputs),
                "payout": _payout(inputs),
                "roe_model": inputs.roe_model.value,
            },
            conf,
            notes=RESEARCH_DISCLAIMER,
        )
        pv_ri_ex = _explained(
            "pv_residual_income",
            pv_ri,
            "Σ RI_t / (1+r)^t  (explicit stage)",
            {"r": inputs.cost_of_equity, "n": inputs.forecast_years},
            {},
            conf,
            notes=RESEARCH_DISCLAIMER,
        )
        cv_ex = _explained(
            "continuing_value",
            continuing,
            "CV = RI_{n+1} / (r − g)  (continuing residual stage)",
            {
                "r": inputs.cost_of_equity,
                "g": inputs.terminal_growth,
                "terminal_roe": inputs.terminal_roe,
            },
            {},
            conf,
            notes=RESEARCH_DISCLAIMER,
        )
        pv_cv_ex = _explained(
            "continuing_value_pv",
            pv_cv,
            "PV(CV) = CV / (1+r)^n  (terminal stage)",
            {"continuing": continuing, "r": inputs.cost_of_equity, "n": inputs.forecast_years},
            {},
            conf,
            notes=RESEARCH_DISCLAIMER,
        )
        iv_ex = _explained(
            "intrinsic_equity_value",
            intrinsic,
            "IV = BV_0 + Σ PV(RI) + PV(CV)",
            {"bv0": inputs.current_book_value},
            {"pv_ri": pv_ri, "pv_cv": pv_cv},
            conf,
            notes=RESEARCH_DISCLAIMER,
        )
        ivps_ex = _explained(
            "intrinsic_value_per_share",
            ivps,
            "IV/share = IV / Shares",
            {"intrinsic": intrinsic, "shares": inputs.shares_outstanding},
            {},
            conf,
            notes=RESEARCH_DISCLAIMER,
        )
        mos = _mos(intrinsic, ivps, inputs, conf)
        conf_ex = _explained(
            "confidence_rationale",
            float(detail.score),
            "Weighted research factors → High/Medium/Low",
            dict(detail.factors),
            {"max_score": detail.max_score, "level": conf},
            conf,
            notes=detail.rationale + " " + RESEARCH_DISCLAIMER,
        )

        base = _scenario(inputs, ResidualIncomeScenario.BASE, 0.0)
        bear = _scenario(
            inputs, ResidualIncomeScenario.BEAR, inputs.bear_roe_delta
        )
        bull = _scenario(
            inputs, ResidualIncomeScenario.BULL, inputs.bull_roe_delta
        )
        sensitivity = _sensitivity(inputs)

        from valuation.residual_income.residual_income_models import (
            RiValidationSummary,
        )

        validation_out = RiValidationSummary(
            ok=validation.ok,
            checks=validation.checks,
            errors=validation.errors,
            warnings=all_cs_warns,
        )

        explainability = (
            book,
            pv_ri_ex,
            cv_ex,
            pv_cv_ex,
            iv_ex,
            ivps_ex,
            mos,
            conf_ex,
            sensitivity.explained,
            *[y.explained for y in years],
            bear.intrinsic_equity_value,
            bull.intrinsic_equity_value,
        )

        return ResidualIncomeResult(
            version=self.version,
            currency=inputs.currency,
            disclaimer=RESEARCH_DISCLAIMER,
            book_value=book,
            years=years,
            pv_residual_income=pv_ri_ex,
            continuing_value=cv_ex,
            continuing_value_pv=pv_cv_ex,
            intrinsic_equity_value=iv_ex,
            intrinsic_value_per_share=ivps_ex,
            margin_of_safety=mos,
            confidence=conf,
            confidence_detail=detail,
            quality_flags=flags,
            clean_surplus_ok=clean_ok,
            clean_surplus_warnings=all_cs_warns,
            validation_summary=validation_out,
            scenarios=(bear, base, bull),
            sensitivity=sensitivity,
            explainability=explainability,
            methodology=_METHODOLOGY,
            limitations=_LIMITATIONS,
            roe_model=inputs.roe_model,
            stages={
                "explicit_forecast": "PV of residual income over forecast_years",
                "continuing_residual_income": "CV = RI_{n+1}/(r−g)",
                "terminal_value": "PV(CV) discounted n periods",
            },
        )
