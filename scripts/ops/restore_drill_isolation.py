#!/usr/bin/env python3
"""P1-08 — controlled backup → wipe → restore drill with tenant isolation checks.

Evidence classes:
  * unit / InMemoryDatabasePort — always available (product-state logical adapter)
  * real PostgreSQL — when DSP_DATABASE_URL + psycopg + reachable DB are present

Usage:
  python scripts/ops/restore_drill_isolation.py
  DSP_DATABASE_URL=postgresql://… python scripts/ops/restore_drill_isolation.py --postgres
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description="P1-08 restore drill")
    parser.add_argument(
        "--postgres",
        action="store_true",
        help="Require real PostgreSQL (fail if unavailable)",
    )
    args = parser.parse_args()

    root = _repo_root()
    sys.path[:0] = [
        str(root / "packages" / "production_platform" / "src"),
        str(root / "packages" / "enterprise" / "src"),
        str(root / "packages" / "dsp_platform" / "src"),
        str(root / "packages" / "api_platform" / "src"),
    ]

    from api_platform.api.dependencies import DatabaseReportStore
    from api_platform.api.tenant_isolation import stamp_report_owner
    from dsp_platform.research_workspace.db_store import DatabaseResearchWorkspaceStore
    from dsp_platform.saas_platform.db_store import DatabaseSaasOverlayStore
    from enterprise import DatabaseEnterpriseStore, EnterpriseService
    from production_platform.production.product_state_backup import (
        RESTORE_CONFIRM_ENV,
        LogicalProductStateBackupAdapter,
        PRODUCT_STATE_TABLES,
    )

    db = None
    evidence = "unit_inmemory"
    if args.postgres or os.environ.get("DSP_DATABASE_URL"):
        from production_platform.adapters.postgres import try_build_postgres

        db = try_build_postgres(
            (os.environ.get("DSP_DATABASE_URL") or os.environ.get("DATABASE_URL") or "").strip()
        )
        if db is not None:
            evidence = "real_postgresql"
        elif args.postgres:
            print("FAIL: --postgres requested but PostgreSQL unavailable", file=sys.stderr)
            return 2

    if db is None:
        from production_platform import InMemoryDatabasePort

        db = InMemoryDatabasePort()

    with tempfile.TemporaryDirectory(prefix="dsp_p108_") as tmp:
        os.environ[RESTORE_CONFIRM_ENV] = "YES"
        os.environ["DSP_BACKUP_DIR"] = tmp

        ent = EnterpriseService(store=DatabaseEnterpriseStore(db))
        org_a = ent.create_organization(
            name="Drill A", slug="drill-a-p108", owner_user_id="owner-a"
        )
        org_b = ent.create_organization(
            name="Drill B", slug="drill-b-p108", owner_user_id="owner-b"
        )
        saas = DatabaseSaasOverlayStore(db)
        saas.upsert_subscription(org_a["org_id"], {"plan_id": "starter", "status": "active"})
        saas.upsert_subscription(
            org_b["org_id"], {"plan_id": "enterprise", "status": "active"}
        )
        ws = DatabaseResearchWorkspaceStore(db)
        note_a = ws.create_note(
            {"title": "A", "body": "secret-a", "created_by": "owner-a"}
        )
        reports = DatabaseReportStore(db)
        reports.put(
            "rpt-a",
            stamp_report_owner({"capability": "x", "payload": {}, "ok": True}, "owner-a"),
        )

        adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp)
        created = adapter.create_snapshot(label="restore-drill")
        if not created.get("ok"):
            print("FAIL backup:", created, file=sys.stderr)
            return 1

        for table in PRODUCT_STATE_TABLES:
            db.execute(f"DELETE FROM {table}")

        restored = adapter.restore_snapshot(created["snapshot_id"])
        if not restored.get("ok"):
            print("FAIL restore:", restored, file=sys.stderr)
            return 1

        ent2 = EnterpriseService(store=DatabaseEnterpriseStore(db))
        assert ent2.get_organization(org_a["org_id"], actor_user_id="owner-a") is not None
        try:
            ent2.get_organization(org_a["org_id"], actor_user_id="owner-b")
            print("FAIL: cross-tenant read allowed after restore", file=sys.stderr)
            return 1
        except Exception:
            pass

        reports2 = DatabaseReportStore(db)
        assert reports2.get("rpt-a")["owner_user_id"] == "owner-a"
        note = DatabaseResearchWorkspaceStore(db).get_note(note_a["note_id"])
        assert note is not None and note["created_by"] == "owner-a"

        print("OK P1-08 restore drill")
        print(f"evidence_class={evidence}")
        print(f"snapshot_id={created['snapshot_id']}")
        print(f"tables={created.get('tables')}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
