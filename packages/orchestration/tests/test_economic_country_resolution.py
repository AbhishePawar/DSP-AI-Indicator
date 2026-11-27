from datetime import date
from types import SimpleNamespace

import pytest

from orchestration.models import AnalysisRequest
from orchestration.exceptions import OrchestrationError


def request(exchange, **kwargs):

    return AnalysisRequest(
        instrument=SimpleNamespace(
            symbol="TEST",
            exchange=exchange,
        ),
        start=date(2025, 1, 1),
        end=date(2026, 11, 27),
        **kwargs,
    )


@pytest.mark.parametrize(
    "exchange",
    ["NSE", "BSE", "AMFI", "nse", " bse "],
)
def test_indian_exchange_resolution(exchange):

    assert request(exchange).economic_country == "IN"


@pytest.mark.parametrize(
    "exchange",
    ["NASDAQ", "NYSE", None],
)
def test_legacy_default_preserved(exchange):

    assert request(exchange).economic_country == "US"


def test_explicit_country_preserved():

    assert request(
        "NSE",
        economic_country="US",
    ).economic_country == "US"


def test_explicit_country_normalized():

    assert request(
        "NSE",
        economic_country=" in ",
    ).economic_country == "IN"


def test_blank_country_rejected():

    with pytest.raises(OrchestrationError):

        request("NSE", economic_country=" ")
