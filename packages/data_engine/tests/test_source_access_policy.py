
import pytest

from data_engine.source_access_policy import (
    evaluate_source_access,
)


@pytest.mark.parametrize(
    "source,capability,url",
    [
        (
            "SEC_COMPANY_FACTS",
            "structured_fundamentals",
            "https://data.sec.gov/api/xbrl/companyfacts/CIK0001067491.json",
        ),
        (
            "SEC_SUBMISSIONS",
            "filing_discovery",
            "https://data.sec.gov/submissions/CIK0001144967.json",
        ),
        (
            "WORLD_BANK",
            "economics",
            "https://api.worldbank.org/v2/country/IND/indicator/NY.GDP.MKTP.CD?format=json",
        ),
    ],
)
def test_reviewed_endpoints(source, capability, url):

    result = evaluate_source_access(
        source, capability, url
    )

    assert result.permitted
    assert not result.authorized_for_valuation


@pytest.mark.parametrize(
    "source,capability,url",
    [
        (
            "UNKNOWN", "fundamentals",
            "https://example.com/",
        ),
        (
            "WORLD_BANK", "fundamentals",
            "https://api.worldbank.org/",
        ),
        (
            "OPENAI_RESEARCH", "source_discovery",
            "https://example.com/",
        ),
        (
            "NSE", "fundamentals",
            "https://www.nseindia.com/",
        ),
        (
            "SEC_COMPANY_FACTS",
            "structured_fundamentals",
            "https://data.sec.gov.attacker.example/",
        ),
        (
            "SEC_COMPANY_FACTS",
            "structured_fundamentals",
            "http://data.sec.gov/api/xbrl/companyfacts/CIK0001067491.json",
        ),
        (
            "SEC_COMPANY_FACTS",
            "structured_fundamentals",
            "https://data.sec.gov/api/xbrl/companyfacts/CIK123.json",
        ),
        (
            "SEC_COMPANY_FACTS",
            "structured_fundamentals",
            "https://data.sec.gov/api/xbrl/companyfacts/../private",
        ),
        (
            "SEC_SUBMISSIONS",
            "filing_discovery",
            "https://data.sec.gov/submissions/CIK0001067491.json?redirect=evil",
        ),
        (
            "SEC_SUBMISSIONS",
            "filing_discovery",
            "https://data.sec.gov/submissions/CIK0001067491.json#fragment",
        ),
        (
            "SEC_SUBMISSIONS",
            "filing_discovery",
            "https://user:password@data.sec.gov/submissions/CIK0001067491.json",
        ),
        (
            "SEC_SUBMISSIONS",
            "filing_discovery",
            "https://data.sec.gov:8443/submissions/CIK0001067491.json",
        ),
    ],
)
def test_unauthorized_endpoints(
    source, capability, url
):

    result = evaluate_source_access(
        source, capability, url
    )

    assert not result.permitted
    assert not result.authorized_for_valuation
