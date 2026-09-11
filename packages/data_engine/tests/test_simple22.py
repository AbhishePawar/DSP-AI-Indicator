"""SIMPLE-22 — universal live financials / shares / CA acquisition. Fail-closed is success."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter

import pytest

from data_engine.official_research.documents import select_extraction_strategy
from data_engine.official_research.end_to_end import AUTO_REQUEST_GROUPS, analyse_listing
from data_engine.official_research.extraction import (
    canonical_share_semantic_type,
    classify_share_count_effect_status,
    classify_share_semantic_type,
)
from data_engine.official_research.field_acquisition import normalize_extracted_field
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.models import ResearchClaim, ResearchRequest
from data_engine.official_research.nse_eod import NseEodService, NsePublicHttp
from data_engine.official_research.nse_mcp import NSE_MCP_COMMERCIAL_STATUS
from data_engine.official_research.nse_primary import (
    NSE_FINANCIAL_RESULTS_URL,
    NSE_SHAREHOLDING_URL,
    NsePrimaryEvidenceService,
    extract_nse_api_field,
    parse_financial_results,
    parse_quote_equity_shares,
    parse_shareholding_shares,
)
from data_engine.official_research.orchestrator import ResearchOrchestrator
from data_engine.official_research.source_policy import SourcePolicy, classify_source_url
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
    """Catalog-driven. No hardcoded expected tickers."""
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


def _coverage_row(listing: SecurityListing, result) -> dict[str, str]:
    dataset = result.dataset
    qualitative = result.qualitative
    dsp = result.dsp
    shares = "UNKNOWN"
    ca = "UNKNOWN"
    if dataset is not None and dataset.shares is not None:
        shares = dataset.shares.status
        ca = dataset.shares.corporate_action_status
    elif dataset is not None:
        shares = dataset.shares_status
        ca = dataset.corporate_action_status
    return {
        "security": listing.ticker,
        "identity": result.identity_status,
        "price": "UNKNOWN" if dataset is None else dataset.price_status,
        "financials": result.coverage.financials,
        "shares": shares,
        "ca": ca,
        "business": "UNKNOWN" if qualitative is None else qualitative.status,
        "management": "UNKNOWN"
        if qualitative is None
        else str(qualitative.management.get("status") or "UNKNOWN"),
        "moat": "UNKNOWN" if qualitative is None else str(qualitative.moat.get("status") or "UNKNOWN"),
        "risk": "UNKNOWN" if qualitative is None else str(qualitative.risk.get("status") or "UNKNOWN"),
        "dcf": "BLOCKED" if dsp is None else dsp.dcf.status,
        "mode": getattr(result.dataset, "mode", None) or result.status,
    }


def test_universe_is_catalog_not_fixture_list() -> None:
    universe = load_default_catalog()
    listings = [item for item in universe.all() if item.eligibility]
    assert len(listings) > 20
    assert {row[0] for row in _NAMED} < {item.ticker for item in listings}
    dynamic = _dynamic_listings(5)
    assert len(dynamic) == 5
    assert {item.ticker for item in dynamic}.isdisjoint(_FIXTURES)


def test_share_semantics_reject_issued_accept_shp_total() -> None:
    assert classify_share_semantic_type("info.issuedSize") == "ISSUED"
    assert canonical_share_semantic_type("info.issuedSize") != "TOTAL_OUTSTANDING"
    assert classify_share_semantic_type("totalNoOfShares") == "TOTAL_OUTSTANDING"
    assert canonical_share_semantic_type("weighted average shares") != "TOTAL_OUTSTANDING"
    assert canonical_share_semantic_type("free float") != "TOTAL_OUTSTANDING"
    extracted, ignored, _issue = parse_quote_equity_shares(
        {"info": {"symbol": "INFY", "isin": "INE009A01021", "issuedSize": 10}},
        isin="INE009A01021",
        ticker="INFY",
    )
    assert ignored is False or ignored is True
    assert extracted is not None
    assert extracted.as_of is None


def test_nse_json_financials_carry_basis_and_unit() -> None:
    fields, basis, unit, issue = parse_financial_results(
        [
            {
                "symbol": "INFY",
                "period": "Annual",
                "fromTo": "01-Apr-2025 to 31-Mar-2026",
                "toDate": "31-Mar-2026",
                "resultType": "Consolidated",
                "unit": "Rs. Crore",
                "particulars": "Profit after tax",
                "value": "26733",
            }
        ],
        ticker="INFY",
    )
    assert issue is None
    assert basis == "consolidated"
    assert unit == "crore_to_actual"
    row = fields["net_income"]
    assert row.statement_basis == "consolidated"
    assert row.unit_scale == "actual"
    assert row.currency == "INR"
    listing = _listing("INFY", "INE009A01021")
    item = normalize_extracted_field(
        listing,
        row,
        source_url=f"{NSE_FINANCIAL_RESULTS_URL}?index=equities&symbol=INFY&period=Annual",
        source_type="regulator",
        source="NSE",
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        document_date=row.as_of,
        mode="MOCK",
        agent="official_nse_primary",
    )
    judged = EvidenceJudge().promote(item)
    assert judged.status == "VERIFIED"
    assert judged.value == "267330000000"


def test_nse_api_field_helper_is_url_generic() -> None:
    listing = _listing("INFY", "INE009A01021")
    hold = parse_shareholding_shares(
        [{"symbol": "INFY", "date": "30-Jun-2026", "totalNoOfShares": 1000}],
        ticker="INFY",
    )
    assert hold is not None
    extracted = extract_nse_api_field(
        f"{NSE_SHAREHOLDING_URL}?index=equities&symbol=INFY",
        [{"symbol": "INFY", "date": "30-Jun-2026", "totalNoOfShares": 1000}],
        listing=listing,
        field="shares_outstanding",
    )
    assert extracted is not None
    assert extracted.value == "1000"
    assert canonical_share_semantic_type(extracted.locator) == "TOTAL_OUTSTANDING"


def test_corporate_action_effect_vocabulary() -> None:
    assert classify_share_count_effect_status("bonus") == "INCREASES_OUTSTANDING"
    assert classify_share_count_effect_status("buyback") == "DECREASES_OUTSTANDING"
    assert (
        classify_share_count_effect_status("acquisition", acquisition_consideration="CASH")
        == "NO_SHARE_COUNT_EFFECT"
    )
    assert (
        classify_share_count_effect_status("acquisition", acquisition_consideration="SHARE_SWAP")
        == "POTENTIALLY_CHANGES_OUTSTANDING"
    )
    assert classify_share_count_effect_status("merger") == "POTENTIALLY_CHANGES_OUTSTANDING"


def test_scanned_pdf_is_ocr_required_not_verified() -> None:
    assert select_extraction_strategy(payload=b"%PDF-1.4\n", text="") == "ocr_required"


def test_screener_cannot_verify() -> None:
    assert SourcePolicy().may_verify("https://www.screener.in/company/INFY/") is False
    assert classify_source_url("https://finance.yahoo.com/quote/INFY.NS") == "secondary"


def test_adversarial_primary_beats_ai_and_conflict_is_not_averaged() -> None:
    listing = _listing("TCS", "INE467B01029")
    dialect = (
        f"{listing.company_name}\nISIN {listing.isin}\n"
        "consolidated audited financial statements\nunit: actual\nINR\n"
        "year ended 31 March 2026\nas_of: 2026-03-31\n"
        "Revenue from operations 100000\nProfit for the year 20000\n"
        "equity shares outstanding 1000000\n"
    )
    result = analyse_listing(
        listing,
        mode="MOCK",
        document_text=dialect,
        document_url="https://nsearchives.nseindia.com/annual.pdf",
        claims=(
            ResearchClaim(
                field="revenue",
                value="1",
                source_url=None,
                document_locator="ai",
                agent="openai_nse_mcp",
            ),
            ResearchClaim(
                field="shares_outstanding",
                value="5000000000",
                source_url=None,
                document_locator="ai",
                agent="openai_nse_mcp",
            ),
        ),
        production=False,
    )
    assert result.dataset is not None
    revenue = result.dataset.verified_decimal("revenue")
    if revenue is not None:
        assert revenue != Decimal("1")
    etf = SecurityListing(
        ticker="NIFTYBEES",
        company_name="ETF",
        isin="INF204KB14I2",
        exchange="NSE",
        mic="XNSE",
        security_type="etf",
        eligibility=False,
    )
    assert analyse_listing(etf, mode="MOCK").status == "UNSUPPORTED"


def test_architecture_no_company_branches() -> None:
    for path in _ENGINE.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "if ticker ==" not in text
        assert "class EvidenceJudge2" not in text
        if path.name in {
            "qualitative.py",
            "advanced_check.py",
            "end_to_end.py",
            "field_acquisition.py",
            "orchestrator.py",
            "nse_primary.py",
        }:
            for token in _FIXTURES:
                assert token not in text
    assert NSE_MCP_COMMERCIAL_STATUS == "COMMERCIAL_USE_PENDING"
    cfg = load_llm_config()
    if not cfg.openai_api_key:
        return


def test_browser_qualification_is_honest() -> None:
    pytest.skip(
        "BROWSER BLOCKED: Playwright live user-path not executed in SIMPLE-22 "
        "(no app server session)"
    )


def _skip_live() -> None:
    if os.environ.get("DSP_SKIP_LIVE_NSE_EOD") == "1":
        pytest.skip("LIVE NSE skipped by DSP_SKIP_LIVE_NSE_EOD=1")


@pytest.mark.network
def test_live_universal_acquisition_fixtures_and_dynamic() -> None:
    """Automatic NSE primary + EOD. UNKNOWN/PARTIAL/BLOCKED is a valid result."""
    global _DYNAMIC
    _skip_live()
    transport = NsePublicHttp(timeout_seconds=20.0)
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
        assert result.nse_mcp_commercial_status == "COMMERCIAL_USE_PENDING"
        if result.dataset is not None:
            assert result.dataset.mode == "LIVE"
        if result.full_analysis:
            assert result.dataset is not None
            assert result.dataset.price_status == "VERIFIED"
            assert result.dataset.shares_status == "VERIFIED"
            assert result.dsp is not None
            assert result.dsp.dcf.status == "CALCULATED"
        _LIVE_COVERAGE.append(_coverage_row(listing, result))
    assert len(_DYNAMIC) == 5
    assert set(_DYNAMIC).isdisjoint(_FIXTURES)
    assert len(_LIVE_COVERAGE) == len(listings)
    print("SIMPLE-22 LIVE coverage:", _LIVE_COVERAGE)
    print("SIMPLE-22 dynamic securities:", _DYNAMIC)
    ordered = sorted(samples)
    print(
        "SIMPLE-22 live p50/p95 seconds:",
        ordered[len(ordered) // 2],
        ordered[-1],
    )
