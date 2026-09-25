"""Public fundamental metrics strip (Figma CompanyHeader / screener columns).

Figma's Company Analysis header renders Market Cap · Sector · ROE · D/E · PE;
the Institutional screener renders P/E · ROE · Rev Growth. Every value here is
either copied from an engine output already present on the ``PipelineResult``
or derived server-side from authenticated inputs with the formula recorded.

CV-001 / CV-002: any missing mandatory input yields ``None`` — never a guess.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

__all__ = ["fundamental_metrics_public"]


def _f(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Mapping):
        return _f(value.get("value"))
    if hasattr(value, "value") and not isinstance(value, (str, bytes, int, float)):
        return _f(getattr(value, "value"))
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if out != out else out


def _ratio_value(group: Any, name: str) -> float | None:
    if not group:
        return None
    for metric in group:
        if getattr(metric, "name", None) == name:
            return _f(getattr(metric, "value", None))
        if isinstance(metric, Mapping) and metric.get("name") == name:
            return _f(metric.get("value"))
    return None


def _metric(
    value: float | None,
    *,
    category: str,
    source: str,
    formula: str | None = None,
) -> dict[str, Any]:
    return {
        "value": value,
        "status": "available" if value is not None else "unavailable",
        "category": category if value is not None else "unavailable",
        "source": source,
        "formula": formula,
    }


def fundamental_metrics_public(result: Any) -> dict[str, Any]:
    trace = getattr(result, "authenticated_valuation_trace", None) or {}
    if not isinstance(trace, Mapping):
        trace = {}
    fa = getattr(result, "financial_analysis", None)
    ratios = getattr(fa, "ratios", None)
    income = getattr(fa, "income", None)

    price = _f(trace.get("current_market_price"))
    market_cap = _f(trace.get("market_cap"))
    sector = trace.get("sector")
    industry = trace.get("industry")

    roe = _ratio_value(getattr(ratios, "profitability", None), "roe")
    debt_to_equity = _ratio_value(getattr(ratios, "leverage", None), "debt_to_equity")

    revenue_growth = _f(
        getattr(getattr(income, "revenue", None), "revenue_growth", None)
    )
    if revenue_growth is None:
        revenue_growth = _f(
            getattr(getattr(income, "growth", None), "revenue_growth", None)
        )

    profitability = getattr(income, "profitability", None)
    eps = _f(getattr(profitability, "diluted_eps", None))
    eps_basis = "diluted"
    if eps is None:
        eps = _f(getattr(profitability, "eps", None))
        eps_basis = "basic"

    pe: float | None = None
    if price is not None and eps is not None and eps > 0:
        pe = price / eps

    revenue = _f(getattr(getattr(income, "revenue", None), "revenue", None))
    if revenue is None:
        revenue = _f(trace.get("revenue"))
    profit = _f(getattr(getattr(income, "profitability", None), "net_income", None))
    if profit is None:
        profit = _f(trace.get("net_income"))
    margins = getattr(income, "margins", None)
    gross_margin = _f(getattr(margins, "gross_margin", None))
    operating_margin = _f(getattr(margins, "operating_margin", None))
    net_margin = _f(getattr(margins, "net_margin", None))
    roce = _ratio_value(getattr(ratios, "profitability", None), "roce")
    if roce is None:
        roce = _ratio_value(getattr(ratios, "returns", None), "roce")
    cash = getattr(fa, "cash_flow", None)
    fcf = _f(getattr(getattr(cash, "free_cash_flow", None), "free_cash_flow", None))
    fcf_margin = _f(getattr(getattr(cash, "free_cash_flow", None), "fcf_margin", None))
    change = _f(trace.get("price_change"))
    change_percent = _f(trace.get("price_change_percent"))
    as_of = trace.get("price_as_of") or trace.get("price_retrieved_at")

    return {
        "authority": "server",
        "price": _metric(
            price, category="verified", source="authenticated_quote"
        ),
        "change": _metric(
            change, category="verified", source="authenticated_quote"
        ),
        "change_percent": _metric(
            change_percent, category="verified", source="authenticated_quote"
        ),
        "as_of": {
            "value": str(as_of) if as_of else None,
            "status": "available" if as_of else "unavailable",
            "category": "verified" if as_of else "unavailable",
            "source": "authenticated_quote",
            "formula": None,
        },
        "market_cap": _metric(
            market_cap,
            category="calculated",
            source="authenticated_valuation",
            formula="current_market_price × shares_outstanding",
        ),
        "sector": {
            "value": str(sector) if sector else None,
            "status": "available" if sector else "unavailable",
            "category": "verified" if sector else "unavailable",
            "source": "identity_resolution",
            "formula": None,
        },
        "industry": {
            "value": str(industry) if industry else None,
            "status": "available" if industry else "unavailable",
            "category": "verified" if industry else "unavailable",
            "source": "identity_resolution",
            "formula": None,
        },
        "revenue": _metric(
            revenue, category="verified", source="authenticated_statements"
        ),
        "profit": _metric(
            profit, category="verified", source="authenticated_statements"
        ),
        "gross_margin": _metric(
            gross_margin,
            category="calculated",
            source="income_statement_intelligence",
            formula="gross_profit ÷ revenue",
        ),
        "operating_margin": _metric(
            operating_margin,
            category="calculated",
            source="income_statement_intelligence",
            formula="operating_income ÷ revenue",
        ),
        "net_margin": _metric(
            net_margin,
            category="calculated",
            source="income_statement_intelligence",
            formula="net_income ÷ revenue",
        ),
        "roe": _metric(
            roe,
            category="calculated",
            source="financial_ratio_engine",
            formula="net_income ÷ average_total_equity",
        ),
        "roce": _metric(
            roce,
            category="calculated",
            source="financial_ratio_engine",
            formula="EBIT ÷ capital_employed",
        ),
        "debt_to_equity": _metric(
            debt_to_equity,
            category="calculated",
            source="financial_ratio_engine",
            formula="total_debt ÷ total_equity",
        ),
        "revenue_growth": _metric(
            revenue_growth,
            category="calculated",
            source="income_statement_intelligence",
            formula="revenue_t ÷ revenue_t-1 − 1",
        ),
        "eps": _metric(
            eps,
            category="verified",
            source=f"income_statement_intelligence ({eps_basis})",
        ),
        "pe": _metric(
            pe,
            category="calculated",
            source="server_derived",
            formula=f"current_market_price ÷ eps_{eps_basis}",
        ),
        "fcf": _metric(
            fcf, category="verified", source="cash_flow_intelligence"
        ),
        "fcf_margin": _metric(
            fcf_margin,
            category="calculated",
            source="cash_flow_intelligence",
            formula="free_cash_flow ÷ revenue",
        ),
    }
