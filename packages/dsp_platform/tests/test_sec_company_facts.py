
import copy
import json

from types import SimpleNamespace

import pytest

from dsp_platform.research_retrieval.sec_company_facts import (
    SecCompanyFactsService,
    SecFactsError,
)


ACCESSION = "0001067491-25-000010"
FILED = "2025-06-20"


@pytest.fixture
def submissions():

    return {
        "cik": "1067491",
        "name": "Infosys Limited",
        "filings": {
            "recent": {
                "form": ["20-F"],
                "reportDate": ["2025-03-31"],
                "filingDate": [FILED],
                "accessionNumber": [ACCESSION],
                "primaryDocument": ["infosys.htm"],
            }
        },
    }


def observation(value=1000, **changes):

    item = {
        "accn": ACCESSION,
        "form": "20-F",
        "filed": FILED,
        "start": "2024-04-01",
        "end": "2025-03-31",
        "val": value,
    }

    item.update(changes)

    return item


@pytest.fixture
def facts():

    return {
        "cik": 1067491,
        "entityName": "Infosys Limited",
        "facts": {
            "ifrs-full": {
                "Revenue": {
                    "label": "Revenue",
                    "units": {
                        "INR": [observation()],
                        "USD": [observation(12)],
                    },
                },
            },
        },
    }


class FakeFetcher:

    def __init__(self, submissions, facts):

        self.submissions = submissions
        self.facts = facts
        self.calls = []
        self.redirect = False

    def fetch(self, url):

        self.calls.append(url)

        data = (
            self.submissions
            if "/submissions/" in url
            else self.facts
        )

        return SimpleNamespace(
            url=url,
            final_url=(
                "https://example.com/"
                if self.redirect
                else url
            ),
            status_code=200,
            redirect_chain=(
                (url,) if self.redirect else ()
            ),
            text_content=json.dumps(data),
            content_hash="a" * 64,
            fetched_at="2026-11-27T00:00:00+00:00",
        )


def acquire(fetcher):

    return SecCompanyFactsService(fetcher).acquire(
        "INFY",
        exchange="NSE",
        fiscal_year=2025,
    )


def test_valid_annual_facts(submissions, facts):

    result = acquire(FakeFetcher(submissions, facts))

    assert result["ticker"] == "INFY"
    assert result["isin"] == "INE009A01021"
    assert len(result["facts"]) == 2
    assert result["filing"]["accession"] == ACCESSION
    assert not result["conflicts"]


def test_currencies_remain_separate(submissions, facts):

    result = acquire(FakeFetcher(submissions, facts))

    values = {
        item["unit"]: item["value"]
        for item in result["facts"]
    }

    assert values == {"INR": "1000", "USD": "12"}


def test_public_data_not_valuation_authorized(
    submissions, facts
):

    result = acquire(FakeFetcher(submissions, facts))

    assert result["authenticated_provider"] is False
    assert result["financial_evidence_verified"] is False
    assert result["authorized_for_valuation"] is False


def test_unregistered_company_blocked(
    submissions, facts
):

    fetcher = FakeFetcher(submissions, facts)

    with pytest.raises(SecFactsError):

        SecCompanyFactsService(fetcher).acquire(
            "UNKNOWN",
            exchange="NSE",
            fiscal_year=2025,
        )

    assert not fetcher.calls


@pytest.mark.parametrize(
    "year",
    [True, "2025", 1800, 9999],
)
def test_invalid_year_blocked(
    submissions, facts, year
):

    fetcher = FakeFetcher(submissions, facts)

    with pytest.raises(SecFactsError):

        SecCompanyFactsService(fetcher).acquire(
            "INFY",
            exchange="NSE",
            fiscal_year=year,
        )

    assert not fetcher.calls


def test_index_identity_mismatch(submissions, facts):

    submissions["cik"] = "1144967"

    with pytest.raises(SecFactsError):

        acquire(FakeFetcher(submissions, facts))


def test_facts_identity_mismatch(submissions, facts):

    facts["cik"] = 1144967

    with pytest.raises(SecFactsError):

        acquire(FakeFetcher(submissions, facts))


def test_missing_annual_filing(submissions, facts):

    submissions["filings"]["recent"]["form"] = ["6-K"]

    with pytest.raises(SecFactsError):

        acquire(FakeFetcher(submissions, facts))


@pytest.mark.parametrize(
    "changes",
    [
        {"start": "2025-01-01"},
        {"end": "2024-03-31"},
        {"accn": "wrong-accession"},
        {"form": "6-K"},
        {"filed": "2025-05-01"},
        {"val": True},
        {"val": None},
        {"val": "1000"},
    ],
)
def test_ineligible_observations(
    submissions, facts, changes
):

    units = facts["facts"]["ifrs-full"]["Revenue"]["units"]

    item = observation()
    item.update(changes)

    units["INR"].append(item)

    result = acquire(FakeFetcher(submissions, facts))

    assert len(result["facts"]) == 2
    assert not result["conflicts"]


def test_conflicting_values_rejected(
    submissions, facts
):

    units = facts["facts"]["ifrs-full"]["Revenue"]["units"]

    units["INR"].append(observation(2000))

    result = acquire(FakeFetcher(submissions, facts))

    assert len(result["conflicts"]) == 1

    assert not any(
        item["unit"] == "INR"
        for item in result["facts"]
    )


def test_identical_observations_deduplicated(
    submissions, facts
):

    units = facts["facts"]["ifrs-full"]["Revenue"]["units"]

    units["INR"].append(observation())

    result = acquire(FakeFetcher(submissions, facts))

    assert len(result["facts"]) == 2
    assert not result["conflicts"]


def test_redirect_rejected(submissions, facts):

    fetcher = FakeFetcher(submissions, facts)
    fetcher.redirect = True

    with pytest.raises(SecFactsError):

        acquire(fetcher)


def test_amended_filing_requires_review(
    submissions, facts
):

    recent = submissions["filings"]["recent"]

    recent["form"].append("20-F/A")
    recent["reportDate"].append("2025-03-31")
    recent["filingDate"].append("2025-07-20")

    recent["accessionNumber"].append(
        "0001067491-25-000011"
    )

    recent["primaryDocument"].append(
        "amended.htm"
    )

    with pytest.raises(
        SecFactsError,
        match="Amended annual filing",
    ):

        acquire(FakeFetcher(submissions, facts))


def test_no_eligible_facts(submissions, facts):

    facts["facts"] = {}

    with pytest.raises(SecFactsError):

        acquire(FakeFetcher(submissions, facts))
