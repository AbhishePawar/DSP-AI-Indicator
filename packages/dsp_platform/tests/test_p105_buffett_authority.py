"""P1-05 — server Buffett authority surface + missing-data honesty."""

from __future__ import annotations

from financial import FinancialEngine, FinancialStatements
from investment_recommendation import ValuationSignals

from dsp_platform import CompositionRequest, PlatformOrchestrator
from dsp_platform.composition.adapters import pipeline_result_public_dict


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


def test_buffett_authority_from_valid_server_bundle() -> None:
    request = CompositionRequest(
        financial_statements=_statements(),
        current_market_price=70.0,
        company="Acme",
        ticker="ACM",
    )
    result = PlatformOrchestrator(platform_version="0.7.1").execute(request)
    public = pipeline_result_public_dict(result)
    authority = public["buffett_authority"]
    assert authority["authority"] == "server"
    assert authority["overall_score"] is not None
    assert authority["factors"]["economic_moat"]["available"] is True
    assert authority["factors"]["management_quality"]["available"] is True
    assert authority["factors"]["business_quality"]["available"] is True
    assert authority["recommendation"] is not None
    assert authority["buffett_reviewer"] is not None


def test_forged_client_valuation_signals_do_not_set_buffett_recommendation() -> None:
    """P0-02 + P1-05 — client IV cannot drive Buffett / recommendation outcomes."""
    forged_iv = 999.0
    request = CompositionRequest(
        financial_statements=_statements(),
        valuation_signals=ValuationSignals(
            intrinsic_value_per_share=forged_iv,
            current_market_price=70.0,
            margin_of_safety=0.95,
            confidence=0.99,
        ),
        company="Acme",
        ticker="ACM",
    )
    result = PlatformOrchestrator(platform_version="0.7.1").execute(request)
    public = pipeline_result_public_dict(result)
    authority = public["buffett_authority"]
    assert authority["client_overrides_accepted"] is False
    signals = result.valuation
    iv = getattr(signals, "intrinsic_value_per_share", None)
    assert iv != forged_iv


def test_determinism_buffett_authority() -> None:
    request = CompositionRequest(
        financial_analysis=FinancialEngine().analyze_financials(_statements()),
        current_market_price=70.0,
        company="Acme",
        ticker="ACM",
    )
    orch = PlatformOrchestrator(platform_version="0.7.1")
    a = pipeline_result_public_dict(orch.execute(request))["buffett_authority"]
    b = pipeline_result_public_dict(orch.execute(request))["buffett_authority"]
    assert a == b


def test_unavailable_valuation_factor_is_honest_when_price_only() -> None:
    """Without authenticated IV, valuation stage may degrade — not fabricate IV score."""
    request = CompositionRequest(
        financial_statements=_statements(),
        current_market_price=70.0,
        company="Acme",
        ticker="ACM",
    )
    result = PlatformOrchestrator(platform_version="0.7.1").execute(request)
    public = pipeline_result_public_dict(result)
    valuation = public["buffett_authority"]["factors"]["valuation"]
    # Price-only degraded path still reports a stage score/status honestly.
    assert valuation["status"] in {"succeeded", "degraded", "unavailable"}
    if valuation["status"] == "unavailable":
        assert valuation["score"] is None
        assert valuation["available"] is False
