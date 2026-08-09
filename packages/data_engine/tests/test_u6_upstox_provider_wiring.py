"""U6 — Wire Upstox into existing FMP production provider factories."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.connector_framework.production_profile import ConnectorConfigurationError
from data_engine.financial_statement.adapters import (
    NullAuthenticatedStatementAdapter,
    build_default_statement_adapter_from_env,
    build_statements_from_mapping,
)
from data_engine.financial_statement.models import FinancialStatementProvenance
from data_engine.financial_statement.service import FinancialStatementService
from data_engine.fmp_investment import (
    FinancialModelingPrepQuoteAdapter,
    FinancialModelingPrepStatementAdapter,
)
from data_engine.investment_data_provider import resolve_investment_data_provider
from data_engine.market_quote.adapters import (
    NullAuthenticatedQuoteAdapter,
    build_default_quote_adapter_from_env,
    build_quote_from_mapping,
)
from data_engine.market_quote.models import MarketQuoteProvenance
from data_engine.market_quote.service import MarketQuoteService
from data_engine.upstox_investment import UpstoxQuoteAdapter, UpstoxStatementAdapter
from dsp_platform import (
    CompositionRequest,
    PlatformOrchestrator,
    load_authenticated_valuation_bundle,
)
from dsp_platform.composition.authenticated_valuation import AuthenticatedValuationError
from dsp_platform.financial_statements import reset_financial_statement_service_for_tests
from dsp_platform.market_quotes import reset_market_quote_service_for_tests


FIXED = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _clear_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "DSP_ENVIRONMENT",
        "DSP_INVESTMENT_DATA_PROVIDER",
        "DSP_UPSTOX_ANALYTICS_TOKEN",
        "DSP_UPSTOX_ACCESS_TOKEN",
        "DSP_FMP_API_KEY",
        "DSP_INVESTMENT_FMP_API_KEY",
        "DSP_MARKET_QUOTE_API_KEY",
        "DSP_MARKET_QUOTE_BASE_URL",
        "DSP_MARKET_QUOTE_MEMORY",
        "DSP_FINANCIAL_STATEMENT_API_KEY",
        "DSP_FINANCIAL_STATEMENT_BASE_URL",
        "DSP_FINANCIAL_STATEMENT_MEMORY",
    ):
        monkeypatch.delenv(key, raising=False)


def test_fmp_provider_unchanged_when_fmp_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_FMP_API_KEY", "fmp-unit-key")
    quote = build_default_quote_adapter_from_env()
    stmt = build_default_statement_adapter_from_env()
    assert isinstance(quote, FinancialModelingPrepQuoteAdapter)
    assert isinstance(stmt, FinancialModelingPrepStatementAdapter)


def test_explicit_fmp_provider_selects_fmp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "fmp")
    monkeypatch.setenv("DSP_FMP_API_KEY", "fmp-unit-key")
    # Upstox token present must not win when provider=fmp
    monkeypatch.setenv("DSP_UPSTOX_ANALYTICS_TOKEN", "upstox-should-not-win")
    quote = build_default_quote_adapter_from_env()
    stmt = build_default_statement_adapter_from_env()
    assert isinstance(quote, FinancialModelingPrepQuoteAdapter)
    assert isinstance(stmt, FinancialModelingPrepStatementAdapter)


def test_upstox_selected_via_same_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    monkeypatch.setenv("DSP_UPSTOX_ANALYTICS_TOKEN", "upstox-unit-token")
    # FMP key must not win / fall back when Upstox is explicitly selected
    monkeypatch.setenv("DSP_FMP_API_KEY", "fmp-must-not-fallback")
    quote = build_default_quote_adapter_from_env()
    stmt = build_default_statement_adapter_from_env()
    assert isinstance(quote, UpstoxQuoteAdapter)
    assert isinstance(stmt, UpstoxStatementAdapter)
    assert quote.provider_id == "upstox_market_quote"
    assert stmt.provider_id == "upstox_financial_statements"


def test_upstox_missing_token_dev_returns_null(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    quote = build_default_quote_adapter_from_env()
    stmt = build_default_statement_adapter_from_env()
    assert isinstance(quote, NullAuthenticatedQuoteAdapter)
    assert isinstance(stmt, NullAuthenticatedStatementAdapter)


def test_upstox_missing_token_production_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    monkeypatch.setenv("DSP_FMP_API_KEY", "fmp-must-not-fallback")
    with pytest.raises(ConnectorConfigurationError, match="DSP_UPSTOX_ANALYTICS_TOKEN"):
        build_default_quote_adapter_from_env()
    with pytest.raises(ConnectorConfigurationError, match="Upstox is selected"):
        build_default_statement_adapter_from_env()


def test_upstox_no_fmp_fallback_on_explicit_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    monkeypatch.setenv("DSP_UPSTOX_ANALYTICS_TOKEN", "tok")
    monkeypatch.setenv("DSP_FMP_API_KEY", "fmp-key")
    monkeypatch.setenv("DSP_MARKET_QUOTE_API_KEY", "http-key")
    monkeypatch.setenv("DSP_MARKET_QUOTE_BASE_URL", "https://vendor.example")
    assert isinstance(build_default_quote_adapter_from_env(), UpstoxQuoteAdapter)
    assert isinstance(build_default_statement_adapter_from_env(), UpstoxStatementAdapter)


def test_invalid_provider_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "yahoo")
    with pytest.raises(ConnectorConfigurationError, match="invalid"):
        resolve_investment_data_provider()


class _UpstoxAuthHttp:
    """Deterministic U1+U2+U4 HTTP for TCS → instrument_key → quote + statements."""

    def __init__(self, *, price: float = 3500.25, revenue: float = 150000.0) -> None:
        self.price = price
        self.revenue = revenue
        self.calls: list[dict[str, Any]] = []

    def get_json(self, url: str, *, params=None, headers=None):
        self.calls.append(
            {"url": url, "params": dict(params or {}), "headers": dict(headers or {})}
        )
        assert headers and str(headers.get("Authorization", "")).startswith("Bearer ")
        # Never log the raw token; callers assert public payloads separately.
        if "instruments/search" in url:
            return {
                "status": "success",
                "data": [
                    {
                        "name": "Tata Consultancy Services Limited",
                        "segment": "NSE_EQ",
                        "exchange": "NSE",
                        "isin": "INE467B01029",
                        "instrument_key": "NSE_EQ|INE467B01029",
                        "trading_symbol": "TCS",
                        "instrument_type": "EQ",
                    }
                ],
            }
        if "market-quote/quotes" in url:
            key = str((params or {}).get("instrument_key") or "")
            assert key == "NSE_EQ|INE467B01029"
            return {
                "status": "success",
                "data": {
                    key: {
                        "ohlc": {
                            "open": self.price - 10,
                            "high": self.price + 10,
                            "low": self.price - 20,
                            "close": 1.0,  # must NOT become current price
                        },
                        "timestamp": "2026-08-09T10:00:00+05:30",
                        "symbol": "TCS",
                        "last_price": self.price,
                        "volume": 1000,
                    }
                },
            }
        if "/income-statement" in url:
            return {
                "status": "success",
                "data": {
                    "type": "consolidated",
                    "time_period": "yearly",
                    "units_in": "crore",
                    "income_statement": [
                        {
                            "category": "revenue",
                            "history": [{"period": "Mar 2025", "value": self.revenue}],
                        },
                        {
                            "category": "net_profit",
                            "history": [{"period": "Mar 2025", "value": 30000}],
                        },
                    ],
                    "full_statement": [
                        {
                            "particular": "EPS - Diluted",
                            "history": [{"period": "Mar 2025", "value": 120.0}],
                        },
                        {
                            "particular": "EPS - Basic",
                            "history": [{"period": "Mar 2025", "value": 121.0}],
                        },
                    ],
                },
            }
        if "/balance-sheet" in url:
            return {
                "status": "success",
                "data": {
                    "units_in": "crore",
                    "history": [
                        {
                            "total_asset": 200000,
                            "total_liability": 80000,
                            "period": "Mar 2025",
                        }
                    ],
                    "full_statement": [
                        {
                            "particular": "Current Assets",
                            "history": [{"period": "Mar 2025", "value": 50000}],
                        },
                        {
                            "particular": "Current Liabilities",
                            "history": [{"period": "Mar 2025", "value": 30000}],
                        },
                        {
                            "particular": "Equity Capital",
                            "history": [{"period": "Mar 2025", "value": 120000}],
                        },
                        {
                            "particular": "Total Assets",
                            "history": [{"period": "Mar 2025", "value": 200000}],
                        },
                    ],
                },
            }
        if "/cash-flow" in url:
            return {
                "status": "success",
                "data": {
                    "units_in": "crore",
                    "cash_flow": [
                        {
                            "category": "operating",
                            "history": [{"period": "Mar 2025", "value": 35000}],
                        }
                    ],
                    "full_statement": [
                        {
                            "particular": "Cash flow from Operations",
                            "history": [{"period": "Mar 2025", "value": 35000}],
                        }
                    ],
                },
            }
        raise AssertionError(url)


def test_tcs_reaches_u1_then_u2_last_price(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    monkeypatch.setenv("DSP_UPSTOX_ANALYTICS_TOKEN", "upstox-secret-token")
    http = _UpstoxAuthHttp(price=3500.25)
    quote_adapter = UpstoxQuoteAdapter(
        access_token="upstox-secret-token", http_client=http
    )
    quote = quote_adapter.get_quote(
        Instrument(symbol="TCS", asset_class=AssetClass.EQUITY, currency="INR")
    )
    assert quote is not None
    assert float(quote.current_price.value) == pytest.approx(3500.25)
    # ohlc.close must not substitute for last_price
    assert float(quote.current_price.value) != pytest.approx(1.0)
    assert any("instruments/search" in c["url"] for c in http.calls)
    assert any("market-quote/quotes" in c["url"] for c in http.calls)
    hist = [c for c in http.calls if "market-quote/quotes" in c["url"]]
    assert hist[0]["params"].get("instrument_key") == "NSE_EQ|INE467B01029"


def test_u4_fundamentals_authoritative_for_tcs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    monkeypatch.setenv("DSP_UPSTOX_ANALYTICS_TOKEN", "upstox-secret-token")
    http = _UpstoxAuthHttp(revenue=150000.0)
    stmt_adapter = UpstoxStatementAdapter(
        access_token="upstox-secret-token", http_client=http
    )
    bundle = stmt_adapter.get_statements(
        __import__(
            "data_engine.financial_statement.service", fromlist=["StatementQuery"]
        ).StatementQuery(
            instrument=Instrument(
                symbol="TCS", asset_class=AssetClass.EQUITY, currency="INR"
            ),
            limit=1,
        )
    )
    assert bundle is not None
    assert float(bundle.periods[0].revenue.value) == pytest.approx(150000.0)
    assert bundle.identity.isin == "INE467B01029"
    assert bundle.reporting_currency == "INR"


def test_client_price_cannot_override_upstox_quote() -> None:
    """Phase 1: auth Upstox price wins over client 999999."""
    from datetime import date

    from financial import (
        BalanceSheet,
        CashFlowStatement,
        CurrencyCode,
        CurrencyRef,
        FinancialPeriod,
        FinancialStatements,
        IncomeStatement,
        PeriodType,
        UnitScale,
    )
    from financial.metadata import StatementMetadata

    http = _UpstoxAuthHttp(price=3500.25)
    quote_adapter = UpstoxQuoteAdapter(access_token="tok", http_client=http)
    base_quote = quote_adapter.get_quote(
        Instrument(symbol="TCS", asset_class=AssetClass.EQUITY, currency="INR")
    )
    assert base_quote is not None

    class _QuoteWithShares:
        provider_id = "upstox_market_quote"

        def get_quote(self, instrument: Instrument):
            q = quote_adapter.get_quote(instrument)
            assert q is not None
            return build_quote_from_mapping(
                symbol=q.symbol,
                payload={
                    "exchange": q.exchange,
                    "currency": q.currency,
                    "current_price": float(q.current_price.value),
                    "shares_outstanding": 250.0,
                    "market_cap": float(q.current_price.value) * 250.0,
                },
                provenance=MarketQuoteProvenance(
                    provider_id="upstox_market_quote",
                    provider_name="Upstox",
                    source_type="licensed_vendor",
                    retrieved_at=FIXED,
                    auth_mode="bearer_token",
                ),
            )

        def health(self):
            return quote_adapter.health()

    stmt = build_statements_from_mapping(
        symbol="TCS",
        payload={
            "identity": {
                "symbol": "TCS",
                "exchange": "NSE",
                "isin": "INE467B01029",
                "currency": "INR",
            },
            "reporting_currency": "INR",
            "statement_basis": "consolidated",
            "unit_scale": "actual",
            "periods": [
                {
                    "period_type": "annual",
                    "fiscal_year": 2025,
                    "period_end": "2025-03-31",
                    "reporting_currency": "INR",
                    "restated": False,
                    "statement_basis": "consolidated",
                    "unit_scale": "actual",
                    "income_statement": {
                        "revenue": 150000.0,
                        "net_income": 30000.0,
                        "eps_basic": 120.0,
                        "eps_diluted": 120.0,
                        "operating_income": 40000.0,
                    },
                    "balance_sheet": {
                        "cash_and_equivalents": 15000.0,
                        "current_assets": 50000.0,
                        "total_assets": 200000.0,
                        "current_liabilities": 30000.0,
                        "total_liabilities": 80000.0,
                        "total_equity": 120000.0,
                        "total_debt": 10000.0,
                    },
                    "cash_flow": {
                        "operating_cash_flow": 35000.0,
                        "capital_expenditures": -5000.0,
                        "free_cash_flow": 30000.0,
                    },
                },
                {
                    "period_type": "annual",
                    "fiscal_year": 2024,
                    "period_end": "2024-03-31",
                    "reporting_currency": "INR",
                    "statement_basis": "consolidated",
                    "unit_scale": "actual",
                    "income_statement": {
                        "revenue": 140000.0,
                        "net_income": 28000.0,
                        "eps_basic": 112.0,
                        "operating_income": 38000.0,
                    },
                    "balance_sheet": {
                        "total_assets": 180000.0,
                        "total_liabilities": 70000.0,
                        "total_equity": 110000.0,
                    },
                    "cash_flow": {"operating_cash_flow": 32000.0},
                },
            ],
        },
        provenance=FinancialStatementProvenance(
            provider_id="upstox_financial_statements",
            provider_name="Upstox",
            source_type="licensed_vendor",
            retrieved_at=FIXED,
            auth_mode="bearer_token",
        ),
    )

    class _StmtPort:
        provider_id = "upstox_financial_statements"

        def get_statements(self, query):
            return stmt

        def resolve_company(self, instrument):
            return stmt.identity

        def health(self):
            return quote_adapter.health()

    client_fs = FinancialStatements(
        period=FinancialPeriod(
            period_type=PeriodType.ANNUAL,
            period_end=date(2025, 3, 31),
            fiscal_year=2025,
            currency=CurrencyRef(CurrencyCode.INR),
        ),
        income_statement=IncomeStatement(
            revenue=999999999.0,
            net_income=1.0,
            eps=0.01,
            weighted_shares=100.0,
        ),
        balance_sheet=BalanceSheet(equity=1.0, total_equity=1.0, total_assets=2.0),
        cash_flow=CashFlowStatement(operating_cash_flow=1.0, capex=-0.1),
        statement_metadata=StatementMetadata(unit_scale=UnitScale.ACTUAL),
    )

    reset_market_quote_service_for_tests(MarketQuoteService(_QuoteWithShares()))
    reset_financial_statement_service_for_tests(FinancialStatementService(_StmtPort()))
    try:
        bundle = load_authenticated_valuation_bundle("TCS", currency="INR")
        assert bundle.current_market_price == pytest.approx(3500.25)
        assert bundle.quote_provenance["provider_id"] == "upstox_market_quote"
        assert float(bundle.financial_snapshot.latest.revenue) == pytest.approx(150000.0)
        request = CompositionRequest(
            financial_statements=client_fs,
            current_market_price=999999.0,
            ticker="TCS",
            company="TCS",
        )
        result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
        signals = result.valuation_signals or result.valuation
        assert signals is not None
        assert getattr(signals, "current_market_price", None) == pytest.approx(3500.25)
    finally:
        reset_market_quote_service_for_tests(None)
        reset_financial_statement_service_for_tests(None)


def test_upstox_quote_without_shares_fails_closed_honestly() -> None:
    """Real U2 quotes lack shares_outstanding — valuation must fail closed, not invent."""
    http = _UpstoxAuthHttp(price=3500.25)
    quote_adapter = UpstoxQuoteAdapter(access_token="tok", http_client=http)
    stmt_adapter = UpstoxStatementAdapter(access_token="tok", http_client=http)
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))
    reset_financial_statement_service_for_tests(
        FinancialStatementService(stmt_adapter)
    )
    try:
        with pytest.raises(AuthenticatedValuationError, match="shares"):
            load_authenticated_valuation_bundle("TCS", currency="INR")
    finally:
        reset_market_quote_service_for_tests(None)
        reset_financial_statement_service_for_tests(None)


def test_token_not_in_public_quote_or_statements() -> None:
    http = _UpstoxAuthHttp()
    token = "super-secret-u6-token"
    quote_adapter = UpstoxQuoteAdapter(access_token=token, http_client=http)
    stmt_adapter = UpstoxStatementAdapter(access_token=token, http_client=http)
    q = quote_adapter.get_quote(
        Instrument(symbol="TCS", asset_class=AssetClass.EQUITY, currency="INR")
    )
    s = stmt_adapter.get_statements(
        __import__(
            "data_engine.financial_statement.service", fromlist=["StatementQuery"]
        ).StatementQuery(
            instrument=Instrument(
                symbol="TCS", asset_class=AssetClass.EQUITY, currency="INR"
            )
        )
    )
    blob = str(q.to_public_dict() if q else {}) + str(s.to_public_dict() if s else {})
    assert token not in blob
    assert "Bearer" not in blob


def test_missing_upstox_fields_remain_unavailable() -> None:
    http = _UpstoxAuthHttp()
    stmt_adapter = UpstoxStatementAdapter(access_token="tok", http_client=http)
    bundle = stmt_adapter.get_statements(
        __import__(
            "data_engine.financial_statement.service", fromlist=["StatementQuery"]
        ).StatementQuery(
            instrument=Instrument(
                symbol="TCS", asset_class=AssetClass.EQUITY, currency="INR"
            )
        )
    )
    assert bundle is not None
    # Official Upstox samples do not provide FCF/capex/COGS — must stay unavailable
    assert not bundle.periods[0].free_cash_flow.available
    assert not bundle.periods[0].capital_expenditures.available
    assert not bundle.periods[0].cost_of_revenue.available


def test_live_upstox_u6_optional() -> None:
    from data_engine.upstox_connectivity import resolve_u0_upstox_analytics_token

    token = resolve_u0_upstox_analytics_token()
    if not token:
        pytest.skip("UPSTOX LIVE TEST = NOT RUN; REASON = CREDENTIAL ABSENT")
    # Smoke only — never print token
    assert isinstance(token, str) and token
