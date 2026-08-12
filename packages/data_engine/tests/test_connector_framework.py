"""Tests for the shared Data Connector Framework primitives."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from data_engine.connector_framework import (
    CircuitOpenError,
    ConnectorField,
    FailoverGroup,
    InMemoryProviderAuditLog,
    NullProviderAuditPort,
    PriorityProviderRegistry,
    ProviderHealth,
)


@dataclass
class _FakeService:
    provider_id: str
    result: str | None = None
    error: Exception | None = None

    def get(self, query: str) -> str | None:
        if self.error is not None:
            raise self.error
        return self.result

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=True,
            detail="ok",
        )


class TestPriorityProviderRegistry:
    def test_orders_by_priority_then_registration(self) -> None:
        registry: PriorityProviderRegistry[str] = PriorityProviderRegistry()
        registry.register("c", provider_id="c", priority=30)
        registry.register("a", provider_id="a", priority=10)
        registry.register("b", provider_id="b", priority=10)
        assert registry.ordered() == ("a", "b", "c")
        assert registry.ordered_ids() == ("a", "b", "c")

    def test_disabled_providers_excluded_from_ordering(self) -> None:
        registry: PriorityProviderRegistry[str] = PriorityProviderRegistry()
        registry.register("a", provider_id="a", priority=10)
        registry.register("b", provider_id="b", priority=20)
        registry.set_enabled("a", False)
        assert registry.ordered() == ("b",)
        assert registry.ordered(include_disabled=True) == ("a", "b")

    def test_get_unknown_provider_raises(self) -> None:
        registry: PriorityProviderRegistry[str] = PriorityProviderRegistry()
        with pytest.raises(Exception):
            registry.get("missing")

    def test_all_ids_sorted(self) -> None:
        registry: PriorityProviderRegistry[str] = PriorityProviderRegistry()
        registry.register("z", provider_id="z")
        registry.register("a", provider_id="a")
        assert registry.all_ids() == ("a", "z")

    def test_len_and_is_empty(self) -> None:
        registry: PriorityProviderRegistry[str] = PriorityProviderRegistry()
        assert registry.is_empty()
        assert len(registry) == 0
        registry.register("a", provider_id="a")
        assert not registry.is_empty()
        assert len(registry) == 1


class TestFailoverGroup:
    def test_returns_first_success(self) -> None:
        primary = _FakeService(provider_id="primary", result="primary-data")
        secondary = _FakeService(provider_id="secondary", result="secondary-data")
        group: FailoverGroup[_FakeService, str, str] = FailoverGroup(
            [primary, secondary],
            call=lambda svc, q: svc.get(q),
            domain="news",
            operation="get_news",
            audit=NullProviderAuditPort(),
        )
        outcome = group.call("AAPL", symbol="AAPL")
        assert outcome is not None
        assert outcome.result == "primary-data"
        assert outcome.provider_id == "primary"
        assert outcome.attempted_provider_ids == ("primary",)

    def test_falls_back_when_primary_unavailable(self) -> None:
        primary = _FakeService(provider_id="primary", result=None)
        secondary = _FakeService(provider_id="secondary", result="secondary-data")
        group: FailoverGroup[_FakeService, str, str] = FailoverGroup(
            [primary, secondary],
            call=lambda svc, q: svc.get(q),
            domain="news",
            operation="get_news",
        )
        outcome = group.call("AAPL")
        assert outcome is not None
        assert outcome.provider_id == "secondary"
        assert outcome.attempted_provider_ids == ("primary", "secondary")

    def test_falls_back_when_primary_raises(self) -> None:
        primary = _FakeService(provider_id="primary", error=RuntimeError("boom"))
        secondary = _FakeService(provider_id="secondary", result="secondary-data")
        group: FailoverGroup[_FakeService, str, str] = FailoverGroup(
            [primary, secondary],
            call=lambda svc, q: svc.get(q),
            domain="filings",
            operation="get_filings",
        )
        outcome = group.call("AAPL")
        assert outcome is not None
        assert outcome.provider_id == "secondary"

    def test_falls_back_when_circuit_open(self) -> None:
        primary = _FakeService(provider_id="primary", error=CircuitOpenError("open"))
        secondary = _FakeService(provider_id="secondary", result="secondary-data")
        group: FailoverGroup[_FakeService, str, str] = FailoverGroup(
            [primary, secondary],
            call=lambda svc, q: svc.get(q),
            domain="filings",
            operation="get_filings",
        )
        outcome = group.call("AAPL")
        assert outcome is not None
        assert outcome.provider_id == "secondary"

    def test_returns_none_when_all_exhausted(self) -> None:
        primary = _FakeService(provider_id="primary", result=None)
        secondary = _FakeService(provider_id="secondary", error=RuntimeError("boom"))
        group: FailoverGroup[_FakeService, str, str] = FailoverGroup(
            [primary, secondary],
            call=lambda svc, q: svc.get(q),
            domain="esg",
            operation="get_esg",
        )
        assert group.call("AAPL") is None

    def test_empty_group_returns_none(self) -> None:
        group: FailoverGroup[_FakeService, str, str] = FailoverGroup(
            [],
            call=lambda svc, q: svc.get(q),
            domain="esg",
            operation="get_esg",
        )
        assert group.is_empty()
        assert group.call("AAPL") is None

    def test_health_reports_every_provider(self) -> None:
        primary = _FakeService(provider_id="primary")
        secondary = _FakeService(provider_id="secondary")
        group: FailoverGroup[_FakeService, str, str] = FailoverGroup(
            [primary, secondary],
            call=lambda svc, q: svc.get(q),
            domain="esg",
            operation="get_esg",
        )
        health = group.health()
        assert [h.provider_id for h in health] == ["primary", "secondary"]

    def test_audit_trail_records_attempt_and_success(self) -> None:
        audit = InMemoryProviderAuditLog()
        primary = _FakeService(provider_id="primary", result=None)
        secondary = _FakeService(provider_id="secondary", result="ok")
        group: FailoverGroup[_FakeService, str, str] = FailoverGroup(
            [primary, secondary],
            call=lambda svc, q: svc.get(q),
            domain="news",
            operation="get_news",
            audit=audit,
        )
        group.call("AAPL", symbol="AAPL")
        event_types = [e.event_type for e in audit.events()]
        assert event_types == ["attempt", "unavailable", "attempt", "success"]

    def test_audit_trail_records_exhaustion(self) -> None:
        audit = InMemoryProviderAuditLog()
        primary = _FakeService(provider_id="primary", result=None)
        group: FailoverGroup[_FakeService, str, str] = FailoverGroup(
            [primary],
            call=lambda svc, q: svc.get(q),
            domain="news",
            operation="get_news",
            audit=audit,
        )
        group.call("AAPL")
        event_types = [e.event_type for e in audit.events()]
        assert event_types == ["attempt", "unavailable", "all_providers_exhausted"]


class TestConnectorField:
    def test_of_none_is_unavailable(self) -> None:
        f = ConnectorField.of(None)
        assert f.available is False
        assert f.value is None

    def test_of_blank_string_is_unavailable(self) -> None:
        assert ConnectorField.of("   ").available is False

    def test_of_numeric_value(self) -> None:
        f = ConnectorField.of(12.5)
        assert f.available is True
        assert f.to_float() == 12.5

    def test_of_invalid_value_is_unavailable(self) -> None:
        f = ConnectorField.of("not-a-number")
        assert f.available is False

    def test_missing(self) -> None:
        f = ConnectorField.missing()
        assert f.available is False
        assert f.to_float() is None
