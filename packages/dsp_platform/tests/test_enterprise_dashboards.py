"""Unit tests — RC1 Milestone 6 enterprise dashboard aggregation."""

from __future__ import annotations

import pytest

from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.enterprise_dashboards import (
    DASHBOARD_ROLES,
    UNAVAILABLE_MESSAGE,
    enterprise_dashboard_schema,
    get_enterprise_dashboard,
)


@pytest.fixture
def platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .build()
    )


def test_schema_lists_all_roles() -> None:
    schema = enterprise_dashboard_schema()
    assert schema["schema_version"]
    assert set(schema["roles"]) == set(DASHBOARD_ROLES)
    assert "aggregation_only" in schema["rules"]


def test_unknown_role_raises(platform: DSPPlatform) -> None:
    with pytest.raises(ValueError, match="Unknown dashboard role"):
        get_enterprise_dashboard("trader", platform=platform)


@pytest.mark.parametrize("role", list(DASHBOARD_ROLES))
def test_each_role_returns_widgets(platform: DSPPlatform, role: str) -> None:
    payload = get_enterprise_dashboard(role, platform=platform)
    assert payload["role"] == role
    assert payload["provenance"]["calculations_performed"] is False
    assert isinstance(payload["widgets"], dict)
    assert payload["widgets"]


def test_research_news_unavailable_without_symbols(platform: DSPPlatform) -> None:
    payload = get_enterprise_dashboard("research", platform=platform)
    news = payload["widgets"]["recent_news"]
    assert news["available"] is False
    assert news["message"] == UNAVAILABLE_MESSAGE


def test_portfolio_manager_health_from_pi_when_symbols_present(
    platform: DSPPlatform,
) -> None:
    payload = get_enterprise_dashboard(
        "portfolio-manager",
        platform=platform,
        portfolio_id="pf-dash-1",
        symbols=["AAPL"],
    )
    health = payload["widgets"]["portfolio_health_score"]
    assert health["available"] is True
    assert health["data"]["health_score"] == UNAVAILABLE_MESSAGE
    assert health["source"].startswith("portfolio_intelligence")
    assert health["data"]["missing_research_count"] == 1


def test_platform_facade(platform: DSPPlatform) -> None:
    schema = platform.enterprise_dashboard_schema()
    assert "research" in schema["roles"]
    result = platform.get_enterprise_dashboard("executive")
    assert result["role"] == "executive"
    assert "system_health" in result["widgets"]
