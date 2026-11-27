import io
import subprocess

import pytest

from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

from dsp_platform.research_retrieval.pdf_extraction import (
    PdfExtractionError,
    extract_pdf_text,
)


def make_pdf(text=None, encrypted=False):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    if text:
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })

        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({
                NameObject("/F1"): writer._add_object(font),
            })
        })

        stream = DecodedStreamObject()
        stream.set_data(
            f"BT /F1 12 Tf 50 700 Td ({text}) Tj ET".encode()
        )

        page[NameObject("/Contents")] = writer._add_object(
            stream
        )

    if encrypted:
        writer.encrypt("test-password")

    output = io.BytesIO()
    writer.write(output)

    return output.getvalue()


def test_financial_text_extraction():
    result = extract_pdf_text(
        make_pdf("Outstanding equity shares 1000000")
    )

    assert "Outstanding equity shares 1000000" in result
    assert "[PDF page 1]" in result


def test_invalid_signature():
    with pytest.raises(PdfExtractionError):
        extract_pdf_text(b"not a pdf")


def test_corrupt_pdf():
    with pytest.raises(PdfExtractionError):
        extract_pdf_text(b"%PDF-1.7\ninvalid")


def test_empty_document():
    with pytest.raises(PdfExtractionError):
        extract_pdf_text(make_pdf())


def test_encrypted_document():
    with pytest.raises(PdfExtractionError):
        extract_pdf_text(make_pdf("Financial report", True))


def test_oversized_document():
    with pytest.raises(PdfExtractionError):
        extract_pdf_text(
            b"%PDF-" + b"x" * (20 * 1024 * 1024)
        )


def test_extraction_timeout(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("pdf_worker", 15)

    monkeypatch.setattr(subprocess, "run", timeout)

    with pytest.raises(PdfExtractionError):
        extract_pdf_text(b"%PDF-1.7\n")


def test_page_limit():
    writer = PdfWriter()

    for _ in range(501):
        writer.add_blank_page(width=612, height=792)

    output = io.BytesIO()
    writer.write(output)

    with pytest.raises(PdfExtractionError):
        extract_pdf_text(output.getvalue())


def test_secure_fetcher_pdf_integration(monkeypatch):
    import hashlib

    from dsp_platform.research_retrieval.url_safety import (
        DefaultSafeHttpFetcher,
    )

    raw = make_pdf("Outstanding equity shares 1000000")

    fetcher = DefaultSafeHttpFetcher()

    monkeypatch.setattr(
        fetcher,
        "_validate_and_resolve_destination",
        lambda url: ("example.com", "8.8.8.8"),
    )

    monkeypatch.setattr(
        fetcher,
        "_execute_request",
        lambda **kwargs: (
            200,
            {"content-type": "application/pdf"},
            raw,
        ),
    )

    document = fetcher.fetch(
        "https://example.com/annual-report.pdf"
    )

    assert "Outstanding equity shares 1000000" in document.text_content
    assert document.content_hash == hashlib.sha256(raw).hexdigest()
    assert document.content_type == "application/pdf"
