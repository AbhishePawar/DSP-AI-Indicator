"""SIMPLE-14N-D — multi-issuer dialects and share-currentness contracts."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from data_engine.official_research.extraction import extract_labeled_field
from data_engine.official_research.forensic_artifacts import (
    classify_forensic_artifact,
    is_promotable_artifact,
    is_stale_rejected_candidate,
)
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.models import EvidenceItem, new_evidence_id
from data_engine.official_research.source_policy import record_source_clash
from data_engine.official_research.statement_tables import (
    PdfSpan,
    balance_sheet_identity,
    extract_field_from_statements,
    reconstruct_statement_pages,
)


def _wipro_spans() -> tuple[tuple[PdfSpan, ...], ...]:
    pl = (
        PdfSpan(1, 80, 740, "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS"),
        PdfSpan(1, 80, 700, "Year ended"),
        PdfSpan(1, 400, 700, "March 31, 2026"),
        PdfSpan(1, 520, 700, "March 31, 2025"),
        PdfSpan(1, 70, 650, "Revenue from operations"),
        PdfSpan(1, 400, 650, "926,240"),
        PdfSpan(1, 520, 650, "890,884"),
        PdfSpan(1, 70, 555, "Profit for the year attributable to:"),
        PdfSpan(1, 70, 540, "Equity holders of the Company"),
        PdfSpan(1, 400, 555, "131,974"),
        PdfSpan(1, 520, 555, "131,354"),
        PdfSpan(1, 80, 80, "(I in millions, except share and per share data, unless otherwise stated)"),
        PdfSpan(1, 80, 50, "Consolidated Statements of Profit and Loss"),
    )
    bs = (
        PdfSpan(2, 80, 740, "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS"),
        PdfSpan(2, 80, 720, "in millions"),
        PdfSpan(2, 417, 700, "March 31, 2026"),
        PdfSpan(2, 488, 700, "March 31, 2025"),
        PdfSpan(2, 221, 500, "TOTAL ASSETS 1,414,077 1,281,852"),
        PdfSpan(2, 221, 460, "TOTAL EQUITY 882,692 825,779"),
        PdfSpan(2, 70, 420, "TOTAL LIABILITIES"),
        PdfSpan(2, 400, 420, "531,385"),
        PdfSpan(2, 470, 420, "456,073"),
    )
    return pl, bs


def test_wipro_14nc_values_and_identity_remain() -> None:
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=(
            "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS\nRevenue from operations\nProfit for the year\n",
            "CONSOLIDATED FINANCIAL STATEMENT UNDER IND AS\nTOTAL ASSETS\nTOTAL EQUITY\nTOTAL LIABILITIES\n",
        ),
        precomputed_spans=_wipro_spans(),
    )
    revenue = extract_field_from_statements(pages, "revenue")
    ni = extract_field_from_statements(pages, "net_income")
    assets = extract_field_from_statements(pages, "total_assets")
    equity = extract_field_from_statements(pages, "equity")
    liab = extract_field_from_statements(pages, "total_liabilities")
    assert revenue is not None and revenue.raw_value == "926240"
    assert ni is not None and ni.raw_value == "131974"
    assert ni.raw_value != "111121"
    assert assets is not None and assets.raw_value == "1414077"
    assert equity is not None and equity.raw_value == "882692"
    assert liab is not None and liab.raw_value == "531385"
    assert Decimal(assets.raw_value) == Decimal(equity.raw_value) + Decimal(liab.raw_value)
    assert balance_sheet_identity(pages) == "PASS"


def test_encoded_crore_unit_and_uk_date() -> None:
    spans = (
        PdfSpan(1, 80, 740, "Consolidated Balance Sheet"),
        PdfSpan(1, 500, 720, "(H crore)"),
        PdfSpan(1, 400, 700, "31 March 2026"),
        PdfSpan(1, 500, 700, "31 March 2025"),
        PdfSpan(1, 70, 500, "TOTAL ASSETS"),
        PdfSpan(1, 400, 500, "182,372"),
        PdfSpan(1, 500, 500, "159,629"),
        PdfSpan(1, 70, 460, "TOTAL EQUITY"),
        PdfSpan(1, 400, 460, "108,478"),
        PdfSpan(1, 500, 460, "95,771"),
        PdfSpan(1, 70, 420, "Cash and cash equivalents"),
        PdfSpan(1, 400, 420, "6,417"),
        PdfSpan(1, 500, 420, "8,342"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("Consolidated Balance Sheet\nTOTAL ASSETS\nTOTAL EQUITY\n",),
        precomputed_spans=(spans,),
    )
    assets = extract_field_from_statements(pages, "total_assets")
    cash = extract_field_from_statements(pages, "cash")
    assert assets is not None
    assert assets.raw_unit == "crore"
    assert assets.raw_value == "182372"
    assert assets.value == "1823720000000"
    assert cash is not None
    assert cash.raw_value == "6417"


def test_ordinal_and_previous_page_title() -> None:
    prev = "Consolidated Balance Sheet\nas at 31st March, 2026\n"
    spans = (
        PdfSpan(2, 80, 720, "(All amounts in H crores, unless otherwise stated)"),
        PdfSpan(2, 400, 700, "31st March, 2026"),
        PdfSpan(2, 520, 700, "31st March, 2025"),
        PdfSpan(2, 70, 500, "TOTAL ASSETS"),
        PdfSpan(2, 400, 500, "60,731"),
        PdfSpan(2, 500, 500, "57,829"),
        PdfSpan(2, 70, 460, "Cash and cash equivalents"),
        PdfSpan(2, 400, 460, "2,583"),
        PdfSpan(2, 500, 460, "6,071"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=(prev, "Particulars Note As at\n31st March, 2026\nTOTAL ASSETS\n"),
        precomputed_spans=((), spans),
    )
    assets = extract_field_from_statements(pages, "total_assets")
    assert assets is not None
    assert assets.raw_unit == "crore"
    assert assets.as_of == date(2026, 3, 31)
    assert assets.raw_value == "60731"


def test_year_pair_in_one_span() -> None:
    spans = (
        PdfSpan(1, 80, 740, "Consolidated Statement of Profit and Loss"),
        PdfSpan(1, 80, 720, "(In ` crore)"),
        PdfSpan(1, 70, 700, "Particulars Note Year ended March 31,"),
        PdfSpan(1, 400, 680, "2026 2025"),
        PdfSpan(1, 70, 650, "Revenue from operations"),
        PdfSpan(1, 400, 650, "178650"),
        PdfSpan(1, 500, 650, "162990"),
        PdfSpan(1, 70, 610, "Profit attributable to:"),
        PdfSpan(1, 70, 595, "Owners of the Company"),
        PdfSpan(1, 400, 595, "29440"),
        PdfSpan(1, 500, 595, "26713"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("Consolidated Statement of Profit and Loss\nRevenue from operations\nProfit for the year\n",),
        precomputed_spans=(spans,),
    )
    revenue = extract_field_from_statements(pages, "revenue")
    assert revenue is not None
    assert revenue.raw_value == "178650"
    spans = (
        PdfSpan(1, 80, 740, "Consolidated Statement of Profit and Loss"),
        PdfSpan(1, 80, 720, "(In ` crore)"),
        PdfSpan(1, 70, 700, "Particulars Note Year ended March 31,"),
        PdfSpan(1, 400, 680, "2026"),
        PdfSpan(1, 500, 680, "2025"),
        PdfSpan(1, 70, 650, "Revenue from operations"),
        PdfSpan(1, 400, 650, "178650"),
        PdfSpan(1, 500, 650, "162990"),
        PdfSpan(1, 70, 610, "Profit attributable to:"),
        PdfSpan(1, 70, 595, "Owners of the Company"),
        PdfSpan(1, 400, 595, "29440"),
        PdfSpan(1, 500, 595, "26713"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("Consolidated Statement of Profit and Loss\nRevenue from operations\nProfit for the year\n",),
        precomputed_spans=(spans,),
    )
    revenue = extract_field_from_statements(pages, "revenue")
    ni = extract_field_from_statements(pages, "net_income")
    assert revenue is not None
    assert revenue.raw_value == "178650"
    assert revenue.as_of == date(2026, 3, 31)
    assert ni is not None
    assert ni.raw_value == "29440"


def test_fy_columns_are_distinct_not_duplicated() -> None:
    spans = (
        PdfSpan(1, 80, 740, "Consolidated Statement of Profit and Loss"),
        PdfSpan(1, 80, 720, "(` in Crores)"),
        PdfSpan(1, 400, 700, "2025-26"),
        PdfSpan(1, 400, 698, "2025-26"),
        PdfSpan(1, 520, 700, "2024-25"),
        PdfSpan(1, 70, 650, "Revenue from operations"),
        PdfSpan(1, 400, 650, "35416.25"),
        PdfSpan(1, 520, 650, "33626.82"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("Consolidated Statement of Profit and Loss\nRevenue from operations\nProfit for the year\n",),
        precomputed_spans=(spans,),
    )
    revenue = extract_field_from_statements(pages, "revenue")
    assert revenue is not None
    assert revenue.raw_value == "35416.25"
    assert revenue.as_of == date(2026, 3, 31)
    assert {col.period_end for col in pages[0].columns} == {date(2026, 3, 31), date(2025, 3, 31)}


def test_dotted_date_and_i_in_crore() -> None:
    spans = (
        PdfSpan(1, 80, 740, "Consolidated Balance Sheet"),
        PdfSpan(1, 80, 720, "(I in crore)"),
        PdfSpan(1, 400, 700, "31.03.2026"),
        PdfSpan(1, 520, 700, "31.03.2025"),
        PdfSpan(1, 70, 500, "TOTAL ASSETS"),
        PdfSpan(1, 400, 500, "2178140"),
        PdfSpan(1, 520, 500, "1950121"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("Consolidated Balance Sheet\nTOTAL ASSETS\nTOTAL EQUITY\n",),
        precomputed_spans=(spans,),
    )
    assets = extract_field_from_statements(pages, "total_assets")
    assert assets is not None
    assert assets.raw_unit == "crore"
    assert assets.as_of == date(2026, 3, 31)


def test_interest_earned_is_not_revenue_and_sale_of_products_is_not_total_revenue() -> None:
    spans = (
        PdfSpan(1, 80, 740, "CONSOLIDATED PROFIT AND LOSS ACCOUNT"),
        PdfSpan(1, 80, 720, "(C in crore)"),
        PdfSpan(1, 400, 700, "March 31, 2026"),
        PdfSpan(1, 520, 700, "March 31, 2025"),
        PdfSpan(1, 70, 650, "Interest earned"),
        PdfSpan(1, 400, 650, "348615.15"),
        PdfSpan(1, 520, 650, "336367.43"),
        PdfSpan(1, 70, 610, "Consolidated Net Profit for the year attributable to the group"),
        PdfSpan(1, 400, 610, "76025.97"),
        PdfSpan(1, 520, 610, "70792.25"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("CONSOLIDATED PROFIT AND LOSS ACCOUNT\nInterest earned\nProfit for the year\n",),
        precomputed_spans=(spans,),
    )
    assert extract_field_from_statements(pages, "revenue") is None
    ni = extract_field_from_statements(pages, "net_income")
    assert ni is not None
    assert ni.raw_value == "76025.97"
    products = (
        PdfSpan(2, 80, 740, "Consolidated Statement of Profit and Loss"),
        PdfSpan(2, 80, 720, "(` in Crores)"),
        PdfSpan(2, 400, 700, "2025-26"),
        PdfSpan(2, 520, 700, "2024-25"),
        PdfSpan(2, 70, 650, "Revenue from Sale of Products"),
        PdfSpan(2, 400, 650, "35416.25"),
        PdfSpan(2, 520, 650, "33626.82"),
        PdfSpan(2, 70, 610, "Profit for the year"),
        PdfSpan(2, 400, 610, "3667.23"),
        PdfSpan(2, 520, 610, "3000.00"),
    )
    pages2 = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("Consolidated Statement of Profit and Loss\nRevenue from operations\nProfit for the year\n",),
        precomputed_spans=(products,),
    )
    assert extract_field_from_statements(pages, "revenue") is None
    assert extract_field_from_statements(pages2, "revenue") is None


def test_board_report_mixed_basis_table_is_not_the_statement() -> None:
    spans = (
        PdfSpan(1, 80, 740, "Board's Report"),
        PdfSpan(1, 80, 720, "(H crore)"),
        PdfSpan(1, 200, 700, "Standalone"),
        PdfSpan(1, 400, 700, "Consolidated"),
        PdfSpan(1, 200, 680, "2025-26"),
        PdfSpan(1, 280, 680, "2024-25"),
        PdfSpan(1, 400, 680, "2025-26"),
        PdfSpan(1, 520, 680, "2024-25"),
        PdfSpan(1, 70, 650, "Revenue from operations"),
        PdfSpan(1, 200, 650, "220,938"),
        PdfSpan(1, 280, 650, "214,853"),
        PdfSpan(1, 400, 650, "267,021"),
        PdfSpan(1, 520, 650, "255,324"),
        PdfSpan(1, 70, 610, "Profit for the year"),
        PdfSpan(1, 200, 610, "48,553"),
        PdfSpan(1, 280, 610, "45,958"),
        PdfSpan(1, 400, 610, "49,210"),
        PdfSpan(1, 520, 610, "48,849"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=(
            "Board's Report\nStandalone Consolidated\nRevenue from operations\nProfit for the year\n"
        ),
        precomputed_spans=(spans,),
    )
    assert pages == ()
    assert extract_field_from_statements(pages, "revenue") is None
    spans = (
        PdfSpan(1, 80, 740, "Financial Highlights"),
        PdfSpan(1, 80, 720, "(H crore)"),
        PdfSpan(1, 400, 700, "2025-26"),
        PdfSpan(1, 520, 700, "2024-25"),
        PdfSpan(1, 70, 650, "Revenue from operations"),
        PdfSpan(1, 400, 650, "220,938"),
        PdfSpan(1, 520, 650, "202,871"),
        PdfSpan(1, 70, 610, "Profit for the year"),
        PdfSpan(1, 400, 610, "48,553"),
        PdfSpan(1, 520, 610, "45,958"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("Financial Highlights\nRevenue from operations\nProfit for the year\n",),
        precomputed_spans=(spans,),
    )
    assert pages == ()
    assert extract_field_from_statements(pages, "revenue") is None


def test_concatenated_spread_token_is_not_a_financial_value() -> None:
    spans = (
        PdfSpan(1, 80, 740, "Consolidated Balance Sheet"),
        PdfSpan(1, 80, 720, "(I in crore)"),
        PdfSpan(1, 400, 700, "March, 2026"),
        PdfSpan(1, 520, 700, "March, 2025"),
        PdfSpan(1, 70, 500, "TOTAL ASSETS"),
        PdfSpan(1, 400, 500, "21781401950121"),
        PdfSpan(1, 520, 500, "19501211700000"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("Consolidated Balance Sheet\nTOTAL ASSETS\nTOTAL EQUITY\n",),
        precomputed_spans=(spans,),
    )
    assert extract_field_from_statements(pages, "total_assets") is None


def test_potential_equity_shares_are_not_outstanding() -> None:
    text = (
        "[[PAGE 477]]\nconsolidated\nunit: actual\nas_of: 2026-03-31\n"
        "Effect of potential equity shares outstanding 7,04,90,586 6,83,54,782\n"
    )
    item = extract_labeled_field(text, "shares_outstanding")
    assert item is None or item.semantic_status != "VERIFIED"
    assert item is None or item.raw_value != "70490586"


def test_mixed_spread_and_eps_rows_are_not_promoted() -> None:
    spans = (
        PdfSpan(1, 80, 740, "Consolidated Balance Sheet"),
        PdfSpan(1, 80, 720, "(I in crore)"),
        PdfSpan(1, 400, 700, "March, 2026"),
        PdfSpan(1, 520, 700, "March, 2025"),
        PdfSpan(1, 70, 500, "Total Assets Total Liabilities"),
        PdfSpan(1, 400, 500, "2178140"),
        PdfSpan(1, 520, 500, "1950121"),
        PdfSpan(1, 70, 460, "Cash and Cash Equivalents Trade Payables"),
        PdfSpan(1, 400, 460, "101459"),
        PdfSpan(1, 520, 460, "77106"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("Consolidated Balance Sheet\nTOTAL ASSETS\nTOTAL EQUITY\n",),
        precomputed_spans=(spans,),
    )
    assert extract_field_from_statements(pages, "total_assets") is None
    assert extract_field_from_statements(pages, "total_liabilities") is None
    assert extract_field_from_statements(pages, "cash") is None
    spans = (
        PdfSpan(1, 80, 740, "Consolidated Balance Sheet"),
        PdfSpan(1, 80, 720, "in millions"),
        PdfSpan(1, 400, 700, "March 31, 2026"),
        PdfSpan(1, 520, 700, "March 31, 2025"),
        PdfSpan(1, 70, 500, "TOTAL ASSETS"),
        PdfSpan(1, 400, 500, "100"),
        PdfSpan(1, 520, 500, "90"),
        PdfSpan(1, 70, 460, "TOTAL EQUITY"),
        PdfSpan(1, 400, 460, "40"),
        PdfSpan(1, 520, 460, "40"),
        PdfSpan(1, 70, 420, "TOTAL LIABILITIES"),
        PdfSpan(1, 400, 420, "50"),
        PdfSpan(1, 520, 420, "40"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("Consolidated Balance Sheet\nTOTAL ASSETS\nTOTAL EQUITY\nTOTAL LIABILITIES\n",),
        precomputed_spans=(spans,),
    )
    assert balance_sheet_identity(pages) == "CONFLICT"
    assets = extract_field_from_statements(pages, "total_assets")
    assert assets is not None
    assert assets.semantic_status == "CONFLICT"
    assert assets.raw_value == "100"


def test_weighted_average_eps_shares_are_not_outstanding() -> None:
    text = (
        "[[PAGE 369]]\nconsolidated\nunit: actual\nas_of: 2026-03-31\n"
        "Weighted average number of equity shares outstanding 10,476,247,846 10,456,741,552\n"
    )
    item = extract_labeled_field(text, "shares_outstanding")
    assert item is None or item.raw_value != "10476247846"
    assert item is None or item.semantic_status != "VERIFIED"


def test_stale_full_document_artifact_cannot_override_focused_verified() -> None:
    label = classify_forensic_artifact("artifacts/simple14nd_reconstruct.json")
    assert label["status"] == "STALE"
    assert label["use"] == "FORENSIC_ONLY"
    assert label["promotable"] is False
    assert is_promotable_artifact("artifacts/simple14nd_reconstruct.json") is False
    assert is_stale_rejected_candidate("TCS", "revenue", "220938")
    assert is_stale_rejected_candidate("ASIANPAINT", "net_income", "33626.82")
    assert is_stale_rejected_candidate("RELIANCE", "total_assets", "21781401950121")
    assert is_stale_rejected_candidate("HINDUNILVR", "revenue", "-59")
    assert not is_stale_rejected_candidate("TCS", "revenue", "267021")
    spans = (
        PdfSpan(1, 80, 740, "Consolidated Statement of Profit and Loss"),
        PdfSpan(1, 80, 720, "(H crore)"),
        PdfSpan(1, 400, 700, "March 31, 2026"),
        PdfSpan(1, 520, 700, "March 31, 2025"),
        PdfSpan(1, 70, 650, "Revenue from operations"),
        PdfSpan(1, 400, 650, "267,021"),
        PdfSpan(1, 520, 650, "255,324"),
    )
    pages = reconstruct_statement_pages(
        b"%PDF-fake",
        page_texts=("Consolidated Statement of Profit and Loss\nRevenue from operations\nProfit for the year\n",),
        precomputed_spans=(spans,),
    )
    revenue = extract_field_from_statements(pages, "revenue")
    assert revenue is not None
    assert revenue.raw_value == "267021"
    assert revenue.semantic_status == "VERIFIED"
    assert not is_stale_rejected_candidate("TCS", "revenue", revenue.raw_value or "")


def test_screener_cannot_become_verified_and_clash_is_recorded() -> None:
    judge = EvidenceJudge()
    raw = EvidenceItem(
        evidence_id=new_evidence_id(),
        company="Wipro Limited",
        ticker="WIPRO",
        isin="INE075A01022",
        mic="XNSE",
        field="net_income",
        value="131974000000",
        as_of=date(2026, 3, 31),
        retrieved_at=datetime(2026, 9, 11, tzinfo=UTC),
        source="Screener",
        source_type="approved_research",
        source_url="https://www.screener.in/company/WIPRO/",
        document_date=date(2026, 3, 31),
        evidence_locator="screener",
        currency="INR",
        unit="actual",
        statement_basis="consolidated",
        agent="official_research",
        identity_status="PASS",
        semantic_status="PASS",
        freshness_status="PASS",
        corporate_action_status="PASS",
        confidence="high",
        stage="RAW",
        status="UNKNOWN",
        mode="MOCK",
    )
    promoted = judge.promote(raw)
    assert promoted.stage != "VERIFIED"
    assert promoted.status != "VERIFIED"
    clash = record_source_clash(
        field="revenue",
        primary_url="https://nsearchives.nseindia.com/annual_reports/tcs.pdf",
        primary_value="267021",
        research_url="https://www.screener.in/company/TCS/",
        research_value="220938",
    )
    assert clash["cross_check"] == "CONFLICT"
    assert clash["winner"] == "primary"
    assert clash["silent_overwrite"] is False
    agree = record_source_clash(
        field="revenue",
        primary_url="https://nsearchives.nseindia.com/annual_reports/tcs.pdf",
        primary_value="267021",
        research_url="https://www.screener.in/company/TCS/",
        research_value="267021",
    )
    assert agree["cross_check"] == "PASS"
