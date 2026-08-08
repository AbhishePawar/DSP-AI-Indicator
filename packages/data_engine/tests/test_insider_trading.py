"""Tests for the authenticated insider trading connector domain."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass

from data_engine import (
    BseInsiderTradingAdapter,
    ConnectorField,
    ConnectorProvenance,
    FinancialModelingPrepInsiderTradingAdapter,
    InMemoryInsiderTradingAdapter,
    InsiderTradingProviderRegistry,
    InsiderTradingQuery,
    InsiderTradingService,
    InsiderTransaction,
    InvalidProviderDataError,
    NseInsiderTradingAdapter,
    NullInsiderTradingAdapter,
    ProviderRequestError,
    SecEdgarInsiderTradingAdapter,
    YahooFinanceInsiderTradingAdapter,
    build_default_insider_trading_registry_from_env,
    build_insider_activity_from_mapping,
)


def _instrument(symbol: str = "AAPL") -> Instrument:
    return Instrument(symbol=symbol, asset_class=AssetClass.EQUITY, currency="USD")


def _txn(**overrides) -> InsiderTransaction:
    defaults = dict(
        transaction_id="t-1",
        insider_name="Jane Doe",
        role="CEO",
        transaction_type="buy",
        shares=ConnectorField.of(1000),
        price=ConnectorField.of(10.0),
        value=ConnectorField.of(10000.0),
        transaction_date=date(2023, 6, 1),
    )
    defaults.update(overrides)
    return InsiderTransaction(**defaults)


class _FakeJsonClient:
    def __init__(self, payload=None, *, sequence=None) -> None:
        self._payload = payload
        self._sequence = sequence
        self._i = 0

    def get_json(self, url, *, params=None, headers=None):
        if self._sequence is not None:
            result = self._sequence[min(self._i, len(self._sequence) - 1)]
            self._i += 1
            return result
        return self._payload


class TestNullAndInMemory:
    def test_null_always_unavailable(self) -> None:
        adapter = NullInsiderTradingAdapter()
        assert adapter.get_insider_activity(InsiderTradingQuery(instrument=_instrument())) is None

    def test_in_memory_requires_key(self) -> None:
        with pytest.raises(ProviderRequestError):
            InMemoryInsiderTradingAdapter().get_insider_activity(
                InsiderTradingQuery(instrument=_instrument())
            )

    def test_in_memory_put_and_get_with_filters(self) -> None:
        adapter = InMemoryInsiderTradingAdapter(api_key="k")
        bundle = build_insider_activity_from_mapping(
            symbol="AAPL",
            transactions=[
                _txn(transaction_id="t-1", transaction_date=date(2023, 1, 1)),
                _txn(transaction_id="t-2", transaction_date=date(2023, 6, 1)),
            ],
            provenance=ConnectorProvenance(
                provider_id="memory_insider_trading",
                provider_name="Memory",
                source_type="public_endpoint",
                retrieved_at=datetime.now(tz=UTC),
            ),
        )
        adapter.put(bundle)
        result = adapter.get_insider_activity(
            InsiderTradingQuery(instrument=_instrument(), start_date=date(2023, 3, 1))
        )
        assert result is not None
        assert len(result.transactions) == 1
        assert result.transactions[0].transaction_id == "t-2"


class TestValidation:
    def test_rejects_unknown_transaction_type(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            build_insider_activity_from_mapping(
                symbol="AAPL",
                transactions=[_txn(transaction_type="not_a_type")],
                provenance=ConnectorProvenance(
                    provider_id="x",
                    provider_name="X",
                    source_type="public_endpoint",
                    retrieved_at=datetime.now(tz=UTC),
                ),
            )

    def test_rejects_missing_insider_name(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            build_insider_activity_from_mapping(
                symbol="AAPL",
                transactions=[_txn(insider_name="")],
                provenance=ConnectorProvenance(
                    provider_id="x",
                    provider_name="X",
                    source_type="public_endpoint",
                    retrieved_at=datetime.now(tz=UTC),
                ),
            )

    def test_rejects_empty_transactions(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            build_insider_activity_from_mapping(
                symbol="AAPL",
                transactions=[],
                provenance=ConnectorProvenance(
                    provider_id="x",
                    provider_name="X",
                    source_type="public_endpoint",
                    retrieved_at=datetime.now(tz=UTC),
                ),
            )


class TestSecEdgarInsiderTradingAdapter:
    def test_requires_user_agent(self) -> None:
        with pytest.raises(ProviderRequestError):
            SecEdgarInsiderTradingAdapter(user_agent="").get_insider_activity(
                InsiderTradingQuery(instrument=_instrument())
            )

    def test_parses_form4_xml(self) -> None:
        tickers_payload = {"0": {"cik_str": 320193, "ticker": "AAPL"}}
        submissions_payload = {
            "filings": {
                "recent": {
                    "form": ["4", "10-K"],
                    "filingDate": ["2023-06-05", "2023-01-01"],
                    "accessionNumber": ["0000320193-23-000010", "0000320193-23-000001"],
                    "primaryDocument": ["form4.xml", "10k.htm"],
                }
            }
        }
        client = _FakeJsonClient(sequence=[tickers_payload, submissions_payload])
        adapter = SecEdgarInsiderTradingAdapter(user_agent="Test test@example.com", http_client=client)

        form4_xml = b"""<?xml version="1.0"?>
        <ownershipDocument>
          <reportingOwner>
            <reportingOwnerId><rptOwnerName>Jane Doe</rptOwnerName></reportingOwnerId>
            <reportingOwnerRelationship>
              <isDirector>0</isDirector>
              <isOfficer>1</isOfficer>
              <officerTitle>CEO</officerTitle>
              <isTenPercentOwner>0</isTenPercentOwner>
            </reportingOwnerRelationship>
          </reportingOwner>
          <nonDerivativeTable>
            <nonDerivativeTransaction>
              <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
              <transactionDate><value>2023-06-05</value></transactionDate>
              <transactionAmounts>
                <transactionShares><value>500</value></transactionShares>
                <transactionPricePerShare><value>150.25</value></transactionPricePerShare>
              </transactionAmounts>
            </nonDerivativeTransaction>
          </nonDerivativeTable>
        </ownershipDocument>
        """

        def _fake_fetch_xml(self, url):
            import xml.etree.ElementTree as ET

            return ET.fromstring(form4_xml)

        adapter._fetch_xml = _fake_fetch_xml.__get__(adapter, SecEdgarInsiderTradingAdapter)
        bundle = adapter.get_insider_activity(InsiderTradingQuery(instrument=_instrument()))
        assert bundle is not None
        assert len(bundle.transactions) == 1
        txn = bundle.transactions[0]
        assert txn.insider_name == "Jane Doe"
        assert txn.transaction_type == "buy"
        assert txn.role == "CEO"
        assert txn.shares.to_float() == 500.0
        assert txn.value.to_float() == pytest.approx(500 * 150.25)

    def test_unknown_ticker_returns_none(self) -> None:
        client = _FakeJsonClient({"0": {"cik_str": 1, "ticker": "MSFT"}})
        adapter = SecEdgarInsiderTradingAdapter(user_agent="Test test@example.com", http_client=client)
        assert adapter.get_insider_activity(InsiderTradingQuery(instrument=_instrument("AAPL"))) is None


class TestFinancialModelingPrepInsiderTradingAdapter:
    def test_maps_array_payload(self) -> None:
        payload = [
            {
                "reportingName": "Jane Doe",
                "transactionDate": "2023-06-05",
                "transactionType": "P-Purchase",
                "securitiesTransacted": 500,
                "price": 150.25,
                "filingDate": "2023-06-06",
                "typeOfOwner": "officer: CEO",
            }
        ]
        adapter = FinancialModelingPrepInsiderTradingAdapter(api_key="k", http_client=_FakeJsonClient(payload))
        bundle = adapter.get_insider_activity(InsiderTradingQuery(instrument=_instrument()))
        assert bundle is not None
        assert bundle.transactions[0].transaction_type == "buy"
        assert bundle.transactions[0].value.to_float() == pytest.approx(500 * 150.25)

    def test_requires_api_key(self) -> None:
        with pytest.raises(ProviderRequestError):
            FinancialModelingPrepInsiderTradingAdapter(api_key="").get_insider_activity(
                InsiderTradingQuery(instrument=_instrument())
            )


class TestNseAndBseInsiderTrading:
    def test_nse_maps_transactions(self) -> None:
        payload = [
            {
                "acquirerName": "Jane Doe",
                "intimDt": "05-Jun-2023",
                "tdpTransactionType": "Buy / Acquisition",
                "secAcq": 500,
                "secVal": 75125,
                "personCategory": "Promoter",
            }
        ]
        adapter = NseInsiderTradingAdapter(enabled=True, http_client=_FakeJsonClient(payload))
        bundle = adapter.get_insider_activity(InsiderTradingQuery(instrument=_instrument("RELIANCE")))
        assert bundle is not None
        assert bundle.transactions[0].transaction_type == "buy"
        assert bundle.transactions[0].transaction_date == date(2023, 6, 5)

    def test_bse_requires_numeric_scrip_code(self) -> None:
        adapter = BseInsiderTradingAdapter(enabled=True)
        assert adapter.get_insider_activity(InsiderTradingQuery(instrument=_instrument("RELIANCE"))) is None


class TestYahooFinanceInsiderTradingAdapter:
    def test_maps_insider_transactions_module(self) -> None:
        payload = {
            "quoteSummary": {
                "result": [
                    {
                        "insiderTransactions": {
                            "transactions": [
                                {
                                    "filerName": "Jane Doe",
                                    "filerRelation": "CEO",
                                    "startDate": {"raw": 1685923200},
                                    "transactionText": "Sale at price",
                                    "shares": {"raw": 500},
                                    "value": {"raw": 75125},
                                }
                            ]
                        }
                    }
                ]
            }
        }
        adapter = YahooFinanceInsiderTradingAdapter(enabled=True, http_client=_FakeJsonClient(payload))
        bundle = adapter.get_insider_activity(InsiderTradingQuery(instrument=_instrument()))
        assert bundle is not None
        assert bundle.transactions[0].transaction_type == "sell"


class TestRegistryAndEnv:
    def test_registry_ordering(self) -> None:
        registry = InsiderTradingProviderRegistry()
        registry.register(NullInsiderTradingAdapter(), provider_id="null_insider_trading", priority=1000)
        registry.register(
            NseInsiderTradingAdapter(enabled=True), provider_id="nse_insider_trading", priority=10
        )
        assert registry.ordered_ids() == ("nse_insider_trading", "null_insider_trading")

    def test_default_registry_falls_back_to_null(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in (
            "DSP_INSIDER_SEC_EDGAR_USER_AGENT",
            "DSP_INSIDER_FMP_API_KEY",
            "DSP_INSIDER_NSE_ENABLED",
            "DSP_INSIDER_BSE_ENABLED",
            "DSP_INSIDER_YAHOO_ENABLED",
            "DSP_INSIDER_MEMORY",
        ):
            monkeypatch.delenv(key, raising=False)
        registry = build_default_insider_trading_registry_from_env()
        assert registry.ordered_ids() == ("null_insider_trading",)


class TestInsiderTradingService:
    def test_cache_hit(self) -> None:
        adapter = InMemoryInsiderTradingAdapter(api_key="k")
        adapter.put(
            build_insider_activity_from_mapping(
                symbol="AAPL",
                transactions=[_txn()],
                provenance=ConnectorProvenance(
                    provider_id="memory_insider_trading",
                    provider_name="Memory",
                    source_type="public_endpoint",
                    retrieved_at=datetime.now(tz=UTC),
                ),
            )
        )
        service = InsiderTradingService(adapter)
        query = InsiderTradingQuery(instrument=_instrument())
        service.get_insider_activity(query)
        second = service.get_insider_activity(query)
        assert second is not None
        assert service.metrics.cache_hits == 1
