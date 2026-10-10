from datetime import UTC, datetime, timedelta
from decimal import Decimal
import pytest

from contracts.domain.instrument import AssetClass, Instrument
from data_engine.exceptions import InvalidProviderDataError
from data_engine.market_quote.models import (
    AuthenticatedMarketQuote,
    MarketQuoteProvenance,
    QuoteField,
)
from data_engine.market_quote.validation import (
    QuoteFreshnessPolicy,
    validate_authenticated_quote,
)


def _valid_quote(
    symbol="INFY",
    exchange="NSE",
    currency="INR",
    current_price=Decimal("1500.00"),
    high=Decimal("1520.00"),
    low=Decimal("1490.00"),
    open_price=Decimal("1510.00"),
    prev_close=Decimal("1495.00"),
    week_52_high=Decimal("1800.00"),
    week_52_low=Decimal("1300.00"),
    volume=Decimal("1000000"),
    as_of=None,
    retrieved_at=None,
    metadata=None,
) -> AuthenticatedMarketQuote:
    now = datetime.now(UTC)
    r_at = retrieved_at or now
    a_of = as_of or now
    meta = metadata or {"instrument_key": "NSE_EQ|INE009A01021"}
    prov = MarketQuoteProvenance(
        provider_id="upstox_market_quote",
        provider_name="Upstox",
        source_type="licensed_vendor",
        retrieved_at=r_at,
        as_of=a_of,
        auth_mode="oauth_bearer",
        metadata=meta,
    )
    return AuthenticatedMarketQuote(
        symbol=symbol,
        exchange=exchange,
        currency=currency,
        current_price=QuoteField(available=True, value=current_price),
        open=QuoteField(available=True, value=open_price) if open_price is not None else QuoteField.missing(),
        high=QuoteField(available=True, value=high) if high is not None else QuoteField.missing(),
        low=QuoteField(available=True, value=low) if low is not None else QuoteField.missing(),
        previous_close=QuoteField(available=True, value=prev_close) if prev_close is not None else QuoteField.missing(),
        week_52_high=QuoteField(available=True, value=week_52_high) if week_52_high is not None else QuoteField.missing(),
        week_52_low=QuoteField(available=True, value=week_52_low) if week_52_low is not None else QuoteField.missing(),
        volume=QuoteField(available=True, value=volume) if volume is not None else QuoteField.missing(),
        average_volume=QuoteField.missing(),
        market_cap=QuoteField.missing(),
        enterprise_value=QuoteField.missing(),
        shares_outstanding=QuoteField.missing(),
        dividend_yield=QuoteField.missing(),
        beta=QuoteField.missing(),
        provenance=prov,
    )


def test_valid_quote_passes():
    quote = _valid_quote()
    inst = Instrument(symbol="INFY", exchange="NSE", currency="INR", asset_class=AssetClass.EQUITY)
    validate_authenticated_quote(quote, requested_instrument=inst)


def test_identity_symbol_mismatch_rejected():
    quote = _valid_quote(symbol="INFY")
    inst = Instrument(symbol="TCS", exchange="NSE", currency="INR", asset_class=AssetClass.EQUITY)
    with pytest.raises(InvalidProviderDataError, match="quote symbol 'INFY' does not match requested symbol 'TCS'"):
        validate_authenticated_quote(quote, requested_instrument=inst)


def test_identity_exchange_mismatch_rejected():
    quote = _valid_quote(exchange="BSE")
    inst = Instrument(symbol="INFY", exchange="NSE", currency="INR", asset_class=AssetClass.EQUITY)
    with pytest.raises(InvalidProviderDataError, match="quote exchange 'BSE' does not match requested exchange 'NSE'"):
        validate_authenticated_quote(quote, requested_instrument=inst)


def test_identity_currency_mismatch_rejected():
    quote = _valid_quote(currency="USD")
    inst = Instrument(symbol="INFY", exchange="NSE", currency="INR", asset_class=AssetClass.EQUITY)
    with pytest.raises(InvalidProviderDataError, match="does not match requested currency"):
        validate_authenticated_quote(quote, requested_instrument=inst)


def test_instrument_key_segment_mismatch_rejected():
    quote = _valid_quote(metadata={"instrument_key": "BSE_EQ|INE009A01021"})
    inst = Instrument(symbol="INFY", exchange="NSE", currency="INR", asset_class=AssetClass.EQUITY)
    with pytest.raises(InvalidProviderDataError, match="instrument key segment 'BSE_EQ' does not match requested exchange 'NSE'"):
        validate_authenticated_quote(quote, requested_instrument=inst)


def test_ohlc_high_below_low_rejected():
    quote = _valid_quote(high=Decimal("1400.00"), low=Decimal("1500.00"))
    with pytest.raises(InvalidProviderDataError, match="cannot be lower than low"):
        validate_authenticated_quote(quote)


def test_ohlc_open_above_high_rejected():
    quote = _valid_quote(open_price=Decimal("1550.00"), high=Decimal("1520.00"))
    with pytest.raises(InvalidProviderDataError, match="quote open .* exceeds high"):
        validate_authenticated_quote(quote)


def test_ohlc_open_below_low_rejected():
    quote = _valid_quote(open_price=Decimal("1450.00"), low=Decimal("1490.00"))
    with pytest.raises(InvalidProviderDataError, match="quote open .* is below low"):
        validate_authenticated_quote(quote)


def test_current_price_above_high_rejected():
    quote = _valid_quote(current_price=Decimal("1550.00"), high=Decimal("1520.00"))
    with pytest.raises(InvalidProviderDataError, match="quote current price .* exceeds high"):
        validate_authenticated_quote(quote)


def test_current_price_below_low_rejected():
    quote = _valid_quote(current_price=Decimal("1450.00"), low=Decimal("1490.00"))
    with pytest.raises(InvalidProviderDataError, match="quote current price .* is below low"):
        validate_authenticated_quote(quote)


def test_52w_high_below_low_rejected():
    quote = _valid_quote(week_52_high=Decimal("1200.00"), week_52_low=Decimal("1500.00"))
    with pytest.raises(InvalidProviderDataError, match="52-week high .* cannot be lower than 52-week low"):
        validate_authenticated_quote(quote)


def test_nan_or_infinite_rejected():
    quote = _valid_quote(current_price=Decimal("NaN"))
    with pytest.raises(InvalidProviderDataError, match="must be a finite Decimal"):
        validate_authenticated_quote(quote)


def test_negative_current_price_rejected():
    quote = _valid_quote(current_price=Decimal("-10.00"))
    with pytest.raises(InvalidProviderDataError, match="current_price must be positive"):
        validate_authenticated_quote(quote)


def test_missing_optional_fields_preserved_as_missing():
    quote = _valid_quote(
        open_price=None,
        high=None,
        low=None,
        prev_close=None,
        week_52_high=None,
        week_52_low=None,
    )
    validate_authenticated_quote(quote)
    assert not quote.open.available
    assert quote.open.value is None
    assert not quote.high.available
    assert quote.high.value is None


def test_future_timestamp_rejected():
    now = datetime.now(UTC)
    future = now + timedelta(minutes=15)
    quote = _valid_quote(retrieved_at=now, as_of=future)
    policy = QuoteFreshnessPolicy(max_future_seconds=60)
    with pytest.raises(InvalidProviderDataError, match="is in the future"):
        validate_authenticated_quote(quote, freshness_policy=policy)


def test_stale_timestamp_rejection_and_market_closed_acceptance():
    now = datetime.now(UTC)
    old = now - timedelta(days=2)
    quote = _valid_quote(retrieved_at=now, as_of=old)

    # When market closed data is disallowed and policy enforces freshness:
    strict_policy = QuoteFreshnessPolicy(max_age_seconds=3600, allow_market_closed=False)
    with pytest.raises(InvalidProviderDataError, match="is stale"):
        validate_authenticated_quote(quote, freshness_policy=strict_policy)

    # When market closed data is allowed (weekend/after-hours):
    market_closed_policy = QuoteFreshnessPolicy(max_age_seconds=3600, allow_market_closed=True)
    validate_authenticated_quote(quote, freshness_policy=market_closed_policy)
