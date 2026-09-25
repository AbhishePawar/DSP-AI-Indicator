"""Figma-first public payload contract — recommendation narrative, RS-005 MoS,
and Business Quality aggregator weights are exposed (never recomputed client-side).
"""

from __future__ import annotations

from financial import FinancialStatements

from dsp_platform import CompositionRequest, PlatformOrchestrator
from dsp_platform.composition.adapters import pipeline_result_public_dict

_DOMAIN_WEIGHT_KEYS = {
    "economic_moat",
    "management_quality",
    "financial_strength",
    "earnings_quality",
    "growth_quality",
}


def _statements() -> FinancialStatements:
    return FinancialStatements.from_dict(
        {
            "period": {
                "period_type": "annual",
                "period_end": "2024-12-31",
                "fiscal_year": 2024,
                "currency": "USD",
            },
            "income_statement": {
                "revenue": 1000.0,
                "cogs": 400.0,
                "gross_profit": 600.0,
                "ebit": 300.0,
                "ebitda": 350.0,
                "interest_expense": 20.0,
                "pretax_income": 280.0,
                "tax": 70.0,
                "net_income": 210.0,
                "weighted_shares": 100.0,
                "eps": 2.1,
            },
            "balance_sheet": {
                "cash": 150.0,
                "short_term_investments": 50.0,
                "accounts_receivable": 120.0,
                "inventory": 80.0,
                "current_assets": 450.0,
                "ppe": 400.0,
                "goodwill": 50.0,
                "intangibles": 50.0,
                "total_assets": 1000.0,
                "accounts_payable": 60.0,
                "short_term_debt": 50.0,
                "current_liabilities": 200.0,
                "long_term_debt": 200.0,
                "total_liabilities": 400.0,
                "retained_earnings": 300.0,
                "equity": 600.0,
                "total_equity": 600.0,
            },
            "cash_flow": {
                "operating_cash_flow": 250.0,
                "capex": -80.0,
                "free_cash_flow": 170.0,
                "dividends_paid": -50.0,
                "share_buybacks": -30.0,
                "debt_issued": 10.0,
                "debt_repaid": -40.0,
            },
        }
    )


def _public() -> dict:
    request = CompositionRequest(
        financial_statements=_statements(),
        current_market_price=70.0,
        company="Acme",
        ticker="ACM",
    )
    result = PlatformOrchestrator(platform_version="0.7.1").execute(request)
    return pipeline_result_public_dict(result)


def test_business_quality_exposes_engine_weights_and_narrative() -> None:
    public = _public()
    bq = public["business_quality"]
    assert bq is not None
    assert bq["authority"] == "server"
    weights = bq["engine_weights"]
    assert isinstance(weights, dict)
    assert set(weights) >= _DOMAIN_WEIGHT_KEYS
    assert abs(sum(weights[k] for k in _DOMAIN_WEIGHT_KEYS) - 1.0) < 1e-6
    assert all(0.0 <= weights[k] <= 1.0 for k in _DOMAIN_WEIGHT_KEYS)
    assert isinstance(bq["strengths"], list)
    assert isinstance(bq["weaknesses"], list)
    # Score in the public dict must equal the stage summary score (no recompute).
    stage = next(
        s for s in public["stage_summaries"] if s["stage"] == "business_quality_aggregator"
    )
    assert bq["score"] == stage["score"]


def test_recommendation_summary_carries_margin_of_safety_and_factors() -> None:
    public = _public()
    rec = public["recommendation_summary"]
    assert rec is not None
    for key in ("positive_factors", "negative_factors", "risks", "key_drivers"):
        assert isinstance(rec[key], list)
        assert all(isinstance(item, str) and item for item in rec[key])
    assessment = rec["margin_of_safety_assessment"]
    if assessment is None:
        # No authenticated IV → MoS honestly absent (never fabricated).
        assert rec["margin_of_safety"] is None
        return
    assert set(assessment) >= {
        "intrinsic_value_per_share",
        "current_market_price",
        "margin_of_safety",
        "classification",
        "reasoning",
    }
    # The scalar ratio mirrors the nested assessment — one authoritative value.
    assert rec["margin_of_safety"] == assessment["margin_of_safety"]


def test_public_payload_is_deterministic_for_new_fields() -> None:
    a = _public()
    b = _public()
    assert a["business_quality"] == b["business_quality"]
    assert a["recommendation_summary"] == b["recommendation_summary"]


def test_missing_stages_stay_honest() -> None:
    """Official listing without evidence: aggregator absent → business_quality None."""
    request = CompositionRequest(
        financial_statements=_statements(),
        current_market_price=70.0,
        company="Acme Solar Holdings Limited",
        ticker="ACMESOLAR",
    )
    result = PlatformOrchestrator(platform_version="0.7.1").execute(request)
    public = pipeline_result_public_dict(result)
    if result.business_quality is None:
        assert public["business_quality"] is None
    if result.investment_recommendation is None:
        assert public["recommendation_summary"] is None
