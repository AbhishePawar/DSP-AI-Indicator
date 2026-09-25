"""Focused reconstruction of remaining issuer statement pages."""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path

logging.getLogger("fontTools").setLevel(logging.ERROR)
from pypdf import PdfReader

from data_engine.official_research.statement_tables import (
    balance_sheet_identity,
    extract_field_from_statements,
    reconstruct_statement_pages,
    spans_from_pdf,
)

PDF_DIR = Path("artifacts/simple14nc_pdfs")
TARGETS = {
    "TCS": (167, 168, 173, 174),
    "INFY": (286, 287, 288, 289),
    "HINDUNILVR": (184, 185, 186, 199, 200),
    "RELIANCE": (138, 139, 140, 141, 142),
    "HDFCBANK": (496, 497, 498, 499),
    "ASIANPAINT": (233, 234, 235, 236, 237),
}
FIELDS = (
    "revenue",
    "net_income",
    "equity",
    "cash",
    "cfo",
    "total_assets",
    "total_liabilities",
)


def run(ticker: str, wanted: tuple[int, ...]) -> None:
    payload = (PDF_DIR / f"{ticker}_AR.pdf").read_bytes()
    reader = PdfReader(BytesIO(payload))
    texts = [""] * len(reader.pages)
    for page_no in wanted:
        texts[page_no - 1] = reader.pages[page_no - 1].extract_text() or ""
        extra = []
        if page_no > 1:
            extra.append(page_no - 1)
            texts[page_no - 2] = reader.pages[page_no - 2].extract_text() or ""
        if page_no < len(reader.pages):
            extra.append(page_no + 1)
            texts[page_no] = reader.pages[page_no].extract_text() or ""
    pages_set = set(wanted)
    for page_no in wanted:
        pages_set.add(max(1, page_no - 1))
        pages_set.add(min(len(reader.pages), page_no + 1))
    selected = tuple(sorted(pages_set))
    for page_no in selected:
        texts[page_no - 1] = reader.pages[page_no - 1].extract_text() or ""
    spans = spans_from_pdf(payload, page_numbers=selected)
    pages = reconstruct_statement_pages(
        payload, page_texts=tuple(texts), precomputed_spans=spans
    )
    print(
        ticker,
        [(p.page, p.statement_type, p.unit_scale, [c.label for c in p.columns]) for p in pages],
        "identity",
        balance_sheet_identity(pages),
    )
    for name in FIELDS:
        item = extract_field_from_statements(pages, name)
        if item is None:
            print(" ", name, None)
        else:
            print(" ", name, item.semantic_status, item.raw_value, item.raw_unit, item.locator[:160])


if __name__ == "__main__":
    for ticker, wanted in TARGETS.items():
        run(ticker, wanted)
        print()
