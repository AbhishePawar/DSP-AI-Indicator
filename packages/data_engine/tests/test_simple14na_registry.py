"""SIMPLE-14N-A — ISIN IR registry and annual-report selector (MOCK)."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

from data_engine.official_research.acquisition import acquire_primary_documents
from data_engine.official_research.annual_report import (
    html_document_links,
    latest_completed_indian_fy,
    normalize_financial_year,
    select_annual_documents,
)
from data_engine.official_research.company_sources import (
    CompanySourceRecord,
    CompanySourceRegistry,
    load_company_source_registry,
    resolve_company_sources,
)
from data_engine.official_research.documents import (
    DocumentStore,
    RetrievalFailure,
    redirect_is_approved,
    retrieve_official_document,
)
from data_engine.official_research.extraction import (
    extract_labeled_field,
    extract_shares_outstanding,
)
from data_engine.official_research.nse_primary import NseAnnouncementDocument
from data_engine.security_master.models import SecurityListing


def _listing(
    ticker: str = "INFY",
    isin: str = "INE009A01021",
    company: str = "Infosys Limited",
) -> SecurityListing:
    return SecurityListing(
        ticker=ticker,
        company_name=company,
        isin=isin,
        exchange="NSE",
        mic="XNSE",
        security_type="equity",
        eligibility=True,
        series="EQ",
    )


class _CaptureHttp:
    def __init__(self, payloads: dict[str, bytes] | None = None) -> None:
        self.payloads = payloads or {}
        self.urls: list[str] = []

    def get_bytes(self, url: str, *, referer: str | None = None) -> bytes:
        _ = referer
        self.urls.append(url)
        if url in self.payloads:
            return self.payloads[url]
        raise LookupError(f"HTTP 404 {url}")


def test_registry_is_isin_first_and_populated() -> None:
    registry = load_company_source_registry()
    infy = registry.record("INE009A01021")
    assert infy is not None
    assert infy.official_domain == "infosys.com"
    assert infy.company_name == "Infosys Limited"
    assert infy.ticker_aliases == ("INFY",)
    hdfc = registry.record("INE040A01034")
    assert hdfc is not None
    assert hdfc.official_domain == "hdfc.bank.in"
    assert registry.record("INFY") is None
    for isin in (
        "INE009A01021",
        "INE467B01029",
        "INE075A01022",
        "INE040A01034",
        "INE002A01018",
        "INE021A01026",
        "INE030A01027",
    ):
        assert registry.record(isin) is not None


def test_registry_rejects_wrong_company_for_isin() -> None:
    registry = CompanySourceRegistry(
        {
            "INE009A01021": CompanySourceRecord(
                isin="INE009A01021",
                company_name="Reliance Industries Limited",
                official_domain="infosys.com",
                investor_relations_url="https://www.infosys.com/investors.html",
                financial_results_url=None,
                annual_reports_url=None,
                source_verified_at="2026-09-10",
                verification_method="test",
                status="ACTIVE",
            )
        }
    )
    ok, issue = registry.matches_listing(_listing())
    assert ok is False
    assert issue is not None
    acquired = acquire_primary_documents(
        _listing(),
        transport=_CaptureHttp(),
        registry=registry,
        extra_document_text="unit: actual\nas_of: 2026-03-31\nnet income: 1",
    )
    assert acquired.fields == {}
    assert any("registry integrity" in item for item in acquired.issues)


def test_unregistered_ir_host_rejected() -> None:
    result = retrieve_official_document(
        "https://evil.example/annual.pdf",
        transport=_CaptureHttp({"https://evil.example/annual.pdf": b"x"}),
        isin="INE009A01021",
        mic="XNSE",
        source_type="company_ir",
        registry=load_company_source_registry(),
    )
    assert isinstance(result, RetrievalFailure)


def test_redirect_policy_blocks_secondary_and_allows_registered() -> None:
    registry = load_company_source_registry()
    assert redirect_is_approved(
        "https://finance.yahoo.com/quote/INFY",
        isin="INE009A01021",
        registry=registry,
    ) is False
    assert redirect_is_approved(
        "https://nsearchives.nseindia.com/a.pdf",
        isin="INE009A01021",
        registry=registry,
    ) is True
    assert redirect_is_approved(
        "https://www.infosys.com/investors/ar.pdf",
        isin="INE009A01021",
        registry=registry,
    ) is True
    assert redirect_is_approved(
        "https://www.infosys.com/investors/ar.pdf",
        isin="INE467B01029",
        registry=registry,
    ) is False


def test_document_store_reuses_identical_hash() -> None:
    url = "https://nsearchives.nseindia.com/a.pdf"
    http = _CaptureHttp({url: b"same-bytes"})
    store = DocumentStore()
    first = retrieve_official_document(
        url,
        transport=http,
        isin="INE009A01021",
        mic="XNSE",
        source_type="regulator",
        store=store,
    )
    second = retrieve_official_document(
        url,
        transport=http,
        isin="INE009A01021",
        mic="XNSE",
        source_type="regulator",
        store=store,
    )
    assert http.urls == [url]
    assert first.document_hash == hashlib.sha256(b"same-bytes").hexdigest()
    assert second is first


def test_document_store_keeps_prior_version_on_hash_change() -> None:
    url = "https://nsearchives.nseindia.com/a.pdf"
    http = _CaptureHttp({url: b"one"})
    store = DocumentStore()
    first = retrieve_official_document(
        url,
        transport=http,
        isin="INE009A01021",
        mic="XNSE",
        source_type="regulator",
        store=store,
    )
    http.payloads[url] = b"two"
    # Bypass cache get by using a fresh retrieve without store hit... store.get returns
    # previous, so construct put of a new record via second store-less retrieve.
    changed = retrieve_official_document(
        url,
        transport=http,
        isin="INE009A01021",
        mic="XNSE",
        source_type="regulator",
    )
    store.put(changed)
    assert first.payload == b"one"
    assert len(store.versions()) == 2
    assert store.versions()[0].document_hash != store.versions()[1].document_hash


def test_financial_year_normalization() -> None:
    assert normalize_financial_year("FY2026") == 2026
    assert normalize_financial_year("FY 2025-26") == 2026
    assert normalize_financial_year("2025-26") == 2026
    assert normalize_financial_year("year ended 31 March 2026") == 2026
    assert latest_completed_indian_fy(date(2026, 9, 10)) == 2026
    assert latest_completed_indian_fy(date(2026, 3, 15)) == 2025


def test_selector_prefers_annual_over_quarterly() -> None:
    announcements = (
        NseAnnouncementDocument(
            title="Unaudited Financial Results Q1 FY2027",
            url="https://nsearchives.nseindia.com/q1.pdf",
            as_of=date(2026, 6, 30),
            kind="financial_results",
        ),
        NseAnnouncementDocument(
            title="Integrated Annual Report FY 2025-26",
            url="https://nsearchives.nseindia.com/ar.pdf",
            as_of=date(2026, 3, 31),
            kind="annual_report",
        ),
        NseAnnouncementDocument(
            title="Investor Presentation",
            url="https://nsearchives.nseindia.com/deck.pdf",
            as_of=date(2026, 5, 1),
            kind="other",
        ),
    )
    selected = select_annual_documents(
        announcements, financial_year=2026, statement_basis="consolidated"
    )
    assert selected
    assert selected[0].url.endswith("ar.pdf")
    assert all("q1" not in item.url for item in selected)
    assert all("deck" not in item.url for item in selected)


def test_html_links_stay_on_approved_host() -> None:
    html = """
    <a href="/investors/annual-report-2026.pdf">Integrated Annual Report 2025-26</a>
    <a href="https://finance.yahoo.com/x.pdf">Annual Report</a>
    <a href="/assets/logo.png">logo</a>
    """
    links = html_document_links(
        html,
        base_url="https://www.infosys.com/investors.html",
        allow_url=lambda url: "infosys.com" in url,
    )
    assert links
    assert all("yahoo" not in url for url, _ in links)


def test_filename_not_directory_for_20f() -> None:
    selected = select_annual_documents(
        (),
        ir_links=(
            (
                "https://www.wipro.com/content/dam/annual-reports/20-f-fy25-26.pdf",
                "20-f-fy25-26.pdf",
            ),
            (
                "https://www.wipro.com/content/dam/annual-reports/Integrated-annual-report-2025-26.pdf",
                "Integrated-annual-report-2025-26.pdf",
            ),
        ),
        financial_year=2026,
    )
    assert selected
    assert "Integrated-annual-report" in selected[0].url
    assert all("20-f" not in item.url for item in selected)
    announcements = (
        NseAnnouncementDocument(
            title="Newspaper advertisement annual",
            url="https://nsearchives.nseindia.com/ad.pdf",
            as_of=date(2026, 5, 1),
            kind="other",
        ),
        NseAnnouncementDocument(
            title="Annual Report FY2026 consolidated",
            url="https://nsearchives.nseindia.com/annual.pdf",
            as_of=date(2026, 3, 31),
            kind="annual_report",
        ),
    )
    selected = select_annual_documents(announcements, financial_year=2026)
    assert selected[0].url.endswith("annual.pdf")


def test_acquire_uses_selected_annual_not_concat() -> None:
    annual = (
        b"Infosys Limited\nconsolidated\nunit: actual\n"
        b"year ended 31 March 2026\nrevenue: 100\nshares outstanding: 50"
    )
    quarterly = b"quarter ended 30 June 2026\nunit: actual\nrevenue: 9"
    announcements = [
        {
            "desc": "Financial Results Q1",
            "an_dt": "15-Jul-2026",
            "attchmntFile": "https://nsearchives.nseindia.com/q1.pdf",
        },
        {
            "desc": "Integrated Annual Report FY 2025-26",
            "an_dt": "15-May-2026",
            "attchmntFile": "https://nsearchives.nseindia.com/ar.pdf",
        },
    ]
    http = _CaptureHttp(
        {
            "https://nsearchives.nseindia.com/q1.pdf": quarterly,
            "https://nsearchives.nseindia.com/ar.pdf": annual,
        }
    )
    acquired = acquire_primary_documents(
        _listing(),
        transport=http,
        announcement_payload=announcements,
        fields=("revenue", "shares_outstanding"),
    )
    assert acquired.fields["revenue"].value == "100"
    assert acquired.fields["revenue"].statement_basis == "consolidated"
    assert acquired.fields["shares_outstanding"].as_of == date(2026, 3, 31)
    assert "q1" not in (acquired.selected_url or "")


def test_mixed_document_extracts_consolidated_not_standalone() -> None:
    text = (
        "unit: actual\nyear ended 31 March 2026\n"
        "standalone\nrevenue: 7\n"
        "consolidated\nrevenue: 10"
    )
    extracted = extract_labeled_field(text, "revenue")
    assert extracted is not None
    assert extracted.semantic_status == "VERIFIED"
    assert extracted.value == "10"
    assert extracted.statement_basis == "consolidated"


def test_wrong_isin_in_selected_document_rejected() -> None:
    body = (
        b"ISIN INE002A01018\nReliance Industries Limited\n"
        b"consolidated\nunit: actual\nyear ended 31 March 2026\nrevenue: 999"
    )
    announcements = [
        {
            "desc": "Annual Report FY2026",
            "an_dt": "15-May-2026",
            "attchmntFile": "https://nsearchives.nseindia.com/wrong.pdf",
        }
    ]
    acquired = acquire_primary_documents(
        _listing(),
        transport=_CaptureHttp({"https://nsearchives.nseindia.com/wrong.pdf": body}),
        announcement_payload=announcements,
        fields=("revenue",),
    )
    assert "revenue" not in acquired.fields
    assert any("identity" in item.reason for item in acquired.failures)


def test_share_definitions_not_outstanding() -> None:
    assert extract_shares_outstanding("authorized shares: 5000") is None
    assert extract_shares_outstanding("paid-up capital: 5000") is None
    dated = extract_shares_outstanding("as_of: 2026-03-31\nshares outstanding: 12")
    assert dated is not None
    assert dated.as_of == date(2026, 3, 31)


def test_resolver_does_not_invent_investors_path() -> None:
    sources = resolve_company_sources(
        _listing("RELIANCE", "INE002A01018", "Reliance Industries Limited")
    )
    assert sources.official_domain == "ril.com"
    assert sources.investor_relations_url is None
    assert sources.annual_report_url is None
    assert not any("/investors" in url for url in sources.candidate_urls)


def test_no_ticker_hardcoding_in_ir_path() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "data_engine" / "official_research"
    for name in ("acquisition.py", "annual_report.py", "company_sources.py", "documents.py"):
        text = (root / name).read_text(encoding="utf-8")
        assert "if ticker ==" not in text
        assert "if ticker==" not in text
        for banned in ("upstox", "yfinance", "financialmodelingprep", "eodhd", "alphavantage"):
            assert banned not in text.lower()
