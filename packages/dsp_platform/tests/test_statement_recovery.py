"""Tests for StatementRecoveryService and P0 targeted recovery."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import pytest

from copilot.enums import LanguageModelStatus
from copilot.models import LanguageModelRequest, LanguageModelResult
from dsp_platform.recovery.statement_recovery import (
    StatementRecoveryService,
    StatementRecoveryStatus,
)


class MockLLMAdapter:
    def __init__(
        self,
        response_dict: dict[str, Any] | None,
        status: LanguageModelStatus = LanguageModelStatus.COMPLETE,
    ) -> None:
        self.response_dict = response_dict
        self.status = status
        self.model_label = "mock-llm"
        self.calls: list[LanguageModelRequest] = []

    def is_configured(self) -> bool:
        return True

    def invoke(self, request: LanguageModelRequest) -> LanguageModelResult:
        self.calls.append(request)
        if self.status != LanguageModelStatus.COMPLETE or self.response_dict is None:
            return LanguageModelResult(
                result_id="mock-1",
                provenance=("mock",),
                status=self.status,
                narrative_text=None,
                model_label=self.model_label,
            )
        return LanguageModelResult(
            result_id="mock-2",
            provenance=("mock",),
            status=LanguageModelStatus.COMPLETE,
            narrative_text=json.dumps(self.response_dict),
            model_label=self.model_label,
        )


def _base_valid_statement() -> dict[str, Any]:
    return {
        "issuer_symbol": "RELIANCE",
        "period_type": "annual",
        "period_end": "2024-03-31",
        "filing_date": "2024-04-30",
        "currency": "INR",
        "statement_basis": "consolidated",
        "unit_scale": "crores",
        "shares_outstanding": 6760000000,
        "revenue": 900000.0,
        "cost_of_revenue": 600000.0,
        "gross_profit": 300000.0,
        "operating_income": 120000.0,
        "ebit": 120000.0,
        "ebitda": 150000.0,
        "net_income": 70000.0,
        "eps_basic": 103.55,
        "eps_diluted": 103.55,
        "total_assets": 1700000.0,
        "total_liabilities": 900000.0,
        "total_equity": 800000.0,
        "total_debt": 300000.0,
        "cash_and_equivalents": 50000.0,
        "operating_cash_flow": 140000.0,
        "capital_expenditures": 90000.0,
        "free_cash_flow": 50000.0,
    }


def test_dual_model_recovery_success() -> None:
    g_data = _base_valid_statement()
    o_data = _base_valid_statement()
    # 2% variation within 5% tolerance
    o_data["revenue"] = 910000.0

    gemini = MockLLMAdapter(g_data)
    openai = MockLLMAdapter(o_data)

    service = StatementRecoveryService(
        gemini_adapter=gemini,
        openai_adapter=openai,
        relative_tolerance=0.05,
    )

    res = service.recover(
        "RELIANCE",
        exchange="NSE",
        currency="INR",
        filing_text="Audited Annual Report 2024 Reliance Industries",
    )

    assert res.status == StatementRecoveryStatus.RECOVERED_AND_VALIDATED
    assert res.is_usable()
    assert res.recovered_statements is not None
    period = res.recovered_statements.periods[0]
    assert period.revenue.available is True
    # In crores: 900000 * 10000000 = 9000000000000
    assert period.revenue.value == Decimal("9000000000000")
    assert period.shares_outstanding.available is True
    assert period.shares_outstanding.value == Decimal("6760000000")
    assert "revenue" in res.provenance.validated_fields
    assert len(res.provenance.conflicts) == 0


def test_material_disagreement_rejected_never_averaged() -> None:
    g_data = _base_valid_statement()
    o_data = _base_valid_statement()
    # 20% difference in revenue -> exceeds 5% threshold
    o_data["revenue"] = 1200000.0

    gemini = MockLLMAdapter(g_data)
    openai = MockLLMAdapter(o_data)

    service = StatementRecoveryService(
        gemini_adapter=gemini,
        openai_adapter=openai,
        relative_tolerance=0.05,
    )

    res = service.recover(
        "RELIANCE",
        exchange="NSE",
        currency="INR",
        filing_text="Audited Annual Report",
    )

    # Revenue should be rejected and not averaged
    assert "revenue" in res.provenance.rejected_fields
    assert any(c["field"] == "revenue" for c in res.provenance.conflicts)
    if res.recovered_statements:
        period = res.recovered_statements.periods[0]
        assert period.revenue.available is False


def test_single_model_fallback_when_gemini_unavailable() -> None:
    o_data = _base_valid_statement()
    gemini = MockLLMAdapter(None, status=LanguageModelStatus.FAILED)
    openai = MockLLMAdapter(o_data)

    service = StatementRecoveryService(
        gemini_adapter=gemini,
        openai_adapter=openai,
    )

    res = service.recover(
        "RELIANCE",
        exchange="NSE",
        currency="INR",
        filing_text="Audited Report",
    )

    assert res.is_usable()
    assert "openai" in res.provenance.models_used
    assert "gemini" not in res.provenance.models_used
    assert res.recovered_statements is not None
    assert res.recovered_statements.periods[0].revenue.available is True


def test_both_models_unavailable() -> None:
    gemini = MockLLMAdapter(None, status=LanguageModelStatus.FAILED)
    openai = MockLLMAdapter(None, status=LanguageModelStatus.FAILED)

    service = StatementRecoveryService(
        gemini_adapter=gemini,
        openai_adapter=openai,
    )

    res = service.recover(
        "RELIANCE",
        exchange="NSE",
        currency="INR",
        filing_text="Audited Report",
    )

    assert res.status == StatementRecoveryStatus.UNAVAILABLE
    assert not res.is_usable()
    assert res.recovered_statements is None


def test_p1_03_percentage_shares_rejected() -> None:
    g_data = _base_valid_statement()
    # Percentage (e.g. promoter holding 75%) must NEVER be treated as shares outstanding
    g_data["shares_outstanding"] = 75.0
    o_data = _base_valid_statement()
    o_data["shares_outstanding"] = 75.0

    gemini = MockLLMAdapter(g_data)
    openai = MockLLMAdapter(o_data)

    service = StatementRecoveryService(
        gemini_adapter=gemini,
        openai_adapter=openai,
    )

    res = service.recover(
        "RELIANCE",
        exchange="NSE",
        currency="INR",
        filing_text="Audited Report",
    )

    assert "shares_outstanding" in res.provenance.rejected_fields
    assert res.recovered_statements is not None
    period = res.recovered_statements.periods[0]
    assert period.shares_outstanding.available is False
    assert period.shares_outstanding.value is None


def test_balance_sheet_equation_violation_rejected() -> None:
    g_data = _base_valid_statement()
    # Assets (1,700,000) != Liab (900,000) + Equity (400,000 = 1,300,000) -> 30% mismatch
    g_data["total_equity"] = 400000.0
    o_data = dict(g_data)

    gemini = MockLLMAdapter(g_data)
    openai = MockLLMAdapter(o_data)

    service = StatementRecoveryService(
        gemini_adapter=gemini,
        openai_adapter=openai,
    )

    res = service.recover(
        "RELIANCE",
        exchange="NSE",
        currency="INR",
        filing_text="Audited Report",
    )

    assert "total_assets" in res.provenance.rejected_fields
    assert "total_equity" in res.provenance.rejected_fields
    assert any(c["field"] == "balance_sheet_equation" for c in res.provenance.conflicts)
    if res.recovered_statements:
        period = res.recovered_statements.periods[0]
        assert period.total_assets.available is False


def test_cash_flow_equation_violation_rejected() -> None:
    g_data = _base_valid_statement()
    # OCF = 140,000, Capex = 90,000 => FCF should be 50,000, but reporting 120,000
    g_data["free_cash_flow"] = 120000.0
    o_data = dict(g_data)

    gemini = MockLLMAdapter(g_data)
    openai = MockLLMAdapter(o_data)

    service = StatementRecoveryService(
        gemini_adapter=gemini,
        openai_adapter=openai,
    )

    res = service.recover(
        "RELIANCE",
        exchange="NSE",
        currency="INR",
        filing_text="Audited Report",
    )

    assert "free_cash_flow" in res.provenance.rejected_fields
    assert any(c["field"] == "cash_flow_equation" for c in res.provenance.conflicts)


def test_issuer_identity_mismatch_fails_closed() -> None:
    g_data = _base_valid_statement()
    g_data["issuer_symbol"] = "TCS"
    o_data = dict(g_data)

    gemini = MockLLMAdapter(g_data)
    openai = MockLLMAdapter(o_data)

    service = StatementRecoveryService(
        gemini_adapter=gemini,
        openai_adapter=openai,
    )

    res = service.recover(
        "RELIANCE",
        exchange="NSE",
        currency="INR",
        filing_text="Audited Report",
    )

    assert res.status == StatementRecoveryStatus.UNAVAILABLE
    assert not res.is_usable()
    assert "mismatch" in (res.unavailability_reason or "").lower()


def test_stale_reporting_period_rejected() -> None:
    svc = StatementRecoveryService(
        gemini_adapter=MockLLMAdapter(
            response_dict={
                "issuer_symbol": "AAPL",
                "period_type": "annual",
                "period_end": "2015-09-30",  # > 4 years stale
                "currency": "USD",
                "revenue": 1000.0,
            }
        ),
        openai_adapter=None,
    )
    res = svc.recover("AAPL", filing_text="Stale 10-K from 2015")
    assert res.status == StatementRecoveryStatus.UNAVAILABLE
    assert "stale" in (res.unavailability_reason or "").lower()


def test_future_reporting_period_rejected() -> None:
    svc = StatementRecoveryService(
        gemini_adapter=MockLLMAdapter(
            response_dict={
                "issuer_symbol": "AAPL",
                "period_type": "annual",
                "period_end": "2099-09-30",  # future
                "currency": "USD",
                "revenue": 1000.0,
            }
        ),
        openai_adapter=None,
    )
    res = svc.recover("AAPL", filing_text="Future 10-K from 2099")
    assert res.status == StatementRecoveryStatus.UNAVAILABLE
    assert "future" in (res.unavailability_reason or "").lower()


def test_negative_revenue_rejected() -> None:
    svc = StatementRecoveryService(
        gemini_adapter=MockLLMAdapter(
            response_dict={
                "issuer_symbol": "AAPL",
                "period_type": "annual",
                "period_end": "2024-09-30",
                "currency": "USD",
                "revenue": -500.0,  # invalid negative revenue
                "net_income": 100.0,
                "total_assets": 1000.0,
                "total_liabilities": 500.0,
                "total_equity": 500.0,
                "operating_cash_flow": 200.0,
                "capital_expenditures": 50.0,
                "free_cash_flow": 150.0,
                "shares_outstanding": 15000000000.0,
            }
        ),
        openai_adapter=None,
    )
    res = svc.recover("AAPL", filing_text="10-K with negative revenue")
    assert "revenue" in res.provenance.rejected_fields
    assert res.recovered_statements is not None
    assert not res.recovered_statements.periods[0].revenue.available


def test_empty_filing_content_fails_unavailable() -> None:
    svc = StatementRecoveryService(
        gemini_adapter=MockLLMAdapter(response_dict={}),
        openai_adapter=None,
    )
    res = svc.recover("AAPL", filing_text="")
    assert res.status == StatementRecoveryStatus.UNAVAILABLE
    assert res.recovered_statements is None


def test_recovery_integration_into_composition_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that when statement service is unauthenticated, recovery supplies statements to FinancialEngine."""
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

    # Provide quote but null statement adapter
    quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key="valid-test-key")
    quote = build_quote_from_mapping(
        symbol="AAPL",
        payload={
            "exchange": "NASDAQ",
            "currency": "USD",
            "current_price": 150.0,
            "previous_close": 149.0,
            "shares_outstanding": 15000000000.0,
        },
        provenance=MarketQuoteProvenance(
            provider_id="licensed_broker",
            provider_name="Broker",
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            auth_mode="api_key",
        ),
    )
    quote_adapter.put(quote)
    reset_financial_statement_service_for_tests(
        FinancialStatementService(NullAuthenticatedStatementAdapter())
    )
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))

    # Mock recovery service with verified dual-model extraction
    mock_gemini = MockLLMAdapter(
        response_dict={
            "issuer_symbol": "AAPL",
            "period_type": "annual",
            "period_end": "2024-09-30",
            "currency": "USD",
            "revenue": 391035000000.0,
            "net_income": 93736000000.0,
            "operating_income": 123216000000.0,
            "total_assets": 364980000000.0,
            "total_liabilities": 308030000000.0,
            "total_equity": 56950000000.0,
            "operating_cash_flow": 118264000000.0,
            "capital_expenditures": 9450000000.0,
            "free_cash_flow": 108814000000.0,
            "shares_outstanding": 15000000000.0,
        }
    )
    mock_openai = MockLLMAdapter(
        response_dict={
            "issuer_symbol": "AAPL",
            "period_type": "annual",
            "period_end": "2024-09-30",
            "currency": "USD",
            "revenue": 391035000000.0,
            "net_income": 93736000000.0,
            "operating_income": 123216000000.0,
            "total_assets": 364980000000.0,
            "total_liabilities": 308030000000.0,
            "total_equity": 56950000000.0,
            "operating_cash_flow": 118264000000.0,
            "capital_expenditures": 9450000000.0,
            "free_cash_flow": 108814000000.0,
            "shares_outstanding": 15000000000.0,
        }
    )
    monkeypatch.setattr(
        "dsp_platform.filings.get_authenticated_filings",
        lambda sym, exchange=None, limit=10: {
            "filings": [
                {
                    "title": "Apple Inc. 10-K Annual Report",
                    "content": "Apple Inc. 10-K Consolidated Financial Statements 2024. Revenue 391035000000 Net Income 93736000000",
                    "url": "https://www.sec.gov/ix?doc=/Archives/edgar/data/320193/000032019324000106/aapl-20240928.htm",
                    "filed_at": "2024-11-01",
                    "period_of_report": "2024-09-30",
                }
            ]
        },
    )
    recovery_svc = StatementRecoveryService(
        gemini_adapter=mock_gemini,
        openai_adapter=mock_openai,
    )
    reset_statement_recovery_service_for_tests(recovery_svc)

    try:
        request = CompositionRequest(
            ticker="AAPL",
            current_market_price=150.0,
        )
        result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
        # Financial analysis ran and succeeded via recovered statements!
        assert result.financial_analysis is not None
        assert result.financial_analysis.income.revenue.revenue == pytest.approx(
            391035000000.0
        )
    finally:
        reset_financial_statement_service_for_tests(None)
        reset_market_quote_service_for_tests(None)
        reset_statement_recovery_service_for_tests(None)


def test_independent_stages_continue_when_financial_fails_and_no_secret_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that when statement recovery fails, stop_on_stage_failure=False preserves independent outcomes without secret leakage."""
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

    SECRET_TOKEN = "SUPER_SECRET_KEY_12345"

    quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key=SECRET_TOKEN)
    quote = build_quote_from_mapping(
        symbol="MSFT",
        payload={
            "exchange": "NASDAQ",
            "currency": "USD",
            "current_price": 400.0,
            "previous_close": 395.0,
            "shares_outstanding": 7400000000.0,
        },
        provenance=MarketQuoteProvenance(
            provider_id="licensed_broker",
            provider_name="Broker",
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            auth_mode="api_key",
        ),
    )
    quote_adapter.put(quote)
    reset_financial_statement_service_for_tests(
        FinancialStatementService(NullAuthenticatedStatementAdapter())
    )
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))

    # Recovery service where both models fail
    recovery_svc = StatementRecoveryService(
        gemini_adapter=MockLLMAdapter(
            response_dict=None, status=LanguageModelStatus.FAILED
        ),
        openai_adapter=MockLLMAdapter(
            response_dict=None, status=LanguageModelStatus.FAILED
        ),
    )
    reset_statement_recovery_service_for_tests(recovery_svc)

    try:
        request = CompositionRequest(
            ticker="MSFT",
            current_market_price=400.0,
            stop_on_stage_failure=False,
        )
        result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
        # Financial failed, but valuation degraded gracefully, dependent stages skipped cleanly
        assert result.ok is False
        assert result.metadata.failed_stage == "financial"
        assert result.financial_analysis is None
        # Verify no secret is leaked in warnings or errors
        all_text = " ".join(result.metadata.warnings + result.errors)
        assert SECRET_TOKEN not in all_text
    finally:
        reset_financial_statement_service_for_tests(None)
        reset_market_quote_service_for_tests(None)
        reset_statement_recovery_service_for_tests(None)



def test_filing_candidate_search_skips_metadata_only_to_find_valid_filing(monkeypatch):
    """Metadata-only first filing must be skipped, finding subsequent valid candidate."""
    from dsp_platform.recovery.statement_recovery import StatementRecoveryService

    mock_filings = [
        {
            "filing_id": "FILING-META-ONLY",
            "title": "Empty Metadata Filing",
            "url": "https://example.com/meta-only",
            "filed_at": "2024-03-31",
            "content": "   ",  # empty content
        },
        {
            "filing_id": "FILING-VALID-2",
            "title": "Valid Filing With Body",
            "url": "https://example.com/valid-2",
            "filed_at": "2024-03-31",
            "content": "Real full filing financial statements and disclosures text.",
        },
    ]

    import dsp_platform.filings
    monkeypatch.setattr(
        dsp_platform.filings,
        "get_authenticated_filings",
        lambda sym, exchange=None, limit=10: {"filings": mock_filings},
    )

    svc = StatementRecoveryService()
    filing, content, checked = svc._find_filing_evidence("AAPL")
    assert filing is not None
    assert filing.filing_id == "FILING-VALID-2"
    assert content == "Real full filing financial statements and disclosures text."
    assert checked == 2


def test_filing_candidate_search_handles_malformed_candidate_dates_gracefully(monkeypatch):
    """Malformed date strings on candidates do not terminate the search."""
    from dsp_platform.recovery.statement_recovery import StatementRecoveryService

    mock_filings = [
        {
            "filing_id": "FILING-BAD-DATE",
            "title": "Bad Date Filing",
            "url": "https://example.com/bad-date",
            "filed_at": "NOT_A_DATE_2024",
            "period_of_report": "CORRUPTED_DATE",
            "content": "Filing with malformed dates but valid content.",
        }
    ]

    import dsp_platform.filings
    monkeypatch.setattr(
        dsp_platform.filings,
        "get_authenticated_filings",
        lambda sym, exchange=None, limit=10: {"filings": mock_filings},
    )

    svc = StatementRecoveryService()
    filing, content, checked = svc._find_filing_evidence("AAPL")
    assert filing is not None
    assert filing.filing_id == "FILING-BAD-DATE"
    assert filing.filed_at is not None  # safely defaulted to today
    assert filing.period_of_report is None
    assert content == "Filing with malformed dates but valid content."
    assert checked == 1


def test_filing_candidate_search_all_unusable_returns_unavailable(monkeypatch):
    """When all candidates have only metadata or empty content, return None and record checked count."""
    from dsp_platform.recovery.statement_recovery import StatementRecoveryService

    mock_filings = [
        {"filing_id": "F1", "content": ""},
        {"filing_id": "F2", "content": None},
        {"filing_id": "F3", "text": "   "},
    ]

    import dsp_platform.filings
    monkeypatch.setattr(
        dsp_platform.filings,
        "get_authenticated_filings",
        lambda sym, exchange=None, limit=10: {"filings": mock_filings},
    )

    svc = StatementRecoveryService()
    filing, content, checked = svc._find_filing_evidence("AAPL")
    assert filing is None
    assert content is None
    assert checked == 3


def test_filing_candidate_search_extraction_exception_continues_to_later_valid_candidate(monkeypatch):
    """A local exception while parsing one candidate does not stop evaluating subsequent candidates."""
    from dsp_platform.recovery.statement_recovery import StatementRecoveryService

    class BrokenDict(dict):
        def get(self, key, default=None):
            if key == "content":
                raise RuntimeError("Simulated extraction crash on candidate")
            return super().get(key, default)

    mock_filings = [
        BrokenDict({"filing_id": "F-BROKEN"}),
        {
            "filing_id": "F-RELIABLE",
            "content": "Valid filing report text after broken candidate.",
            "filed_at": "2024-06-30",
        },
    ]

    import dsp_platform.filings
    monkeypatch.setattr(
        dsp_platform.filings,
        "get_authenticated_filings",
        lambda sym, exchange=None, limit=10: {"filings": mock_filings},
    )

    svc = StatementRecoveryService()
    filing, content, checked = svc._find_filing_evidence("AAPL")
    assert filing is not None
    assert filing.filing_id == "F-RELIABLE"
    assert content == "Valid filing report text after broken candidate."
    assert checked == 2
