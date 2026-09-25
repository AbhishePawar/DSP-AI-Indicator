"""Inspect candidate statement pages for dialect features. Not evidence."""

from __future__ import annotations

import json
import logging
import re
from io import BytesIO
from pathlib import Path

logging.getLogger("fontTools").setLevel(logging.ERROR)
logging.getLogger("pypdf").setLevel(logging.ERROR)

from pypdf import PdfReader

from data_engine.official_research.documents import retrieve_official_document
from data_engine.official_research.nse_eod import NsePublicHttp
from data_engine.official_research.statement_tables import (
    extract_field_from_statements,
    reconstruct_statement_pages,
    spans_from_pdf,
)

PDF_DIR = Path("artifacts/simple14nc_pdfs")
OUT = Path("artifacts/simple14nd_page_probe.json")

TARGETS = {
    "WIPRO": {
        "url": "https://nsearchives.nseindia.com/annual_reports/AR_29427_WIPRO_2025_2026_A_8877705_22062026190140.pdf",
        "isin": "INE075A01022",
        "pages": (295, 296, 297, 298, 303, 304, 369),
    },
    "TCS": {
        "url": "https://nsearchives.nseindia.com/annual_reports/AR_29263_TCS_2025_2026_A_17427580_15052026234830.pdf",
        "isin": "INE467B01029",
        "pages": (166, 167, 168, 169, 173, 174),
    },
    "INFY": {
        "url": "https://nsearchives.nseindia.com/annual_reports/AR_29313_INFY_2025_2026_U_8985411_30052026200413.pdf",
        "isin": "INE009A01021",
        "pages": (242, 243, 244, 285, 286, 287, 288, 289, 295, 296),
    },
    "ASIANPAINT": {
        "url": "https://nsearchives.nseindia.com/annual_reports/AR_29385_ASIANPAINT_2025_2026_A_26278926_12062026160918.pdf",
        "isin": "INE021A01026",
        "pages": (232, 233, 234, 235, 236, 237),
    },
    "RELIANCE": {
        "url": "https://nsearchives.nseindia.com/annual_reports/AR_29285_RELIANCE_2025_2026_A_11007429_28052026133947.pdf",
        "isin": "INE002A01018",
        "pages": (130, 131, 135, 136, 141, 142, 146),
    },
    "HINDUNILVR": {
        "url": "https://nsearchives.nseindia.com/annual_reports/AR_29330_HINDUNILVR_2025_2026_A_21643813_02062026215058.pdf",
        "isin": "INE030A01027",
        "pages": (185, 186, 199, 200),
    },
    "HDFCBANK": {
        "url": "https://nsearchives.nseindia.com/annual_reports/AR_29735_HDFCBANK_2025_2026_A_12667766_11072026001055.pdf",
        "isin": "INE040A01034",
        "pages": (495, 496, 497, 498, 499, 561, 571),
    },
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


def _headerish(text: str) -> bool:
    blob = text.lower()
    return bool(
        re.search(
            r"march|fy\s*20|in crore|in million|year ended|31\.03|profit and loss|"
            r"balance sheet|cash flow|crore|million|standalone|consolidated",
            blob,
            re.I,
        )
    )


def inspect_pages(ticker: str, payload: bytes, wanted: tuple[int, ...]) -> dict:
    reader = PdfReader(BytesIO(payload))
    page_texts = [""] * len(reader.pages)
    for page_no in wanted:
        if 1 <= page_no <= len(reader.pages):
            page_texts[page_no - 1] = reader.pages[page_no - 1].extract_text() or ""
    spans_by_page = spans_from_pdf(payload, page_numbers=wanted)
    reconstructed = reconstruct_statement_pages(
        payload,
        page_texts=tuple(page_texts),
        precomputed_spans=spans_by_page,
    )
    fields = {}
    for name in FIELDS:
        item = extract_field_from_statements(reconstructed, name)
        fields[name] = None if item is None else {
            "status": item.semantic_status,
            "raw": item.raw_value,
            "value": item.value,
            "unit": item.raw_unit,
            "locator": item.locator,
            "period": None if item.period_end is None else item.period_end.isoformat(),
            "basis": item.statement_basis,
        }
    page_dump = []
    for page_no in wanted:
        if page_no < 1 or page_no > len(spans_by_page):
            continue
        spans = spans_by_page[page_no - 1]
        text = page_texts[page_no - 1] if page_no <= len(page_texts) else ""
        headers = [
            {"text": s.text[:120], "x": round(s.x, 1), "y": round(s.y, 1)}
            for s in spans
            if _headerish(s.text) and len(s.text) < 160
        ][:18]
        unique_rows = []
        for page in reconstructed:
            if page.page != page_no:
                continue
            unique_rows = [
                {
                    "label": r.label[:90],
                    "current": r.current_raw,
                    "prior": r.prior_raw,
                    "pairing": r.pairing,
                }
                for r in page.rows
                if r.pairing == "UNIQUE" and r.current_raw
            ][:20]
        page_dump.append(
            {
                "page": page_no,
                "chars": len(text),
                "spans": len(spans),
                "title_hits": bool(
                    re.search(
                        r"consolidated (balance sheet|statement of profit|statement of cash)",
                        text,
                        re.I,
                    )
                ),
                "unit_hits": re.findall(
                    r".{0,20}(crore|million|crs).{0,20}", text, re.I
                )[:8],
                "period_hits": re.findall(
                    r"(March[^\n]{0,20}20\d{2}|31[^\n]{0,12}2026|FY\s*20\d{2}[^\n]{0,12}|31\.03\.20\d{2})",
                    text,
                )[:10],
                "headers": headers,
                "reconstructed": [
                    {
                        "kind": p.statement_type,
                        "name": p.statement_name,
                        "basis": p.basis,
                        "unit": p.unit_scale,
                        "columns": [c.label for c in p.columns],
                    }
                    for p in reconstructed
                    if p.page == page_no
                ],
                "unique_rows": unique_rows,
                "text_head": text[:700],
            }
        )
    return {
        "pages": len(reader.pages),
        "fields": fields,
        "dump": page_dump,
        "reconstructed_pages": [
            {
                "page": p.page,
                "kind": p.statement_type,
                "unit": p.unit_scale,
                "basis": p.basis,
                "columns": [c.label for c in p.columns],
            }
            for p in reconstructed
        ],
    }


def main() -> None:
    transport = NsePublicHttp()
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    rows = {}
    for ticker, spec in TARGETS.items():
        local = PDF_DIR / f"{ticker}_AR.pdf"
        print("LOAD", ticker, flush=True)
        if local.exists() and local.stat().st_size > 100000:
            payload = local.read_bytes()
            url = spec["url"]
            digest = None
        else:
            record = retrieve_official_document(
                spec["url"],
                transport=transport,
                isin=spec["isin"],
                mic="XNSE",
                source_type="regulator",
            )
            if hasattr(record, "reason"):
                rows[ticker] = {"fail": record.reason, "url": spec["url"]}
                print("FAIL", ticker, record.reason, flush=True)
                continue
            payload = record.payload
            local.write_bytes(payload)
            url = record.url
            digest = record.document_hash
        result = inspect_pages(ticker, payload, spec["pages"])
        result["url"] = url
        result["hash"] = digest
        result["size"] = len(payload)
        rows[ticker] = result
        print(
            ticker,
            "recon",
            result["reconstructed_pages"],
            {k: (v or {}).get("raw") for k, v in result["fields"].items()},
            flush=True,
        )
    OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
