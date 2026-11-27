import pytest

from dsp_platform.research_retrieval.document_validator import (
    _period_matches_value_context,
)


@pytest.mark.parametrize(
    "text",
    [
        "Revenue 1000 FY2026",
        "Revenue 1000 FY26",
        "Revenue 1000 FY 2025-26",
        "Revenue 1000 fy2026",
    ],
)
def test_correct_period_accepted(text):
    assert _period_matches_value_context(
        "FY2026", text
    )


@pytest.mark.parametrize(
    "text",
    [
        "Revenue 1000 FY2025",
        "Revenue 1000",
        "Revenue 1000 FY2020",
        "Revenue 1000 FY2025 and 1200 FY2026",
        "Revenue 1000 FY2026 and 800 FY2025",
    ],
)
def test_wrong_or_ambiguous_period_rejected(text):
    assert not _period_matches_value_context(
        "FY2026", text
    )


def test_quarter_mismatch():
    assert not _period_matches_value_context(
        "Q1FY2026",
        "Revenue 1000 Q2FY2026",
    )


def test_correct_quarter():
    assert _period_matches_value_context(
        "Q1FY2026",
        "Revenue 1000 Q1FY2026",
    )
