"""Tests for data_engine.providers.metadata and data_engine.providers.enums."""

import pytest

from data_engine.exceptions import DataEngineError
from data_engine.providers import (
    AuthenticationType,
    ProviderCapabilities,
    ProviderMetadata,
    ProviderStatus,
    RateLimitPolicy,
)


class TestProviderMetadata:
    """Tests for the ProviderMetadata descriptor."""

    def test_defaults(self) -> None:
        metadata = ProviderMetadata(provider_id="fake_vendor", name="Fake Vendor")

        assert metadata.provider_id == "fake_vendor"
        assert metadata.name == "Fake Vendor"
        assert metadata.version == "0.1.0"
        assert metadata.description == ""
        assert metadata.homepage is None
        assert metadata.capabilities == ProviderCapabilities()
        assert metadata.rate_limit is None
        assert metadata.auth_type is AuthenticationType.NONE
        assert metadata.priority is None
        assert metadata.status is ProviderStatus.ACTIVE

    def test_provider_id_is_normalized_to_lowercase(self) -> None:
        metadata = ProviderMetadata(provider_id=" Fake_Vendor ", name="Fake Vendor")
        assert metadata.provider_id == "fake_vendor"

    def test_empty_provider_id_raises(self) -> None:
        with pytest.raises(DataEngineError, match="provider_id"):
            ProviderMetadata(provider_id="   ", name="Fake Vendor")

    def test_empty_name_raises(self) -> None:
        with pytest.raises(DataEngineError, match="name"):
            ProviderMetadata(provider_id="fake_vendor", name="   ")

    def test_full_metadata_round_trips(self) -> None:
        rate_limit = RateLimitPolicy(
            requests_per_minute=60, requests_per_day=1_000, concurrent_requests=5
        )
        capabilities = ProviderCapabilities.from_flags(market_data=True, daily=True)

        metadata = ProviderMetadata(
            provider_id="fake_vendor",
            name="Fake Vendor",
            version="2.1.0",
            description="A fake vendor used only in tests.",
            homepage="https://example.invalid",
            capabilities=capabilities,
            rate_limit=rate_limit,
            auth_type=AuthenticationType.API_KEY,
            priority=3,
            status=ProviderStatus.EXPERIMENTAL,
        )

        assert metadata.version == "2.1.0"
        assert metadata.description == "A fake vendor used only in tests."
        assert metadata.homepage == "https://example.invalid"
        assert metadata.capabilities is capabilities
        assert metadata.rate_limit == rate_limit
        assert metadata.auth_type is AuthenticationType.API_KEY
        assert metadata.priority == 3
        assert metadata.status is ProviderStatus.EXPERIMENTAL

    def test_is_immutable(self) -> None:
        metadata = ProviderMetadata(provider_id="fake_vendor", name="Fake Vendor")
        with pytest.raises(AttributeError):
            metadata.name = "Renamed"  # type: ignore[misc]


class TestRateLimitPolicy:
    """Tests for the RateLimitPolicy value object."""

    def test_defaults_to_no_declared_limits(self) -> None:
        policy = RateLimitPolicy()
        assert policy.requests_per_minute is None
        assert policy.requests_per_day is None
        assert policy.concurrent_requests is None


class TestProviderStatus:
    """Tests for the ProviderStatus enum."""

    def test_expected_members_exist(self) -> None:
        assert ProviderStatus.ACTIVE == "active"
        assert ProviderStatus.DISABLED == "disabled"
        assert ProviderStatus.EXPERIMENTAL == "experimental"
        assert ProviderStatus.DEPRECATED == "deprecated"


class TestAuthenticationType:
    """Tests for the AuthenticationType enum."""

    def test_expected_members_exist(self) -> None:
        assert AuthenticationType.NONE == "none"
        assert AuthenticationType.API_KEY == "api_key"
        assert AuthenticationType.OAUTH == "oauth"
        assert AuthenticationType.BASIC == "basic"
        assert AuthenticationType.TOKEN == "token"
