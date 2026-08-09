"""First-class financial quality signals.

EPS CAGR, FCF/NI, OCF/NI, share dilution, operating working capital.

Fail-closed: missing / invalid evidence → None (never invent).
Annual fiscal-year endpoints only for multi-year rates.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Sequence

from financial.period import PeriodType

__all__ = [
    "annual_positive_cagr",
    "eps_cagr_from_series",
    "fcf_to_earnings_ratio",
    "ocf_to_earnings_ratio",
    "map_fcf_to_earnings_01",
    "map_ocf_to_earnings_01",
    "share_dilution_rate",
    "dilution_discipline_01",
    "operating_working_capital",
    "period_change_rate",
    "growth_gap",
    "days_from_turnover",
]


def _cagr(start: float, end: float, years: int) -> float | None:
    if years < 1:
        return None
    if start <= 0 or end <= 0:
        return None
    result = (end / start) ** (1.0 / years) - 1.0
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def annual_positive_cagr(
    values_with_stmts: Sequence[tuple[float | None, Any]],
) -> tuple[float | None, int | None, int | None]:
    """CAGR over annual fiscal years for strictly positive values.

    Returns ``(cagr, start_fy, end_fy)``.
    """
    points: list[tuple[int, float]] = []
    for value, stmt in values_with_stmts:
        if value is None or stmt is None:
            continue
        period = getattr(stmt, "period", None)
        if period is None or period.period_type is not PeriodType.ANNUAL:
            continue
        fy = period.fiscal_year
        if fy is None:
            continue
        try:
            v = float(value)
        except (TypeError, ValueError):
            continue
        if v <= 0 or not math.isfinite(v):
            continue
        points.append((int(fy), v))
    if len(points) < 2:
        return None, None, None
    points.sort(key=lambda item: item[0])
    start_fy, start_v = points[0]
    end_fy, end_v = points[-1]
    years = end_fy - start_fy
    return _cagr(start_v, end_v, years), start_fy, end_fy


def eps_cagr_from_series(
    incomes: Sequence[Any],
    stmts: Sequence[Any],
) -> tuple[float | None, str]:
    """EPS CAGR preferring diluted EPS; else basic ``eps``. Never mix bases.

    Returns ``(cagr, basis)`` where basis is ``diluted``, ``basic``, or
    ``unavailable``. Zero/negative EPS endpoints → unavailable (no conventional CAGR).
    """
    diluted_points: list[tuple[float | None, Any]] = []
    basic_points: list[tuple[float | None, Any]] = []
    for income, stmt in zip(incomes, stmts, strict=False):
        diluted_points.append((getattr(income, "diluted_eps", None), stmt))
        basic_points.append((getattr(income, "eps", None), stmt))

    diluted_cagr, _, _ = annual_positive_cagr(diluted_points)
    if diluted_cagr is not None:
        return diluted_cagr, "diluted"

    basic_cagr, _, _ = annual_positive_cagr(basic_points)
    if basic_cagr is not None:
        return basic_cagr, "basic"

    return None, "unavailable"


def fcf_to_earnings_ratio(
    fcf: float | None,
    net_income: float | None,
) -> float | None:
    """Point-in-time FCF / Net Income.

    Rules:
    - Both required
    - NI == 0 → unavailable
    - Negative NI → unavailable (not a conventional conversion score)
    - Negative FCF with positive NI → negative ratio (valid weak-conversion signal)
    """
    if fcf is None or net_income is None:
        return None
    try:
        fcf_f = float(fcf)
        ni_f = float(net_income)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(fcf_f) or not math.isfinite(ni_f):
        return None
    if ni_f == 0.0:
        return None
    if ni_f < 0.0:
        return None
    result = fcf_f / ni_f
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def map_fcf_to_earnings_01(ratio: float | None) -> float | None:
    """Map FCF/NI ratio to [0, 1] quality contribution (None stays None)."""
    if ratio is None:
        return None
    try:
        r = float(ratio)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(r):
        return None
    if r < 0:
        return 0.15
    if r >= 1.0:
        return min(1.0, 0.80 + min(0.20, (r - 1.0) * 0.20))
    return max(0.20, min(0.80, r * 0.80))


def ocf_to_earnings_ratio(
    ocf: float | None,
    net_income: float | None,
) -> float | None:
    """Point-in-time OCF / Net Income (accrual-bridge signal).

    Distinct from ``cash_conversion`` (FCF/OCF) and ``fcf_to_earnings`` (FCF/NI).
    NI == 0 or NI < 0 → unavailable. Negative OCF with positive NI → negative ratio.
    """
    if ocf is None or net_income is None:
        return None
    try:
        ocf_f = float(ocf)
        ni_f = float(net_income)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(ocf_f) or not math.isfinite(ni_f):
        return None
    if ni_f == 0.0:
        return None
    if ni_f < 0.0:
        return None
    result = ocf_f / ni_f
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def map_ocf_to_earnings_01(ratio: float | None) -> float | None:
    """Map OCF/NI to [0, 1] accrual-quality contribution (None stays None)."""
    # Same shape as FCF/NI mapping — both are earnings-cash conversion ratios.
    return map_fcf_to_earnings_01(ratio)


def operating_working_capital(
    accounts_receivable: float | None,
    inventory: float | None,
    accounts_payable: float | None,
) -> float | None:
    """Operating WC = AR + Inventory − AP.

    Requires all three line items. Does not substitute CA−CL or invent zeros
    for missing components (cash/debt excluded by construction).
    """
    if (
        accounts_receivable is None
        or inventory is None
        or accounts_payable is None
    ):
        return None
    try:
        ar = float(accounts_receivable)
        inv = float(inventory)
        ap = float(accounts_payable)
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(v) for v in (ar, inv, ap)):
        return None
    return ar + inv - ap


def period_change_rate(
    current: float | None,
    prior: float | None,
) -> float | None:
    """(current − prior) / |prior|. Zero/missing prior → unavailable."""
    if current is None or prior is None:
        return None
    try:
        cur = float(current)
        prev = float(prior)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(cur) or not math.isfinite(prev) or prev == 0.0:
        return None
    result = (cur - prev) / abs(prev)
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def growth_gap(
    component_growth: float | None,
    reference_growth: float | None,
) -> float | None:
    """component_growth − reference_growth when both present."""
    if component_growth is None or reference_growth is None:
        return None
    try:
        gap = float(component_growth) - float(reference_growth)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(gap):
        return None
    return gap


def days_from_turnover(turnover: float | None, *, days: float = 365.0) -> float | None:
    """Convert a turnover ratio into days outstanding. turnover ≤ 0 → None."""
    if turnover is None:
        return None
    try:
        t = float(turnover)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(t) or t <= 0.0:
        return None
    result = days / t
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def share_dilution_rate(
    incomes: Sequence[Any],
    stmts: Sequence[Any],
    *,
    share_getter: Callable[[Any], float | None] | None = None,
) -> float | None:
    """Share-count change rate over annual fiscal years.

    ``(end_shares - start_shares) / start_shares`` using ``weighted_shares``.
    Positive = net dilution; negative = net contraction.
    Zero start shares / missing history → None.
    """
    getter = share_getter or (lambda inc: getattr(inc, "weighted_shares", None))
    points: list[tuple[int, float]] = []
    for income, stmt in zip(incomes, stmts, strict=False):
        if stmt is None:
            continue
        period = getattr(stmt, "period", None)
        if period is None or period.period_type is not PeriodType.ANNUAL:
            continue
        fy = period.fiscal_year
        if fy is None:
            continue
        shares = getter(income)
        if shares is None:
            continue
        try:
            s = float(shares)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(s) or s <= 0:
            continue
        points.append((int(fy), s))
    if len(points) < 2:
        return None
    points.sort(key=lambda item: item[0])
    start_fy, start_s = points[0]
    end_fy, end_s = points[-1]
    if end_fy <= start_fy:
        return None
    if start_s <= 0:
        return None
    rate = (end_s - start_s) / start_s
    if math.isnan(rate) or math.isinf(rate):
        return None
    return rate


def dilution_discipline_01(dilution_rate: float | None) -> float | None:
    """Map share dilution rate to [0, 1] discipline (lower dilution → higher).

    ≈0% change → 0.85; +10% dilution → ~0.35; ≥+25% → near 0;
    share contraction (negative rate) → up to 1.0.
    """
    if dilution_rate is None:
        return None
    try:
        rate = float(dilution_rate)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(rate):
        return None
    # Invert: each +10pp of share growth subtracts 0.5 from a 0.85 baseline.
    score = 0.85 - (rate * 5.0)
    if rate < 0:
        # Contraction is shareholder-friendly up to a point.
        score = min(1.0, 0.85 + min(0.15, abs(rate) * 1.5))
    return max(0.0, min(1.0, score))
