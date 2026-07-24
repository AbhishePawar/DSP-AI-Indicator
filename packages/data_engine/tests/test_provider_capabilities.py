"""Tests for data_engine.providers.capabilities."""

import pytest

from data_engine.providers import DataCapability, ProviderCapabilities


class TestProviderCapabilities:
    """Tests for the ProviderCapabilities structured capability model."""

    def test_defaults_to_no_capabilities(self) -> None:
        capabilities = ProviderCapabilities()
        assert capabilities.flags == frozenset()
        assert capabilities.market_data is False
        assert capabilities.crypto is False

    def test_from_flags_sets_only_named_capabilities(self) -> None:
        capabilities = ProviderCapabilities.from_flags(market_data=True, daily=True)

        assert capabilities.market_data is True
        assert capabilities.daily is True
        assert capabilities.crypto is False
        assert capabilities.news is False

    def test_from_flags_covers_every_named_capability(self) -> None:
        capabilities = ProviderCapabilities.from_flags(
            market_data=True,
            fundamentals=True,
            economic_data=True,
            alternative_data=True,
            intraday=True,
            daily=True,
            options=True,
            crypto=True,
            forex=True,
            news=True,
            etf=True,
            indices=True,
            mutual_funds=True,
        )

        assert capabilities.flags == frozenset(DataCapability)

    def test_has_returns_true_for_supported_capability(self) -> None:
        capabilities = ProviderCapabilities.from_flags(crypto=True)
        assert capabilities.has(DataCapability.CRYPTO) is True
        assert capabilities.has(DataCapability.FOREX) is False

    def test_has_all_requires_every_capability(self) -> None:
        capabilities = ProviderCapabilities.from_flags(market_data=True, daily=True)

        assert (
            capabilities.has_all(DataCapability.MARKET_DATA, DataCapability.DAILY)
            is True
        )
        assert (
            capabilities.has_all(DataCapability.MARKET_DATA, DataCapability.CRYPTO)
            is False
        )

    def test_has_any_requires_at_least_one_capability(self) -> None:
        capabilities = ProviderCapabilities.from_flags(crypto=True)

        assert capabilities.has_any(DataCapability.CRYPTO, DataCapability.FOREX)
        assert not capabilities.has_any(DataCapability.FOREX, DataCapability.NEWS)

    def test_is_immutable(self) -> None:
        capabilities = ProviderCapabilities.from_flags(market_data=True)
        with pytest.raises(AttributeError):
            capabilities.flags = frozenset()  # type: ignore[misc]
