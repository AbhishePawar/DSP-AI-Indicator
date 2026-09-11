"""SIMPLE-14N-D local PDF reconstruction. Skips if the forensic PDFs are absent."""

from __future__ import annotations

from pathlib import Path

import pytest

from data_engine.official_research.statement_tables import (
    extract_field_from_statements,
    reconstruct_statement_pages,
)

_PDF_DIR = Path("artifacts/simple14nc_pdfs")


def _payload(ticker: str) -> bytes:
    path = _PDF_DIR / f"{ticker}_AR.pdf"
    if not path.exists():
        pytest.skip(f"local {ticker} annual report PDF is not present")
    return path.read_bytes()


def _pages(ticker: str, wanted: tuple[int, ...]):
    from io import BytesIO

    from pypdf import PdfReader

    from data_engine.official_research.statement_tables import spans_from_pdf

    payload = _payload(ticker)
    reader = PdfReader(BytesIO(payload))
    texts = [""] * len(reader.pages)
    selected = set(wanted)
    for page_no in wanted:
        selected.add(max(1, page_no - 1))
    for page_no in sorted(selected):
        texts[page_no - 1] = reader.pages[page_no - 1].extract_text() or ""
    spans = spans_from_pdf(payload, page_numbers=tuple(sorted(selected)))
    return reconstruct_statement_pages(
        payload, page_texts=tuple(texts), precomputed_spans=spans
    )


def test_local_wipro_14nc_values_remain() -> None:
    pages = _pages("WIPRO", (295, 296, 297, 298, 303))
    revenue = extract_field_from_statements(pages, "revenue")
    ni = extract_field_from_statements(pages, "net_income")
    assert revenue is not None and revenue.raw_value == "926240"
    assert ni is not None and ni.raw_value == "131974"
    assert ni.raw_value != "111121"


def test_local_tcs_crore_dialect_has_multiple_verified_fields() -> None:
    pages = _pages("TCS", (167, 168))
    revenue = extract_field_from_statements(pages, "revenue")
    equity = extract_field_from_statements(pages, "equity")
    assets = extract_field_from_statements(pages, "total_assets")
    assert revenue is not None and revenue.semantic_status == "VERIFIED"
    assert revenue.raw_unit == "crore"
    assert revenue.raw_value == "267021"
    assert equity is not None and equity.raw_value == "108478"
    assert assets is not None and assets.raw_value == "182372"


def test_local_infy_year_under_month_dialect() -> None:
    pages = _pages("INFY", (286, 287, 288, 289))
    revenue = extract_field_from_statements(pages, "revenue")
    ni = extract_field_from_statements(pages, "net_income")
    cash = extract_field_from_statements(pages, "cash")
    assert revenue is not None and revenue.raw_value == "178650"
    assert ni is not None and ni.raw_value == "29440"
    assert cash is not None and cash.raw_value == "22201"
