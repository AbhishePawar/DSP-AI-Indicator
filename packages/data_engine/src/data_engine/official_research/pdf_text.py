"""PDF/HTML text extraction. No OCR. Scanned PDFs stay UNAVAILABLE."""

from __future__ import annotations

import re
from io import BytesIO

__all__ = ["document_text_from_payload", "split_marked_pages"]


def document_text_from_payload(payload: bytes, *, content_type: str = "") -> str | None:
    """Return extractable text or None when the document has no usable text layer."""
    _ = content_type
    if not payload:
        return None
    if payload.lstrip().startswith(b"%PDF"):
        return _pdf_text(payload)
    if b"\x00" in payload[:1024] and not payload.lstrip().startswith((b"<", b"{")):
        return None
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = payload.decode("latin-1")
        except UnicodeDecodeError:
            return None
    cleaned = text.strip()
    return cleaned or None


def split_marked_pages(text: str) -> tuple[str, ...]:
    """Split [[PAGE n]] marked extraction into 1-indexed page texts."""
    matches = list(re.finditer(r"\[\[PAGE (\d+)\]\]\n?", str(text or "")))
    if not matches:
        return (text,) if str(text or "").strip() else ()
    pages: list[str] = []
    expected = 1
    for index, match in enumerate(matches):
        number = int(match.group(1))
        while expected < number:
            pages.append("")
            expected += 1
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        pages.append(text[match.end() : end])
        expected = number + 1
    return tuple(pages)


def _pdf_text(payload: bytes) -> str | None:
    try:
        from pypdf import PdfReader  # type: ignore[import-untyped]
    except ImportError:
        PdfReader = None  # type: ignore[misc, assignment]
    if PdfReader is not None:
        try:
            reader = PdfReader(BytesIO(payload))
            pages: list[str] = []
            for index, page in enumerate(reader.pages, start=1):
                pages.append(f"[[PAGE {index}]]\n{page.extract_text() or ''}")
            text = "\n".join(pages).strip()
            if text:
                return text
        except Exception:
            pass
    strings = re.findall(rb"\((?:\\.|[^\\)]){3,}\)", payload)
    decoded: list[str] = []
    for raw in strings[:4000]:
        inner = raw[1:-1].replace(b"\\(", b"(").replace(b"\\)", b")")
        try:
            decoded.append(inner.decode("latin-1"))
        except UnicodeDecodeError:
            continue
    text = "\n".join(decoded).strip()
    return text or None
