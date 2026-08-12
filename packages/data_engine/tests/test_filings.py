"""Tests for the authenticated filings connector domain."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass

from data_engine import (
    BseFilingsAdapter,
    ConnectorProvenance,
    Filing,
    FilingsProviderRegistry,
    FilingsQuery,
    FilingsService,
    FinancialModelingPrepFilingsAdapter,
    InMemoryFilingsAdapter,
    InvalidProviderDataError,
    NseFilingsAdapter,
    NullFilingsAdapter,
    ProviderRequestError,
    ScreenerFilingsAdapter,
    SecEdgarFilingsAdapter,
    build_default_filings_registry_from_env,
    build_filings_bundle_from_mapping,
)


def _instrument(symbol: str = "AAPL") -> Instrument:
    return Instrument(symbol=symbol, asset_class=AssetClass.EQUITY, currency="USD")


class _FakeJsonClient:
    """Returns ``payload`` for every call, or advances through ``sequence``."""

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
        assert NullFilingsAdapter().get_filings(FilingsQuery(instrument=_instrument())) is None

    def test_in_memory_requires_key(self) -> None:
        with pytest.raises(ProviderRequestError):
            InMemoryFilingsAdapter().get_filings(FilingsQuery(instrument=_instrument()))

    def test_in_memory_put_get_and_filter(self) -> None:
        adapter = InMemoryFilingsAdapter(api_key="k")
        bundle = build_filings_bundle_from_mapping(
            symbol="AAPL",
            filings=[
                Filing(
                    filing_id="1",
                    filing_type="10-K",
                    title="Annual report",
                    url="https://sec.gov/1",
                    filed_at=date(2023, 11, 1),
                ),
                Filing(
                    filing_id="2",
                    filing_type="8-K",
                    title="Current report",
                    url="https://sec.gov/2",
                    filed_at=date(2023, 6, 1),
                ),
            ],
            provenance=ConnectorProvenance(
                provider_id="memory_filings",
                provider_name="Memory",
                source_type="regulatory_filing",
                retrieved_at=datetime.now(tz=UTC),
            ),
        )
        adapter.put(bundle)
        result = adapter.get_filings(
            FilingsQuery(instrument=_instrument(), filing_types=("10-K",))
        )
        assert result is not None
        assert len(result.filings) == 1
        assert result.filings[0].filing_type == "10-K"


class TestValidation:
    def test_rejects_unknown_filing_type(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            build_filings_bundle_from_mapping(
                symbol="AAPL",
                filings=[
                    Filing(
                        filing_id="1",
                        filing_type="not-a-type",
                        title="x",
                        url="https://x",
                        filed_at=date(2023, 1, 1),
                    )
                ],
                provenance=ConnectorProvenance(
                    provider_id="x",
                    provider_name="X",
                    source_type="regulatory_filing",
                    retrieved_at=datetime.now(tz=UTC),
                ),
            )


class TestSecEdgarFilingsAdapter:
    def test_requires_user_agent(self) -> None:
        adapter = SecEdgarFilingsAdapter(user_agent="")
        with pytest.raises(ProviderRequestError):
            adapter.get_filings(FilingsQuery(instrument=_instrument()))

    def test_resolves_cik_and_maps_filings(self) -> None:
        tickers_payload = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc"}}
        submissions_payload = {
            "filings": {
                "recent": {
                    "form": ["10-K", "8-K"],
                    "filingDate": ["2023-11-03", "2023-08-01"],
                    "accessionNumber": ["0000320193-23-000106", "0000320193-23-000080"],
                    "primaryDocument": ["aapl-20230930.htm", "aapl-8k.htm"],
                    "reportDate": ["2023-09-30", ""],
                }
            }
        }
        client = _FakeJsonClient(sequence=[tickers_payload, submissions_payload])
        adapter = SecEdgarFilingsAdapter(user_agent="Test test@example.com", http_client=client)
        bundle = adapter.get_filings(FilingsQuery(instrument=_instrument()))
        assert bundle is not None
        assert bundle.filings[0].filing_type in {"10-K", "8-K"}
        assert "0000320193" in bundle.filings[0].url

    def test_unknown_ticker_returns_none(self) -> None:
        client = _FakeJsonClient({"0": {"cik_str": 1, "ticker": "MSFT"}})
        adapter = SecEdgarFilingsAdapter(user_agent="Test test@example.com", http_client=client)
        assert adapter.get_filings(FilingsQuery(instrument=_instrument("ZZZZ"))) is None


class TestFinancialModelingPrepFilingsAdapter:
    def test_maps_array_payload(self) -> None:
        client = _FakeJsonClient(
            [
                {
                    "symbol": "AAPL",
                    "fillingDate": "2023-11-03 00:00:00",
                    "type": "10-K",
                    "link": "https://sec.gov/link",
                    "finalLink": "https://sec.gov/final",
                    "cik": "320193",
                }
            ]
        )
        adapter = FinancialModelingPrepFilingsAdapter(api_key="k", http_client=client)
        bundle = adapter.get_filings(FilingsQuery(instrument=_instrument()))
        assert bundle is not None
        assert bundle.filings[0].url == "https://sec.gov/final"


class TestNseAndBseFilings:
    def test_nse_disabled_raises(self) -> None:
        with pytest.raises(ProviderRequestError):
            NseFilingsAdapter(enabled=False).get_filings(FilingsQuery(instrument=_instrument()))

    def test_nse_maps_announcements(self) -> None:
        client = _FakeJsonClient(
            [
                {
                    "desc": "Board Meeting Intimation",
                    "attchmntFile": "https://nse.com/a.pdf",
                    "an_dt": "01-Nov-2023 10:00:00",
                }
            ]
        )
        adapter = NseFilingsAdapter(enabled=True, http_client=client)
        bundle = adapter.get_filings(FilingsQuery(instrument=_instrument("RELIANCE")))
        assert bundle is not None
        assert bundle.filings[0].filing_type == "corporate_announcement"

    def test_bse_requires_numeric_scrip_code_by_default(self) -> None:
        adapter = BseFilingsAdapter(enabled=True)
        assert adapter.get_filings(FilingsQuery(instrument=_instrument("RELIANCE"))) is None

    def test_bse_maps_table_payload(self) -> None:
        client = _FakeJsonClient(
            {
                "Table": [
                    {
                        "NEWSSUB": "Quarterly Results",
                        "NEWS_DT": "2023-11-01T00:00:00",
                        "ATTACHMENTNAME": "result.pdf",
                        "CATEGORYNAME": "Result",
                    }
                ]
            }
        )
        adapter = BseFilingsAdapter(enabled=True, http_client=client)
        bundle = adapter.get_filings(FilingsQuery(instrument=_instrument("500325")))
        assert bundle is not None
        assert bundle.filings[0].title == "Quarterly Results"


class TestScreenerFilingsAdapter:
    def test_maps_annual_reports_with_year_fallback(self) -> None:
        client = _FakeJsonClient(
            {"documents": {"annual_reports": [{"title": "Financial Year 2023", "link": "https://screener.in/ar.pdf"}]}}
        )
        adapter = ScreenerFilingsAdapter(enabled=True, http_client=client)
        bundle = adapter.get_filings(FilingsQuery(instrument=_instrument("RELIANCE")))
        assert bundle is not None
        assert bundle.filings[0].filed_at == date(2023, 3, 31)


class TestRegistryAndEnv:
    def test_registry_ordering(self) -> None:
        registry = FilingsProviderRegistry()
        registry.register(NullFilingsAdapter(), provider_id="null_filings", priority=1000)
        registry.register(FinancialModelingPrepFilingsAdapter(api_key="k"), provider_id="fmp_filings", priority=10)
        assert registry.ordered_ids() == ("fmp_filings", "null_filings")

    def test_default_registry_falls_back_to_null(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in (
            "DSP_FILINGS_SEC_EDGAR_USER_AGENT",
            "DSP_FILINGS_FMP_API_KEY",
            "DSP_FILINGS_NSE_ENABLED",
            "DSP_FILINGS_BSE_ENABLED",
            "DSP_FILINGS_SCREENER_ENABLED",
            "DSP_FILINGS_MEMORY",
        ):
            monkeypatch.delenv(key, raising=False)
        registry = build_default_filings_registry_from_env()
        assert registry.ordered_ids() == ("null_filings",)


class TestFilingsService:
    def test_cache_hit(self) -> None:
        adapter = InMemoryFilingsAdapter(api_key="k")
        adapter.put(
            build_filings_bundle_from_mapping(
                symbol="AAPL",
                filings=[
                    Filing(
                        filing_id="1",
                        filing_type="10-K",
                        title="t",
                        url="https://x",
                        filed_at=date(2023, 1, 1),
                    )
                ],
                provenance=ConnectorProvenance(
                    provider_id="memory_filings",
                    provider_name="Memory",
                    source_type="regulatory_filing",
                    retrieved_at=datetime.now(tz=UTC),
                ),
            )
        )
        service = FilingsService(adapter)
        query = FilingsQuery(instrument=_instrument())
        service.get_filings(query)
        second = service.get_filings(query)
        assert second is not None
        assert service.metrics.cache_hits == 1
