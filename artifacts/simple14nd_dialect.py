"""SIMPLE-14N-D — dialect classification + shareholding/CA discovery. Not evidence."""

from __future__ import annotations

import json
import logging
import re
from io import BytesIO
from pathlib import Path
from time import perf_counter

logging.getLogger("fontTools").setLevel(logging.ERROR)
logging.getLogger("pypdf").setLevel(logging.ERROR)

from pypdf import PdfReader

from data_engine.official_research.documents import DocumentStore, retrieve_official_document
from data_engine.official_research.nse_eod import NsePublicHttp
from data_engine.official_research.nse_primary import (
    NSE_ANNOUNCEMENTS_URL,
    NSE_ANNUAL_REPORTS_URL,
    NSE_SHAREHOLDING_URL,
    parse_annual_report_documents,
    parse_announcement_capital_events,
    parse_announcement_documents,
    parse_shareholding_shares,
)
from data_engine.official_research.pdf_text import document_text_from_payload
from data_engine.official_research.statement_tables import (
    extract_field_from_statements,
    reconstruct_statement_pages,
)
from data_engine.official_research.pdf_text import split_marked_pages
from data_engine.security_master.catalog import load_default_catalog
from data_engine.security_master.service import SecurityMasterService

FIXTURES = (
    ("INFY", "INE009A01021"),
    ("TCS", "INE467B01029"),
    ("WIPRO", "INE075A01022"),
    ("HDFCBANK", "INE040A01034"),
    ("RELIANCE", "INE002A01018"),
    ("ASIANPAINT", "INE021A01026"),
    ("HINDUNILVR", "INE030A01027"),
)
FIELDS = (
    "revenue",
    "net_income",
    "equity",
    "cash",
    "cfo",
    "total_assets",
    "total_liabilities",
)
OUT = Path("artifacts/simple14nd_dialect.json")
PDF_DIR = Path("artifacts/simple14nc_pdfs")


def _classify_dialect(pages) -> str:
    if not pages:
        return "UNCLASSIFIED"
    titles_bottom = 0
    wrapped = 0
    multi = 0
    encoding = 0
    for page in pages:
        blob = " ".join(s.text for s in page.spans[-8:])
        if re.search(r"balance sheet|profit and loss|cash flow", blob, re.I):
            titles_bottom += 1
        if any(" " in (r.current_raw or "") for r in page.rows):
            wrapped += 1
        if page.unit_scale is None:
            encoding += 1
    kinds = {p.statement_type for p in pages}
    if len(pages) >= 4 and {"pl", "bs", "cf"} <= kinds:
        multi += 1
    tags = []
    if titles_bottom:
        tags.append("D_TITLE_BOTTOM")
    if wrapped:
        tags.append("B_WRAPPED")
    if multi:
        tags.append("C_MULTI_PAGE")
    if encoding:
        tags.append("E_UNIT_ENCODING")
    if {"pl", "bs"} <= kinds:
        tags.append("A_POSITIONAL")
    return "+".join(tags) or "F_MIXED"


def main() -> None:
    master = SecurityMasterService(load_default_catalog())
    transport = NsePublicHttp()
    store = DocumentStore()
    rows = []
    for ticker, isin in FIXTURES:
        listing = master.resolve(ticker, exchange="NSE", isin=isin, mic="XNSE").identity
        assert listing is not None
        t0 = perf_counter()
        ar_url = f"{NSE_ANNUAL_REPORTS_URL}?index=equities&symbol={ticker}"
        ar_payload = json.loads(
            transport.get_bytes(ar_url, referer="https://www.nseindia.com/all-reports")
        )
        docs = parse_annual_report_documents(ar_payload)
        fy26 = [d for d in docs if "2025-2026" in (d.title or "") or "2025_2026" in d.url]
        selected = fy26[0] if fy26 else None
        hold = None
        events = []
        share_docs = []
        try:
            hold_url = f"{NSE_SHAREHOLDING_URL}?index=equities&symbol={ticker}"
            hold_payload = json.loads(
                transport.get_bytes(hold_url, referer="https://www.nseindia.com/all-reports")
            )
            hold_field = parse_shareholding_shares(hold_payload, ticker=ticker)
            hold = None if hold_field is None else {
                "value": hold_field.value,
                "as_of": None if hold_field.as_of is None else hold_field.as_of.isoformat(),
                "locator": hold_field.locator,
            }
        except LookupError as exc:
            hold = {"error": str(exc)}
        try:
            ann_url = f"{NSE_ANNOUNCEMENTS_URL}?index=equities&symbol={ticker}"
            ann_payload = json.loads(
                transport.get_bytes(ann_url, referer="https://www.nseindia.com/all-reports")
            )
            events = [
                {"type": e.event_type, "date": e.event_date.isoformat()}
                for e in parse_announcement_capital_events(ann_payload)
                if e.event_date.year >= 2025
            ]
            for d in parse_announcement_documents(ann_payload):
                title = (d.title or "").lower()
                if any(
                    k in title
                    for k in (
                        "buyback",
                        "extinguish",
                        "share capital",
                        "paid-up",
                        "paid up",
                        "esop",
                        "allotment",
                    )
                ):
                    share_docs.append(
                        {
                            "title": d.title,
                            "url": d.url,
                            "as_of": None if d.as_of is None else d.as_of.isoformat(),
                            "kind": d.kind,
                        }
                    )
        except LookupError as exc:
            events = [{"error": str(exc)}]
        json_s = perf_counter() - t0
        if selected is None:
            rows.append({"ticker": ticker, "error": "no FY26 AR"})
            print(ticker, "NO AR", flush=True)
            continue
        dl = perf_counter()
        record = retrieve_official_document(
            selected.url,
            transport=transport,
            isin=isin,
            mic="XNSE",
            source_type="regulator",
            store=store,
        )
        download_s = perf_counter() - dl
        if hasattr(record, "reason"):
            rows.append({"ticker": ticker, "fail": record.reason, "url": selected.url})
            print(ticker, "FAIL", record.reason, flush=True)
            continue
        PDF_DIR.mkdir(parents=True, exist_ok=True)
        (PDF_DIR / f"{ticker}_AR.pdf").write_bytes(record.payload)
        open_s = perf_counter()
        reader = PdfReader(BytesIO(record.payload))
        page_count = len(reader.pages)
        open_elapsed = perf_counter() - open_s
        tx = perf_counter()
        from data_engine.official_research.pdf_text import document_text_from_payload
        text = document_text_from_payload(record.payload) or ""
        text_s = perf_counter() - tx
        rec_s = perf_counter()
        pages = reconstruct_statement_pages(
            record.payload, page_texts=split_marked_pages(text)
        )
        reconstruct_s = perf_counter() - rec_s
        fields = {}
        for name in FIELDS:
            item = extract_field_from_statements(pages, name)
            fields[name] = None if item is None else {
                "status": item.semantic_status,
                "raw": item.raw_value,
                "value": item.value,
                "unit": item.raw_unit,
                "locator": item.locator,
                "period": None if item.period_end is None else item.period_end.isoformat(),
                "basis": item.statement_basis,
            }
        sample_headers = []
        for page in pages[:6]:
            sample_headers.append(
                {
                    "page": page.page,
                    "kind": page.statement_type,
                    "unit": page.unit_scale,
                    "basis": page.basis,
                    "columns": [c.label[:40] for c in page.columns],
                    "row_labels": [r.label[:60] for r in page.rows if r.pairing == "UNIQUE"][:8],
                }
            )
        rows.append(
            {
                "ticker": ticker,
                "isin": isin,
                "url": selected.url,
                "hash": record.document_hash,
                "size": record.content_length,
                "pages": page_count,
                "json_s": round(json_s, 3),
                "download_s": round(download_s, 3),
                "open_s": round(open_elapsed, 3),
                "text_s": round(text_s, 3),
                "reconstruct_s": round(reconstruct_s, 3),
                "statement_pages": len(pages),
                "dialect": _classify_dialect(pages),
                "fields": fields,
                "sample": sample_headers,
                "shareholding": hold,
                "ca_2025plus": events[:20],
                "share_docs": share_docs[:12],
            }
        )
        print(
            ticker,
            "pages",
            page_count,
            "stmts",
            len(pages),
            "dialect",
            _classify_dialect(pages),
            {k: (v or {}).get("status") for k, v in fields.items()},
            flush=True,
        )
    OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
