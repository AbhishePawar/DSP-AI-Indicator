from types import SimpleNamespace

import pytest

from dsp_platform.composition.authenticated_valuation import (
    AuthenticatedValuationError,
    _resolve_price,
)


def field(value):
    return SimpleNamespace(
        value=value,
        available=value is not None,
    )


def quote(current, previous):
    return SimpleNamespace(
        current_price=field(current),
        previous_close=field(previous),
    )


@pytest.mark.parametrize(
    "invalid",
    [None, 0, -1, float("nan"), float("inf"), float("-inf")],
)
def test_invalid_current_price_uses_previous_close(invalid):
    assert _resolve_price(quote(invalid, 100.0)) == 100.0


@pytest.mark.parametrize(
    "invalid",
    [None, 0, -1, float("nan"), float("inf"), float("-inf")],
)
def test_invalid_prices_fail_closed(invalid):
    with pytest.raises(AuthenticatedValuationError):
        _resolve_price(quote(invalid, invalid))


def test_valid_current_price_has_priority():
    assert _resolve_price(quote(110.0, 100.0)) == 110.0
