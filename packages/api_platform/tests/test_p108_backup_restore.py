"""P1-08 — backup / restore drill (ownership + isolation survive restore)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from api_platform.api.dependencies import DatabaseReportStore
from api_platform.api.tenant_isolation import stamp_report_owner
from dsp_platform.research_workspace.db_store import DatabaseResearchWorkspaceStore
from dsp_platform.saas_platform.db_store import DatabaseSaasOverlayStore
from enterprise import DatabaseEnterpriseStore, EnterpriseService
from production_platform import InMemoryDatabasePort
from production_platform.production.backup import (
    NullBackupAdapter,
    build_backup_adapter,
)
from production_platform.production.product_state_backup import (
    RESTORE_CONFIRM_ENV,
    LogicalProductStateBackupAdapter,
)


def _seed_two_tenants(db: object) -> dict[str, str]:
    ent = EnterpriseService(store=DatabaseEnterpriseStore(db))
    org_a = ent.create_organization(
        name="Backup Org A", slug="backup-org-a-p108", owner_user_id="owner-a"
    )
    org_b = ent.create_organization(
        name="Backup Org B", slug="backup-org-b-p108", owner_user_id="owner-b"
    )
    org_a_id = org_a["org_id"]
    org_b_id = org_b["org_id"]

    saas = DatabaseSaasOverlayStore(db)
    saas.upsert_subscription(org_a_id, {"plan_id": "starter", "status": "active"})
    saas.upsert_subscription(org_b_id, {"plan_id": "enterprise", "status": "active"})

    ws = DatabaseResearchWorkspaceStore(db)
    note_a = ws.create_note(
        {"title": "A notes", "body": "tenant A", "created_by": "owner-a"}
    )
    note_b = ws.create_note(
        {"title": "B notes", "body": "tenant B", "created_by": "owner-b"}
    )

    reports = DatabaseReportStore(db)
    reports.put(
        "rpt-a",
        stamp_report_owner({"capability": "x", "payload": {}, "ok": True}, "owner-a"),
    )
    reports.put(
        "rpt-b",
        stamp_report_owner({"capability": "x", "payload": {}, "ok": True}, "owner-b"),
    )

    return {
        "org_a": org_a_id,
        "org_b": org_b_id,
        "note_a": note_a["note_id"],
        "note_b": note_b["note_id"],
    }


def _assert_isolation(db: object, ids: dict[str, str]) -> None:
    ent = EnterpriseService(store=DatabaseEnterpriseStore(db))
    assert ent.get_organization(ids["org_a"], actor_user_id="owner-a") is not None
    assert ent.get_organization(ids["org_b"], actor_user_id="owner-b") is not None
    with pytest.raises(Exception):
        ent.get_organization(ids["org_a"], actor_user_id="owner-b")
    with pytest.raises(Exception):
        ent.get_organization(ids["org_b"], actor_user_id="owner-a")

    saas = DatabaseSaasOverlayStore(db)
    assert saas.get_subscription(ids["org_a"])["plan_id"] == "starter"
    assert saas.get_subscription(ids["org_b"])["plan_id"] == "enterprise"

    ws = DatabaseResearchWorkspaceStore(db)
    assert ws.get_note(ids["note_a"])["created_by"] == "owner-a"
    assert ws.get_note(ids["note_b"])["created_by"] == "owner-b"

    reports = DatabaseReportStore(db)
    assert reports.get("rpt-a")["owner_user_id"] == "owner-a"
    assert reports.get("rpt-b")["owner_user_id"] == "owner-b"


def test_build_backup_adapter_default_null() -> None:
    adapter = build_backup_adapter(database=InMemoryDatabasePort())
    assert isinstance(adapter, NullBackupAdapter)
    assert adapter.is_available() is False


def test_build_backup_adapter_logical(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DSP_BACKUP_ADAPTER", "logical")
    monkeypatch.setenv("DSP_BACKUP_DIR", str(tmp_path))
    db = InMemoryDatabasePort()
    adapter = build_backup_adapter(database=db, backup_root=tmp_path)
    assert isinstance(adapter, LogicalProductStateBackupAdapter)
    assert adapter.is_available() is True


def test_logical_backup_restore_preserves_ownership_and_isolation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = InMemoryDatabasePort()
    ids = _seed_two_tenants(db)
    _assert_isolation(db, ids)

    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    created = adapter.create_snapshot(label="p108-drill")
    assert created["ok"] is True, created
    snapshot_id = created["snapshot_id"]
    assert created["tables"]["enterprise_snapshots"] >= 1
    assert created["tables"]["api_report_snapshots"] >= 1

    # Destroy durable product state (simulate lost database contents).
    for table in (
        "enterprise_snapshots",
        "enterprise_audit_log",
        "saas_overlay_snapshots",
        "research_workspace_snapshots",
        "api_report_snapshots",
    ):
        db.execute(f"DELETE FROM {table}")

    wiped = EnterpriseService(store=DatabaseEnterpriseStore(db))
    assert wiped.get_organization(ids["org_a"]) is None

    restored = adapter.restore_snapshot(snapshot_id)
    assert restored["ok"] is True, restored

    # Fresh workers after restore (restart durability on shared DatabasePort).
    _assert_isolation(db, ids)

    # Second worker view
    ent2 = EnterpriseService(store=DatabaseEnterpriseStore(db))
    assert ent2.get_organization(ids["org_a"], actor_user_id="owner-a")["name"] == (
        "Backup Org A"
    )
    reports2 = DatabaseReportStore(db)
    assert reports2.get("rpt-a")["owner_user_id"] == "owner-a"
    assert reports2.get("rpt-b")["owner_user_id"] == "owner-b"


def test_restore_refuses_without_confirm(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(RESTORE_CONFIRM_ENV, raising=False)
    db = InMemoryDatabasePort()
    _seed_two_tenants(db)
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    created = adapter.create_snapshot(label="no-confirm")
    assert created["ok"] is True
    refused = adapter.restore_snapshot(created["snapshot_id"])
    assert refused["ok"] is False
    assert RESTORE_CONFIRM_ENV in refused["message"]


def test_restore_refuses_checksum_tamper(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = InMemoryDatabasePort()
    _seed_two_tenants(db)
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    created = adapter.create_snapshot(label="tamper")
    path = Path(created["path"])
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    refused = adapter.restore_snapshot(created["snapshot_id"])
    assert refused["ok"] is False
    assert "Checksum" in refused["message"]


def test_restore_refuses_path_traversal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = InMemoryDatabasePort()
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    refused = adapter.restore_snapshot("../etc/passwd")
    assert refused["ok"] is False


def test_incomplete_archive_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = InMemoryDatabasePort()
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    created = adapter.create_snapshot(label="incomplete")
    path = Path(created["path"])
    import hashlib
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    del data["tables"]["api_report_snapshots"]
    payload = json.dumps(data, separators=(",", ":"), sort_keys=True)
    path.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    Path(str(path) + ".sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    refused = adapter.restore_snapshot(created["snapshot_id"])
    assert refused["ok"] is False
    assert "Incomplete" in refused["message"]


def _postgres_port():
    dsn = (os.environ.get("DSP_DATABASE_URL") or os.environ.get("DATABASE_URL") or "").strip()
    if not dsn:
        return None
    try:
        from production_platform.adapters.postgres import try_build_postgres

        return try_build_postgres(dsn)
    except Exception:  # noqa: BLE001
        return None


@pytest.mark.skipif(
    _postgres_port() is None,
    reason=(
        "P1-08 real PostgreSQL restore evidence unavailable on this host "
        "(no DSP_DATABASE_URL / psycopg / reachable Postgres)"
    ),
)
def test_postgres_logical_restore_drill(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Real PostgreSQL evidence path — skipped when Postgres is not available."""
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = _postgres_port()
    assert db is not None

    # Isolate drill tables by wiping product tables first.
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    for table in (
        "enterprise_snapshots",
        "enterprise_audit_log",
        "saas_overlay_snapshots",
        "research_workspace_snapshots",
        "api_report_snapshots",
    ):
        try:
            db.execute(f"DELETE FROM {table}")
        except Exception:  # noqa: BLE001
            pass

    ids = _seed_two_tenants(db)  # type: ignore[arg-type]
    _assert_isolation(db, ids)  # type: ignore[arg-type]
    created = adapter.create_snapshot(label="pg-drill")
    assert created["ok"] is True, created

    for table in (
        "enterprise_snapshots",
        "enterprise_audit_log",
        "saas_overlay_snapshots",
        "research_workspace_snapshots",
        "api_report_snapshots",
    ):
        db.execute(f"DELETE FROM {table}")

    restored = adapter.restore_snapshot(created["snapshot_id"])
    assert restored["ok"] is True, restored
    _assert_isolation(db, ids)  # type: ignore[arg-type]
