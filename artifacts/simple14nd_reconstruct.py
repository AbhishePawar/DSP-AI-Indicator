"""Reconstruct local FY26 ARs with the 14N-D engine. Not committed."""

from __future__ import annotations

import json
import logging
from io import BytesIO
from pathlib import Path
from time import perf_counter

logging.getLogger("fontTools").setLevel(logging.ERROR)
logging.getLogger("pypdf").setLevel(logging.ERROR)

from pypdf import PdfReader

from data_engine.official_research.pdf_text import document_text_from_payload, split_marked_pages
from data_engine.official_research.statement_tables import (
    balance_sheet_identity,
    extract_field_from_statements,
    reconstruct_statement_pages,
)

PDF_DIR = Path("artifacts/simple14nc_pdfs")
OUT = Path("artifacts/simple14nd_reconstruct.json")
URLS = {
    "WIPRO": "https://nsearchives.nseindia.com/annual_reports/AR_29427_WIPRO_2025_2026_A_8877705_22062026190140.pdf",
    "TCS": "https://nsearchives.nseindia.com/annual_reports/AR_29263_TCS_2025_2026_A_17427580_15052026234830.pdf",
    "INFY": "https://nsearchives.nseindia.com/annual_reports/AR_29313_INFY_2025_2026_U_8985411_30052026200413.pdf",
    "ASIANPAINT": "https://nsearchives.nseindia.com/annual_reports/AR_29385_ASIANPAINT_2025_2026_A_26278926_12062026160918.pdf",
    "RELIANCE": "https://nsearchives.nseindia.com/annual_reports/AR_29285_RELIANCE_2025_2026_A_11007429_28052026133947.pdf",
    "HINDUNILVR": "https://nsearchives.nseindia.com/annual_reports/AR_29330_HINDUNILVR_2025_2026_A_21643813_02062026215058.pdf",
    "HDFCBANK": "https://nsearchives.nseindia.com/annual_reports/AR_29735_HDFCBANK_2025_2026_A_12667766_11072026001055.pdf",
}
HASHES = {
    "WIPRO": "48f0612b11ccd1883d229d9c6ae3fcc0de65c6ae6bc6034b562884ecbbd5afd9",
    "TCS": "d0bdc7fe1ae741b07bb76a158019cae05ab18abd2c2eeda43177d367bef24eb8",
    "INFY": "4fc4a071157f446bfc96f71763159122059c9881870e245cb9383069906bf3e8",
    "ASIANPAINT": "b7977d2419ed2e211d0ad53270165cc4205cafff7982b6b74fed6502fa25aacb",
    "RELIANCE": "6fc365c08e7be923eedfa824bc92e605e094da98ad18e1f54cf71db7392c4a94",
    "HINDUNILVR": "ab3842889a4dbfe697fa2bbed89d3b8bc622e7a13b052841b4908b92be719054",
    "HDFCBANK": "92de3c75b6fc05afe8731e97705c9d3534cc192e677af02f4b325e3d82eafca6",
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


def dialect_of(pages) -> str:
    if not pages:
        return "UNCLASSIFIED"
    tags = []
    if any(p.unit_scale == "million" for p in pages):
        tags.append("A_POSITIONAL_MILLION")
    if any(p.unit_scale == "crore" for p in pages):
        tags.append("E_CRORE_ENCODING")
    labels = " ".join(c.label for p in pages for c in p.columns)
    if "March 31," in labels and any(c.label.startswith("March 31,") for p in pages for c in p.columns):
        tags.append("US_DATE")
    if any("31st" in c.label or "31 March" in c.label for p in pages for c in p.columns):
        tags.append("UK_ORDINAL")
    if any(c.label.startswith("March 31, 20") and len(c.label) <= 16 for p in pages for c in p.columns):
        tags.append("B_YEAR_UNDER_MONTH")
    if any("-" in c.label and c.label[:4].isdigit() for p in pages for c in p.columns):
        tags.append("FY_RANGE")
    if len({p.page for p in pages if p.statement_type == "bs"}) >= 2:
        tags.append("C_MULTI_PAGE")
    return "+".join(tags) or "F_MIXED"


def main() -> None:
    rows = {}
    for ticker, url in URLS.items():
        payload = (PDF_DIR / f"{ticker}_AR.pdf").read_bytes()
        t0 = perf_counter()
        text = document_text_from_payload(payload) or ""
        text_s = perf_counter() - t0
        t1 = perf_counter()
        pages = reconstruct_statement_pages(
            payload, page_texts=split_marked_pages(text)
        )
        rec_s = perf_counter() - t1
        fields = {}
        for name in FIELDS:
            item = extract_field_from_statements(pages, name)
            fields[name] = None if item is None else {
                "status": item.semantic_status,
                "raw": item.raw_value,
                "value": item.value,
                "unit": item.raw_unit,
                "currency": item.currency,
                "locator": item.locator,
                "period": None if item.period_end is None else item.period_end.isoformat(),
                "basis": item.statement_basis,
                "document": url,
                "sha256": HASHES[ticker],
            }
        rows[ticker] = {
            "pages_pdf": len(PdfReader(BytesIO(payload)).pages),
            "statement_pages": [
                {
                    "page": p.page,
                    "kind": p.statement_type,
                    "unit": p.unit_scale,
                    "basis": p.basis,
                    "columns": [c.label for c in p.columns],
                }
                for p in pages
            ],
            "dialect": dialect_of(pages),
            "identity": balance_sheet_identity(pages),
            "text_s": round(text_s, 3),
            "reconstruct_s": round(rec_s, 3),
            "fields": fields,
        }
        print(
            ticker,
            dialect_of(pages),
            "identity",
            balance_sheet_identity(pages),
            {k: None if v is None else (v["status"], v["raw"], v["unit"]) for k, v in fields.items()},
            flush=True,
        )
    OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
