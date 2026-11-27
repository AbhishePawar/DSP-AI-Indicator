import pytest

from dsp_platform.research_retrieval import pdf_extraction


def test_busy_extraction_rejected():
    slot = pdf_extraction._PDF_EXTRACTION_SLOT

    assert slot.acquire(blocking=False)

    try:
        with pytest.raises(
            pdf_extraction.PdfExtractionError,
            match="capacity",
        ):
            pdf_extraction.extract_pdf_text(b"%PDF-1.7")
    finally:
        slot.release()


def test_slot_released_after_failure():
    with pytest.raises(pdf_extraction.PdfExtractionError):
        pdf_extraction.extract_pdf_text(b"invalid")

    slot = pdf_extraction._PDF_EXTRACTION_SLOT

    assert slot.acquire(blocking=False)
    slot.release()


def test_slot_released_after_success(monkeypatch):
    monkeypatch.setattr(
        pdf_extraction,
        "_extract_pdf_text",
        lambda raw: "Financial report",
    )

    assert (
        pdf_extraction.extract_pdf_text(b"%PDF-1.7")
        == "Financial report"
    )

    slot = pdf_extraction._PDF_EXTRACTION_SLOT

    assert slot.acquire(blocking=False)
    slot.release()
