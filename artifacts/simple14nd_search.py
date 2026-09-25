"""Locate Reliance statement pages and HDFC 70,490,586 context."""

from __future__ import annotations

import logging
import re
from io import BytesIO
from pathlib import Path

logging.getLogger("fontTools").setLevel(logging.ERROR)
from pypdf import PdfReader

PDF_DIR = Path("artifacts/simple14nc_pdfs")


def search(ticker: str, patterns: tuple[str, ...], *, limit: int = 12) -> None:
    reader = PdfReader(BytesIO((PDF_DIR / f"{ticker}_AR.pdf").read_bytes()))
    compiled = [re.compile(p, re.I) for p in patterns]
    hits = 0
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for pattern in compiled:
            match = pattern.search(text)
            if match is None:
                continue
            start = max(0, match.start() - 160)
            print(f"\n=== {ticker} p{index} {pattern.pattern} ===")
            print(text[start : match.end() + 220].replace("\n", " | "))
            hits += 1
            break
        if hits >= limit:
            break
    print(f"{ticker} hits={hits} pages={len(reader.pages)}")


if __name__ == "__main__":
    search(
        "RELIANCE",
        (
            r"Consolidated Balance Sheet",
            r"Consolidated Statement of Profit",
            r"Consolidated Statement of Cash",
        ),
        limit=8,
    )
    search(
        "HDFCBANK",
        (
            r"70,490,586",
            r"70490586",
            r"70,49,05,86",
            r"equity shares outstanding",
            r"shares issued under",
            r"ESOS",
        ),
        limit=15,
    )
    search(
        "WIPRO",
        (r"equity shares outstanding", r"buyback of 60,00,00,000", r"10,476,247,846"),
        limit=6,
    )
