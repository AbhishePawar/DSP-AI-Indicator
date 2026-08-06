"""Tax Optimization — unrealized gain/loss, holding period, loss-harvesting.

Requires caller-supplied ``cost_basis_per_unit`` and ``purchase_date`` per
position plus a current price per symbol. No cost basis, purchase date, or
price is ever fabricated — positions missing any of the three are marked
``available=False`` with an explicit ``reason_unavailable``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

from portfolio_analytics.enums import AnalyticsStatus, TaxTerm
from portfolio_analytics.models import PositionInput, TaxLotAnalysis, TaxReport

__all__ = ["compute_tax_report"]

_LONG_TERM_THRESHOLD_DAYS_DEFAULT = 365


def compute_tax_report(
    positions: Sequence[PositionInput],
    *,
    current_prices: Mapping[str, float],
    as_of: date,
    long_term_threshold_days: int = _LONG_TERM_THRESHOLD_DAYS_DEFAULT,
) -> TaxReport:
    lots: list[TaxLotAnalysis] = []
    harvesting_candidates: list[str] = []

    for position in positions:
        if position.cost_basis_per_unit is None:
            lots.append(
                TaxLotAnalysis(
                    symbol=position.symbol,
                    available=False,
                    reason_unavailable="cost_basis_per_unit not supplied.",
                )
            )
            continue
        if position.purchase_date is None:
            lots.append(
                TaxLotAnalysis(
                    symbol=position.symbol,
                    available=False,
                    reason_unavailable="purchase_date not supplied.",
                )
            )
            continue
        current_price = current_prices.get(position.symbol)
        if current_price is None:
            lots.append(
                TaxLotAnalysis(
                    symbol=position.symbol,
                    available=False,
                    reason_unavailable="current price unavailable for symbol.",
                )
            )
            continue

        cost_basis = position.cost_basis_per_unit
        gain_loss_per_unit = current_price - cost_basis
        gain_loss_pct = gain_loss_per_unit / cost_basis if cost_basis != 0 else None
        holding_period_days = (as_of - position.purchase_date).days
        term = (
            TaxTerm.LONG_TERM
            if holding_period_days >= long_term_threshold_days
            else TaxTerm.SHORT_TERM
        )
        harvesting_candidate = gain_loss_per_unit < 0
        if harvesting_candidate:
            harvesting_candidates.append(position.symbol)

        lots.append(
            TaxLotAnalysis(
                symbol=position.symbol,
                available=True,
                unrealized_gain_loss_pct=gain_loss_pct,
                unrealized_gain_loss_per_unit=gain_loss_per_unit,
                holding_period_days=holding_period_days,
                term=term,
                harvesting_candidate=harvesting_candidate,
            )
        )

    available = [lot for lot in lots if lot.available]
    if not available:
        status = AnalyticsStatus.UNAVAILABLE
    elif len(available) < len(lots):
        status = AnalyticsStatus.PARTIAL
    else:
        status = AnalyticsStatus.COMPLETE

    return TaxReport(
        status=status,
        lots=tuple(lots),
        harvesting_candidates=tuple(harvesting_candidates),
    )
