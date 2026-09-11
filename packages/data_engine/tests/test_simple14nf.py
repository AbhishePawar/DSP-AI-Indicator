"""SIMPLE-14N-F — universal planned-field acquisition. Issuers are fixtures, not workflows."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from data_engine.official_research.currentness import CapitalEvent, currentness_label
from data_engine.official_research.documents import (
    DocumentRecord,
    RetrievalFailure,
    identify_document_characteristics,
    select_extraction_strategy,
)
from data_engine.official_research.dsp_gate import dsp_gate
from data_engine.official_research.extraction import (
    attack_corporate_actions,
    classify_acquisition_consideration,
    classify_capital_effect,
    classify_share_semantic_type,
)
from data_engine.official_research.field_acquisition import (
    ACQUISITION_STAGES,
    VALUATION_SHARE_SEMANTIC,
    acquire_planned_fields,
)
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.models import EvidenceItem, ResearchRequest, new_evidence_id
from data_engine.official_research.nse_mcp import NSE_MCP_COMMERCIAL_STATUS
from data_engine.official_research.research_failures import (
    DOMAIN_FAILURE_CODES,
    TRANSPORT_FAILURE_CODES,
    is_transport_failure,
    map_retrieval_to_failure_code,
)
from data_engine.official_research.research_plan import (
    build_research_plan,
    expand_requested_fields,
    field_retrieval_strategy,
    field_source_priority,
    plan_report_block,
)
from data_engine.security_master import SecurityMasterService, load_default_catalog
from data_engine.security_master.models import SecurityListing

_ENGINE = Path(__file__).resolve().parents[1] / "src" / "data_engine" / "official_research"
_NAMED = (
    ("TCS", "INE467B01029", "XNSE"),
    ("INFY", "INE009A01021", "XNSE"),
    ("RELIANCE", "INE002A01018", "XNSE"),
    ("HDFCBANK", "INE040A01034", "XNSE"),
    ("WIPRO", "INE075A01022", "XNSE"),
    ("20MICRONS", "INE144J01027", "XNSE"),
)
_PRIMARY = "https://nsearchives.nseindia.com/annual.pdf"
_SCREENER = "https://www.screener.in/company/ANY/"
_AS_OF = date(2026, 3, 31)
_RETRIEVED = datetime(2026, 9, 11, tzinfo=UTC)
_STATEMENT = (
    "consolidated audited financial statements\n"
    "unit: actual\n"
    "₹ INR\n"
    "year ended 31 March 2026\n"
    "as_of: 2026-03-31\n"
    "Statement of profit and loss\n"
    "Revenue from operations 100000\n"
    "Profit for the year 20000\n"
    "Balance sheet\n"
    "Total equity 50000\n"
    "Cash and cash equivalents 4000\n"
    "Statement of cash flows\n"
    "Net cash from operating activities 15000\n"
    "equity shares outstanding 1000000\n"
)


def _master() -> SecurityMasterService:
    return SecurityMasterService(load_default_catalog())


def _listing(ticker: str, isin: str, mic: str = "XNSE") -> SecurityListing:
    resolved = _master().resolve(isin, isin=isin, mic=mic)
    assert resolved.status == "RESOLVED" and resolved.identity is not None
    assert resolved.identity.ticker == ticker
    return resolved.identity


def _raw(
    listing: SecurityListing,
    field: str,
    value: str,
    *,
    source_url: str = _PRIMARY,
    source_type: str = "regulator",
    source: str = "NSE",
    agent: str = "official_research",
    locator: str = "row",
    as_of: date | None = _AS_OF,
    unit: str | None = "actual",
    basis: str | None = "consolidated",
    freshness: str = "PASS",
    semantic: str = "PASS",
    identity: str = "PASS",
    ca: str = "PASS",
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=new_evidence_id(),
        company=listing.company_name,
        ticker=listing.ticker,
        isin=listing.isin,
        mic=listing.mic,
        field=field,
        value=value,
        as_of=as_of,
        retrieved_at=_RETRIEVED,
        source=source,
        source_type=source_type,
        source_url=source_url,
        document_date=as_of,
        evidence_locator=locator,
        currency="INR",
        unit=unit,
        statement_basis=basis,
        agent=agent,
        identity_status=identity,
        semantic_status=semantic,
        freshness_status=freshness,
        corporate_action_status=ca,
        confidence=None,
        stage="RAW",
        status="UNKNOWN",
        mode="MOCK",
        current_through=as_of,
        document_hash="doc-hash",
    )


def _request(listing: SecurityListing, fields: tuple[str, ...]) -> ResearchRequest:
    return ResearchRequest(
        fields=fields,
        isin=listing.isin,
        mic=listing.mic,
        ticker=listing.ticker,
        mode="MOCK",
        request_id=f"14nf-{listing.ticker}",
        purpose="research_report",
    )


def test_request_groups_expand_without_issuer_plans() -> None:
    concrete, groups = expand_requested_fields(
        ("IDENTITY", "PRICE", "FINANCIALS", "SHARES", "VALUATION_INPUTS")
    )
    assert "PRICE" in groups
    assert "eod_close" in concrete
    assert "net_income" in concrete
    assert "shares_outstanding" in concrete
    listing = _listing("TCS", "INE467B01029")
    plan = build_research_plan(listing, _request(listing, ("PRICE", "SHARES")))
    block = plan_report_block(plan)
    assert block["REQUESTED_FIELDS"] == ["eod_close", "shares_outstanding"]
    assert "SOURCE_PRIORITY" in block
    assert field_source_priority("eod_close")[0] == "nse_bse"
    assert field_retrieval_strategy("net_income") == "official_financial_statement"
    assert field_retrieval_strategy("shares_outstanding") == (
        "official_share_capital_plus_corporate_actions"
    )


def test_same_engine_across_named_and_dynamic_securities() -> None:
    master = _master()
    catalog = load_default_catalog()
    named_isins = {isin for _, isin, _ in _NAMED}
    dynamic = next(
        item
        for item in catalog.all()
        if item.eligibility
        and item.mic == "XNSE"
        and item.isin not in named_isins
        and item.security_type == "equity"
    )
    listings = [_listing(*row) for row in _NAMED]
    listings.append(dynamic)
    assert dynamic.ticker not in {row[0] for row in _NAMED}
    statuses = []
    for listing in listings:
        price_as_of = date(2026, 9, 11)
        result = acquire_planned_fields(
            listing,
            _request(listing, ("PRICE", "FINANCIALS", "SHARES")),
            candidates={
                "eod_close": (
                    _raw(
                        listing,
                        "eod_close",
                        "100.00",
                        as_of=price_as_of,
                        unit=None,
                        basis=None,
                        source_type="exchange_eod",
                    ),
                )
            },
            document_text=_STATEMENT,
            document_url=_PRIMARY,
            production=False,
        )
        assert result.security_type_status != "UNSUPPORTED_SECURITY_TYPE"
        assert result.nse_mcp_commercial_status == "COMMERCIAL_USE_PENDING"
        assert set(result.timings) >= {"plan", *ACQUISITION_STAGES}
        assert all(value >= 0 for value in result.timings.values())
        by_field = {item.field: item.status for item in result.outcomes}
        assert by_field.get("eod_close") == "VERIFIED"
        assert by_field.get("net_income") == "VERIFIED"
        assert by_field.get("shares_outstanding") == "VERIFIED"
        if listing.ticker == "HDFCBANK":
            assert "revenue" not in by_field
        else:
            assert by_field.get("revenue") == "VERIFIED"
        statuses.append(tuple(sorted(by_field)))
    assert len(listings) == 7
    assert len({listing.isin for listing in listings}) == 7


def test_bank_equity_does_not_force_ordinary_dcf_inputs() -> None:
    bank = _listing("HDFCBANK", "INE040A01034")
    ordinary = _listing("INFY", "INE009A01021")
    bank_result = acquire_planned_fields(
        bank,
        _request(bank, ("FINANCIALS",)),
        document_text=_STATEMENT,
        document_url=_PRIMARY,
    )
    eq_result = acquire_planned_fields(
        ordinary,
        _request(ordinary, ("FINANCIALS",)),
        document_text=_STATEMENT,
        document_url=_PRIMARY,
    )
    assert "revenue" not in {item.field for item in bank_result.outcomes}
    assert "revenue" in {item.field for item in eq_result.outcomes}
    assert "dcf" in {item.lower() for item in bank_result.blocked_calculations} or "DCF" in bank_result.blocked_calculations


def test_unsupported_security_type_fails_closed() -> None:
    listing = SecurityListing(
        ticker="DUMMYETF",
        company_name="Dummy Exchange Traded Fund",
        isin="INE000Z01000",
        exchange="NSE",
        mic="XNSE",
        security_type="etf",
        eligibility=False,
    )
    result = acquire_planned_fields(
        listing,
        ResearchRequest(fields=("PRICE", "VALUATION_INPUTS"), isin=listing.isin, mic=listing.mic, mode="MOCK"),
        document_text=_STATEMENT,
        document_url=_PRIMARY,
    )
    assert result.security_type_status == "UNSUPPORTED_SECURITY_TYPE"
    assert result.verified_fields == ()
    assert "DCF" in result.blocked_calculations or "dcf" in result.blocked_calculations


def test_share_semantics_gate_valuation_denominator() -> None:
    listing = _listing("WIPRO", "INE075A01022")
    assert classify_share_semantic_type("Total outstanding equity shares") == "TOTAL_OUTSTANDING"
    assert classify_share_semantic_type("Issued share capital") == "ISSUED"
    assert classify_share_semantic_type("Paid-up capital") == "PAID_UP"
    assert classify_share_semantic_type("Listed quantity of shares") == "LISTED"
    assert classify_share_semantic_type("Free float shares") == "FREE_FLOAT"
    assert classify_share_semantic_type("Promoter holding") == "PROMOTER"
    assert classify_share_semantic_type("Weighted average number of equity shares") == "WEIGHTED_AVERAGE"
    assert classify_share_semantic_type("Authorized share capital") == "AUTHORIZED"
    paid = acquire_planned_fields(
        listing,
        _request(listing, ("SHARES",)),
        candidates={
            "shares_outstanding": (
                _raw(
                    listing,
                    "shares_outstanding",
                    "999",
                    locator="paid-up capital",
                    unit="shares",
                    basis=None,
                ),
            )
        },
    )
    outcome = paid.outcomes[0]
    assert outcome.status == "UNKNOWN"
    assert outcome.semantic_type != VALUATION_SHARE_SEMANTIC
    assert any(item.code == "SEMANTIC_FAILURE" for item in outcome.failures)


def test_acquisition_does_not_imply_share_change() -> None:
    assert classify_capital_effect("acquisition") == "UNKNOWN"
    assert classify_acquisition_consideration("The company completed an acquisition.") == "UNKNOWN"
    assert classify_acquisition_consideration("cash consideration for the acquisition") == "CASH"
    assert classify_acquisition_consideration("the deal was a share swap") == "SHARE_SWAP"
    assert classify_acquisition_consideration(
        "consideration in cash and share swap"
    ) == "MIXED"
    events = attack_corporate_actions(
        "as_of: 2026-06-26\nThe company completed an acquisition for cash consideration.\n",
        event_date=date(2026, 6, 26),
    )
    assert any(item.event_type == "acquisition" and item.capital_changing is False for item in events)
    listing = _listing("RELIANCE", "INE002A01018")
    result = acquire_planned_fields(
        listing,
        _request(listing, ("SHARES",)),
        document_text=_STATEMENT + "\nThe company completed an acquisition for cash consideration.\n",
        document_url=_PRIMARY,
        capital_events=events,
    )
    shares = next(item for item in result.outcomes if item.field == "shares_outstanding")
    assert shares.status == "VERIFIED"


def test_buyback_stales_share_count() -> None:
    listing = _listing("TCS", "INE467B01029")
    events = (CapitalEvent("buyback", date(2026, 6, 26), capital_changing=True),)
    result = acquire_planned_fields(
        listing,
        _request(listing, ("SHARES",)),
        document_text=_STATEMENT,
        document_url=_PRIMARY,
        capital_events=events,
    )
    shares = result.outcomes[0]
    assert shares.status == "REFRESH_REQUIRED"


def test_currentness_does_not_confuse_retrieved_at_with_as_of() -> None:
    label = currentness_label(
        field="revenue",
        as_of=_AS_OF,
        retrieved_at=_RETRIEVED,
        freshness_status="PASS",
    )
    assert label == "CURRENT"
    assert _RETRIEVED.date() != _AS_OF
    missing = currentness_label(
        field="revenue",
        as_of=None,
        retrieved_at=_RETRIEVED,
        freshness_status="PASS",
    )
    assert missing == "UNKNOWN"


def test_unknown_units_period_and_basis_fail_closed() -> None:
    listing = _listing("INFY", "INE009A01021")
    no_units = acquire_planned_fields(
        listing,
        _request(listing, ("net_income",)),
        document_text="consolidated\nyear ended 31 March 2026\nProfit for the year 20\n",
        document_url=_PRIMARY,
    )
    assert no_units.outcomes[0].status == "UNKNOWN"
    no_basis = acquire_planned_fields(
        listing,
        _request(listing, ("net_income",)),
        document_text="unit: actual\n₹\nyear ended 31 March 2026\nProfit for the year 20\n",
        document_url=_PRIMARY,
    )
    assert no_basis.outcomes[0].status == "UNKNOWN"
    no_period = acquire_planned_fields(
        listing,
        _request(listing, ("net_income",)),
        document_text="consolidated\nunit: actual\n₹\nProfit for the year 20\n",
        document_url=_PRIMARY,
    )
    assert no_period.outcomes[0].status == "UNKNOWN"


def test_document_characteristics_are_generic() -> None:
    chars = identify_document_characteristics(
        url=_PRIMARY,
        text=_STATEMENT,
        retrieved_at=_RETRIEVED,
        content_hash="abc",
    )
    assert chars.document_type in {"annual_report", "financial_statements"}
    assert chars.statement_basis == "consolidated"
    assert chars.audit_status == "audited"
    assert chars.currency == "INR"
    assert chars.units == "actual"
    assert chars.url == _PRIMARY
    assert chars.content_hash == "abc"
    assert chars.retrieved_at == _RETRIEVED
    assert select_extraction_strategy(payload=b"%PDF-1.4\n", text="") == "ocr_required"
    assert select_extraction_strategy(payload=b"%PDF-1.4\n", text=_STATEMENT) in {
        "native_pdf_text",
        "table",
    }
    record = DocumentRecord(
        url=_PRIMARY,
        retrieved_at=_RETRIEVED,
        http_status=200,
        content_type="application/pdf",
        content_length=4,
        document_hash="aa",
        payload=b"%PDF",
        company_isin="INE467B01029",
        company_mic="XNSE",
        document_date="2026-03-31",
    )
    listing = _listing("TCS", "INE467B01029")
    result = acquire_planned_fields(
        listing,
        _request(listing, ("net_income",)),
        documents=(record,),
        document_text=_STATEMENT,
        document_url=_PRIMARY,
    )
    assert result.document_characteristics
    assert result.extraction_strategy is not None


def test_primary_conflict_is_not_silently_picked() -> None:
    listing = _listing("TCS", "INE467B01029")
    result = acquire_planned_fields(
        listing,
        _request(listing, ("net_income",)),
        candidates={
            "net_income": (
                _raw(listing, "net_income", "10", source_url="https://nsearchives.nseindia.com/a.pdf"),
                _raw(listing, "net_income", "11", source_url="https://www.bseindia.com/b.pdf"),
            )
        },
    )
    assert result.outcomes[0].status == "CONFLICT"
    assert result.conflicts == ("net_income",)


def test_screener_cannot_override_or_become_verified() -> None:
    listing = _listing("20MICRONS", "INE144J01027")
    clash = acquire_planned_fields(
        listing,
        _request(listing, ("revenue",)),
        candidates={
            "revenue": (
                _raw(listing, "revenue", "100", source_url=_PRIMARY, source_type="regulator"),
                _raw(
                    listing,
                    "revenue",
                    "90",
                    source_url=_SCREENER,
                    source_type="approved_research",
                    source="Screener",
                ),
            )
        },
    )
    assert clash.outcomes[0].status == "VERIFIED"
    assert clash.outcomes[0].evidence is not None
    assert clash.outcomes[0].evidence.value == "100"
    assert clash.outcomes[0].cross_check is not None
    assert clash.outcomes[0].cross_check["silent_overwrite"] is False
    only_screener = acquire_planned_fields(
        listing,
        _request(listing, ("revenue",)),
        candidates={
            "revenue": (
                _raw(
                    listing,
                    "revenue",
                    "90",
                    source_url=_SCREENER,
                    source_type="approved_research",
                    source="Screener",
                ),
            )
        },
    )
    assert only_screener.outcomes[0].status != "VERIFIED"


def test_retry_skips_failed_source_and_does_not_repeat_it() -> None:
    listing = _listing("INFY", "INE009A01021")
    calls: list[str] = []

    def retrieve(url: str) -> DocumentRecord | RetrievalFailure:
        assert url not in calls, "failed sources must not be retried"
        calls.append(url)
        return RetrievalFailure(url=url, reason="timed out", http_status=None)

    result = acquire_planned_fields(
        listing,
        _request(listing, ("net_income",)),
        retrieve_fn=retrieve,
    )
    assert calls
    assert len(calls) == len(set(calls))
    assert result.outcomes[0].status == "UNKNOWN"
    assert any(item.code == "NETWORK" for item in result.outcomes[0].failures)

    recovered: list[str] = []

    def recover(url: str) -> DocumentRecord | RetrievalFailure:
        recovered.append(url)
        if len(set(recovered)) == 1:
            return RetrievalFailure(url=url, reason="timed out")
        return DocumentRecord(
            url=url,
            retrieved_at=_RETRIEVED,
            http_status=200,
            content_type="text/plain",
            content_length=len(_STATEMENT.encode()),
            document_hash="bb",
            payload=_STATEMENT.encode(),
            company_isin=listing.isin,
            company_mic=listing.mic,
        )

    recovered_result = acquire_planned_fields(
        listing,
        _request(listing, ("net_income",)),
        retrieve_fn=recover,
    )
    assert len(recovered) >= 2
    assert recovered[0] not in recovered[1:]
    assert recovered_result.outcomes[0].status == "VERIFIED"
    assert map_retrieval_to_failure_code("timed out") == "NETWORK"
    assert is_transport_failure("NETWORK")
    assert not is_transport_failure("SEMANTIC_FAILURE")
    assert "NETWORK" in TRANSPORT_FAILURE_CODES
    assert "RECONCILIATION_CONFLICT" in DOMAIN_FAILURE_CODES


def test_ai_and_raw_cannot_enter_dsp() -> None:
    listing = _listing("TCS", "INE467B01029")
    ai = acquire_planned_fields(
        listing,
        _request(listing, ("net_income",)),
        candidates={
            "net_income": (
                _raw(
                    listing,
                    "net_income",
                    "42",
                    source_url="https://example.invalid/ai",
                    source_type="llm",
                    source="model",
                    agent="gemini_find",
                ),
            )
        },
    )
    assert ai.outcomes[0].status != "VERIFIED"
    raw_only = _raw(listing, "net_income", "20000")
    assert raw_only.stage == "RAW"
    promoted = EvidenceJudge().promote(raw_only)
    assert promoted.stage == "VERIFIED"
    dataset = acquire_planned_fields(
        listing,
        _request(listing, ("PRICE", "FINANCIALS", "SHARES")),
        candidates={
            "eod_close": (
                _raw(
                    listing,
                    "eod_close",
                    "3500",
                    as_of=date(2026, 9, 11),
                    unit=None,
                    basis=None,
                    source_type="exchange_eod",
                ),
            )
        },
        document_text=_STATEMENT,
        document_url=_PRIMARY,
    ).dataset
    assert dataset is not None
    gate = dsp_gate(dataset)
    assert dataset.field_status("net_income") == "VERIFIED"
    assert all(not (item.stage == "RAW" and item.status == "VERIFIED") for item in dataset.evidence)
    _ = gate


def test_partial_research_blocks_only_dependent_calculations() -> None:
    listing = _listing("WIPRO", "INE075A01022")
    result = acquire_planned_fields(
        listing,
        _request(listing, ("PRICE", "FINANCIALS", "SHARES")),
        candidates={
            "eod_close": (
                _raw(
                    listing,
                    "eod_close",
                    "250",
                    as_of=date(2026, 9, 11),
                    unit=None,
                    basis=None,
                    source_type="exchange_eod",
                ),
            )
        },
        document_text=(
            "consolidated audited financial statements\n"
            "unit: actual\n"
            "₹ INR\n"
            "year ended 31 March 2026\n"
            "as_of: 2026-03-31\n"
            "Statement of profit and loss\n"
            "Revenue from operations 100000\n"
            "Profit for the year 20000\n"
        ),
        document_url=_PRIMARY,
    )
    by_field = {item.field: item.status for item in result.outcomes}
    assert by_field["eod_close"] == "VERIFIED"
    assert by_field["revenue"] == "VERIFIED"
    assert by_field["net_income"] == "VERIFIED"
    assert by_field["shares_outstanding"] == "UNKNOWN"
    assert result.unknown_fields
    blocked = {item.upper() for item in result.blocked_calculations}
    assert "DCF" in blocked
    assert result.plan.status != "CAPABILITY_UNAVAILABLE"


def test_nse_mcp_stays_commercially_pending() -> None:
    listing = _listing("TCS", "INE467B01029")
    result = acquire_planned_fields(
        listing,
        _request(listing, ("PRICE",)),
        candidates={
            "eod_close": (
                _raw(
                    listing,
                    "eod_close",
                    "3500",
                    as_of=date(2026, 9, 11),
                    unit=None,
                    basis=None,
                    source_url="https://mcp.nseindia.in/bhavcopy/cm/mcp",
                    source_type="regulator",
                    agent="official_nse_mcp",
                ),
            )
        },
        production=True,
    )
    assert NSE_MCP_COMMERCIAL_STATUS == "COMMERCIAL_USE_PENDING"
    assert result.nse_mcp_commercial_status == "COMMERCIAL_USE_PENDING"
    assert result.outcomes[0].status != "VERIFIED"


def test_no_ticker_specific_production_logic() -> None:
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
    text = (_ENGINE / "field_acquisition.py").read_text(encoding="utf-8")
    for token in forbidden:
        assert token not in text
    lowered = text.replace(" ", "")
    assert "ifticker==" not in lowered.lower()
    assert "ifcompany==" not in lowered.lower()
    assert "ifisin==" not in lowered.lower()
    plan_text = (_ENGINE / "research_plan.py").read_text(encoding="utf-8")
    for token in forbidden:
        assert token not in plan_text
