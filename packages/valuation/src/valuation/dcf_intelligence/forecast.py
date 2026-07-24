"""Free cash flow forecast — historical support + explicit FCFF projection."""

from __future__ import annotations

from dataclasses import dataclass

from valuation.dcf_intelligence.assumptions import DcfForecastAssumptions
from valuation.dcf_intelligence.explain import ExplainedValue

__all__ = ["ForecastLine", "ForecastResult", "build_fcff_forecast"]


@dataclass(frozen=True, slots=True)
class ForecastLine:
    """One explicit forecast year."""

    year: int
    revenue: float
    ebit: float
    nopat: float
    depreciation: float
    capex: float
    delta_nwc: float
    fcff: float
    explained: ExplainedValue


@dataclass(frozen=True, slots=True)
class ForecastResult:
    """Full explicit-period forecast with historical context."""

    lines: tuple[ForecastLine, ...]
    historical_fcf: tuple[tuple[str, float], ...]
    historical_fcf_explained: ExplainedValue
    last_fcff: float
    last_ebitda: float


def build_fcff_forecast(assumptions: DcfForecastAssumptions) -> ForecastResult:
    """Build deterministic FCFF forecast.

    ``FCFF = EBIT(1−t) + D&A − CapEx − ΔNWC``
    """
    hist = tuple((p.period, p.fcf) for p in assumptions.historical_fcf)
    hist_vals = [p.fcf for p in assumptions.historical_fcf]
    hist_mean = (
        sum(hist_vals) / len(hist_vals) if hist_vals else None
    )
    historical_explained = ExplainedValue(
        name="historical_fcf",
        value=hist_mean,
        formula="historical_fcf_mean = mean(historical FCF observations)",
        inputs={"observations": len(hist_vals)},
        intermediates={
            "sum": sum(hist_vals) if hist_vals else None,
            "count": len(hist_vals),
        },
        confidence="medium" if hist_vals else "insufficient",
        notes=(
            "Historical FCF is contextual support only; explicit forecast "
            "uses revenue/margin/reinvestment drivers."
            if hist_vals
            else "No historical FCF provided."
        ),
    )

    lines: list[ForecastLine] = []
    prev_revenue = assumptions.base_revenue
    last_fcff = 0.0
    last_ebitda = 0.0

    for year in range(1, assumptions.forecast_years + 1):
        revenue = prev_revenue * (1.0 + assumptions.revenue_growth)
        ebit = revenue * assumptions.operating_margin
        nopat = ebit * (1.0 - assumptions.tax_rate)
        depreciation = revenue * assumptions.depreciation_pct_of_revenue
        capex = revenue * assumptions.capex_pct_of_revenue
        delta_nwc = (revenue - prev_revenue) * assumptions.nwc_pct_of_revenue
        fcff = nopat + depreciation - capex - delta_nwc
        ebitda = ebit + depreciation

        explained = ExplainedValue(
            name=f"fcff_year_{year}",
            value=fcff,
            formula="FCFF = EBIT(1−t) + D&A − CapEx − ΔNWC",
            inputs={
                "revenue": revenue,
                "operating_margin": assumptions.operating_margin,
                "tax_rate": assumptions.tax_rate,
                "depreciation_pct_of_revenue": assumptions.depreciation_pct_of_revenue,
                "capex_pct_of_revenue": assumptions.capex_pct_of_revenue,
                "nwc_pct_of_revenue": assumptions.nwc_pct_of_revenue,
                "prior_revenue": prev_revenue,
            },
            intermediates={
                "ebit": ebit,
                "nopat": nopat,
                "depreciation": depreciation,
                "capex": capex,
                "delta_nwc": delta_nwc,
            },
            confidence="high",
        )
        lines.append(
            ForecastLine(
                year=year,
                revenue=revenue,
                ebit=ebit,
                nopat=nopat,
                depreciation=depreciation,
                capex=capex,
                delta_nwc=delta_nwc,
                fcff=fcff,
                explained=explained,
            )
        )
        prev_revenue = revenue
        last_fcff = fcff
        last_ebitda = ebitda

    return ForecastResult(
        lines=tuple(lines),
        historical_fcf=hist,
        historical_fcf_explained=historical_explained,
        last_fcff=last_fcff,
        last_ebitda=last_ebitda,
    )
