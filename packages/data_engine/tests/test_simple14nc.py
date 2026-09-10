"""SIMPLE-14N-C — statement reconstruction and cache/share contracts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from data_engine.official_research.documents import DocumentRecord, DocumentStore
from data_engine.official_research.extraction import extract_labeled_field
from data_engine.official_research.pdf_text import split_marked_pages
from data_engine.official_research.statement_tables import (
    PdfSpan,
    extract_field_from_statements,
    reconstruct_statement_pages,
)
from data_engine.official_research.models import utc_now


def _pl_spans() -> tuple[PdfSpan, ...]:
    return (
        PdfSpan(1, 80, 740, "Consolidated Statement of Profit and Loss"),
        PdfSpan(1, 80, 720, "in INR million"),
        PdfSpan(1, 400, 700, "31 March 2026"),
        PdfSpan(1, 520, 700, "31 March 2025"),
        PdfSpan(1, 70, 650, "Revenue from operations"),
        PdfSpan(1, 400, 650, "890860"),
        PdfSpan(1, 520, 650, "809648"),
        PdfSpan(1, 70, 610, "Profit for the year"),
        PdfSpan(1, 400, 610, "111121"),
        PdfSpan(1, 520, 610, "113500"),
        PdfSpan(1, 70, 570, "12"),
        PdfSpan(1, 80, 530, "Infographic revenue from operations"),
        PdfSpan(1, 200, 530, "22"),
    )


def test_statement_page_detection_and_column_reconstruction() -> None:
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("Consolidated Statement of Profit and Loss\n",),
        precomputed_spans=(_pl_spans(),),
    )
    assert len(pages) == 1
    assert pages[0].basis == "consolidated"
    assert pages[0].unit_scale == "million"
    revenue = extract_field_from_statements(pages, "revenue")
    assert revenue is not None
    assert revenue.semantic_status == "VERIFIED"
    assert revenue.raw_value == "890860"
    assert revenue.raw_unit == "million"
    assert "page=1" in revenue.locator
    assert "Profit and Loss" in revenue.locator
    ni = extract_field_from_statements(pages, "net_income")
    assert ni is not None
    assert ni.raw_value == "111121"
    assert ni.as_of == date(2026, 3, 31)


def test_standalone_page_not_used_for_consolidated() -> None:
    spans = (
        PdfSpan(1, 80, 740, "Standalone Statement of Profit and Loss"),
        PdfSpan(1, 80, 720, "in INR million"),
        PdfSpan(1, 400, 700, "31 March 2026"),
        PdfSpan(1, 520, 700, "31 March 2025"),
        PdfSpan(1, 70, 650, "Revenue from operations"),
        PdfSpan(1, 400, 650, "100"),
        PdfSpan(1, 520, 650, "90"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("Standalone Statement of Profit and Loss\n",),
        precomputed_spans=(spans,),
    )
    assert pages == ()


def test_infographic_and_ambiguous_pair_remain_unverified() -> None:
    infographic = extract_labeled_field(
        "[[PAGE 3]]\nConsolidated Statement of Profit and Loss\n"
        + ("x\n" * 5000)
        + "revenue from operations: 22\n",
        "revenue",
    )
    assert infographic is None or infographic.semantic_status != "VERIFIED"

    spans = (
        PdfSpan(1, 80, 740, "Consolidated Statement of Profit and Loss"),
        PdfSpan(1, 80, 720, "Rs. crore"),
        PdfSpan(1, 400, 700, "31 March 2026"),
        PdfSpan(1, 430, 700, "31 March 2025"),
        PdfSpan(1, 70, 650, "Revenue from operations"),
        PdfSpan(1, 415, 650, "100"),
        PdfSpan(1, 425, 650, "90"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("Consolidated Statement of Profit and Loss\n",),
        precomputed_spans=(spans,),
    )
    revenue = extract_field_from_statements(pages, "revenue")
    assert revenue is None


def test_unit_inherited_from_statement_header() -> None:
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("Consolidated Balance Sheet\n",),
        precomputed_spans=(
            (
                PdfSpan(1, 80, 740, "Consolidated Balance Sheet"),
                PdfSpan(1, 80, 720, "Rs. crore"),
                PdfSpan(1, 400, 700, "31 March 2026"),
                PdfSpan(1, 520, 700, "31 March 2025"),
                PdfSpan(1, 70, 650, "Total assets"),
                PdfSpan(1, 400, 650, "1414077"),
                PdfSpan(1, 520, 650, "1150000"),
            ),
        ),
    )
    assets = extract_field_from_statements(pages, "total_assets")
    assert assets is not None
    assert assets.raw_unit == "crore"
    assert assets.value == str(Decimal("1414077") * Decimal("10000000"))


def test_page_locator_from_markers() -> None:
    text = (
        "[[PAGE 12]]\nconsolidated\nunit: actual\nyear ended 31 March 2026\n"
        "equity shares outstanding: 10476247846\nas_of: 2026-03-31\n"
    )
    shares = extract_labeled_field(text, "shares_outstanding")
    assert shares is not None
    assert "page=12" in shares.locator


def test_document_store_hash_reuse_and_new_version() -> None:
    store = DocumentStore()
    first = DocumentRecord(
        url="https://nsearchives.nseindia.com/a.pdf",
        retrieved_at=utc_now(),
        http_status=200,
        content_type="application/pdf",
        content_length=4,
        document_hash="abc",
        payload=b"%PDF",
        company_isin="INE075A01022",
        company_mic="XNSE",
    )
    same = DocumentRecord(
        url="https://nsearchives.nseindia.com/a.pdf",
        retrieved_at=utc_now(),
        http_status=200,
        content_type="application/pdf",
        content_length=4,
        document_hash="abc",
        payload=b"%PDF",
        company_isin="INE075A01022",
        company_mic="XNSE",
    )
    alias = DocumentRecord(
        url="https://nsearchives.nseindia.com/b.pdf",
        retrieved_at=utc_now(),
        http_status=200,
        content_type="application/pdf",
        content_length=4,
        document_hash="abc",
        payload=b"%PDF",
        company_isin="INE075A01022",
        company_mic="XNSE",
    )
    changed = DocumentRecord(
        url="https://nsearchives.nseindia.com/a.pdf",
        retrieved_at=utc_now(),
        http_status=200,
        content_type="application/pdf",
        content_length=5,
        document_hash="def",
        payload=b"%PDF2",
        company_isin="INE075A01022",
        company_mic="XNSE",
    )
    stored = store.put(first)
    assert store.put(same) is stored
    assert store.put(alias) is stored
    updated = store.put(changed)
    assert updated is not stored
    assert len(store.versions()) == 2


def test_split_marked_pages() -> None:
    pages = split_marked_pages("[[PAGE 1]]\na\n[[PAGE 2]]\nb\n")
    assert pages[0].strip() == "a"
    assert pages[1].strip() == "b"


def test_wipro_stale_shares_remain_refresh_required() -> None:
    from data_engine.official_research.currentness import CapitalEvent
    from data_engine.official_research.orchestrator import ResearchOrchestrator
    from data_engine.official_research.models import ResearchRequest
    from dsp_platform.composition.mock_nse_eod import default_master, mock_nse

    text = (
        "[[PAGE 180]]\nWipro Limited INE075A01022\nconsolidated\nunit: actual\n"
        "year ended 31 March 2026\n"
        "revenue from operations: 890000000000\n"
        "equity shares outstanding: 10476247846\n"
        "as_of: 2026-03-31\n"
    )
    result = ResearchOrchestrator(
        security_master=default_master(),
        nse_eod=mock_nse(),
        production=False,
    ).research(
        ResearchRequest(
            ticker="WIPRO",
            isin="INE075A01022",
            mic="XNSE",
            fields=("revenue", "shares_outstanding"),
            mode="MOCK",
            document_url="https://www.wipro.com/investors/annual-report.pdf",
        ),
        document_text=text,
        corporate_actions=(CapitalEvent("buyback", date(2026, 6, 26)),),
    )
    shares = result.evidence_for("shares_outstanding")[0]
    assert shares.status == "REFRESH_REQUIRED"
    assert shares.as_of == date(2026, 3, 31)


def test_embedded_label_and_two_values_in_one_span() -> None:
    spans = (
        PdfSpan(1, 80, 740, "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS"),
        PdfSpan(1, 80, 720, "in millions"),
        PdfSpan(1, 417, 700, "March 31, 2026"),
        PdfSpan(1, 488, 700, "March 31, 2025"),
        PdfSpan(1, 221, 500, "TOTAL ASSETS 1,414,077 1,281,852"),
        PdfSpan(1, 221, 460, "TOTAL EQUITY 882,692 825,779"),
        PdfSpan(1, 221, 400, "TOTAL LIABILITIES 531,385 456,073"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=(
            "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS\nTOTAL ASSETS\nTOTAL EQUITY\nTOTAL LIABILITIES\n"
        ),
        precomputed_spans=(spans,),
    )
    assets = extract_field_from_statements(pages, "total_assets")
    equity = extract_field_from_statements(pages, "equity")
    liabilities = extract_field_from_statements(pages, "total_liabilities")
    assert assets is not None and assets.raw_value == "1414077"
    assert equity is not None and equity.raw_value == "882692"
    assert liabilities is not None and liabilities.raw_value == "531385"


def test_right_aligned_prior_year_is_not_current() -> None:
    pl_spans = (
        PdfSpan(1, 80, 740, "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS"),
        PdfSpan(1, 80, 720, "in millions"),
        PdfSpan(1, 417, 700, "March 31, 2026"),
        PdfSpan(1, 488, 700, "March 31, 2025"),
        PdfSpan(1, 70, 650, "Revenue from operations"),
        PdfSpan(1, 380, 650, "926,240"),
        PdfSpan(1, 448, 650, "890,884"),
        PdfSpan(1, 70, 610, "Profit for the year"),
        PdfSpan(1, 375, 610, "132,655"),
        PdfSpan(1, 448, 610, "132,180"),
    )
    bs_spans = (
        PdfSpan(2, 80, 740, "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS"),
        PdfSpan(2, 80, 720, "in millions"),
        PdfSpan(2, 417, 700, "March 31, 2026"),
        PdfSpan(2, 488, 700, "March 31, 2025"),
        PdfSpan(2, 70, 500, "TOTAL ASSETS"),
        PdfSpan(2, 370, 500, "1,414,077"),
        PdfSpan(2, 440, 500, "1,281,852"),
        PdfSpan(2, 70, 460, "TOTAL EQUITY"),
        PdfSpan(2, 375, 460, "882,692"),
        PdfSpan(2, 448, 460, "825,779"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=(
            "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS\nRevenue from operations\nProfit for the year\n",
            "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS\nTOTAL ASSETS\nTOTAL EQUITY\n",
        ),
        precomputed_spans=(pl_spans, bs_spans),
    )
    revenue = extract_field_from_statements(pages, "revenue")
    assets = extract_field_from_statements(pages, "total_assets")
    equity = extract_field_from_statements(pages, "equity")
    assert revenue is not None
    assert revenue.raw_value == "926240"
    assert assets is not None
    assert assets.raw_value == "1414077"
    assert equity is not None
    assert equity.raw_value == "882692"


def test_total_equity_and_liabilities_is_not_equity() -> None:
    spans = (
        PdfSpan(1, 80, 740, "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS"),
        PdfSpan(1, 80, 720, "in millions"),
        PdfSpan(1, 417, 700, "March 31, 2026"),
        PdfSpan(1, 488, 700, "March 31, 2025"),
        PdfSpan(1, 221, 500, "TOTAL ASSETS 1,414,077 1,281,852"),
        PdfSpan(1, 221, 460, "TOTAL EQUITY 882,692 825,779"),
        PdfSpan(1, 221, 400, "TOTAL EQUITY AND LIABILITIES 1,414,077 1,281,852"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=(
            "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS\nTOTAL ASSETS\nTOTAL EQUITY\n"
        ),
        precomputed_spans=(spans,),
    )
    equity = extract_field_from_statements(pages, "equity")
    assert equity is not None
    assert equity.semantic_status == "VERIFIED"
    assert equity.raw_value == "882692"


def test_us_date_headers_and_footer_millions_reconstruct() -> None:
    spans = (
        PdfSpan(1, 80, 740, "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS"),
        PdfSpan(1, 80, 700, "Year ended"),
        PdfSpan(1, 400, 700, "March 31, 2026"),
        PdfSpan(1, 520, 700, "March 31, 2025"),
        PdfSpan(1, 70, 650, "Revenue from operations"),
        PdfSpan(1, 400, 650, "926,240"),
        PdfSpan(1, 520, 650, "890,884"),
        PdfSpan(1, 70, 610, "Profit for the year"),
        PdfSpan(1, 400, 610, "132,655"),
        PdfSpan(1, 520, 610, "132,180"),
        PdfSpan(1, 70, 570, "Profit for the year attributable to:"),
        PdfSpan(1, 70, 555, "Equity holders of the Company"),
        PdfSpan(1, 400, 555, "131,974"),
        PdfSpan(1, 520, 555, "131,354"),
        PdfSpan(1, 80, 80, "(I in millions, except share and per share data, unless otherwise stated)"),
        PdfSpan(1, 80, 50, "Consolidated Statements of Profit and Loss"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS\nRevenue from operations\nProfit for the year\n",),
        precomputed_spans=(spans,),
    )
    revenue = extract_field_from_statements(pages, "revenue")
    ni = extract_field_from_statements(pages, "net_income")
    assert revenue is not None
    assert revenue.raw_value == "926240"
    assert revenue.raw_unit == "million"
    assert "page=1" in revenue.locator
    assert ni is not None
    assert ni.raw_value == "131974"
    assert ni.as_of == date(2026, 3, 31)


def test_negative_undated_authorized_freefloat_and_listed_quantity() -> None:
    undated = extract_labeled_field(
        "consolidated\nequity shares outstanding: 1000\n", "shares_outstanding"
    )
    assert undated is None or undated.as_of is None
    assert extract_labeled_field("as_of: 2026-03-31\nauthorized shares: 5000000000\n", "shares_outstanding") is None
    assert extract_labeled_field("as_of: 2026-03-31\nfree float: 4000000000\n", "shares_outstanding") is None
    listed = extract_labeled_field("as_of: 2026-03-31\nlisted quantity: 10476247846\n", "shares_outstanding")
    assert listed is None or listed.semantic_status != "VERIFIED"
    shares = extract_labeled_field(
        "[[PAGE 298]]\nconsolidated\nunit: actual\nas_of: 2026-03-31\n"
        "Weighted average number of equity shares used in computing earnings per equity share\n"
        "Basic 10,476,247,846 10,456,741,552\n",
        "shares_outstanding",
    )
    assert shares is None or shares.semantic_status != "VERIFIED"


def test_post_buyback_explicit_dated_count_is_current() -> None:
    from data_engine.official_research.currentness import CapitalEvent
    from data_engine.official_research.orchestrator import ResearchOrchestrator
    from data_engine.official_research.models import ResearchRequest
    from dsp_platform.composition.mock_nse_eod import default_master, mock_nse

    text = (
        "[[PAGE 2]]\nWipro Limited INE075A01022\nconsolidated\nunit: actual\n"
        "equity shares outstanding: 9870000000\n"
        "as_of: 2026-07-01\n"
        "year ended 31 March 2026\n"
        "revenue from operations: 890000000000\n"
    )
    result = ResearchOrchestrator(
        security_master=default_master(),
        nse_eod=mock_nse(),
        production=False,
    ).research(
        ResearchRequest(
            ticker="WIPRO",
            isin="INE075A01022",
            mic="XNSE",
            fields=("shares_outstanding",),
            mode="MOCK",
            document_url="https://nsearchives.nseindia.com/wipro-post-buyback.pdf",
        ),
        document_text=text,
        corporate_actions=(CapitalEvent("buyback", date(2026, 6, 26)),),
    )
    shares = result.evidence_for("shares_outstanding")[0]
    assert shares.status == "VERIFIED"
    assert shares.as_of == date(2026, 7, 1)


def test_missing_unit_does_not_verify() -> None:
    spans = (
        PdfSpan(1, 80, 740, "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS"),
        PdfSpan(1, 417, 700, "March 31, 2026"),
        PdfSpan(1, 488, 700, "March 31, 2025"),
        PdfSpan(1, 70, 650, "Revenue from operations"),
        PdfSpan(1, 400, 650, "926240"),
        PdfSpan(1, 520, 650, "890884"),
        PdfSpan(1, 70, 610, "Profit for the year"),
        PdfSpan(1, 400, 610, "132655"),
        PdfSpan(1, 520, 610, "132180"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=(
            "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS\n"
            "Revenue from operations\nProfit for the year\n"
        ),
        precomputed_spans=(spans,),
    )
    assert extract_field_from_statements(pages, "revenue") is None
