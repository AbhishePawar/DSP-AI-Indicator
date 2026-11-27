
import json

from types import SimpleNamespace

import pytest

from dsp_platform.research_retrieval.world_bank_data import (
    INDICATORS,
    WorldBankDataService,
    WorldBankDataError,
)


def observation(value=6.5, **changes):

    item = {
        "countryiso3code": "IND",
        "indicator": {
            "id": "NY.GDP.MKTP.KD.ZG"
        },
        "date": "2024",
        "value": value,
    }

    item.update(changes)

    return item


class FakeFetcher:

    def __init__(self, rows, pages=1, redirect=False):

        self.rows = rows
        self.pages = pages
        self.redirect = redirect
        self.calls = []

    def fetch(self, url):

        self.calls.append(url)

        return SimpleNamespace(
            url=url,
            final_url=(
                "https://example.com/"
                if self.redirect else url
            ),
            redirect_chain=(
                (url,) if self.redirect else ()
            ),
            status_code=200,
            text_content=json.dumps([
                {
                    "pages": self.pages,
                    "lastupdated": "2026-01-01",
                },
                self.rows,
            ]),
            content_hash="a" * 64,
            fetched_at="2026-11-27T00:00:00+00:00",
        )


def acquire(rows, **kwargs):

    return WorldBankDataService(
        FakeFetcher(rows, **kwargs)
    ).acquire(
        "gdp_growth",
        start_year=2020,
        end_year=2025,
    )


def test_valid_economic_observation():

    result = acquire([observation()])

    assert result["country"] == "IND"
    assert result["unit"] == "percent"

    assert result["observations"] == [
        {"year": 2024, "value": "6.5"}
    ]

    assert result["authorized_for_valuation"] is False


def test_supported_indicators():

    assert len(INDICATORS) == 8


def test_missing_value_is_not_zero():

    result = acquire([
        observation(),
        observation(None, date="2025"),
    ])

    assert len(result["observations"]) == 1


def test_reported_zero_is_preserved():

    result = acquire([observation(0)])

    assert result["observations"][0]["value"] == "0"


def test_conflicting_values_rejected():

    with pytest.raises(WorldBankDataError):

        acquire([
            observation(6.5),
            observation(7.5),
        ])


def test_identical_values_deduplicated():

    result = acquire([
        observation(),
        observation(),
    ])

    assert len(result["observations"]) == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"countryiso3code": "USA"},
        {"indicator": {"id": "INVALID"}},
        {"date": "1999"},
        {"date": "2026"},
        {"value": True},
        {"value": "6.5"},
        {"value": float("inf")},
    ],
)
def test_invalid_observation(changes):

    with pytest.raises(WorldBankDataError):

        acquire([observation(**changes)])


def test_pagination_not_silently_ignored():

    with pytest.raises(WorldBankDataError):

        acquire([observation()], pages=2)


def test_redirect_rejected():

    with pytest.raises(WorldBankDataError):

        acquire([observation()], redirect=True)


def test_empty_dataset_rejected():

    with pytest.raises(WorldBankDataError):

        acquire([observation(None)])


@pytest.mark.parametrize(
    "start,end",
    [
        (1950, 2025),
        (2025, 2020),
        (True, 2025),
        (2000, 9999),
    ],
)
def test_invalid_reporting_period(start, end):

    fetcher = FakeFetcher([observation()])

    with pytest.raises(WorldBankDataError):

        WorldBankDataService(fetcher).acquire(
            "gdp_growth",
            start_year=start,
            end_year=end,
        )

    assert not fetcher.calls


def test_unknown_indicator_rejected():

    fetcher = FakeFetcher([])

    with pytest.raises(WorldBankDataError):

        WorldBankDataService(fetcher).acquire(
            "unknown"
        )

    assert not fetcher.calls
