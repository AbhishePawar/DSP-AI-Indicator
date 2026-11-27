"""Prevent development OTP delivery in protected environments."""

import pytest

from auth.sms import (
    DevSmsAdapter,
    NullSmsAdapter,
    build_sms_provider,
)


@pytest.mark.parametrize(
    "environment", ["production", "prod", "staging"]
)
@pytest.mark.parametrize("provider", ["dev", "console"])
def test_debug_sms_disabled_in_protected_environments(
    monkeypatch, environment, provider
):
    monkeypatch.setenv("DSP_ENVIRONMENT", environment)
    monkeypatch.setenv("DSP_SMS_PROVIDER", provider)

    adapter = build_sms_provider()

    assert isinstance(adapter, NullSmsAdapter)
    assert not adapter.is_available()


@pytest.mark.parametrize("provider", ["dev", "console"])
def test_debug_sms_available_in_development(
    monkeypatch, provider
):
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    monkeypatch.setenv("DSP_SMS_PROVIDER", provider)

    assert isinstance(build_sms_provider(), DevSmsAdapter)


@pytest.mark.parametrize(
    "environment", ["production", "prod", "staging"]
)
def test_explicit_debug_adapter_selection_is_blocked(
    monkeypatch, environment
):
    monkeypatch.setenv("DSP_ENVIRONMENT", environment)

    assert isinstance(
        build_sms_provider("dev"), NullSmsAdapter
    )
