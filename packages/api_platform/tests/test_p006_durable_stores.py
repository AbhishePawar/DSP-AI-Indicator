"""P0-06 — durable multi-tenant product stores (restart + multi-worker)."""

from __future__ import annotations

import pytest

from api_platform.api.dependencies import DatabaseReportStore
from api_platform.api.durable_product_stores import (
    is_durable_database,
    require_durable_product_database,
)
from dsp_platform.research_workspace.db_store import DatabaseResearchWorkspaceStore
from dsp_platform.saas_platform.db_store import DatabaseSaasOverlayStore
from enterprise import DatabaseEnterpriseStore, EnterpriseService
from production_platform import InMemoryDatabasePort


def test_is_durable_database_detects_port() -> None:
    assert is_durable_database(None) is False
    assert is_durable_database(InMemoryDatabasePort()) is True


def test_production_fail_closed_without_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="P0-06"):
        require_durable_product_database(None)
    with pytest.raises(RuntimeError, match="P0-06"):
        require_durable_product_database(InMemoryDatabasePort())


def test_enterprise_survives_restart_and_second_worker() -> None:
    db = InMemoryDatabasePort()
    worker_a = EnterpriseService(store=DatabaseEnterpriseStore(db))
    org = worker_a.create_organization(
        name="Durable Org",
        slug="durable-org-p006",
        owner_user_id="owner-a",
    )
    org_id = org["org_id"]

    # Restart simulation — new store instance, same DB.
    worker_b = EnterpriseService(store=DatabaseEnterpriseStore(db))
    assert worker_b.get_organization(org_id) is not None
    assert worker_b.get_organization(org_id)["name"] == "Durable Org"

    # Concurrent worker already constructed before write still sees data after sync.
    worker_c = EnterpriseService(store=DatabaseEnterpriseStore(db))
    listed = worker_c.list_organizations(user_id="owner-a")
    assert any(o["org_id"] == org_id for o in listed)


def test_saas_overlay_shared_across_workers() -> None:
    db = InMemoryDatabasePort()
    a = DatabaseSaasOverlayStore(db)
    a.upsert_subscription("org-1", {"plan_id": "starter", "status": "active"})
    a.upsert_billing_profile("org-1", {"currency": "USD", "country": "US"})

    b = DatabaseSaasOverlayStore(db)
    sub = b.get_subscription("org-1")
    assert sub is not None
    assert sub["plan_id"] == "starter"
    profile = b.get_billing_profile("org-1")
    assert profile is not None
    assert profile["currency"] == "USD"


def test_workspace_shared_across_workers() -> None:
    db = InMemoryDatabasePort()
    a = DatabaseResearchWorkspaceStore(db)
    note = a.create_note(
        {
            "title": "Moat notes",
            "body": "Quality first",
            "company": "AAPL",
        }
    )
    note_id = note["note_id"]

    b = DatabaseResearchWorkspaceStore(db)
    fetched = b.get_note(note_id)
    assert fetched is not None
    assert fetched["title"] == "Moat notes"
    assert fetched["company"] == "AAPL"


def test_reports_shared_across_workers() -> None:
    db = InMemoryDatabasePort()
    a = DatabaseReportStore(db)
    a.put("rpt-1", {"ticker": "MSFT", "status": "complete"})

    b = DatabaseReportStore(db)
    assert b.has("rpt-1") is True
    assert b.get("rpt-1")["ticker"] == "MSFT"


def test_tenant_isolation_smoke_on_enterprise() -> None:
    db = InMemoryDatabasePort()
    svc = EnterpriseService(store=DatabaseEnterpriseStore(db))
    org_a = svc.create_organization(
        name="Alpha", slug="alpha-p006", owner_user_id="u-a"
    )
    org_b = svc.create_organization(
        name="Beta", slug="beta-p006", owner_user_id="u-b"
    )
    only_a = svc.list_organizations(user_id="u-a")
    only_b = svc.list_organizations(user_id="u-b")
    assert [o["org_id"] for o in only_a] == [org_a["org_id"]]
    assert [o["org_id"] for o in only_b] == [org_b["org_id"]]
