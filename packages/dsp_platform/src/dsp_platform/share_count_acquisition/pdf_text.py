"""Untrusted PDF text extraction. Does not follow embedded URLs or execute JS."""

from __future__ import annotations

from io import BytesIO

__all__ = ["MAX_PDF_CHARS", "MAX_PDF_PAGES", "extract_pdf_text"]

MAX_PDF_PAGES = 40
MAX_PDF_CHARS = 200_000


def extract_pdf_text(raw: bytes, *, max_pages: int = MAX_PDF_PAGES) -> str:
    """Return extracted text or empty string. Fail closed on parser errors."""
    if not raw or not raw.lstrip().startswith(b"%PDF"):
        return ""
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(BytesIO(raw), strict=False)
        pages = list(reader.pages)[: max(0, int(max_pages))]
        chunks: list[str] = []
        total = 0
        for page in pages:
            text = str(page.extract_text() or "")
            text = text.replace("\x00", "")
            chunks.append(text)
            total += len(text)
            if total >= MAX_PDF_CHARS:
                break
        return "\n".join(chunks)[:MAX_PDF_CHARS]
    except Exception:
        return ""
