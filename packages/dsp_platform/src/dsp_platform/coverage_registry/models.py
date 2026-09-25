"""Coverage registry records (Figma Institutional / Dashboard / Directory).

A ``CoverageRecord`` is an append-only, server-authored row written after each
successful ``/analyse``. It copies public payload fields (never recomputes
scores) so coverage-wide views (screener, rating distribution, coverage
growth, signals, watchlist ratings, recent research) can be served without
re-running engines or provider calls.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "RATING_SCALE",
    "CoverageRecord",
    "letter_rating",
]

# Institutional rating scale — identical thresholds to the ARCH-002 frontend
# scale so the browser never has to derive a grade itself.
RATING_SCALE: tuple[tuple[float, str], ...] = (
    (90.0, "A+"),
    (80.0, "A"),
    (70.0, "B+"),
    (60.0, "B"),
    (50.0, "C"),
    (40.0, "D"),
)


def letter_rating(score: float | None) -> str | None:
    """Map a 0–100 business-quality score to the institutional letter grade."""
    if score is None:
        return None
    try:
        value = float(score)
    except (TypeError, ValueError):
        return None
    if value != value:  # NaN
        return None
    for threshold, grade in RATING_SCALE:
        if value >= threshold:
            return grade
    return "F"


@dataclass(frozen=True, slots=True)
class CoverageRecord:
    record_id: str
    symbol: str
    exchange: str | None
    company_name: str | None
    sector: str | None
    industry: str | None
    as_of: str
    business_quality_score: float | None
    rating: str | None
    recommendation: str | None
    price: float | None
    market_cap: float | None
    pe: float | None
    roe: float | None
    debt_to_equity: float | None
    revenue_growth: float | None
    intrinsic_value: float | None
    margin_of_safety: float | None
    risk_score: float | None
    roce: float | None = None
    fcf: float | None = None
    research_id: str | None = None
    owner_user_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "company_name": self.company_name,
            "sector": self.sector,
            "industry": self.industry,
            "as_of": self.as_of,
            "business_quality_score": self.business_quality_score,
            "rating": self.rating,
            "recommendation": self.recommendation,
            "price": self.price,
            "market_cap": self.market_cap,
            "pe": self.pe,
            "roe": self.roe,
            "roce": self.roce,
            "debt_to_equity": self.debt_to_equity,
            "revenue_growth": self.revenue_growth,
            "fcf": self.fcf,
            "intrinsic_value": self.intrinsic_value,
            "margin_of_safety": self.margin_of_safety,
            "risk_score": self.risk_score,
            "research_id": self.research_id,
            "owner_user_id": self.owner_user_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> CoverageRecord:
        def f(key: str) -> float | None:
            v = raw.get(key)
            if v is None or isinstance(v, bool):
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        def s(key: str) -> str | None:
            v = raw.get(key)
            return str(v) if v is not None and str(v).strip() else None

        return cls(
            record_id=str(raw.get("record_id")),
            symbol=str(raw.get("symbol") or "").upper(),
            exchange=s("exchange"),
            company_name=s("company_name"),
            sector=s("sector"),
            industry=s("industry"),
            as_of=str(raw.get("as_of") or ""),
            business_quality_score=f("business_quality_score"),
            rating=s("rating"),
            recommendation=s("recommendation"),
            price=f("price"),
            market_cap=f("market_cap"),
            pe=f("pe"),
            roe=f("roe"),
            roce=f("roce"),
            debt_to_equity=f("debt_to_equity"),
            revenue_growth=f("revenue_growth"),
            fcf=f("fcf"),
            intrinsic_value=f("intrinsic_value"),
            margin_of_safety=f("margin_of_safety"),
            risk_score=f("risk_score"),
            research_id=s("research_id"),
            owner_user_id=s("owner_user_id"),
            metadata=dict(raw.get("metadata") or {}),
        )
