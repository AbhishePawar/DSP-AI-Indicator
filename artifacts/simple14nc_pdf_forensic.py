"""SIMPLE-14N-C — inspect official NSE AR PDFs for coordinates/tables. Not evidence."""

from __future__ import annotations

import hashlib
import json
import re
import warnings
from io import BytesIO
from pathlib import Path
from time import perf_counter

from pypdf import PdfReader

from data_engine.official_research.documents import retrieve_official_document, DocumentStore
from data_engine.official_research.nse_eod import NsePublicHttp
from data_engine.official_research.nse_primary import (
    NSE_ANNOUNCEMENTS_URL,
    NSE_ANNUAL_REPORTS_URL,
    parse_annual_report_documents,
    parse_announcement_documents,
    parse_announcement_capital_events,
)
from data_engine.security_master.catalog import load_default_catalog
from data_engine.security_master.service import SecurityMasterService

warnings.filterwarnings("ignore")

FIXTURES = (
    ("INFY", "INE009A01021"),
    ("TCS", "INE467B01029"),
    ("WIPRO", "INE075A01022"),
    ("HDFCBANK", "INE040A01034"),
    ("RELIANCE", "INE002A01018"),
    ("ASIANPAINT", "INE021A01026"),
    ("HINDUNILVR", "INE030A01027"),
)

_PL = re.compile(
    r"statement of profit\s*(?:and|&)\s*loss|statement of financial performance",
    re.I,
)
_BS = re.compile(r"balance sheet|statement of financial position", re.I)
_CF = re.compile(r"statement of cash flows|cash flow statement", re.I)
_STAND = re.compile(r"\bstandalone\b", re.I)
_CONS = re.compile(r"\bconsolidated\b", re.I)
_NUM = re.compile(r"\d{2,}")
_OUT = Path("artifacts/simple14nc_pdf_forensic.json")


def _visitor_collect(page) -> list[dict]:
    found: list[dict] = []

    def visitor(text, cm, tm, font_dict, font_size) -> None:
        raw = str(text or "").strip()
        if not raw:
            return
        found.append(
            {
                "text": raw[:80],
                "x": round(float(tm[4]), 2),
                "y": round(float(tm[5]), 2),
                "size": None if font_size is None else round(float(font_size), 1),
            }
        )

    page.extract_text(visitor_text=visitor)
    return found


def _classify_page(text: str) -> str | None:
    if _PL.search(text):
        kind = "pl"
    elif _BS.search(text):
        kind = "bs"
    elif _CF.search(text):
        kind = "cf"
    else:
        return None
    if len(_NUM.findall(text)) < 6:
        return None
    if _STAND.search(text) and not _CONS.search(text):
        return f"standalone_{kind}"
    if _CONS.search(text):
        return f"consolidated_{kind}"
    return f"unlabeled_{kind}"


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
        ar_payload = json.loads(transport.get_bytes(ar_url, referer="https://www.nseindia.com/all-reports"))
        docs = parse_annual_report_documents(ar_payload)
        fy26 = [d for d in docs if "2025-2026" in (d.title or "") or "2025_2026" in d.url]
        selected = fy26[0] if fy26 else (docs[0] if docs else None)
        try:
            ann_url = f"{NSE_ANNOUNCEMENTS_URL}?index=equities&symbol={ticker}"
            ann_payload = json.loads(
                transport.get_bytes(ann_url, referer="https://www.nseindia.com/all-reports")
            )
            events = [
                {"type": e.event_type, "date": e.event_date.isoformat()}
                for e in parse_announcement_capital_events(ann_payload)
            ]
            buyback_docs = [
                {
                    "title": d.title,
                    "url": d.url,
                    "as_of": None if d.as_of is None else d.as_of.isoformat(),
                }
                for d in parse_announcement_documents(ann_payload)
                if "buy" in (d.title or "").lower()
            ]
        except LookupError as exc:
            events = [{"error": str(exc)}]
            buyback_docs = []
        json_s = perf_counter() - t0
        if selected is None:
            rows.append({"ticker": ticker, "error": "no annual report"})
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
            rows.append({"ticker": ticker, "retrieval": record.reason, "url": selected.url})
            print(ticker, "FAIL", record.reason, flush=True)
            continue
        payload = record.payload
        open_s = perf_counter()
        reader = PdfReader(BytesIO(payload))
        page_count = len(reader.pages)
        open_elapsed = perf_counter() - open_s
        text_s = 0.0
        coord_s = 0.0
        statement_pages = []
        scanned = 0
        coord_samples = []
        for index, page in enumerate(reader.pages, start=1):
            ts = perf_counter()
            text = page.extract_text() or ""
            text_s += perf_counter() - ts
            if len(text.strip()) < 40:
                scanned += 1
            kind = _classify_page(text)
            if kind is None:
                continue
            cs = perf_counter()
            coords = _visitor_collect(page)
            coord_s += perf_counter() - cs
            xs = [c["x"] for c in coords]
            ys = [c["y"] for c in coords]
            numbers = [
                c
                for c in coords
                if re.fullmatch(r"[-+]?\d[\d,]*\.?\d*", c["text"].replace(",", ""))
            ]
            statement_pages.append(
                {
                    "page": index,
                    "kind": kind,
                    "chars": len(text),
                    "coord_fragments": len(coords),
                    "number_fragments": len(numbers),
                    "x_range": None if not xs else [min(xs), max(xs)],
                    "y_range": None if not ys else [min(ys), max(ys)],
                }
            )
            if kind.startswith("consolidated_") and len(coord_samples) < 3:
                head = [
                    c
                    for c in coords
                    if re.search(r"31 March|March 31|2026|crore|million|₹", c["text"], re.I)
                ]
                coord_samples.append(
                    {
                        "page": index,
                        "kind": kind,
                        "headers": head[:16],
                        "numbers": numbers[:10],
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
                "coord_s": round(coord_s, 3),
                "low_text_pages": scanned,
                "statement_pages": statement_pages,
                "coord_samples": coord_samples,
                "ca_events": events[:12],
                "buyback_docs": buyback_docs[:8],
                "sha256_payload": hashlib.sha256(payload).hexdigest(),
            }
        )
        print(
            ticker,
            "pages",
            page_count,
            "stmts",
            len(statement_pages),
            "coords",
            bool(coord_samples),
            "hash",
            record.document_hash[:12],
            flush=True,
        )
    _OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("wrote", _OUT, flush=True)


if __name__ == "__main__":
    main()
