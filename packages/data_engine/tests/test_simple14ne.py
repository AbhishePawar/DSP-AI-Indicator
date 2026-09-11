"""SIMPLE-14N-E — universal research planner. Issuers are fixtures, not workflows."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from data_engine.official_research.agents import (
    GeminiFindAgent,
    RESEARCH_CAPABILITIES,
    ROLE_CAPABILITY,
)
from data_engine.official_research.annual_report import select_annual_documents
from data_engine.official_research.currentness import CapitalEvent, is_current
from data_engine.official_research.documents import (
    DocumentCandidate,
    DocumentRecord,
    DocumentStore,
    document_version_relation,
)
from data_engine.official_research.extraction import (
    attack_corporate_actions,
    classify_capital_effect,
    classify_share_semantic_type,
    extract_labeled_field,
)
from data_engine.official_research.forensic_artifacts import (
    classify_forensic_artifact,
    is_promotable_artifact,
)
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.models import EvidenceItem, ResearchRequest, new_evidence_id
from data_engine.official_research.nse_primary import NseAnnouncementDocument
from data_engine.official_research.provider_router import route_research_roles
from data_engine.official_research.research_loop import MAX_RESEARCH_LOOPS, run_research_loop
from data_engine.official_research.research_plan import (
    build_research_plan,
    classify_research_capability,
    field_freshness_class,
    plan_report_block,
)
from data_engine.official_research.semantics import valuation_gate
from data_engine.official_research.source_policy import (
    SourcePolicy,
    classify_source_url,
    field_authority_chain,
    record_source_clash,
    source_authority_rank,
)
from data_engine.official_research.statement_tables import (
    PdfSpan,
    extract_field_from_statements,
    reconstruct_statement_pages,
)
from data_engine.security_master import SecurityMasterService, load_default_catalog
from data_engine.security_master.models import SecurityListing

_ENGINE = Path(__file__).resolve().parents[1] / "src" / "data_engine" / "official_research"
_FIXTURES = (
    ("RELIANCE", "INE002A01018", "XNSE"),
    ("20MICRONS", "INE144J01027", "XNSE"),
    ("21STCENMGM", "INE253B01015", "XNSE"),
)


def _master() -> SecurityMasterService:
    return SecurityMasterService(load_default_catalog())


def _listing(ticker: str, isin: str, mic: str = "XNSE") -> SecurityListing:
    resolved = _master().resolve(isin, isin=isin, mic=mic)
    assert resolved.status == "RESOLVED" and resolved.identity is not None
    assert resolved.identity.ticker == ticker
    assert resolved.identity.listing_id == f"{isin}.{mic}"
    return resolved.identity


def test_three_securities_produce_automatic_plans() -> None:
    plans = []
    for ticker, isin, mic in _FIXTURES:
        listing = _listing(ticker, isin, mic)
        plan = build_research_plan(
            listing,
            ResearchRequest(
                fields=(),
                isin=isin,
                mic=mic,
                ticker=ticker,
                request_id=f"14ne-{ticker}",
                purpose="research_report",
            ),
            artifact_path="artifacts/simple14nd_reconstruct.json",
        )
        block = plan_report_block(plan)
        assert block["ISIN"] == isin
        assert block["MIC"] == mic
        assert block["SECURITY"] == ticker
        assert "identity" in block["RESEARCH_TASKS"]
        assert block["STATUS"] in {"INCOMPLETE", "COMPLETE"}
        assert "primary" in block["SOURCE_CLASSES"]
        plans.append(block)
    assert len({item["ISIN"] for item in plans}) == 3
    reliance = plans[0]
    microns = plans[1]
    assert reliance["CAPABILITY"] == "equity"
    assert microns["CAPABILITY"] == "equity"
    assert "revenue" in reliance["REQUIRED_FIELDS"]
    assert "eod_close" in microns["MISSING_FIELDS"]
    assert microns["IR_STATUS"] == "DISCOVERY_REQUIRED"
    assert reliance["IR_STATUS"] in {"REGISTRY", "DOMAIN_ONLY"}
    assert reliance["DCF_STATUS"] == "UNAVAILABLE"


def test_bank_vs_ordinary_equity_capabilities() -> None:
    bank = _listing("HDFCBANK", "INE040A01034")
    ordinary = _listing("20MICRONS", "INE144J01027")
    assert classify_research_capability(bank) == "bank_equity"
    assert classify_research_capability(ordinary) == "equity"
    bank_plan = build_research_plan(bank, ResearchRequest(fields=(), isin=bank.isin, mic=bank.mic))
    eq_plan = build_research_plan(
        ordinary, ResearchRequest(fields=(), isin=ordinary.isin, mic=ordinary.mic)
    )
    assert "revenue" in bank_plan.not_applicable_fields
    assert "total_assets" in bank_plan.required_fields
    assert "revenue" in eq_plan.required_fields
    assert "revenue" not in bank_plan.missing_fields
    assert bank_plan.dcf_status == "UNAVAILABLE"


def test_unsupported_etf_is_capability_unavailable() -> None:
    listing = SecurityListing(
        ticker="DUMMYETF",
        company_name="Dummy Exchange Traded Fund",
        isin="INE000Z01000",
        exchange="NSE",
        mic="XNSE",
        security_type="etf",
        eligibility=False,
    )
    plan = build_research_plan(listing, ResearchRequest(fields=("nav",), isin=listing.isin, mic=listing.mic))
    assert plan.status == "CAPABILITY_UNAVAILABLE"
    assert plan.missing_fields == ()
    assert any(item.code == "CAPABILITY_UNAVAILABLE" for item in plan.failures)


def test_generic_share_semantics_not_issuer_tables() -> None:
    assert classify_share_semantic_type(
        "Weighted average number of equity shares outstanding"
    ) == "WEIGHTED_AVERAGE"
    assert classify_share_semantic_type(
        "Effect of potential equity shares outstanding"
    ) == "TRANCHE"
    assert classify_share_semantic_type(
        "Total outstanding equity shares"
    ) == "TOTAL_OUTSTANDING"
    wa = extract_labeled_field(
        "consolidated\nunit: actual\nas_of: 2026-03-31\n"
        "Weighted average number of equity shares outstanding 10,476,247,846\n",
        "shares_outstanding",
    )
    tranche = extract_labeled_field(
        "consolidated\nunit: actual\nas_of: 2026-03-31\n"
        "Effect of potential equity shares outstanding 70,490,586\n",
        "shares_outstanding",
    )
    assert wa is None or wa.raw_value != "10476247846"
    assert tranche is None or tranche.raw_value != "70490586"


def test_buyback_triggers_currentness_review_without_arithmetic() -> None:
    retrieved = datetime(2026, 9, 11, tzinfo=UTC)
    events = attack_corporate_actions(
        "as_of: 2026-06-26\nThe company completed a buyback of equity shares.\n",
        event_date=date(2026, 6, 26),
    )
    assert any(item.event_type == "buyback" for item in events)
    assert classify_capital_effect("buyback") == "DECREASE"
    assert classify_capital_effect("acquisition") == "UNKNOWN"
    assert classify_capital_effect("merger") == "UNKNOWN"
    assert (
        is_current(
            as_of=date(2026, 3, 31),
            current_through=date(2026, 3, 31),
            retrieved_at=retrieved,
            corporate_actions=(CapitalEvent("buyback", date(2026, 6, 26)),),
            valuation_date=date(2026, 9, 11),
        )
        is False
    )


def test_stale_reconstruct_artifact_cannot_enter_plan_or_loop() -> None:
    path = "artifacts/simple14nd_reconstruct.json"
    label = classify_forensic_artifact(path)
    assert label["status"] == "STALE"
    assert label["promotable"] is False
    assert is_promotable_artifact(path) is False
    listing = _listing("20MICRONS", "INE144J01027")
    plan = build_research_plan(
        listing,
        ResearchRequest(fields=("revenue",), isin=listing.isin, mic=listing.mic),
        existing_verified=(),
        artifact_path=path,
    )
    assert "revenue" in plan.missing_fields
    loop = run_research_loop(
        listing,
        ResearchRequest(fields=("revenue",), isin=listing.isin, mic=listing.mic),
        artifact_path=path,
    )
    assert loop.iterations <= MAX_RESEARCH_LOOPS
    assert all("simple14nd_reconstruct" not in url for url in loop.discovered_urls)
    assert all("/investors" not in url.lower() for url in loop.discovered_urls)


def test_keyword_url_is_not_trusted() -> None:
    url = "https://evil.example/company/investor/annual-report.pdf"
    assert classify_source_url(url) == "unknown"
    assert SourcePolicy().may_verify(url) is False
    assert classify_source_url("https://www.screener.in/company/ANY/") == "approved_research"
    assert SourcePolicy().may_verify("https://www.screener.in/company/ANY/") is False
    clash = record_source_clash(
        field="revenue",
        primary_url="https://nsearchives.nseindia.com/annual.pdf",
        primary_value="100",
        research_url="https://www.screener.in/company/ANY/",
        research_value="90",
    )
    assert clash["winner"] == "primary"
    assert clash["cross_check"] == "CONFLICT"
    assert clash["silent_overwrite"] is False
    assert source_authority_rank("eod_close", "primary", source_type="exchange_eod") < (
        source_authority_rank("eod_close", "approved_research")
    )
    assert field_authority_chain("eod_close")[0] == "nse_bse"
    assert field_authority_chain("revenue")[0] == "company_or_exchange_filing"


def test_screener_cannot_become_verified_without_primary() -> None:
    item = EvidenceItem(
        evidence_id=new_evidence_id(),
        company="20 Microns Limited",
        ticker="20MICRONS",
        isin="INE144J01027",
        mic="XNSE",
        field="revenue",
        value="100",
        as_of=date(2026, 3, 31),
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        source="Screener",
        source_type="approved_research",
        source_url="https://www.screener.in/company/20MICRONS/",
        document_date=date(2026, 3, 31),
        evidence_locator="screener",
        currency="INR",
        unit="crore",
        statement_basis="consolidated",
        agent="official_research",
        identity_status="PASS",
        semantic_status="PASS",
        freshness_status="PASS",
        corporate_action_status="PASS",
        confidence="medium",
        stage="RAW",
        status="UNKNOWN",
        mode="MOCK",
        document_hash="abc",
    )
    promoted = EvidenceJudge().promote(item)
    assert promoted.stage != "VERIFIED"
    assert promoted.status != "VERIFIED"
    assert promoted.document_hash == "abc"


def test_document_discovery_ranking_and_rejection() -> None:
    selected = select_annual_documents(
        (
            NseAnnouncementDocument(
                "Investor presentation FY2026",
                "https://nsearchives.nseindia.com/presentation.pdf",
                date(2026, 5, 1),
                "other",
            ),
            NseAnnouncementDocument(
                "Audited consolidated financial statements FY2026",
                "https://nsearchives.nseindia.com/audited-cfs.pdf",
                date(2026, 5, 2),
                "annual_report",
            ),
            NseAnnouncementDocument(
                "Integrated Annual Report FY2026",
                "https://nsearchives.nseindia.com/iar.pdf",
                date(2026, 5, 3),
                "annual_report",
            ),
            NseAnnouncementDocument(
                "Annual Report FY2026",
                "https://nsearchives.nseindia.com/ar.pdf",
                date(2026, 5, 4),
                "annual_report",
            ),
        )
    )
    assert selected[0].title.startswith("Integrated Annual Report")
    assert all("presentation" not in item.title.lower() for item in selected)
    candidate = DocumentCandidate(
        url=selected[0].url,
        host="nsearchives.nseindia.com",
        source_type="regulator",
        document_type=selected[0].kind,
        company="20 Microns Limited",
        isin="INE144J01027",
        period="FY2026",
        basis="consolidated",
        publication_date=selected[0].as_of,
        retrieved_at=None,
        document_hash=None,
        status="CANDIDATE",
    )
    assert candidate.status == "CANDIDATE"
    assert document_version_relation(
        url_a="https://a/x.pdf", hash_a="h1", url_b="https://a/x.pdf", hash_b="h1"
    ) == "reuse"
    assert document_version_relation(
        url_a="https://a/x.pdf", hash_a="h1", url_b="https://b/y.pdf", hash_b="h1"
    ) == "alias"
    assert document_version_relation(
        url_a="https://a/x.pdf", hash_a="h1", url_b="https://a/x.pdf", hash_b="h2"
    ) == "new_version"


def test_document_store_preserves_versions() -> None:
    store = DocumentStore()
    first = DocumentRecord(
        url="https://nsearchives.nseindia.com/a.pdf",
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        http_status=200,
        content_type="application/pdf",
        content_length=4,
        document_hash="aa",
        payload=b"%PDF",
        company_isin="INE144J01027",
        company_mic="XNSE",
    )
    reused = store.put(first)
    alias = store.put(
        DocumentRecord(
            url="https://www.nseindia.com/copy.pdf",
            retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
            http_status=200,
            content_type="application/pdf",
            content_length=4,
            document_hash="aa",
            payload=b"%PDF",
            company_isin="INE144J01027",
            company_mic="XNSE",
        )
    )
    newer = store.put(
        DocumentRecord(
            url="https://nsearchives.nseindia.com/a.pdf",
            retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
            http_status=200,
            content_type="application/pdf",
            content_length=5,
            document_hash="bb",
            payload=b"%PDF2",
            company_isin="INE144J01027",
            company_mic="XNSE",
        )
    )
    assert reused is first
    assert alias.document_hash == "aa"
    assert newer.document_hash == "bb"
    assert len(store.versions()) == 2


def test_two_statement_dialects_share_generic_extractor() -> None:
    million = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=(
            "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS\nRevenue from operations\nProfit for the year\n",
        ),
        precomputed_spans=(
            (
                PdfSpan(1, 80, 740, "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS"),
                PdfSpan(1, 80, 700, "Year ended"),
                PdfSpan(1, 400, 700, "March 31, 2026"),
                PdfSpan(1, 520, 700, "March 31, 2025"),
                PdfSpan(1, 70, 650, "Revenue from operations"),
                PdfSpan(1, 400, 650, "926,240"),
                PdfSpan(1, 520, 650, "890,884"),
                PdfSpan(1, 80, 80, "(I in millions, except share and per share data, unless otherwise stated)"),
                PdfSpan(1, 80, 50, "Consolidated Statements of Profit and Loss"),
            ),
        ),
    )
    crore = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("Consolidated Statement of Profit and Loss\nRevenue from operations\nProfit for the year\n",),
        precomputed_spans=(
            (
                PdfSpan(1, 80, 740, "Consolidated Statement of Profit and Loss"),
                PdfSpan(1, 80, 720, "(H crore)"),
                PdfSpan(1, 400, 700, "March 31, 2026"),
                PdfSpan(1, 520, 700, "March 31, 2025"),
                PdfSpan(1, 70, 650, "Revenue from operations"),
                PdfSpan(1, 400, 650, "267,021"),
                PdfSpan(1, 520, 650, "255,324"),
            ),
        ),
    )
    left = extract_field_from_statements(million, "revenue")
    right = extract_field_from_statements(crore, "revenue")
    assert left is not None and left.raw_value == "926240" and left.raw_unit == "million"
    assert right is not None and right.raw_value == "267021" and right.raw_unit == "crore"


def test_research_loop_discovers_generic_primary_locators() -> None:
    listing = _listing("21STCENMGM", "INE253B01015")
    loop = run_research_loop(
        listing,
        ResearchRequest(fields=("revenue", "shares_outstanding"), isin=listing.isin, mic=listing.mic),
    )
    assert loop.iterations <= MAX_RESEARCH_LOOPS
    assert loop.iterations >= 1
    assert any("nseindia.com" in url for url in loop.discovered_urls)
    assert all("screener.in" not in url for url in loop.discovered_urls)
    assert all("yahoo" not in url.lower() for url in loop.discovered_urls)
    assert loop.plan.status == "INCOMPLETE"
    bank = _listing("HDFCBANK", "INE040A01034")
    bank_loop = run_research_loop(
        bank,
        ResearchRequest(fields=("net_income",), isin=bank.isin, mic=bank.mic),
    )
    assert any("hdfc.bank.in" in url for url in bank_loop.discovered_urls)
    assert any("nseindia.com" in url for url in bank_loop.discovered_urls)


def test_freshness_is_field_specific() -> None:
    assert field_freshness_class("eod_close") == "session_or_latest_eod"
    assert field_freshness_class("revenue") == "latest_audited_period"
    assert field_freshness_class("shares_outstanding") == "latest_count_plus_ca_review"


def test_dcf_unavailable_does_not_block_other_research() -> None:
    listing = _listing("RELIANCE", "INE002A01018")
    plan = build_research_plan(
        listing,
        ResearchRequest(fields=("revenue", "net_income"), isin=listing.isin, mic=listing.mic),
        existing_verified=("revenue",),
    )
    assert plan.dcf_status == "UNAVAILABLE"
    assert "net_income" in plan.missing_fields
    assert "revenue" in plan.existing_verified
    gate = valuation_gate(cfo=False, capex=False, net_income=False, shares=False)
    assert gate.status == "UNAVAILABLE"


def test_provider_roles_are_interchangeable_without_apis() -> None:
    assert RESEARCH_CAPABILITIES == ("FIND", "VERIFY", "ATTACK", "REVIEW")
    assert ROLE_CAPABILITY["gemini_find"] == "FIND"
    assert GeminiFindAgent().available() is False
    assigned = route_research_roles(
        {"gemini": False, "chatgpt": True, "claude": True, "deep_search": False}
    )
    assert assigned["FIND"] == "chatgpt"
    assert assigned["VERIFY"] == "claude"
    assert assigned["ATTACK"] is None


def test_new_security_does_not_require_custom_parser() -> None:
    forbidden = (
        "WIPRO",
        "TCS",
        "INFY",
        "HDFCBANK",
        "RELIANCE",
        "ASIANPAINT",
        "HINDUNILVR",
        "20MICRONS",
        "21STCENMGM",
    )
    for name in (
        "research_plan.py",
        "research_loop.py",
        "provider_router.py",
        "research_failures.py",
    ):
        text = (_ENGINE / name).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text
    extraction = (_ENGINE / "extraction.py").read_text(encoding="utf-8")
    assert "WIPRO" not in extraction
    assert "HDFCBANK" not in extraction
