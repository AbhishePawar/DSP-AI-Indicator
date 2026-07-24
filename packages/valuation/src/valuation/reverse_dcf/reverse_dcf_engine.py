"""Reverse DCF Intelligence Engine — implied growth from market price.

Research capability only. Not a recommendation engine.
Independent of ``valuation.dcf_intelligence`` (does not modify it).
"""

from __future__ import annotations

from dataclasses import replace

from valuation.exceptions import ValuationError
from valuation.reverse_dcf.reverse_dcf_explainability import ReverseExplainedValue
from valuation.reverse_dcf.reverse_dcf_models import (
    REVERSE_DCF_VERSION,
    ReverseDcfInputs,
    ReverseDcfResult,
    ReverseDcfScenario,
    ScenarioResult,
    SensitivityCell,
    SensitivityMatrix,
    SolverMetadata,
)
from valuation.reverse_dcf.reverse_dcf_validation import validate_reverse_dcf_inputs

__all__ = ["ReverseDcfEngine", "REVERSE_DCF_VERSION"]

_METHODOLOGY = (
    "Reverse DCF: binary-search the revenue CAGR such that a Gordon FCFF "
    "model reproduces the enterprise value implied by market price. "
    "FCFF_t ≈ NOPAT_t × (1 − reinvestment); "
    "TV = FCFF_n(1+g_t)/(WACC−g_t); EV = Σ PV(FCFF) + PV(TV). "
    "Research Mode only — not a recommendation."
)

_LIMITATIONS = (
    "Implied growth is model-dependent and assumption-sensitive",
    "Simplified reinvestment link from NOPAT; not full BS forecast",
    "Research posture only — not Buy/Sell advice",
    "Does not enable Overall Valuation",
    "Deterministic binary search; no external optimizer",
)

_DISCLAIMER = (
    "Reverse DCF implies growth embedded in market price for research. "
    "It is NOT a Buy/Sell/Hold recommendation. Research Mode only."
)


def _target_enterprise_value(inputs: ReverseDcfInputs) -> float:
    equity = inputs.current_share_price * inputs.shares_outstanding
    return (
        equity
        + inputs.debt
        + inputs.minority_interest
        - inputs.cash
        - inputs.investments
    )


def _project_paths(
    inputs: ReverseDcfInputs,
    revenue_cagr: float,
    margin_delta: float = 0.0,
) -> tuple[list[float], list[float], list[float], float]:
    """Return (revenues, ebits, fcffs, terminal_value) for candidate CAGR."""
    n = inputs.forecast_years
    base_margin = inputs.current_operating_margin + margin_delta
    revenues: list[float] = []
    ebits: list[float] = []
    fcffs: list[float] = []
    rev = inputs.current_revenue
    for t in range(1, n + 1):
        rev = inputs.current_revenue * ((1.0 + revenue_cagr) ** t)
        # Linear fade-in of expected margin expansion over horizon
        expand = inputs.expected_margin_expansion * (t / n)
        margin = base_margin + expand
        ebit = rev * margin
        nopat = ebit * (1.0 - inputs.tax_rate)
        # Optional ROIC hint: higher ROIC → slightly lower effective reinvestment
        reinvest = inputs.reinvestment_rate
        if inputs.expected_roic is not None and inputs.expected_roic > 0:
            # research heuristic: reinvest ≈ g / ROIC capped
            reinvest = min(
                max(revenue_cagr / inputs.expected_roic, 0.0),
                1.0,
            )
        fcff = nopat * (1.0 - reinvest)
        revenues.append(rev)
        ebits.append(ebit)
        fcffs.append(fcff)

    last_fcff = fcffs[-1]
    if inputs.wacc <= inputs.terminal_growth:
        raise ValuationError("WACC must exceed terminal growth during projection")
    tv = last_fcff * (1.0 + inputs.terminal_growth) / (
        inputs.wacc - inputs.terminal_growth
    )
    return revenues, ebits, fcffs, tv


def _model_enterprise_value(
    inputs: ReverseDcfInputs,
    revenue_cagr: float,
    margin_delta: float = 0.0,
) -> tuple[float, float, list[float], list[float], list[float]]:
    """EV, TV, and paths for a candidate growth."""
    revenues, ebits, fcffs, tv = _project_paths(inputs, revenue_cagr, margin_delta)
    wacc = inputs.wacc
    pv_fcff = 0.0
    for t, fcff in enumerate(fcffs, start=1):
        pv_fcff += fcff / ((1.0 + wacc) ** t)
    n = inputs.forecast_years
    pv_tv = tv / ((1.0 + wacc) ** n)
    return pv_fcff + pv_tv, tv, revenues, ebits, fcffs


def _cagr(first: float, last: float, years: int) -> float | None:
    if first <= 0 or last <= 0 or years < 1:
        return None
    return (last / first) ** (1.0 / years) - 1.0


def _solve_growth(
    inputs: ReverseDcfInputs,
    *,
    margin_delta: float = 0.0,
    target_ev: float | None = None,
) -> tuple[float, SolverMetadata, float, list[float], list[float], list[float]]:
    """Binary-search revenue CAGR so model EV matches target EV."""
    target = target_ev if target_ev is not None else _target_enterprise_value(inputs)
    if target <= 0:
        raise ValuationError(
            f"implied target enterprise value must be positive, got {target}"
        )

    low = inputs.growth_low
    high = inputs.growth_high
    precision = inputs.precision
    max_iter = inputs.max_iterations

    # Ensure bracket: EV(low) should be below target, EV(high) above when possible
    ev_low, _, _, _, _ = _model_enterprise_value(inputs, low, margin_delta)
    ev_high, _, _, _, _ = _model_enterprise_value(inputs, high, margin_delta)

    # If monotonicity fails extreme targets, still search mid
    iterations = 0
    best_g = 0.0
    best_err = float("inf")
    best_paths: tuple[float, list[float], list[float], list[float]] | None = None
    stop_reason = "max_iterations"

    # Expand bounds if target outside (limited)
    if ev_low > target and low > -0.9:
        low = -0.9
        ev_low, _, _, _, _ = _model_enterprise_value(inputs, low, margin_delta)
    if ev_high < target and high < 1.0:
        high = 1.0
        ev_high, _, _, _, _ = _model_enterprise_value(inputs, high, margin_delta)

    lo, hi = low, high
    converged = False
    residual = float("inf")

    while iterations < max_iter:
        iterations += 1
        mid = (lo + hi) / 2.0
        ev, tv, revs, ebits, fcffs = _model_enterprise_value(
            inputs, mid, margin_delta
        )
        err = (ev - target) / target
        abs_err = abs(err)
        if abs_err < best_err:
            best_err = abs_err
            best_g = mid
            best_paths = (tv, revs, ebits, fcffs)
            residual = abs_err

        # Growth precision ±0.01% → bracket width
        if abs_err <= precision or (hi - lo) <= precision:
            converged = True
            stop_reason = (
                "precision_met"
                if abs_err <= precision
                else "bracket_width_met"
            )
            best_g = mid
            best_paths = (tv, revs, ebits, fcffs)
            residual = abs_err
            break

        if ev < target:
            lo = mid
        else:
            hi = mid

    if best_paths is None:
        raise ValuationError("Reverse DCF solver failed to evaluate any candidate")

    meta = SolverMetadata(
        iterations=iterations,
        residual_error=residual,
        converged=converged,
        stop_reason=stop_reason if converged else "max_iterations",
        low_bound=inputs.growth_low,
        high_bound=inputs.growth_high,
        precision_target=precision,
    )
    tv, revs, ebits, fcffs = best_paths
    return best_g, meta, tv, revs, ebits, fcffs


def _confidence_score(inputs: ReverseDcfInputs, residual: float) -> str:
    """Research confidence from stability / completeness / residual heuristics."""
    score = 0
    # Data completeness
    if inputs.current_fcff != 0:
        score += 1
    if inputs.current_ebit != 0:
        score += 1
    if inputs.shares_outstanding > 0 and inputs.current_share_price > 0:
        score += 1
    # Margin stability proxy: |margin| reasonable
    if 0.0 < inputs.current_operating_margin < 0.5:
        score += 1
    # Capital structure completeness
    if inputs.debt >= 0 and inputs.cash >= 0:
        score += 1
    # Forecast sensitivity / residual
    if residual <= inputs.precision:
        score += 2
    elif residual <= inputs.precision * 10:
        score += 1
    # Revenue scale
    if inputs.current_revenue > 0:
        score += 1

    if score >= 7:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def _explained(
    name: str,
    value: float | None,
    formula: str,
    inputs: dict,
    intermediates: dict,
    confidence: str,
    notes: str = "",
    convergence_notes: str = "",
) -> ReverseExplainedValue:
    return ReverseExplainedValue(
        name=name,
        value=value,
        formula=formula,
        inputs=inputs,
        intermediates=intermediates,
        confidence=confidence,  # type: ignore[arg-type]
        notes=notes,
        convergence_notes=convergence_notes,
    )


def _scenario_result(
    inputs: ReverseDcfInputs,
    scenario: ReverseDcfScenario,
    margin_delta: float,
    target_ev: float,
) -> ScenarioResult:
    g, meta, tv, revs, ebits, fcffs = _solve_growth(
        inputs, margin_delta=margin_delta, target_ev=target_ev
    )
    conf = _confidence_score(inputs, meta.residual_error)
    fcff0 = inputs.current_fcff if inputs.current_fcff > 0 else fcffs[0]
    implied_fcff = _cagr(fcff0, fcffs[-1], inputs.forecast_years)
    ebit0 = inputs.current_ebit if inputs.current_ebit != 0 else ebits[0]
    implied_ebit = _cagr(abs(ebit0) if ebit0 != 0 else ebits[0], ebits[-1], inputs.forecast_years)
    ev, _, _, _, _ = _model_enterprise_value(inputs, g, margin_delta)
    equity = (
        ev
        - inputs.debt
        - inputs.minority_interest
        + inputs.cash
        + inputs.investments
    )

    return ScenarioResult(
        scenario=scenario,
        implied_revenue_cagr=_explained(
            f"implied_revenue_cagr_{scenario.value}",
            g,
            "binary search g s.t. model EV(g) ≈ market-implied EV",
            {"scenario": scenario.value, "margin_delta": margin_delta},
            {"target_ev": target_ev, "model_ev": ev},
            conf,
            notes=_DISCLAIMER,
            convergence_notes=(
                f"stop={meta.stop_reason}; iters={meta.iterations}; "
                f"residual={meta.residual_error:.6g}"
            ),
        ),
        implied_fcff_cagr=_explained(
            f"implied_fcff_cagr_{scenario.value}",
            implied_fcff,
            "CAGR(FCFF_0, FCFF_n, n)",
            {"fcff_0": fcff0, "fcff_n": fcffs[-1], "n": inputs.forecast_years},
            {},
            conf,
        ),
        implied_ebit_growth=_explained(
            f"implied_ebit_growth_{scenario.value}",
            implied_ebit,
            "CAGR(EBIT_0, EBIT_n, n)",
            {"ebit_0": ebit0, "ebit_n": ebits[-1], "n": inputs.forecast_years},
            {},
            conf,
        ),
        implied_terminal_value=_explained(
            f"implied_terminal_value_{scenario.value}",
            tv,
            "TV = FCFF_n(1+g_t)/(WACC−g_t)",
            {
                "fcff_n": fcffs[-1],
                "terminal_growth": inputs.terminal_growth,
                "wacc": inputs.wacc,
            },
            {},
            conf,
        ),
        enterprise_value=_explained(
            f"enterprise_value_{scenario.value}",
            ev,
            "EV = Σ PV(FCFF) + PV(TV)",
            {"wacc": inputs.wacc, "n": inputs.forecast_years},
            {},
            conf,
        ),
        equity_value=_explained(
            f"equity_value_{scenario.value}",
            equity,
            "Equity = EV − Debt − Minority + Cash + Investments",
            {
                "ev": ev,
                "debt": inputs.debt,
                "minority": inputs.minority_interest,
                "cash": inputs.cash,
                "investments": inputs.investments,
            },
            {},
            conf,
        ),
        solver=meta,
        confidence=conf,
    )


def _sensitivity(inputs: ReverseDcfInputs, target_ev: float) -> SensitivityMatrix:
    wacc_cells: list[SensitivityCell] = []
    for delta in (-0.01, 0.0, 0.01):
        w = inputs.wacc + delta
        if w <= inputs.terminal_growth or w <= 0:
            wacc_cells.append(
                SensitivityCell("wacc", w, None, None, False)
            )
            continue
        patched = replace(inputs, wacc=w)
        try:
            g, meta, *_ = _solve_growth(patched, target_ev=_target_enterprise_value(patched))
            wacc_cells.append(
                SensitivityCell("wacc", w, g, meta.residual_error, meta.converged)
            )
        except ValuationError:
            wacc_cells.append(SensitivityCell("wacc", w, None, None, False))

    tg_cells: list[SensitivityCell] = []
    for delta in (-0.005, 0.0, 0.005):
        tg = inputs.terminal_growth + delta
        if inputs.wacc <= tg:
            tg_cells.append(
                SensitivityCell("terminal_growth", tg, None, None, False)
            )
            continue
        patched = replace(inputs, terminal_growth=tg)
        try:
            g, meta, *_ = _solve_growth(patched, target_ev=target_ev)
            tg_cells.append(
                SensitivityCell(
                    "terminal_growth", tg, g, meta.residual_error, meta.converged
                )
            )
        except ValuationError:
            tg_cells.append(
                SensitivityCell("terminal_growth", tg, None, None, False)
            )

    price_cells: list[SensitivityCell] = []
    for mult in (0.9, 1.0, 1.1):
        price = inputs.current_share_price * mult
        patched = replace(inputs, current_share_price=price)
        try:
            g, meta, *_ = _solve_growth(
                patched, target_ev=_target_enterprise_value(patched)
            )
            price_cells.append(
                SensitivityCell(
                    "share_price", price, g, meta.residual_error, meta.converged
                )
            )
        except ValuationError:
            price_cells.append(
                SensitivityCell("share_price", price, None, None, False)
            )

    explained = _explained(
        "sensitivity_matrix",
        float(len(wacc_cells) + len(tg_cells) + len(price_cells)),
        "OTAT re-solve implied g for WACC, terminal growth, share price",
        {
            "wacc_deltas": [-0.01, 0.0, 0.01],
            "tg_deltas": [-0.005, 0.0, 0.005],
            "price_multiples": [0.9, 1.0, 1.1],
        },
        {},
        "high",
        notes="Deterministic; research-only.",
    )
    return SensitivityMatrix(
        wacc=tuple(wacc_cells),
        terminal_growth=tuple(tg_cells),
        share_price=tuple(price_cells),
        explained=explained,
    )


class ReverseDcfEngine:
    """Domain Reverse DCF engine — pure, deterministic, explainable."""

    version = REVERSE_DCF_VERSION

    def analyze(self, inputs: ReverseDcfInputs) -> ReverseDcfResult:
        """Solve implied growth from market price.

        Raises:
            ValuationError: On invalid inputs or non-computable paths.
        """
        validation = validate_reverse_dcf_inputs(inputs)
        target_ev = _target_enterprise_value(inputs)
        market_cap = inputs.current_share_price * inputs.shares_outstanding

        base = _scenario_result(inputs, ReverseDcfScenario.BASE, 0.0, target_ev)
        bear = _scenario_result(
            inputs,
            ReverseDcfScenario.BEAR,
            inputs.bear_margin_delta,
            target_ev,
        )
        bull = _scenario_result(
            inputs,
            ReverseDcfScenario.BULL,
            inputs.bull_margin_delta,
            target_ev,
        )
        sensitivity = _sensitivity(inputs, target_ev)

        conf = base.confidence
        price_ex = _explained(
            "current_market_price",
            inputs.current_share_price,
            "P = observed share price",
            {"current_share_price": inputs.current_share_price},
            {},
            conf,
        )
        mcap_ex = _explained(
            "current_market_cap",
            market_cap,
            "MarketCap = Price × Shares",
            {
                "price": inputs.current_share_price,
                "shares": inputs.shares_outstanding,
            },
            {},
            conf,
        )
        wacc_ex = _explained(
            "discount_rate",
            inputs.wacc,
            "WACC (input)",
            {"wacc": inputs.wacc},
            {},
            conf,
        )
        tg_ex = _explained(
            "terminal_growth",
            inputs.terminal_growth,
            "g_terminal (input)",
            {"terminal_growth": inputs.terminal_growth},
            {},
            conf,
        )
        period_ex = _explained(
            "forecast_period",
            float(inputs.forecast_years),
            "N = explicit forecast years",
            {"forecast_years": inputs.forecast_years},
            {},
            conf,
        )

        explainability = (
            base.implied_revenue_cagr,
            base.implied_fcff_cagr,
            base.implied_ebit_growth,
            base.implied_terminal_value,
            base.enterprise_value,
            base.equity_value,
            price_ex,
            mcap_ex,
            wacc_ex,
            tg_ex,
            period_ex,
            sensitivity.explained,
            bear.implied_revenue_cagr,
            bull.implied_revenue_cagr,
        )

        return ReverseDcfResult(
            version=self.version,
            currency=inputs.currency,
            disclaimer=_DISCLAIMER,
            implied_revenue_cagr=base.implied_revenue_cagr,
            implied_fcff_cagr=base.implied_fcff_cagr,
            implied_ebit_growth=base.implied_ebit_growth,
            implied_terminal_value=base.implied_terminal_value,
            enterprise_value=base.enterprise_value,
            equity_value=base.equity_value,
            current_market_price=price_ex,
            current_market_cap=mcap_ex,
            discount_rate=wacc_ex,
            terminal_growth=tg_ex,
            forecast_period=period_ex,
            convergence_iterations=base.solver.iterations,
            residual_error=base.solver.residual_error,
            confidence=conf,
            validation_summary=validation,
            solver=base.solver,
            scenarios=(bear, base, bull),
            sensitivity=sensitivity,
            explainability=explainability,
            methodology=_METHODOLOGY,
            limitations=_LIMITATIONS,
        )
