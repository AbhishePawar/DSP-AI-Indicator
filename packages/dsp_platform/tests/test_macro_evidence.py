from datetime import date

import pytest

from contracts.domain.economic_series import (
    EconomicDataPoint,
    EconomicSeries,
)

from contracts.enums import EconomicFrequency

from dsp_platform.composition.macro_evidence import (
    MacroeconomicEvidenceService,
)


class FakeAdapter:

    def __init__(self, failed=(), country="IN"):

        self.failed = set(failed)
        self.country = country
        self.calls = []

    def acquire_with_evidence(self, code, country):

        self.calls.append((code, country))

        if code in self.failed:

            raise ValueError("Unavailable source")

        value = (
            7.5 if code == "GDP_GROWTH"
            else 2.4
        )

        return (
            EconomicSeries(
                indicator_code=code,
                indicator_name=code,
                country=self.country,
                frequency=EconomicFrequency.ANNUAL,
                unit="percent",
                points=(
                    EconomicDataPoint(
                        observation_date=date(
                            2025, 12, 31
                        ),
                        value=value,
                    ),
                ),
            ),
            {
                "source": "WORLD_BANK",
                "content_hash": "a" * 64,
            },
        )


@pytest.mark.parametrize(
    "exchange",
    ["NSE", "BSE", "AMFI", " nse "],
)
def test_supported_indian_exchange(exchange):

    result = MacroeconomicEvidenceService(
        FakeAdapter()
    ).acquire(exchange=exchange)

    assert result["country"] == "IN"
    assert result["status"] == "partial"

    assert result["snapshot"][
        "gdp_growth"
    ] == pytest.approx(0.075)

    assert result["snapshot"][
        "cpi_inflation"
    ] == pytest.approx(0.024)


@pytest.mark.parametrize(
    "exchange",
    ["NASDAQ", "NYSE", "", None],
)
def test_unsupported_exchange_no_network(exchange):

    adapter = FakeAdapter()

    result = MacroeconomicEvidenceService(
        adapter
    ).acquire(exchange=exchange)

    assert result["status"] == "unavailable"
    assert not adapter.calls


def test_partial_source_failure():

    result = MacroeconomicEvidenceService(
        FakeAdapter(
            failed=("INFLATION_RATE",)
        )
    ).acquire(exchange="NSE")

    assert result["status"] == "partial"

    assert result["snapshot"]["gdp_growth"] == (
        pytest.approx(0.075)
    )

    assert result["snapshot"]["cpi_inflation"] is None


def test_all_sources_unavailable():

    result = MacroeconomicEvidenceService(
        FakeAdapter(
            failed=(
                "GDP_GROWTH",
                "INFLATION_RATE",
            )
        )
    ).acquire(exchange="NSE")

    assert result["status"] == "unavailable"
    assert result["snapshot"] is None


def test_cross_country_evidence_rejected():

    result = MacroeconomicEvidenceService(
        FakeAdapter(country="US")
    ).acquire(exchange="NSE")

    assert result["status"] == "unavailable"


def test_historical_requests_rejected():

    adapter = FakeAdapter()

    result = MacroeconomicEvidenceService(
        adapter
    ).acquire(
        exchange="NSE",
        as_of=date(2024, 12, 31),
    )

    assert result["status"] == "unavailable"
    assert not adapter.calls


def test_no_valuation_authorization():

    result = MacroeconomicEvidenceService(
        FakeAdapter()
    ).acquire(exchange="NSE")

    assert not result["authorized_for_valuation"]

    assert not result[
        "historical_point_in_time_verified"
    ]


def test_provenance_retained():

    result = MacroeconomicEvidenceService(
        FakeAdapter()
    ).acquire(exchange="NSE")

    assert len(result["sources"]) == 2

    assert all(
        source["content_hash"] == "a" * 64
        for source in result["sources"]
    )
