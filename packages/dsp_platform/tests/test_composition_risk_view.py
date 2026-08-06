"""Unit tests for the composition-time Risk stage (structural mapping only)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from dsp_platform.composition.risk_view import (
    CompanyRiskView,
    build_company_risk_view,
)


@dataclass
class _FakeFinancialStrength:
    overall_strength_rating: object
    risks: tuple[str, ...] = ()


@dataclass
class _FakeRating:
    value: str


@dataclass
class _FakeEconomicMoat:
    overall_moat_rating: object
    risks: tuple[str, ...] = ()


def test_build_company_risk_view_both_inputs_available() -> None:
    fs = _FakeFinancialStrength(
        overall_strength_rating=_FakeRating("weak"),
        risks=("High leverage",),
    )
    moat = _FakeEconomicMoat(
        overall_moat_rating=_FakeRating("narrow"),
        risks=("Rising competitive intensity",),
    )
    view = build_company_risk_view(financial_strength=fs, economic_moat=moat)

    assert isinstance(view, CompanyRiskView)
    assert view.financial_risk.available is True
    assert view.financial_risk.level == "elevated"
    assert view.financial_risk.source_stage == "financial_strength"
    assert view.financial_risk.evidence == ("High leverage",)

    assert view.business_risk.available is True
    assert view.business_risk.level == "moderate"
    assert view.business_risk.source_stage == "economic_moat"

    # Worst of {elevated, moderate} is elevated.
    assert view.overall_risk_level == "elevated"
    assert view.categories_available == 2
    assert view.categories_total == 6


def test_build_company_risk_view_missing_moat_degrades_gracefully() -> None:
    fs = _FakeFinancialStrength(overall_strength_rating=_FakeRating("strong"))
    view = build_company_risk_view(financial_strength=fs, economic_moat=None)

    assert view.financial_risk.available is True
    assert view.financial_risk.level == "low"
    assert view.business_risk.available is False
    assert view.business_risk.message is not None
    assert view.overall_risk_level == "low"
    assert view.categories_available == 1


def test_unavailable_categories_are_honest_not_fabricated() -> None:
    view = build_company_risk_view(financial_strength=None, economic_moat=None)

    for category in (
        view.regulatory_risk,
        view.technology_risk,
        view.currency_risk,
        view.customer_concentration_risk,
        view.business_risk,
        view.financial_risk,
    ):
        assert category.available is False
        assert category.level is None
        assert category.message == "Data unavailable — no data source connected."
    assert view.overall_risk_level is None
    assert view.categories_available == 0


@pytest.mark.parametrize(
    ("rating_value", "expected_level"),
    [
        ("very_weak", "high"),
        ("weak", "elevated"),
        ("average", "moderate"),
        ("strong", "low"),
        ("exceptional", "very_low"),
    ],
)
def test_financial_strength_rating_to_risk_level_mapping(
    rating_value: str, expected_level: str
) -> None:
    fs = _FakeFinancialStrength(overall_strength_rating=_FakeRating(rating_value))
    view = build_company_risk_view(financial_strength=fs, economic_moat=None)
    assert view.financial_risk.level == expected_level


@pytest.mark.parametrize(
    ("rating_value", "expected_level"),
    [
        ("no_moat", "high"),
        ("weak", "elevated"),
        ("narrow", "moderate"),
        ("strong", "low"),
        ("wide", "very_low"),
    ],
)
def test_moat_rating_to_business_risk_level_mapping(
    rating_value: str, expected_level: str
) -> None:
    fs = _FakeFinancialStrength(overall_strength_rating=_FakeRating("average"))
    moat = _FakeEconomicMoat(overall_moat_rating=_FakeRating(rating_value))
    view = build_company_risk_view(financial_strength=fs, economic_moat=moat)
    assert view.business_risk.level == expected_level


def test_to_dict_round_trips_all_categories() -> None:
    fs = _FakeFinancialStrength(overall_strength_rating=_FakeRating("average"))
    view = build_company_risk_view(financial_strength=fs, economic_moat=None)
    payload = view.to_dict()
    for key in (
        "business_risk",
        "financial_risk",
        "regulatory_risk",
        "technology_risk",
        "currency_risk",
        "customer_concentration_risk",
        "overall_risk_level",
        "categories_available",
        "categories_total",
        "limitations",
    ):
        assert key in payload


def test_label_score_confidence_aliases_for_generic_stage_summary() -> None:
    fs = _FakeFinancialStrength(overall_strength_rating=_FakeRating("average"))
    view = build_company_risk_view(financial_strength=fs, economic_moat=None)
    assert view.label == view.overall_risk_level
    assert view.score is None
    assert view.confidence is None
