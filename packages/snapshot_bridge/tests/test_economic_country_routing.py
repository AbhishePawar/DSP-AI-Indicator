from datetime import date

from snapshot_bridge import EconomicBridgeService

from snapshot_bridge.services import (
    economic_codes_for_country,
)


class FakeEconomicService:

    def __init__(self):
        self.calls = []

    def get_available_series(self, **kwargs):

        self.calls.append(kwargs)

        return {}


def test_india_requests_reported_rates():

    codes = economic_codes_for_country("IN")

    assert "GDP_GROWTH" in codes
    assert "INFLATION_RATE" in codes

    assert "GDP" not in codes
    assert "CPI" not in codes


def test_us_preserves_existing_indicators():

    codes = economic_codes_for_country("US")

    assert "GDP" in codes
    assert "CPI" in codes

    assert "GDP_GROWTH" not in codes


def test_country_case_normalized():

    assert economic_codes_for_country(" in ") == (
        economic_codes_for_country("IN")
    )


def test_default_indian_bridge_request():

    economic = FakeEconomicService()

    bridge = EconomicBridgeService(
        economic=economic
    )

    result = bridge.get_snapshot(
        country="IN",
        as_of=date(2026, 11, 27),
    )

    assert economic.calls[0]["indicator_codes"] == (
        economic_codes_for_country("IN")
    )

    assert result.country == "IN"
    assert result.gdp_growth is None


def test_explicit_indicators_preserved():

    economic = FakeEconomicService()

    bridge = EconomicBridgeService(
        economic=economic
    )

    bridge.get_snapshot(
        country="IN",
        indicator_codes=("POPULATION",),
        as_of=date(2026, 11, 27),
    )

    assert economic.calls[0]["indicator_codes"] == (
        "POPULATION",
    )


def test_explicit_provider_preserved():

    economic = FakeEconomicService()

    bridge = EconomicBridgeService(
        economic=economic
    )

    bridge.get_snapshot(
        country="IN",
        provider_name="world_bank",
        as_of=date(2026, 11, 27),
    )

    assert economic.calls[0]["provider_name"] == (
        "world_bank"
    )


def test_explicit_empty_indicator_list_preserved():

    economic = FakeEconomicService()

    bridge = EconomicBridgeService(
        economic=economic
    )

    bridge.get_snapshot(
        country="IN",
        indicator_codes=(),
        as_of=date(2026, 11, 27),
    )

    assert economic.calls[0]["indicator_codes"] == ()
