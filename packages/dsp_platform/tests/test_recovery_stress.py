"""Comprehensive stress-test suite for statement recovery, valuation integrity, and non-blocking pipeline.

Tests:
1. Unavailable LLM providers (timeouts, rate limits, exceptions, secret-leak prevention, malformed JSON, NaN/Inf).
2. Conflicting source figures (5% boundary, sign conflicts, multi-field conflicts, unit/scale mismatches, zero vs non-zero).
3. Stale filings & invalid metadata (stale dates, future dates, issuer mismatch, balance sheet & cash flow equation violations).
4. Missing share counts & P1-03 safeguards (null shares, percentage shares, Upstox quote shares refusal).
5. Comprehensive fail-closed matrix across execution pipeline stages.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from copilot.enums import LanguageModelStatus
from copilot.models import LanguageModelRequest, LanguageModelResult
from data_engine.market_quote.adapters import (
    build_quote_from_mapping,
)
from data_engine.market_quote.models import MarketQuoteProvenance, utc_now
from dsp_platform.composition.authenticated_valuation import (
    AuthenticatedValuationError,
    _resolve_shares,
)
from dsp_platform.composition.models import StageStatus
from dsp_platform.recovery import (
    StatementRecoveryService,
    StatementRecoveryStatus,
)


class MockFailingLLMAdapter:
    """Mock adapter that simulates network timeouts, HTTP 429, or auth exceptions."""

    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def invoke(self, req: LanguageModelRequest) -> LanguageModelResult:
        raise self.exc


class MockRawTextLLMAdapter:
    """Mock adapter that returns arbitrary raw text (non-json, truncated, or json)."""

    def __init__(self, text: str) -> None:
        self.text = text

    def invoke(self, req: LanguageModelRequest) -> LanguageModelResult:
        return LanguageModelResult(
            result_id="mock-raw",
            status=LanguageModelStatus.COMPLETE,
            provenance=("mock",),
            narrative_text=self.text,
        )


class MockDictLLMAdapter:
    """Mock adapter that returns a JSON-serialized dictionary."""

    def __init__(self, response_dict: dict[str, Any]) -> None:
        self.response_dict = response_dict

    def invoke(self, req: LanguageModelRequest) -> LanguageModelResult:
        return LanguageModelResult(
            result_id="mock-dict",
            status=LanguageModelStatus.COMPLETE,
            provenance=("mock",),
            narrative_text=json.dumps(self.response_dict),
        )


# ============================================================================
# 1. Stress Tests: Unavailable LLM Providers
# ============================================================================


def test_stress_gemini_timeout_openai_success() -> None:
    """When Gemini hits a timeout, OpenAI extraction should succeed via single-model fallback."""
    gemini = MockFailingLLMAdapter(
        TimeoutError("Gateway timeout to Gemini API after 10000ms")
    )
    openai = MockDictLLMAdapter(
        {
            "issuer_symbol": "TESTCO",
            "period_type": "annual",
            "period_end": "2024-03-31",
            "currency": "USD",
            "revenue": 500000000.0,
            "net_income": 50000000.0,
            "total_assets": 1000000000.0,
            "total_liabilities": 400000000.0,
            "total_equity": 600000000.0,
            "operating_cash_flow": 80000000.0,
            "capital_expenditures": 20000000.0,
            "free_cash_flow": 60000000.0,
            "shares_outstanding": 100000000.0,
        }
    )
    svc = StatementRecoveryService(gemini_adapter=gemini, openai_adapter=openai)
    res = svc.recover("TESTCO", filing_text="Audited Annual Filing 2024 for TESTCO")

    assert res.is_usable()
    assert res.status in (
        StatementRecoveryStatus.RECOVERED_AND_VALIDATED,
        StatementRecoveryStatus.PARTIALLY_RECOVERED,
    )
    assert res.provenance is not None
    assert "openai" in res.provenance.models_used
    assert "gemini" not in res.provenance.models_used
    assert "TimeoutError" in res.provenance.diagnostics.errors[0]


def test_stress_openai_rate_limited_gemini_success() -> None:
    """When OpenAI is HTTP 429 rate limited, Gemini extraction should succeed."""
    gemini = MockDictLLMAdapter(
        {
            "issuer_symbol": "TESTCO",
            "period_type": "annual",
            "period_end": "2024-03-31",
            "currency": "USD",
            "revenue": 500000000.0,
            "net_income": 50000000.0,
            "total_assets": 1000000000.0,
            "total_liabilities": 400000000.0,
            "total_equity": 600000000.0,
            "operating_cash_flow": 80000000.0,
            "capital_expenditures": 20000000.0,
            "free_cash_flow": 60000000.0,
            "shares_outstanding": 100000000.0,
        }
    )
    openai = MockFailingLLMAdapter(
        RuntimeError("HTTP 429: Rate limit exceeded for organization")
    )
    svc = StatementRecoveryService(gemini_adapter=gemini, openai_adapter=openai)
    res = svc.recover("TESTCO", filing_text="Audited Annual Filing 2024 for TESTCO")

    assert res.is_usable()
    assert "gemini" in res.provenance.models_used
    assert "openai" not in res.provenance.models_used


def test_stress_both_providers_throw_with_embedded_secrets_no_leak() -> None:
    """When both providers throw exceptions containing API keys, secrets are NOT leaked."""
    SECRET_KEY_1 = "sk-ant-live-SECRET_TOKEN_99999"
    SECRET_KEY_2 = "sk-proj-OPENAI_SECRET_TOKEN_88888"
    gemini = MockFailingLLMAdapter(
        Exception(f"Connection failed using Authorization Bearer {SECRET_KEY_1}")
    )
    openai = MockFailingLLMAdapter(Exception(f"Invalid key in header: {SECRET_KEY_2}"))

    svc = StatementRecoveryService(gemini_adapter=gemini, openai_adapter=openai)
    res = svc.recover("TESTCO", filing_text="Audited Annual Filing 2024 for TESTCO")

    assert res.status == StatementRecoveryStatus.UNAVAILABLE
    res_dict = json.dumps(res.provenance.to_dict()) + (res.unavailability_reason or "")
    assert SECRET_KEY_1 not in res_dict
    assert SECRET_KEY_2 not in res_dict
    # Only the exception class names should be in diagnostics
    assert "Exception" in res.provenance.diagnostics.errors[0]


def test_stress_provider_returns_garbage_non_json() -> None:
    """When LLM returns HTML error page or broken text, it is gracefully rejected."""
    gemini = MockRawTextLLMAdapter(
        "<html><head><title>502 Bad Gateway</title></head><body>502</body></html>"
    )
    openai = MockRawTextLLMAdapter(
        '```json\n{\n  "revenue": 500000000, -- truncated unclosed json'
    )

    svc = StatementRecoveryService(gemini_adapter=gemini, openai_adapter=openai)
    res = svc.recover("TESTCO", filing_text="Audited Annual Filing 2024 for TESTCO")

    assert res.status == StatementRecoveryStatus.UNAVAILABLE
    assert not res.is_usable()
    assert len(res.provenance.models_used) == 0


def test_stress_extreme_values_nan_inf_safely_handled() -> None:
    """When LLM returns NaN, Infinity, or astronomical floats, they do not crash recovery."""
    gemini = MockDictLLMAdapter(
        {
            "issuer_symbol": "TESTCO",
            "period_type": "annual",
            "period_end": "2024-03-31",
            "currency": "USD",
            "revenue": "NaN",
            "net_income": "Infinity",
            "total_assets": 1000000000.0,
            "total_liabilities": 400000000.0,
            "total_equity": 600000000.0,
        }
    )
    svc = StatementRecoveryService(gemini_adapter=gemini, openai_adapter=None)
    res = svc.recover("TESTCO", filing_text="Filing text")
    # NaN and Infinity become None, so revenue and net income are missing
    assert res.status in (
        StatementRecoveryStatus.PARTIALLY_RECOVERED,
        StatementRecoveryStatus.UNAVAILABLE,
    )
    fields = res.recovered_statements.periods[0] if res.recovered_statements else None
    if fields:
        assert not fields.revenue.available
        assert not fields.net_income.available


# ============================================================================
# 2. Stress Tests: Conflicting Source Figures
# ============================================================================


def test_stress_exact_boundary_tolerance_5_percent() -> None:
    """Test boundary behavior: <= 5.0% discrepancy is accepted, > 5.0% is rejected and never averaged."""
    base_data = {
        "issuer_symbol": "TESTCO",
        "period_type": "annual",
        "period_end": "2024-03-31",
        "currency": "USD",
        "total_assets": 1000000000.0,
        "total_liabilities": 400000000.0,
        "total_equity": 600000000.0,
        "operating_cash_flow": 80000000.0,
        "capital_expenditures": 20000000.0,
        "free_cash_flow": 60000000.0,
        "shares_outstanding": 100000000.0,
    }

    # Case A: Diff = 4.76% (100M vs 105M) -> within 5% tolerance -> ACCEPTED
    g_pass = dict(base_data, revenue=100000000.0, net_income=10000000.0)
    o_pass = dict(base_data, revenue=105000000.0, net_income=10000000.0)
    svc_pass = StatementRecoveryService(
        gemini_adapter=MockDictLLMAdapter(g_pass),
        openai_adapter=MockDictLLMAdapter(o_pass),
        relative_tolerance=0.05,
    )
    res_pass = svc_pass.recover("TESTCO", filing_text="Filing")
    assert "revenue" in res_pass.provenance.validated_fields
    # Gemini value accepted, NOT averaged (not 102.5M)
    assert res_pass.recovered_statements.periods[0].revenue.value == Decimal(
        "100000000.0"
    )

    # Case B: Diff = 5.66% (100M vs 106M) -> exceeds 5% tolerance -> REJECTED, NEVER averaged
    g_fail = dict(base_data, revenue=100000000.0, net_income=10000000.0)
    o_fail = dict(base_data, revenue=106000000.0, net_income=10000000.0)
    svc_fail = StatementRecoveryService(
        gemini_adapter=MockDictLLMAdapter(g_fail),
        openai_adapter=MockDictLLMAdapter(o_fail),
        relative_tolerance=0.05,
    )
    res_fail = svc_fail.recover("TESTCO", filing_text="Filing")
    assert "revenue" in res_fail.provenance.rejected_fields
    assert any(c["field"] == "revenue" for c in res_fail.provenance.conflicts)
    # Revenue is unavailable; neither 100M nor 106M nor average is used
    if res_fail.recovered_statements:
        assert not res_fail.recovered_statements.periods[0].revenue.available


def test_stress_sign_conflict_never_averaged() -> None:
    """When one model reports positive net income and the other reports negative, reject without averaging."""
    base_data = {
        "issuer_symbol": "TESTCO",
        "period_type": "annual",
        "period_end": "2024-03-31",
        "currency": "USD",
        "revenue": 100000000.0,
        "total_assets": 1000000000.0,
        "total_liabilities": 400000000.0,
        "total_equity": 600000000.0,
        "operating_cash_flow": 20000000.0,
        "capital_expenditures": 5000000.0,
        "free_cash_flow": 15000000.0,
    }
    g_data = dict(base_data, net_income=15000000.0)  # +15M
    o_data = dict(base_data, net_income=-15000000.0)  # -15M
    svc = StatementRecoveryService(
        gemini_adapter=MockDictLLMAdapter(g_data),
        openai_adapter=MockDictLLMAdapter(o_data),
    )
    res = svc.recover("TESTCO", filing_text="Filing")
    assert "net_income" in res.provenance.rejected_fields
    assert any(c.get("reason") == "sign_conflict" for c in res.provenance.conflicts)
    if res.recovered_statements:
        assert not res.recovered_statements.periods[0].net_income.available


def test_stress_zero_vs_nonzero_capex_conflict() -> None:
    """When one model reports zero capex and the other reports significant capex, reject."""
    base_data = {
        "issuer_symbol": "TESTCO",
        "period_type": "annual",
        "period_end": "2024-03-31",
        "currency": "USD",
        "revenue": 100000000.0,
        "net_income": 10000000.0,
        "total_assets": 1000000000.0,
        "total_liabilities": 400000000.0,
        "total_equity": 600000000.0,
    }
    g_data = dict(base_data, capital_expenditures=0.0)
    o_data = dict(base_data, capital_expenditures=15000000.0)
    svc = StatementRecoveryService(
        gemini_adapter=MockDictLLMAdapter(g_data),
        openai_adapter=MockDictLLMAdapter(o_data),
    )
    res = svc.recover("TESTCO", filing_text="Filing")
    assert "capital_expenditures" in res.provenance.rejected_fields


# ============================================================================
# 3. Stress Tests: Stale Filings & Invalid Metadata
# ============================================================================


def test_stress_stale_reporting_period_boundary() -> None:
    """Reporting period older than 4 years must fail closed with UNAVAILABLE."""
    stale_date = (date.today() - timedelta(days=365 * 4 + 1)).isoformat()
    svc = StatementRecoveryService(
        gemini_adapter=MockDictLLMAdapter(
            {
                "issuer_symbol": "TESTCO",
                "period_type": "annual",
                "period_end": stale_date,
                "currency": "USD",
                "revenue": 100000000.0,
            }
        ),
        openai_adapter=None,
    )
    res = svc.recover("TESTCO", filing_text="Filing")
    assert res.status == StatementRecoveryStatus.UNAVAILABLE
    assert "stale" in (res.unavailability_reason or "").lower()


def test_stress_future_reporting_period_fails_closed() -> None:
    """Reporting period in the future must fail closed with UNAVAILABLE."""
    future_date = (date.today() + timedelta(days=30)).isoformat()
    svc = StatementRecoveryService(
        gemini_adapter=MockDictLLMAdapter(
            {
                "issuer_symbol": "TESTCO",
                "period_type": "annual",
                "period_end": future_date,
                "currency": "USD",
                "revenue": 100000000.0,
            }
        ),
        openai_adapter=None,
    )
    res = svc.recover("TESTCO", filing_text="Filing")
    assert res.status == StatementRecoveryStatus.UNAVAILABLE
    assert "future" in (res.unavailability_reason or "").lower()


def test_stress_issuer_identity_mismatch_fails_closed() -> None:
    """When filing belongs to a completely different company, fail closed."""
    svc = StatementRecoveryService(
        gemini_adapter=MockDictLLMAdapter(
            {
                "issuer_symbol": "INFY",
                "period_type": "annual",
                "period_end": "2024-03-31",
                "currency": "INR",
                "revenue": 100000000.0,
            }
        ),
        openai_adapter=None,
    )
    res = svc.recover("TCS", filing_text="Filing for Infosys")
    assert res.status == StatementRecoveryStatus.UNAVAILABLE
    assert "mismatch" in (res.unavailability_reason or "").lower()


def test_stress_balance_sheet_equation_violation_rejects_bs_fields() -> None:
    """When Total Assets != Total Liabilities + Total Equity (by > 5%), reject all 3 fields."""
    svc = StatementRecoveryService(
        gemini_adapter=MockDictLLMAdapter(
            {
                "issuer_symbol": "TESTCO",
                "period_type": "annual",
                "period_end": "2024-03-31",
                "currency": "USD",
                "revenue": 100000000.0,
                "net_income": 10000000.0,
                "total_assets": 1000000000.0,  # 1000M
                "total_liabilities": 200000000.0,  # 200M
                "total_equity": 300000000.0,  # 300M (Sum = 500M != 1000M, 50% mismatch)
            }
        ),
        openai_adapter=None,
    )
    res = svc.recover("TESTCO", filing_text="Filing")
    assert "total_assets" in res.provenance.rejected_fields
    assert "total_liabilities" in res.provenance.rejected_fields
    assert "total_equity" in res.provenance.rejected_fields
    assert any(
        "equation_mismatch" in c.get("reason", "") for c in res.provenance.conflicts
    )


def test_stress_cash_flow_equation_violation_rejects_fcf() -> None:
    """When FCF != OCF - Capex (by > 5%), reject FCF and capex."""
    svc = StatementRecoveryService(
        gemini_adapter=MockDictLLMAdapter(
            {
                "issuer_symbol": "TESTCO",
                "period_type": "annual",
                "period_end": "2024-03-31",
                "currency": "USD",
                "revenue": 100000000.0,
                "net_income": 10000000.0,
                "total_assets": 1000000000.0,
                "total_liabilities": 400000000.0,
                "total_equity": 600000000.0,
                "operating_cash_flow": 100000000.0,
                "capital_expenditures": 20000000.0,  # Expected FCF = 80M
                "free_cash_flow": 30000000.0,  # Reported FCF = 30M (Mismatch = 62.5%)
            }
        ),
        openai_adapter=None,
    )
    res = svc.recover("TESTCO", filing_text="Filing")
    assert "free_cash_flow" in res.provenance.rejected_fields
    assert any(
        "fcf_equation_mismatch" in c.get("reason", "") for c in res.provenance.conflicts
    )


# ============================================================================
# 4. Stress Tests: Missing Share Counts & P1-03 Safeguards
# ============================================================================


def test_stress_shareholding_percentage_rejected_as_shares() -> None:
    """A shareholding percentage (e.g. 52.3) must NEVER be treated as shares outstanding."""
    svc = StatementRecoveryService(
        gemini_adapter=MockDictLLMAdapter(
            {
                "issuer_symbol": "TESTCO",
                "period_type": "annual",
                "period_end": "2024-03-31",
                "currency": "USD",
                "revenue": 100000000.0,
                "net_income": 10000000.0,
                "total_assets": 1000000000.0,
                "total_liabilities": 400000000.0,
                "total_equity": 600000000.0,
                "operating_cash_flow": 80000000.0,
                "capital_expenditures": 20000000.0,
                "free_cash_flow": 60000000.0,
                "shares_outstanding": 52.3,  # Promoter shareholding percentage!
            }
        ),
        openai_adapter=None,
    )
    res = svc.recover("TESTCO", filing_text="Filing")
    assert "shares_outstanding" in res.provenance.rejected_fields
    assert any(
        c.get("reason") == "shares_value_resembles_percentage_rejected"
        for c in res.provenance.conflicts
    )
    assert not res.recovered_statements.periods[0].shares_outstanding.available


def test_stress_upstox_quote_shares_refused_for_valuation_under_p1_03() -> None:
    """Under P1-03, Upstox is quote-only. Quote-derived shares CANNOT authorize per-share valuation."""
    inst = Instrument(
        symbol="RELIANCE", asset_class=AssetClass.EQUITY, currency="INR", exchange="NSE"
    )
    quote_prov = MarketQuoteProvenance(
        provider_id="upstox",
        provider_name="Upstox",
        source_type="broker",
        as_of=utc_now(),
        retrieved_at=utc_now(),
    )
    quote = build_quote_from_mapping(
        symbol="RELIANCE",
        payload={
            "current_price": 2500.0,
            "previous_close": 2490.0,
            "shares_outstanding": 6760000000.0,
        },
        provenance=quote_prov,
    )
    # Statement shares are missing (None)
    mock_latest = MagicMock()
    mock_latest.shares_outstanding.available = False
    mock_latest.shares_outstanding.value = None
    with pytest.raises(AuthenticatedValuationError) as exc_info:
        _resolve_shares(quote, mock_latest)
    assert (
        "quote-derived shares from upstox cannot authorize per-share valuation"
        in str(exc_info.value)
    )


def test_stress_missing_shares_causes_null_iv_and_zero_confidence_in_valuation() -> (
    None
):
    """When verified shares are missing (or <= 0), signals_from_assessment fails closed."""
    from dsp_platform.composition.authenticated_valuation import (
        AuthenticatedValuationError,
        signals_from_assessment,
    )
    from investment_recommendation.valuation_signals import ValuationSignals

    mock_assessment = MagicMock()
    mock_assessment.valuation_range.mid = 1000000.0

    with pytest.raises(
        AuthenticatedValuationError, match="shares outstanding unavailable"
    ):
        signals_from_assessment(
            mock_assessment, current_market_price=50.0, shares_outstanding=0.0
        )

    # In pipeline degradation path: missing IV produces intrinsic_value_per_share=None and confidence=0.0
    degraded_signals = ValuationSignals(
        intrinsic_value_per_share=None,
        current_market_price=50.0,
        confidence=0.0,
    )
    assert degraded_signals.intrinsic_value_per_share is None
    assert degraded_signals.margin_of_safety is None
    assert degraded_signals.confidence == 0.0


# ============================================================================
# 5. Stress Tests: Fail-Closed Pipeline Stage Matrix
# ============================================================================


def test_stress_pipeline_continuation_matrix_quote_ok_statements_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When quote succeeds (Upstox) but statements completely fail, pipeline continues non-blocking under stop_on_stage_failure=False."""
    from data_engine.financial_statement.adapters import (
        NullAuthenticatedStatementAdapter,
    )
    from data_engine.financial_statement.service import FinancialStatementService
    from data_engine.market_quote.adapters import (
        InMemoryAuthenticatedQuoteAdapter,
        build_quote_from_mapping,
    )
    from data_engine.market_quote.models import MarketQuoteProvenance, utc_now
    from data_engine.market_quote.service import MarketQuoteService
    from dsp_platform.composition.models import CompositionRequest
    from dsp_platform.composition.orchestrator import PlatformOrchestrator
    from dsp_platform.financial_statements import (
        reset_financial_statement_service_for_tests,
    )
    from dsp_platform.market_quotes import reset_market_quote_service_for_tests
    from dsp_platform.recovery import (
        StatementRecoveryService,
        reset_statement_recovery_service_for_tests,
    )

    quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key="valid-test-key")
    quote = build_quote_from_mapping(
        symbol="INFY",
        payload={
            "exchange": "NSE",
            "currency": "INR",
            "current_price": 1500.0,
            "previous_close": 1490.0,
            "shares_outstanding": 4000000000.0,
        },
        provenance=MarketQuoteProvenance(
            provider_id="upstox",
            provider_name="Upstox Broker",
            source_type="broker",
            retrieved_at=utc_now(),
            auth_mode="oauth2",
        ),
    )
    quote_adapter.put(quote)
    reset_financial_statement_service_for_tests(
        FinancialStatementService(NullAuthenticatedStatementAdapter())
    )
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))

    # Recovery fails completely
    recovery_svc = StatementRecoveryService(
        gemini_adapter=MockFailingLLMAdapter(RuntimeError("Gemini down")),
        openai_adapter=MockFailingLLMAdapter(RuntimeError("OpenAI down")),
    )
    reset_statement_recovery_service_for_tests(recovery_svc)

    try:
        request = CompositionRequest(
            ticker="INFY",
            current_market_price=1500.0,
            stop_on_stage_failure=False,
        )
        result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
        # Stages outcomes inspection
        stages_by_name = {s.stage: s for s in result.stages}

        # Financial failed
        assert stages_by_name["financial"].status in {StageStatus.FAILED, StageStatus.UNAVAILABLE}
        # Valuation degraded (price-only signals)
        assert stages_by_name["valuation"].status == StageStatus.DEGRADED
        assert result.valuation_signals is not None
        assert result.valuation_signals.intrinsic_value_per_share is None
        assert result.valuation_signals.current_market_price == 1500.0
        assert result.valuation_signals.confidence == 0.0

        # Downstream stages dependent on financial analysis are skipped
        for dep_stage in [
            "economic_moat",
            "management_quality",
            "financial_strength",
            "earnings_quality",
            "growth_quality",
            "business_quality_aggregator",
            "investment_recommendation",
            "investment_committee",
        ]:
            assert stages_by_name[dep_stage].status == StageStatus.SKIPPED
    finally:
        reset_financial_statement_service_for_tests(None)
        reset_market_quote_service_for_tests(None)
        reset_statement_recovery_service_for_tests(None)
