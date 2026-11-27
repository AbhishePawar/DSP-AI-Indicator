import pytest

from dsp_platform.research_retrieval.document_validator import (
    DocumentValidator,
)

from dsp_platform.research_retrieval.url_safety import (
    FetchedDocument,
)


def validate(text, value=1000, period="FY2026"):
    url = "https://www.bseindia.com/report"

    document = FetchedDocument(
        url=url,
        final_url=url,
        status_code=200,
        content_type="text/plain",
        text_content=text,
        content_hash="test_hash",
        fetched_at="2026-11-27",
    )

    return DocumentValidator().validate_claim(
        document,
        "RELIANCE",
        "Revenue",
        metric_name="revenue",
        claimed_value=value,
        claimed_period=period,
    )


@pytest.mark.parametrize(
    "text",
    [
        "RELIANCE revenue 1000 FY2026",
        "RELIANCE revenue 1000 FY26",
        "RELIANCE revenue 1000 FY 2025-26",
    ],
)
def test_matching_period(text):
    assert validate(text).is_valid


@pytest.mark.parametrize(
    "text",
    [
        "RELIANCE revenue 1000 FY2025",
        "RELIANCE revenue 1000 Q1FY2026",
        "RELIANCE revenue 1000 FY2025\nFY2026 outlook",
        "RELIANCE revenue 1000 FY2025 and 1500 FY2026",
        "RELIANCE revenue 1000\nFY2026 outlook",
    ],
)
def test_wrong_or_ambiguous_period(text):
    assert not validate(text).is_valid


def test_correct_value_in_correct_period():
    assert validate(
        "RELIANCE revenue 800 FY2025\n"
        "RELIANCE revenue 1000 FY2026"
    ).is_valid


def test_annual_and_quarterly_values_not_interchangeable():
    assert not validate(
        "RELIANCE revenue 1000 Q2FY2026",
        period="Q1FY2026",
    ).is_valid
