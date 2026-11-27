import pytest

from dsp_platform.research_retrieval.document_validator import (
    DocumentValidator,
)
from dsp_platform.research_retrieval.governance import (
    RetrievalGovernance,
)
from dsp_platform.research_retrieval.models import (
    FetchedDocument,
)


@pytest.mark.parametrize(
    "source,url,purpose",
    [
        ("NSE", "", "fundamental"),
        ("NSE", "http://nseindia.com/filing", "fundamental"),
        ("NSE", "https://bseindia.com/filing", "fundamental"),
        ("BSE", "https://nseindia.com/filing", "fundamental"),
        ("UPSTOX", "https://example.com/quote", "market_quote"),
        ("NSE", "https://nseindia.com.example.com", "fundamental"),
        ("NSE", "https://nseindia.com:8443/filing", "fundamental"),
        ("NSE", "https://nseindia.com/filing", "unknown"),
    ],
)
def test_invalid_source_rejected(source, url, purpose):
    decision = RetrievalGovernance().evaluate_source(
        source, url, purpose
    )
    assert not decision.is_approved


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        -100,
        0,
        100.5,
        101,
    ],
)
def test_invalid_share_claim_rejected(value):
    document = FetchedDocument(
        "https://nseindia.com/filing",
        "https://nseindia.com/filing",
        200,
        "text/plain",
        "RELIANCE outstanding shares were 100.",
        "synthetic-test-hash",
        "2026-11-27",
    )

    result = DocumentValidator().validate_claim(
        document,
        "RELIANCE",
        "Outstanding shares",
        claimed_value=value,
        is_share_count=True,
    )

    assert not result.is_valid


def test_exact_share_claim_accepted():
    document = FetchedDocument(
        "https://nseindia.com/filing",
        "https://nseindia.com/filing",
        200,
        "text/plain",
        "RELIANCE outstanding shares were 100.",
        "synthetic-test-hash",
        "2026-11-27",
    )

    result = DocumentValidator().validate_claim(
        document,
        "RELIANCE",
        "Outstanding shares",
        claimed_value=100,
        is_share_count=True,
    )

    assert result.is_valid
