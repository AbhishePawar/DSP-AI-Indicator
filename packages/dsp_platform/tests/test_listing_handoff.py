"""Selected listing exchange feeds existing Stage 4I handoff (not a second path)."""

from __future__ import annotations

from datetime import UTC, datetime

from data_engine import (
    FinancialStatementService,
    InMemoryAuthenticatedQuoteAdapter,
    MarketQuoteService,
    build_quote_from_mapping,
    build_statements_from_mapping,
)
from data_engine.financial_statement.models import (
    FinancialStatementProvenance,
    utc_now,
)
from data_engine.financial_statement.service import (
    FinancialStatementPort,
    StatementProviderHealth,
)
from data_engine.market_quote.models import MarketQuoteProvenance
from dsp_platform import build_composition_request
from dsp_platform.financial_statements import (
    get_authenticated_financial_statements,
    reset_financial_statement_service_for_tests,
)
from dsp_platform.listing_selection import ListingCandidate, select_indian_listing
from dsp_platform.market_quotes import (
    get_authenticated_market_quote,
    reset_market_quote_service_for_tests,
)

TCS_ISIN = "INE467B01029"


class _ExchangeProbeStatementAdapter(FinancialStatementPort):
    def __init__(self) -> None:
        self.exchanges_seen: list[str | None] = []
        self._bundle = build_statements_from_mapping(
            symbol="TCS",
            payload={
                "identity": {
                    "symbol": "TCS",
                    "exchange": "BSE",
                    "company_name": "TCS",
                    "currency": "INR",
                },
                "reporting_currency": "INR",
                "periods": [
                    {
                        "period_type": "annual",
                        "fiscal_year": 2024,
                        "period_end": "2024-03-31",
                        "reporting_currency": "INR",
                        "income_statement": {"revenue": 1.0, "net_income": 1.0},
                        "balance_sheet": {"total_assets": 1.0, "equity": 1.0},
                        "cash_flow": {"operating_cash_flow": 1.0},
                    }
                ],
            },
            provenance=FinancialStatementProvenance(
                provider_id="probe_statements",
                provider_name="Probe",
                source_type="licensed_vendor",
                retrieved_at=utc_now(),
                auth_mode="api_key",
            ),
        )

    @property
    def provider_id(self) -> str:
        return "probe_statements"

    def resolve_company(self, instrument):
        return self._bundle.identity

    def get_statements(self, query):
        self.exchanges_seen.append(query.instrument.exchange)
        if query.instrument.exchange != "BSE":
            return None
        return self._bundle

    def health(self) -> StatementProviderHealth:
        return StatementProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=True,
            detail="test",
        )


class _ExchangeProbeQuoteAdapter(InMemoryAuthenticatedQuoteAdapter):
    def __init__(self) -> None:
        super().__init__(api_key="test-key")
        self.exchanges_seen: list[str | None] = []
        self.put(
            build_quote_from_mapping(
                symbol="TCS",
                payload={
                    "exchange": "BSE",
                    "currency": "INR",
                    "current_price": 10.0,
                    "previous_close": 10.0,
                },
                provenance=MarketQuoteProvenance(
                    provider_id="probe_quote",
                    provider_name="Probe",
                    source_type="licensed_vendor",
                    retrieved_at=datetime.now(tz=UTC),
                    auth_mode="api_key",
                ),
            )
        )

    def get_quote(self, instrument):  # type: ignore[override]
        self.exchanges_seen.append(instrument.exchange)
        if instrument.exchange != "BSE":
            return None
        return super().get_quote(instrument)


def teardown_function() -> None:
    reset_financial_statement_service_for_tests(None)
    reset_market_quote_service_for_tests(None)


def test_selected_exchange_reaches_statements_quote_and_analyse() -> None:
    selection = select_indian_listing(
        "TCS",
        None,
        (
            ListingCandidate(exchange="NSE", isin=TCS_ISIN),
            ListingCandidate(exchange="BSE", isin=TCS_ISIN),
        ),
    )
    assert selection.exchange == "BSE"

    stmt = _ExchangeProbeStatementAdapter()
    quote = _ExchangeProbeQuoteAdapter()
    reset_financial_statement_service_for_tests(FinancialStatementService(stmt))
    reset_market_quote_service_for_tests(MarketQuoteService(quote))

    statements = get_authenticated_financial_statements(
        "TCS", exchange=selection.exchange
    )
    market = get_authenticated_market_quote("TCS", exchange=selection.exchange)
    analyse_req = build_composition_request(ticker="TCS", exchange=selection.exchange)

    assert "BSE" in stmt.exchanges_seen
    assert statements is not None
    assert "BSE" in quote.exchanges_seen
    assert market is not None
    assert analyse_req.exchange == "BSE"


def test_omitted_exchange_does_not_auto_pick_on_statements() -> None:
    stmt = _ExchangeProbeStatementAdapter()
    reset_financial_statement_service_for_tests(FinancialStatementService(stmt))
    payload = get_authenticated_financial_statements("TCS", exchange=None)
    assert payload is None
    assert None in stmt.exchanges_seen
