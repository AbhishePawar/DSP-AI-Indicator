"""Wire FMP into existing production provider factories.

Validates the canonical investment path after Upstox removal:
factory selection, fail-closed production, no stale vendor fallback,
and authenticated FMP quote/statement honesty.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.connector_framework.production_profile import (
    ConnectorConfigurationError,
)
from data_engine.financial_statement.adapters import (
    NullAuthenticatedStatementAdapter,
    build_default_statement_adapter_from_env,
    build_statements_from_mapping,
)
from data_engine.financial_statement.models import FinancialStatementProvenance
from data_engine.financial_statement.service import (
    FinancialStatementService,
    StatementQuery,
)
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
from dsp_platform import load_authenticated_valuation_bundle
from dsp_platform.composition.authenticated_valuation import AuthenticatedValuationError
from dsp_platform.financial_statements import (
    reset_financial_statement_service_for_tests,
)
from dsp_platform.market_quotes import reset_market_quote_service_for_tests

FIXED = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _clear_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "DSP_ENVIRONMENT",
        "DSP_INVESTMENT_DATA_PROVIDER",
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


def test_fmp_provider_unchanged_when_fmp_key_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_FMP_API_KEY", "fmp-unit-key")
    quote = build_default_quote_adapter_from_env()
    stmt = build_default_statement_adapter_from_env()
    assert isinstance(quote, FinancialModelingPrepQuoteAdapter)
    assert isinstance(stmt, FinancialModelingPrepStatementAdapter)


def test_explicit_fmp_provider_selects_fmp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "fmp")
    monkeypatch.setenv("DSP_FMP_API_KEY", "fmp-unit-key")
    quote = build_default_quote_adapter_from_env()
    stmt = build_default_statement_adapter_from_env()
    assert isinstance(quote, FinancialModelingPrepQuoteAdapter)
    assert isinstance(stmt, FinancialModelingPrepStatementAdapter)
    assert quote.provider_id == "fmp_market_quote"
    assert stmt.provider_id == "fmp_financial_statements"


def test_fmp_missing_key_dev_returns_null(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "fmp")
    quote = build_default_quote_adapter_from_env()
    stmt = build_default_statement_adapter_from_env()
    assert isinstance(quote, NullAuthenticatedQuoteAdapter)
    assert isinstance(stmt, NullAuthenticatedStatementAdapter)


def test_fmp_missing_key_production_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "fmp")
    with pytest.raises(ConnectorConfigurationError, match="DSP_FMP_API_KEY"):
        build_default_quote_adapter_from_env()
    with pytest.raises(ConnectorConfigurationError, match="DSP_FMP_API_KEY"):
        build_default_statement_adapter_from_env()


def test_explicit_fmp_beats_configured_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "fmp")
    monkeypatch.setenv("DSP_FMP_API_KEY", "fmp-key")
    monkeypatch.setenv("DSP_MARKET_QUOTE_API_KEY", "http-key")
    monkeypatch.setenv("DSP_MARKET_QUOTE_BASE_URL", "https://vendor.example")
    assert isinstance(
        build_default_quote_adapter_from_env(), FinancialModelingPrepQuoteAdapter
    )
    assert isinstance(
        build_default_statement_adapter_from_env(),
        FinancialModelingPrepStatementAdapter,
    )


def test_invalid_provider_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "yahoo")
    with pytest.raises(ConnectorConfigurationError, match="invalid"):
        resolve_investment_data_provider()


def test_stale_upstox_provider_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    with pytest.raises(ConnectorConfigurationError, match="invalid"):
        resolve_investment_data_provider()


def test_unavailable_provider_is_honest_null(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "unavailable")
    monkeypatch.setenv("DSP_FMP_API_KEY", "fmp-must-not-activate")
    quote = build_default_quote_adapter_from_env()
    stmt = build_default_statement_adapter_from_env()
    assert isinstance(quote, NullAuthenticatedQuoteAdapter)
    assert isinstance(stmt, NullAuthenticatedStatementAdapter)
    from data_engine.connector_framework.production_profile import (
        assert_production_investment_connectors_configured,
    )

    selected = assert_production_investment_connectors_configured()
    assert selected["market_quote"] == "INVESTMENT_DATA_UNAVAILABLE"
    assert selected["financial_statement"] == "INVESTMENT_DATA_UNAVAILABLE"


class _FmpAuthHttp:
    """Deterministic FMP quote + statements HTTP for TCS."""

    def __init__(
        self,
        *,
        price: float = 3500.25,
        revenue: float = 150000.0,
        shares: float | None = None,
        include_optional_statement_fields: bool = False,
    ) -> None:
        self.price = price
        self.revenue = revenue
        self.shares = shares
        self.include_optional_statement_fields = include_optional_statement_fields
        self.calls: list[dict[str, Any]] = []

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        self.calls.append({"url": url, "params": dict(params or {})})
        assert params is not None and params.get("apikey")
        if "/quote/" in url:
            row: dict[str, Any] = {
                "symbol": "TCS",
                "price": self.price,
                "open": self.price - 10,
                "dayHigh": self.price + 10,
                "dayLow": self.price - 20,
                "previousClose": 1.0,
                "exchange": "NSE",
                "currency": "INR",
            }
            if self.shares is not None:
                row["sharesOutstanding"] = self.shares
            return [row]
        if "/profile/" in url:
            return [
                {
                    "symbol": "TCS",
                    "companyName": "Tata Consultancy Services Limited",
                    "exchangeShortName": "NSE",
                    "currency": "INR",
                    "isin": "INE467B01029",
                }
            ]
        if "/income-statement/" in url:
            row = {
                "date": "2025-03-31",
                "calendarYear": "2025",
                "period": "FY",
                "reportedCurrency": "INR",
                "revenue": self.revenue,
                "netIncome": 30000.0,
                "eps": 121.0,
                "epsdiluted": 120.0,
                "operatingIncome": 40000.0,
            }
            if self.include_optional_statement_fields:
                row["costOfRevenue"] = 40000.0
            return [row]
        if "/balance-sheet-statement/" in url:
            return [
                {
                    "date": "2025-03-31",
                    "cashAndCashEquivalents": 15000.0,
                    "totalCurrentAssets": 50000.0,
                    "totalAssets": 200000.0,
                    "totalCurrentLiabilities": 30000.0,
                    "totalLiabilities": 80000.0,
                    "totalStockholdersEquity": 120000.0,
                    "totalDebt": 10000.0,
                }
            ]
        if "/cash-flow-statement/" in url:
            row = {
                "date": "2025-03-31",
                "operatingCashFlow": 35000.0,
            }
            if self.include_optional_statement_fields:
                row["capitalExpenditure"] = -5000.0
                row["freeCashFlow"] = 30000.0
            return [row]
        raise AssertionError(url)


def test_tcs_quote_uses_last_price_not_previous_close() -> None:
    http = _FmpAuthHttp(price=3500.25)
    quote_adapter = FinancialModelingPrepQuoteAdapter(
        api_key="fmp-secret", http_client=http
    )
    quote = quote_adapter.get_quote(
        Instrument(symbol="TCS", asset_class=AssetClass.EQUITY, currency="INR")
    )
    assert quote is not None
    assert float(quote.current_price.value) == pytest.approx(3500.25)
    assert float(quote.current_price.value) != pytest.approx(1.0)
    assert any("/quote/TCS" in c["url"] for c in http.calls)


def test_fmp_fundamentals_authoritative_for_tcs() -> None:
    http = _FmpAuthHttp(revenue=150000.0)
    stmt_adapter = FinancialModelingPrepStatementAdapter(
        api_key="fmp-secret", http_client=http
    )
    bundle = stmt_adapter.get_statements(
        StatementQuery(
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


def test_client_price_cannot_override_authenticated_quote() -> None:
    http = _FmpAuthHttp(price=3500.25, shares=250.0)
    quote_adapter = FinancialModelingPrepQuoteAdapter(
        api_key="fmp-secret", http_client=http
    )
    base_quote = quote_adapter.get_quote(
        Instrument(symbol="TCS", asset_class=AssetClass.EQUITY, currency="INR")
    )
    assert base_quote is not None
    assert float(base_quote.current_price.value) == pytest.approx(3500.25)

    class _QuoteWithShares:
        provider_id = "fmp_market_quote"

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
                    provider_id="fmp_market_quote",
                    provider_name="Financial Modeling Prep",
                    source_type="licensed_vendor",
                    retrieved_at=FIXED,
                    auth_mode="api_key",
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
            provider_id="fmp_financial_statements",
            provider_name="Financial Modeling Prep",
            source_type="licensed_vendor",
            retrieved_at=FIXED,
            auth_mode="api_key",
        ),
    )

    class _StmtPort:
        provider_id = "fmp_financial_statements"

        def get_statements(self, query):
            return stmt

        def resolve_company(self, instrument):
            return stmt.identity

        def health(self):
            return quote_adapter.health()

    reset_market_quote_service_for_tests(MarketQuoteService(_QuoteWithShares()))
    reset_financial_statement_service_for_tests(FinancialStatementService(_StmtPort()))
    try:
        bundle = load_authenticated_valuation_bundle("TCS", currency="INR")
        assert bundle.current_market_price == pytest.approx(3500.25)
        assert bundle.current_market_price != pytest.approx(999999.0)
        assert bundle.quote_provenance["provider_id"] == "fmp_market_quote"
        assert float(bundle.financial_snapshot.latest.revenue) == pytest.approx(
            150000.0
        )
        assert float(bundle.financial_snapshot.latest.revenue) != pytest.approx(
            999999999.0
        )
    finally:
        reset_market_quote_service_for_tests(None)
        reset_financial_statement_service_for_tests(None)


def test_quote_without_shares_fails_closed_honestly() -> None:
    http = _FmpAuthHttp(price=3500.25, shares=None)
    quote_adapter = FinancialModelingPrepQuoteAdapter(
        api_key="fmp-secret", http_client=http
    )
    stmt_adapter = FinancialModelingPrepStatementAdapter(
        api_key="fmp-secret", http_client=http
    )
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))
    reset_financial_statement_service_for_tests(FinancialStatementService(stmt_adapter))
    try:
        with pytest.raises(AuthenticatedValuationError, match="shares"):
            load_authenticated_valuation_bundle("TCS", currency="INR")
    finally:
        reset_market_quote_service_for_tests(None)
        reset_financial_statement_service_for_tests(None)


def test_api_key_not_in_public_quote_or_statements() -> None:
    http = _FmpAuthHttp(include_optional_statement_fields=True)
    secret = "super-secret-fmp-key"
    quote_adapter = FinancialModelingPrepQuoteAdapter(api_key=secret, http_client=http)
    stmt_adapter = FinancialModelingPrepStatementAdapter(
        api_key=secret, http_client=http
    )
    q = quote_adapter.get_quote(
        Instrument(symbol="TCS", asset_class=AssetClass.EQUITY, currency="INR")
    )
    s = stmt_adapter.get_statements(
        StatementQuery(
            instrument=Instrument(
                symbol="TCS", asset_class=AssetClass.EQUITY, currency="INR"
            )
        )
    )
    blob = str(q.to_public_dict() if q else {}) + str(s.to_public_dict() if s else {})
    assert secret not in blob
    assert "apikey" not in blob.lower()


def test_missing_fmp_fields_remain_unavailable() -> None:
    http = _FmpAuthHttp(include_optional_statement_fields=False)
    stmt_adapter = FinancialModelingPrepStatementAdapter(
        api_key="fmp-key", http_client=http
    )
    bundle = stmt_adapter.get_statements(
        StatementQuery(
            instrument=Instrument(
                symbol="TCS", asset_class=AssetClass.EQUITY, currency="INR"
            )
        )
    )
    assert bundle is not None
    assert not bundle.periods[0].free_cash_flow.available
    assert not bundle.periods[0].capital_expenditures.available
    assert not bundle.periods[0].cost_of_revenue.available
