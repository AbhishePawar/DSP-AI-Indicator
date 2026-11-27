from datetime import date

import pytest

from data_engine import ShareCount
from dsp_platform.research_retrieval.document_validator import (
    DocumentValidator,
)
from dsp_platform.research_retrieval.models import (
    FetchedDocument,
)


@pytest.mark.parametrize(
    "text,value,expected",
    [
        (
            "RELIANCE outstanding shares were 100.",
            100,
            True,
        ),
        (
            "RELIANCE shares outstanding were 100.",
            100,
            True,
        ),
        (
            "RELIANCE period-end shares were 100.",
            100,
            True,
        ),
        (
            "RELIANCE weighted average shares were 100.",
            100,
            False,
        ),
        (
            "RELIANCE diluted shares were 100.\n"
            "Outstanding shares were 200.",
            100,
            False,
        ),
        (
            "RELIANCE weighted average shares were 100.\n"
            "Outstanding shares were 200.",
            100,
            False,
        ),
        (
            "RELIANCE revenue was 100.",
            100,
            False,
        ),
    ],
)
def test_share_metric_context(text, value, expected):
    doc = FetchedDocument(
        "https://nseindia.com/filing",
        "https://nseindia.com/filing",
        200,
        "text/plain",
        text,
        "synthetic-test-hash",
        "2026-11-27",
    )

    result = DocumentValidator().validate_claim(
        doc,
        "RELIANCE",
        "Outstanding shares",
        claimed_value=value,
        is_share_count=True,
    )

    assert result.is_valid is expected


@pytest.mark.parametrize("value", [0.5, 100.25, 100.999])
def test_fractional_share_count_rejected(value):
    with pytest.raises(ValueError, match="whole number"):
        ShareCount(
            "RELIANCE",
            value,
            date(2026, 9, 30),
            "NSE",
            verified=True,
        )
