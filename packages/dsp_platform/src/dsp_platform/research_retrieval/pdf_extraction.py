"""Bounded PDF extraction interface."""

import subprocess
import threading
import sys
from pathlib import Path


class PdfExtractionError(ValueError):
    pass



_PDF_EXTRACTION_SLOT = threading.BoundedSemaphore(1)


def extract_pdf_text(raw: bytes) -> str:
    if not _PDF_EXTRACTION_SLOT.acquire(blocking=False):
        raise PdfExtractionError(
            "PDF extraction capacity temporarily exhausted"
        )

    try:
        return _extract_pdf_text(raw)
    finally:
        _PDF_EXTRACTION_SLOT.release()


def _extract_pdf_text(raw: bytes) -> str:
    if len(raw) > 20 * 1024 * 1024:
        raise PdfExtractionError("PDF exceeds size limit")

    if not raw.startswith(b"%PDF-"):
        raise PdfExtractionError("Invalid PDF signature")

    worker = Path(__file__).with_name("pdf_worker.py")

    try:
        result = subprocess.run(
            [sys.executable, "-I", str(worker)],
            input=raw,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=15,
            check=False,
            env={"PYTHONIOENCODING": "utf-8"},
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise PdfExtractionError(
            "PDF extraction unavailable or timed out"
        ) from exc

    if result.returncode != 0:
        raise PdfExtractionError(
            "PDF extraction failed or exceeded resource limits"
        )

    text = result.stdout.decode("utf-8")

    if not text.strip() or len(text) > 2_000_000:
        raise PdfExtractionError("Invalid extracted PDF text")

    return text
