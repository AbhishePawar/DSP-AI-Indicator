"""Composition-time Risk stage — structural aggregation only (EPIC-001 add-on).

No new risk-scoring algorithm lives here. This module organizes narrative
``risks`` evidence and ordinal ratings *already computed* by the
``financial_strength`` and ``economic_moat`` engines into the institutional
risk taxonomy (business / financial / regulatory / technology / currency /
customer concentration). Categories with no underlying computed source in
the platform are reported as unavailable rather than fabricated.

Rating -> risk-level is a fixed, documented, one-to-one presentation mapping
(the inverse of an already-computed ordinal rating) — not a new quantitative
or qualitative scoring formula.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "CompanyRiskView",
    "RiskCategoryView",
    "build_company_risk_view",
]

# Ordinal severity used only to pick the single worst *available* category
# label for ``overall_risk_level`` — a structural max(), not a new score.
_LEVEL_SEVERITY = {
    "very_low": 0,
    "low": 1,
    "moderate": 2,
    "elevated": 3,
    "high": 4,
}

# FinancialStrengthRating.value -> risk level (weaker balance sheet == higher
# financial risk). Fixed presentation mapping of an existing rating.
_FINANCIAL_STRENGTH_TO_RISK = {
    "very_weak": "high",
    "weak": "elevated",
    "average": "moderate",
    "strong": "low",
    "exceptional": "very_low",
}

# MoatRating.value -> business risk level (weaker competitive protection ==
# higher exposure to competitive/business risk). Fixed presentation mapping.
_MOAT_TO_BUSINESS_RISK = {
    "no_moat": "high",
    "weak": "elevated",
    "narrow": "moderate",
    "strong": "low",
    "wide": "very_low",
}

_UNAVAILABLE_MESSAGE = "Data unavailable — no data source connected."


@dataclass(frozen=True, slots=True)
class RiskCategoryView:
    """One institutional risk category — real data or an honest gap."""

    category: str
    available: bool
    level: str | None = None
    source_stage: str | None = None
    source_rating: str | None = None
    evidence: tuple[str, ...] = ()
    message: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "available": self.available,
            "level": self.level,
            "source_stage": self.source_stage,
            "source_rating": self.source_rating,
            "evidence": list(self.evidence),
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class CompanyRiskView:
    """Single-company Risk section — aggregates existing engine outputs only.

    ``score``/``label``/``confidence`` mirror the shape other pipeline stage
    payloads expose (see ``composition.adapters._stage_summary``) so this
    stage renders consistently in ``stage_summaries`` without bespoke code.
    """

    business_risk: RiskCategoryView
    financial_risk: RiskCategoryView
    regulatory_risk: RiskCategoryView
    technology_risk: RiskCategoryView
    currency_risk: RiskCategoryView
    customer_concentration_risk: RiskCategoryView
    overall_risk_level: str | None
    categories_available: int
    categories_total: int
    limitations: tuple[str, ...] = (
        "Structural aggregation of existing financial_strength / economic_moat "
        "ratings only — no new risk-scoring algorithm.",
        "Regulatory, technology, currency, and customer-concentration risk "
        "have no connected data source and are reported as unavailable.",
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "limitations", tuple(self.limitations))

    @property
    def label(self) -> str | None:
        """Alias so generic stage-summary readers (``getattr(x, 'label')``) work."""
        return self.overall_risk_level

    @property
    def score(self) -> None:
        """No composite numeric score is fabricated for this stage."""
        return None

    @property
    def confidence(self) -> None:
        """No composite confidence is fabricated for this stage."""
        return None

    @property
    def categories(self) -> tuple[RiskCategoryView, ...]:
        return (
            self.business_risk,
            self.financial_risk,
            self.regulatory_risk,
            self.technology_risk,
            self.currency_risk,
            self.customer_concentration_risk,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "business_risk": self.business_risk.to_dict(),
            "financial_risk": self.financial_risk.to_dict(),
            "regulatory_risk": self.regulatory_risk.to_dict(),
            "technology_risk": self.technology_risk.to_dict(),
            "currency_risk": self.currency_risk.to_dict(),
            "customer_concentration_risk": self.customer_concentration_risk.to_dict(),
            "overall_risk_level": self.overall_risk_level,
            "categories_available": self.categories_available,
            "categories_total": self.categories_total,
            "limitations": list(self.limitations),
        }


def _unavailable(category: str) -> RiskCategoryView:
    return RiskCategoryView(
        category=category,
        available=False,
        message=_UNAVAILABLE_MESSAGE,
    )


def _financial_risk_category(financial_strength: object | None) -> RiskCategoryView:
    if financial_strength is None:
        return _unavailable("financial_risk")
    rating = getattr(financial_strength, "overall_strength_rating", None)
    rating_value = getattr(rating, "value", None)
    level = _FINANCIAL_STRENGTH_TO_RISK.get(rating_value) if rating_value else None
    evidence = tuple(getattr(financial_strength, "risks", ()) or ())
    if level is None:
        return RiskCategoryView(
            category="financial_risk",
            available=False,
            source_stage="financial_strength",
            evidence=evidence,
            message=(
                "Financial risk level unavailable — financial_strength stage "
                "returned no overall rating."
            ),
        )
    return RiskCategoryView(
        category="financial_risk",
        available=True,
        level=level,
        source_stage="financial_strength",
        source_rating=rating_value,
        evidence=evidence,
    )


def _business_risk_category(economic_moat: object | None) -> RiskCategoryView:
    if economic_moat is None:
        return _unavailable("business_risk")
    rating = getattr(economic_moat, "overall_moat_rating", None)
    rating_value = getattr(rating, "value", None)
    level = _MOAT_TO_BUSINESS_RISK.get(rating_value) if rating_value else None
    evidence = tuple(getattr(economic_moat, "risks", ()) or ())
    if level is None:
        return RiskCategoryView(
            category="business_risk",
            available=False,
            source_stage="economic_moat",
            evidence=evidence,
            message=(
                "Business risk level unavailable — economic_moat stage "
                "returned no overall moat rating."
            ),
        )
    return RiskCategoryView(
        category="business_risk",
        available=True,
        level=level,
        source_stage="economic_moat",
        source_rating=rating_value,
        evidence=evidence,
    )


def build_company_risk_view(
    *,
    financial_strength: object | None,
    economic_moat: object | None,
) -> CompanyRiskView:
    """Aggregate already-computed engine ratings into the Risk section.

    Args:
        financial_strength: Output of ``financial_strength.FinancialStrengthEngine``
            (or ``None`` when unavailable).
        economic_moat: Output of ``economic_moat.EconomicEngine`` (or ``None``).

    Returns:
        A :class:`CompanyRiskView` — never raises for missing inputs; absent
        categories are marked ``available=False`` with an honest message.
    """
    financial_risk = _financial_risk_category(financial_strength)
    business_risk = _business_risk_category(economic_moat)
    regulatory_risk = _unavailable("regulatory_risk")
    technology_risk = _unavailable("technology_risk")
    currency_risk = _unavailable("currency_risk")
    customer_concentration_risk = _unavailable("customer_concentration_risk")

    categories = (
        business_risk,
        financial_risk,
        regulatory_risk,
        technology_risk,
        currency_risk,
        customer_concentration_risk,
    )
    available_levels = [c.level for c in categories if c.available and c.level]
    overall_risk_level = None
    if available_levels:
        overall_risk_level = max(
            available_levels, key=lambda lvl: _LEVEL_SEVERITY.get(lvl, -1)
        )

    return CompanyRiskView(
        business_risk=business_risk,
        financial_risk=financial_risk,
        regulatory_risk=regulatory_risk,
        technology_risk=technology_risk,
        currency_risk=currency_risk,
        customer_concentration_risk=customer_concentration_risk,
        overall_risk_level=overall_risk_level,
        categories_available=sum(1 for c in categories if c.available),
        categories_total=len(categories),
    )
