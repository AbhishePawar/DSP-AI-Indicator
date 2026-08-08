"""EPIC-016 — production identity / durable store / billing / audit tests."""

from __future__ import annotations

import pytest

from enterprise import (
    BILLING_PROVIDER_UNAVAILABLE,
    DatabaseEnterpriseStore,
    EnterpriseService,
    InMemoryEnterpriseStore,
    NullBillingAdapter,
    PaddleBillingAdapter,
    RazorpayBillingAdapter,
    StripeBillingAdapter,
    build_billing_adapter,
)
from production_platform import InMemoryDatabasePort


@pytest.fixture()
def durable_svc() -> EnterpriseService:
    db = InMemoryDatabasePort()
    store = DatabaseEnterpriseStore(db)
    return EnterpriseService(store=store, billing=NullBillingAdapter())


def test_database_enterprise_store_survives_rehydrate() -> None:
    db = InMemoryDatabasePort()
    svc = EnterpriseService(store=DatabaseEnterpriseStore(db))
    org = svc.create_organization(
        name="Durable Org",
        slug="durable-org",
        owner_user_id="owner-1",
    )
    org_id = org["org_id"]
    svc.assign_license(
        org_id, tier="enterprise", seats=5, actor_user_id="owner-1"
    )

    reloaded = EnterpriseService(store=DatabaseEnterpriseStore(db))
    assert reloaded.get_organization(org_id) is not None
    assert reloaded.get_organization(org_id)["name"] == "Durable Org"
    assert reloaded.validate_license(org_id)["valid"] is True
    assert len(reloaded.list_audit(org_id, actor_user_id="owner-1")) >= 2


def test_audit_append_only_and_enriched_fields(durable_svc: EnterpriseService) -> None:
    org = durable_svc.create_organization(
        name="Audit Co", slug="audit-co", owner_user_id="u1"
    )
    event = durable_svc.record_audit(
        org_id=org["org_id"],
        actor_user_id="u1",
        action="settings.update",
        resource_type="settings",
        resource_id="branding",
        before={"theme": "light"},
        after={"theme": "dark"},
        ip_address="203.0.113.10",
        correlation_id="corr-abc",
    )
    assert event["immutable"] is True
    assert event["before"] == {"theme": "light"}
    assert event["after"] == {"theme": "dark"}
    assert event["ip_address"] == "203.0.113.10"
    assert event["correlation_id"] == "corr-abc"

    with pytest.raises(Exception):
        durable_svc.mutate_audit_forbidden(event["event_id"])

    # Rehydrate — audit still present, no overwrite path.
    store2 = DatabaseEnterpriseStore(durable_svc.store._db)  # noqa: SLF001
    ids = {a.event_id for a in store2.audit}
    assert event["event_id"] in ids


def test_billing_adapters_unavailable() -> None:
    for adapter in (
        NullBillingAdapter(),
        StripeBillingAdapter(api_key="sk_test"),
        RazorpayBillingAdapter(key_id="rzp", key_secret="secret"),
        PaddleBillingAdapter(api_key="pdl"),
        build_billing_adapter("stripe"),
        build_billing_adapter("razorpay"),
        build_billing_adapter("paddle"),
    ):
        assert adapter.is_available() is False
        status = adapter.payment_status("org_x")
        assert status["available"] is False
        assert "unavailable" in status["message"].lower() or status[
            "message"
        ] == BILLING_PROVIDER_UNAVAILABLE


def test_inmemory_store_still_for_tests() -> None:
    svc = EnterpriseService(store=InMemoryEnterpriseStore())
    assert isinstance(svc.store, InMemoryEnterpriseStore)
    svc.create_organization(name="T", slug="t-org", owner_user_id="u")
    # flush is no-op
    svc.store.flush()
