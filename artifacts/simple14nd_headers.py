"""Dump remaining dialect blockers: INFY/HUL/RIL/AP/HDFC headers and HDFC 70m context."""

from __future__ import annotations

import json
import logging
import re
from io import BytesIO
from pathlib import Path

logging.getLogger("fontTools").setLevel(logging.ERROR)

from pypdf import PdfReader

from data_engine.official_research.statement_tables import spans_from_pdf

PDF_DIR = Path("artifacts/simple14nc_pdfs")
OUT = Path("artifacts/simple14nd_headers.json")


def dump(ticker: str, pages: tuple[int, ...], needles: tuple[str, ...] = ()) -> dict:
    payload = (PDF_DIR / f"{ticker}_AR.pdf").read_bytes()
    reader = PdfReader(BytesIO(payload))
    wanted = spans_from_pdf(payload, page_numbers=pages)
    rows = []
    for page_no in pages:
        text = reader.pages[page_no - 1].extract_text() or ""
        spans = wanted[page_no - 1]
        short = [
            {"t": s.text[:80], "x": round(s.x, 1), "y": round(s.y, 1)}
            for s in sorted(spans, key=lambda item: (-item.y, item.x))
            if len(s.text) <= 40
        ][:40]
        hits = []
        for needle in needles:
            idx = text.lower().find(needle.lower())
            if idx >= 0:
                hits.append(text[max(0, idx - 120) : idx + 220])
        rows.append(
            {
                "page": page_no,
                "title": bool(
                    re.search(
                        r"consolidated (balance sheet|statement of profit|profit and loss|cash flow)",
                        text,
                        re.I,
                    )
                ),
                "head": text[:900],
                "short_spans": short,
                "needles": hits,
            }
        )
    return rows


def main() -> None:
    data = {
        "INFY_286_289": dump("INFY", (285, 286, 287, 288, 289)),
        "HUL_184_186": dump("HINDUNILVR", (184, 185, 186, 199, 200)),
        "RIL_145_147": dump("RELIANCE", (145, 146, 147)),
        "AP_232_234": dump("ASIANPAINT", (232, 233, 234)),
        "HDFC_496_571": dump(
            "HDFCBANK",
            (496, 497, 561, 571),
            needles=("70,490,586", "70490586", "70,490,586", "equity shares"),
        ),
        "TCS_167_equity": dump("TCS", (167,), needles=("TOTAL EQUITY", "Equity attributable", "TOTAL LIABILITIES")),
    }
    OUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
