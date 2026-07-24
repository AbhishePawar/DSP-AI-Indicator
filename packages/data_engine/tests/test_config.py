"""Tests for data_engine.config."""

from data_engine.config import DataEngineConfig


class TestDataEngineConfig:
    """Tests for the DataEngineConfig settings shape."""

    def test_defaults(self) -> None:
        config = DataEngineConfig()
        assert config.default_provider is None
        assert config.cache_ttl_seconds == 300.0
        assert config.request_timeout_seconds == 30.0

    def test_is_immutable(self) -> None:
        config = DataEngineConfig()
        try:
            config.default_provider = "fake_vendor"  # type: ignore[misc]
        except AttributeError:
            pass
        else:
            raise AssertionError("DataEngineConfig should be frozen")

    def test_custom_values_are_stored(self) -> None:
        config = DataEngineConfig(
            default_provider="fake_vendor",
            cache_ttl_seconds=60.0,
            request_timeout_seconds=5.0,
        )
        assert config.default_provider == "fake_vendor"
        assert config.cache_ttl_seconds == 60.0
        assert config.request_timeout_seconds == 5.0
