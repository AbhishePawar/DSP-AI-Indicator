"""SIMPLE-23 — universal filing-detail / IR document extraction. Fail-closed is success."""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from time import perf_counter
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from data_engine.official_research.acquisition import acquire_primary_documents
from data_engine.official_research.documents import (
    validate_document_payload,
    unwrap_archive_payload,
)
from data_engine.official_research.end_to_end import AUTO_REQUEST_GROUPS, analyse_listing
from data_engine.official_research.extraction import canonical_share_semantic_type
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.models import ResearchRequest
from data_engine.official_research.nse_eod import NseEodService, NsePublicHttp
from data_engine.official_research.nse_mcp import NSE_MCP_COMMERCIAL_STATUS
from data_engine.official_research.nse_primary import (
    NseAnnouncementDocument,
    NsePrimaryEvidenceService,
    parse_financial_result_documents,
)
from data_engine.official_research.orchestrator import ResearchOrchestrator
from data_engine.official_research.xbrl import extract_xbrl_fields
from data_engine.security_master import SecurityMasterService, load_default_catalog
from data_engine.security_master.models import SecurityListing
from llm_adapters.config import load_llm_config

_ENGINE = Path(__file__).resolve().parents[1] / "src" / "data_engine" / "official_research"
_NAMED = (
    ("TCS", "INE467B01029", "XNSE"),
    ("INFY", "INE009A01021", "XNSE"),
    ("RELIANCE", "INE002A01018", "XNSE"),
    ("HDFCBANK", "INE040A01034", "XNSE"),
    ("WIPRO", "INE075A01022", "XNSE"),
    ("20MICRONS", "INE144J01027", "XNSE"),
)
_FIXTURES = {row[0] for row in _NAMED}
_LIVE_COVERAGE: list[dict[str, str]] = []
_DYNAMIC: list[str] = []

_XBRL = """<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:in-bse-fin="http://www.bseindia.com/xbrl/fin">
  <xbrli:context id="CurrentYearDurationConsolidated">
    <xbrli:entity>
      <xbrli:identifier scheme="http://www.nseindia.com/isin">INE009A01021</xbrli:identifier>
    </xbrli:entity>
    <xbrli:period>
      <xbrli:startDate>2023-04-01</xbrli:startDate>
      <xbrli:endDate>2024-03-31</xbrli:endDate>
    </xbrli:period>
  </xbrli:context>
  <xbrli:context id="CurrentYearInstantConsolidated">
    <xbrli:entity>
      <xbrli:identifier scheme="http://www.nseindia.com/isin">INE009A01021</xbrli:identifier>
    </xbrli:entity>
    <xbrli:period>
      <xbrli:instant>2024-03-31</xbrli:instant>
    </xbrli:period>
  </xbrli:context>
  <xbrli:unit id="INR"><xbrli:measure>iso4217:INR</xbrli:measure></xbrli:unit>
  <xbrli:unit id="shares"><xbrli:measure>shares</xbrli:measure></xbrli:unit>
  <in-bse-fin:RevenueFromOperations contextRef="CurrentYearDurationConsolidated" unitRef="INR" decimals="-5">1467670000000</in-bse-fin:RevenueFromOperations>
  <in-bse-fin:ProfitAfterTax contextRef="CurrentYearDurationConsolidated" unitRef="INR" decimals="-5">262330000000</in-bse-fin:ProfitAfterTax>
  <in-bse-fin:NetCashFlowsFromOperatingActivities contextRef="CurrentYearDurationConsolidated" unitRef="INR" decimals="-5">252000000000</in-bse-fin:NetCashFlowsFromOperatingActivities>
  <in-bse-fin:CashAndCashEquivalents contextRef="CurrentYearInstantConsolidated" unitRef="INR" decimals="-5">19500000000</in-bse-fin:CashAndCashEquivalents>
  <in-bse-fin:Borrowings contextRef="CurrentYearInstantConsolidated" unitRef="INR" decimals="-5">1000000000</in-bse-fin:Borrowings>
  <in-bse-fin:TotalEquity contextRef="CurrentYearInstantConsolidated" unitRef="INR" decimals="-5">880000000000</in-bse-fin:TotalEquity>
  <in-bse-fin:TotalAssets contextRef="CurrentYearInstantConsolidated" unitRef="INR" decimals="-5">1410000000000</in-bse-fin:TotalAssets>
  <in-bse-fin:TotalLiabilities contextRef="CurrentYearInstantConsolidated" unitRef="INR" decimals="-5">530000000000</in-bse-fin:TotalLiabilities>
  <in-bse-fin:NumberOfEquitySharesOutstanding contextRef="CurrentYearInstantConsolidated" unitRef="shares" decimals="0">4151511667</in-bse-fin:NumberOfEquitySharesOutstanding>
</xbrl>
"""


def _master() -> SecurityMasterService:
    return SecurityMasterService(load_default_catalog())


def _listing(ticker: str, isin: str, mic: str = "XNSE") -> SecurityListing:
    resolved = _master().resolve(isin, isin=isin, mic=mic)
    assert resolved.status == "RESOLVED" and resolved.identity is not None
    return resolved.identity


def _kind(listing: SecurityListing) -> str:
    name = listing.company_name.lower()
    if "bank" in name or "finance" in name or "nbfc" in name:
        return "financial"
    if any(token in name for token in ("software", "infotech", "technology", "consult")):
        return "technology"
    if any(token in name for token in ("steel", "cement", "power", "oil", "gas", "infra")):
        return "industrial"
    if any(token in name for token in ("consumer", "food", "fmcg", "retail", "textile")):
        return "consumer"
    return "other"


def _dynamic_listings(count: int = 5) -> list[SecurityListing]:
    wanted = ("financial", "technology", "industrial", "consumer", "other")
    by_kind: dict[str, SecurityListing] = {}
    extras: list[SecurityListing] = []
    for item in load_default_catalog().all():
        if not item.eligibility or item.mic != "XNSE" or item.security_type != "equity":
            continue
        if item.ticker in _FIXTURES:
            continue
        kind = _kind(item)
        if kind not in by_kind:
            by_kind[kind] = item
        elif len(extras) < count:
            extras.append(item)
        if len(by_kind) == len(wanted) and len(extras) >= count:
            break
    picked: list[SecurityListing] = []
    for kind in wanted:
        listing = by_kind.get(kind)
        if listing is not None and listing.ticker not in {row.ticker for row in picked}:
            picked.append(listing)
        if len(picked) >= count:
            return picked
    for listing in extras:
        if listing.ticker not in {row.ticker for row in picked}:
            picked.append(listing)
        if len(picked) >= count:
            break
    assert len(picked) >= count
    return picked[:count]


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


def test_xbrl_extracts_labeled_financials_and_outstanding_shares() -> None:
    listing = _listing("INFY", "INE009A01021")
    parsed = extract_xbrl_fields(_XBRL.encode("utf-8"), isin=listing.isin)
    assert parsed.identity_ok is True
    assert parsed.fields["revenue"].value == "1467670000000"
    assert parsed.fields["revenue"].currency == "INR"
    assert parsed.fields["revenue"].unit_scale == "actual"
    assert parsed.fields["revenue"].statement_basis == "consolidated"
    assert parsed.fields["revenue"].as_of == date(2024, 3, 31)
    assert parsed.fields["net_income"].value == "262330000000"
    assert parsed.fields["cfo"].value == "252000000000"
    assert parsed.fields["shares_outstanding"].value == "4151511667"
    assert (
        canonical_share_semantic_type(parsed.fields["shares_outstanding"].locator)
        == "TOTAL_OUTSTANDING"
    )
    judged = EvidenceJudge().promote(
        __import__(
            "data_engine.official_research.field_acquisition",
            fromlist=["normalize_extracted_field"],
        ).normalize_extracted_field(
            listing,
            parsed.fields["revenue"],
            source_url="https://nsearchives.nseindia.com/corporate/xbrl/sample.xml",
            source_type="regulator",
            source="NSE",
            retrieved_at=__import__("datetime").datetime.now(
                __import__("datetime").UTC
            ),
            document_date=date(2024, 3, 31),
            document_text=parsed.labeled_text,
            mode="MOCK",
        )
    )
    assert judged.status == "VERIFIED"


def test_xbrl_wrong_isin_is_rejected() -> None:
    parsed = extract_xbrl_fields(_XBRL.encode("utf-8"), isin="INE467B01029")
    assert parsed.identity_ok is False
    assert parsed.fields == {}


def test_xbrl_malformed_is_unknown() -> None:
    parsed = extract_xbrl_fields(b"<not-xml", isin="INE009A01021")
    assert parsed.fields == {}
    assert parsed.issues


def test_xbrl_prefers_annual_fourd_over_quarter_oned() -> None:
    xml = """<?xml version="1.0"?>
<xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:in-bse-fin="http://www.bseindia.com/xbrl/fin">
  <xbrli:context id="OneD">
    <xbrli:entity><xbrli:identifier scheme="http://www.nseindia.com/isin">INE009A01021</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate><xbrli:endDate>2024-03-31</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="FourD">
    <xbrli:entity><xbrli:identifier scheme="http://www.nseindia.com/isin">INE009A01021</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate><xbrli:endDate>2024-03-31</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:unit id="INR"><xbrli:measure>iso4217:INR</xbrli:measure></xbrli:unit>
  <in-bse-fin:RevenueFromOperations contextRef="OneD" unitRef="INR">1</in-bse-fin:RevenueFromOperations>
  <in-bse-fin:RevenueFromOperations contextRef="FourD" unitRef="INR">1536700000000</in-bse-fin:RevenueFromOperations>
</xbrl>
"""
    parsed = extract_xbrl_fields(
        xml.encode("utf-8"),
        isin="INE009A01021",
        document_basis="consolidated",
    )
    assert parsed.fields["revenue"].value == "1536700000000"
    assert parsed.fields["revenue"].period_type == "FY"
    parsed = extract_xbrl_fields(b"<not-xml", isin="INE009A01021")
    assert parsed.fields == {}
    assert parsed.issues


def test_weighted_average_and_paid_up_are_not_outstanding() -> None:
    assert canonical_share_semantic_type("WeightedAverageNumberOfEquityShares") != (
        "TOTAL_OUTSTANDING"
    )
    assert canonical_share_semantic_type("PaidUpValueOfEquityShares") != "TOTAL_OUTSTANDING"
    assert canonical_share_semantic_type("FaceValueOfEquityShare") != "TOTAL_OUTSTANDING"
    assert canonical_share_semantic_type("DilutedEPSDenominator") != "TOTAL_OUTSTANDING"
    xml = _XBRL.replace(
        "NumberOfEquitySharesOutstanding",
        "WeightedAverageNumberOfEquityShares",
    )
    parsed = extract_xbrl_fields(xml.encode("utf-8"), isin="INE009A01021")
    assert "shares_outstanding" not in parsed.fields


def test_html_masquerading_as_pdf_and_empty_are_rejected() -> None:
    assert (
        validate_document_payload(
            "https://nsearchives.nseindia.com/a.pdf",
            b"<!DOCTYPE html><html><body>login password</body></html>",
        )
        == "HTML instead of PDF"
    )
    assert (
        validate_document_payload("https://nsearchives.nseindia.com/a.pdf", b"")
        == "empty document"
    )
    assert (
        validate_document_payload(
            "https://nsearchives.nseindia.com/a.xml",
            b"<!DOCTYPE html><html><body>error</body></html>",
        )
        == "HTML instead of XML"
    )


def test_zip_unwraps_inner_xml() -> None:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("filing.xml", _XBRL.encode("utf-8"))
    inner = unwrap_archive_payload(buffer.getvalue())
    assert inner
    assert inner[0][0].endswith(".xml")
    parsed = extract_xbrl_fields(inner[0][1], isin="INE009A01021")
    assert "revenue" in parsed.fields


def test_acquire_primary_downloads_xbrl_not_index() -> None:
    listing = _listing("INFY", "INE009A01021")
    xbrl_url = "https://nsearchives.nseindia.com/corporate/xbrl/INDAS_sample.xml"
    http = _CaptureHttp({xbrl_url: _XBRL.encode("utf-8")})
    acquired = acquire_primary_documents(
        listing,
        transport=http,
        extra_announcements=(
            NseAnnouncementDocument(
                title="Infosys Limited Annual financial results XBRL Consolidated",
                url=xbrl_url,
                as_of=date(2024, 3, 31),
                kind="xbrl",
                source="nse_financial_results",
                isin=listing.isin,
                statement_basis="consolidated",
            ),
        ),
    )
    assert "revenue" in acquired.fields
    assert acquired.fields["revenue"].statement_basis == "consolidated"
    assert acquired.selected_url == xbrl_url
    assert acquired.fields["shares_outstanding"].value == "4151511667"


def test_acquire_skips_empty_xbrl_and_uses_newer_labeled() -> None:
    listing = _listing("INFY", "INE009A01021")
    empty = """<?xml version="1.0"?>
<xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance">
  <xbrli:context id="FourD">
    <xbrli:entity>
      <xbrli:identifier scheme="http://www.nseindia.com/isin">INE009A01021</xbrli:identifier>
    </xbrli:entity>
    <xbrli:period><xbrli:instant>2019-03-31</xbrli:instant></xbrli:period>
  </xbrli:context>
</xbrl>
"""
    empty_url = "https://nsearchives.nseindia.com/corporate/xbrl/INDAS_old_WEB.xml"
    good_url = "https://nsearchives.nseindia.com/corporate/xbrl/INDAS_new.xml"
    missing_url = "https://nsearchives.nseindia.com/corporate/xbrl/INDAS_missing.xml"
    http = _CaptureHttp(
        {
            empty_url: empty.encode("utf-8"),
            good_url: _XBRL.encode("utf-8"),
        }
    )
    acquired = acquire_primary_documents(
        listing,
        transport=http,
        extra_announcements=(
            NseAnnouncementDocument(
                title="Annual financial results XBRL WEB",
                url=empty_url,
                as_of=date(2019, 3, 31),
                kind="xbrl",
                source="nse_financial_results",
                statement_basis="consolidated",
            ),
            NseAnnouncementDocument(
                title="Annual financial results XBRL missing",
                url=missing_url,
                as_of=date(2025, 3, 31),
                kind="xbrl",
                source="nse_financial_results",
                statement_basis="consolidated",
            ),
            NseAnnouncementDocument(
                title="Annual financial results XBRL Consolidated",
                url=good_url,
                as_of=date(2024, 3, 31),
                kind="xbrl",
                source="nse_financial_results",
                isin=listing.isin,
                statement_basis="consolidated",
            ),
        ),
    )
    assert acquired.selected_url == good_url
    assert acquired.fields["revenue"].value == "1467670000000"
    assert any("404" in item.reason or item.http_status == 404 for item in acquired.failures)


def test_http_403_does_not_fabricate() -> None:
    listing = _listing("INFY", "INE009A01021")

    class _Forbidden:
        def get_bytes(self, url: str, *, referer: str | None = None) -> bytes:
            _ = referer
            raise LookupError("NSE HTTP 403 for official URL")

    acquired = acquire_primary_documents(
        listing,
        transport=_Forbidden(),
        extra_announcements=(
            NseAnnouncementDocument(
                title="Annual financial results XBRL Consolidated",
                url="https://nsearchives.nseindia.com/corporate/xbrl/blocked.xml",
                as_of=date(2024, 3, 31),
                kind="xbrl",
                source="nse_financial_results",
            ),
        ),
    )
    assert acquired.fields == {}
    assert acquired.failures
    assert acquired.failures[0].http_status == 403 or "403" in acquired.failures[0].reason


def test_standalone_xbrl_is_not_mixed_into_consolidated_preference() -> None:
    listing = _listing("INFY", "INE009A01021")
    xml = _XBRL.replace("Consolidated", "Standalone")
    parsed = extract_xbrl_fields(
        xml.encode("utf-8"),
        isin=listing.isin,
        preferred_basis="consolidated",
        document_basis="standalone",
    )
    if "revenue" in parsed.fields:
        assert parsed.fields["revenue"].statement_basis == "standalone"


def test_financial_result_index_is_not_treated_as_line_items() -> None:
    docs = parse_financial_result_documents(
        [
            {
                "symbol": "TCS",
                "isin": "INE467B01029",
                "period": "Annual",
                "consolidated": "Consolidated",
                "toDate": "31-Mar-2025",
                "xbrl": "https://nsearchives.nseindia.com/corporate/xbrl/t.xml",
            }
        ],
        ticker="TCS",
    )
    assert docs[0].kind == "xbrl"
    assert "146767" not in docs[0].title


def test_architecture_no_company_branches() -> None:
    for path in _ENGINE.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "if ticker ==" not in text
        assert "class EvidenceJudge2" not in text
        if path.name in {
            "xbrl.py",
            "acquisition.py",
            "orchestrator.py",
            "nse_primary.py",
            "field_acquisition.py",
            "end_to_end.py",
        }:
            for token in _FIXTURES:
                assert token not in text
    assert NSE_MCP_COMMERCIAL_STATUS == "COMMERCIAL_USE_PENDING"
    cfg = load_llm_config()
    if not cfg.openai_api_key:
        return


def test_browser_is_parked() -> None:
    pytest.skip("FRONTEND PARKED: SIMPLE-23 is backend filing-detail only")


def _skip_live() -> None:
    if os.environ.get("DSP_SKIP_LIVE_NSE_EOD") == "1":
        pytest.skip("LIVE NSE skipped by DSP_SKIP_LIVE_NSE_EOD=1")


def _coverage_row(listing: SecurityListing, result, *, discovered: str, acquired: str) -> dict[str, str]:
    dataset = result.dataset
    financials = "UNKNOWN"
    shares = "UNKNOWN"
    ca = "UNKNOWN"
    dcf = "BLOCKED"
    if dataset is not None:
        fin_fields = [
            dataset.verified_decimal(name) is not None
            for name in ("revenue", "net_income", "cfo", "equity")
        ]
        if all(fin_fields):
            financials = "VERIFIED"
        elif any(fin_fields):
            financials = "PARTIAL"
        shares = dataset.shares_status
        if dataset.shares is not None:
            ca = dataset.shares.corporate_action_status
    if result.dsp is not None and result.dsp.dcf.status == "CALCULATED":
        dcf = "VERIFIED"
    return {
        "security": listing.ticker,
        "identity": result.identity_status,
        "price": "UNKNOWN"
        if dataset is None
        else dataset.price_status,
        "financials": financials,
        "shares": shares,
        "ca": ca,
        "dcf": dcf,
        "filing_discovered": discovered,
        "document_acquired": acquired,
        "analysis_state": result.analysis_state,
        "mode": "UNKNOWN" if dataset is None else dataset.mode,
    }


@pytest.mark.network
def test_live_filing_detail_fixtures_and_dynamic() -> None:
    """Automatic index → XBRL/PDF detail. UNKNOWN/BLOCKED is a valid result."""
    global _DYNAMIC
    _skip_live()
    transport = NsePublicHttp(timeout_seconds=30.0)
    nse_eod = NseEodService(transport, mode="LIVE")
    nse_primary = NsePrimaryEvidenceService(transport, mode="LIVE")
    try:
        bundle = nse_eod.fetch_latest()
    except LookupError as exc:
        pytest.skip(f"LIVE NSE EOD not reachable: {exc}")
    orch = ResearchOrchestrator(
        security_master=_master(),
        nse_eod=nse_eod,
        nse_primary=nse_primary,
        production=False,
    )
    listings = [_listing(ticker, isin, mic) for ticker, isin, mic in _NAMED]
    dynamic = _dynamic_listings(5)
    _DYNAMIC = [item.ticker for item in dynamic]
    listings.extend(dynamic)
    samples: list[float] = []
    for listing in listings:
        started = perf_counter()
        result = orch.analyse(
            ResearchRequest(
                ticker=listing.ticker,
                company=listing.company_name,
                isin=listing.isin,
                mic=listing.mic,
                exchange=listing.exchange,
                fields=AUTO_REQUEST_GROUPS,
                mode="LIVE",
            ),
            nse_bundle=bundle,
        )
        samples.append(perf_counter() - started)
        assert result.production is False
        assert result.identity_status == "VERIFIED"
        acquired = "NO"
        if result.acquisition is not None and result.acquisition.evidence:
            if any(
                item.source_url and ("xbrl" in item.source_url.lower() or ".pdf" in item.source_url.lower())
                for item in result.acquisition.evidence
            ):
                acquired = "YES"
        if result.full_analysis:
            assert result.dataset is not None
            assert result.dataset.shares_status == "VERIFIED"
        _LIVE_COVERAGE.append(
            _coverage_row(listing, result, discovered=acquired, acquired=acquired)
        )
    assert len(_DYNAMIC) == 5
    assert set(_DYNAMIC).isdisjoint(_FIXTURES)
    ordered = sorted(samples)
    print("SIMPLE-23 LIVE coverage:", _LIVE_COVERAGE)
    print("SIMPLE-23 dynamic securities:", _DYNAMIC)
    print(
        "SIMPLE-23 live p50/p95 seconds:",
        ordered[len(ordered) // 2],
        ordered[-1] if ordered else None,
    )
    assert all(row["identity"] == "VERIFIED" for row in _LIVE_COVERAGE)
    assert all(row["mode"] in {"LIVE", "UNKNOWN"} for row in _LIVE_COVERAGE)
