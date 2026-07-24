"""Tests for the Instrument domain contract."""

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from contracts.exceptions import ContractValidationError


class TestInstrument:
    """Tests for Instrument construction, normalization, and validation."""

    def test_symbol_and_currency_normalized_to_uppercase(self) -> None:
        instrument = Instrument(
            symbol="aapl", asset_class=AssetClass.EQUITY, currency="usd"
        )
        assert instrument.symbol == "AAPL"
        assert instrument.currency == "USD"

    def test_optional_fields_default_none(self) -> None:
        instrument = Instrument(
            symbol="MSFT", asset_class=AssetClass.EQUITY, currency="USD"
        )
        assert instrument.name is None
        assert instrument.exchange is None
        assert instrument.isin is None

    def test_all_fields_set(self) -> None:
        instrument = Instrument(
            symbol="MSFT",
            asset_class=AssetClass.EQUITY,
            currency="USD",
            name="Microsoft Corporation",
            exchange="NASDAQ",
            sector="Technology",
            industry="Software",
            country="US",
            isin="US5949181045",
            figi="BBG000BPHF17",
        )
        assert instrument.name == "Microsoft Corporation"
        assert instrument.isin == "US5949181045"

    def test_empty_symbol_raises(self) -> None:
        with pytest.raises(ContractValidationError, match="symbol"):
            Instrument(symbol="   ", asset_class=AssetClass.EQUITY, currency="USD")

    def test_empty_currency_raises(self) -> None:
        with pytest.raises(ContractValidationError, match="currency"):
            Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="")

    def test_invalid_currency_length_raises(self) -> None:
        with pytest.raises(ContractValidationError, match="ISO 4217"):
            Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="US")

    def test_immutable(self) -> None:
        instrument = Instrument(
            symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD"
        )
        with pytest.raises(AttributeError):
            instrument.symbol = "MSFT"  # type: ignore[misc]

    def test_asset_class_enum_values(self) -> None:
        assert AssetClass.EQUITY == "equity"
        instrument = Instrument(
            symbol="BTC", asset_class=AssetClass.CRYPTO, currency="USD"
        )
        assert instrument.asset_class is AssetClass.CRYPTO
