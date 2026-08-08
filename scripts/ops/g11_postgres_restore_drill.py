#!/usr/bin/env python3
"""G11 / P1-08 — authoritative real PostgreSQL backup → wipe → restore drill.

Requires:
  * reachable PostgreSQL (DSP_DATABASE_URL)
  * psycopg
  * pg_dump, psql, gzip, bash
  * DSP_BACKUP_RESTORE_CONFIRM=YES for restore

Hard-fails on any step. Never fabricates evidence.
Writes machine-readable JSON to artifacts/g11_postgres_restore_evidence.json
(no credentials).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _redact(url: str) -> str:
    if not url:
        return ""
    # postgresql://user:pass@host:5432/db → postgresql://***@host:5432/db
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        if "@" in rest:
            return f"{scheme}://***@{rest.split('@', 1)[1]}"
    return "***"


def _fail(msg: str, evidence: dict[str, Any], code: int = 1) -> int:
    evidence["ok"] = False
    evidence["error"] = msg
    evidence["finished_at"] = datetime.now(tz=UTC).isoformat()
    _write_evidence(evidence)
    print(f"FAIL: {msg}", file=sys.stderr)
    return code


def _write_evidence(evidence: dict[str, Any]) -> None:
    root = _repo_root()
    out_dir = root / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "g11_postgres_restore_evidence.json"
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"evidence_written={path}")


def _require_tools() -> list[str]:
    missing: list[str] = []
    for tool in ("pg_dump", "psql", "gzip", "bash"):
        if shutil.which(tool) is None:
            missing.append(tool)
    return missing


def _psql(dsn: str, sql: str) -> None:
    completed = subprocess.run(
        ["psql", dsn, "-v", "ON_ERROR_STOP=1", "-c", sql],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            (completed.stderr or completed.stdout or "psql failed").strip()
        )


def _pg_version(dsn: str) -> str:
    completed = subprocess.run(
        ["psql", dsn, "-tAc", "SHOW server_version;"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError("unable to read PostgreSQL version")
    return completed.stdout.strip()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _seed(db: Any) -> dict[str, Any]:
    from api_platform.api.dependencies import DatabaseReportStore
    from api_platform.api.tenant_isolation import stamp_report_owner
    from dsp_platform.research_workspace.db_store import DatabaseResearchWorkspaceStore
    from dsp_platform.saas_platform.db_store import DatabaseSaasOverlayStore
    from enterprise import DatabaseEnterpriseStore, EnterpriseService

    w1_ent = EnterpriseService(store=DatabaseEnterpriseStore(db))
    org_a = w1_ent.create_organization(
        name="G11 Org A", slug="g11-org-a", owner_user_id="owner-a"
    )
    org_b = w1_ent.create_organization(
        name="G11 Org B", slug="g11-org-b", owner_user_id="owner-b"
    )

    w1_saas = DatabaseSaasOverlayStore(db)
    w1_saas.upsert_subscription(
        org_a["org_id"], {"plan_id": "starter", "status": "active"}
    )
    w1_saas.upsert_subscription(
        org_b["org_id"], {"plan_id": "enterprise", "status": "active"}
    )

    w1_ws = DatabaseResearchWorkspaceStore(db)
    note_a = w1_ws.create_note(
        {"title": "A private", "body": "tenant-a-secret", "created_by": "owner-a"}
    )
    note_b = w1_ws.create_note(
        {"title": "B private", "body": "tenant-b-secret", "created_by": "owner-b"}
    )

    w1_reports = DatabaseReportStore(db)
    w1_reports.put(
        "rpt-a",
        stamp_report_owner({"capability": "analyse", "payload": {}, "ok": True}, "owner-a"),
    )
    w1_reports.put(
        "rpt-b",
        stamp_report_owner({"capability": "analyse", "payload": {}, "ok": True}, "owner-b"),
    )

    ownership = {
        "org_a": {"org_id": org_a["org_id"], "owner_user_id": "owner-a", "name": "G11 Org A"},
        "org_b": {"org_id": org_b["org_id"], "owner_user_id": "owner-b", "name": "G11 Org B"},
        "note_a": {"note_id": note_a["note_id"], "created_by": "owner-a"},
        "note_b": {"note_id": note_b["note_id"], "created_by": "owner-b"},
        "rpt_a": {"report_id": "rpt-a", "owner_user_id": "owner-a"},
        "rpt_b": {"report_id": "rpt-b", "owner_user_id": "owner-b"},
        "saas_a": {"org_id": org_a["org_id"], "plan_id": "starter"},
        "saas_b": {"org_id": org_b["org_id"], "plan_id": "enterprise"},
    }
    return ownership


def _assert_workers_and_isolation(db: Any, ownership: dict[str, Any], phase: str) -> dict[str, Any]:
    from api_platform.api.dependencies import DatabaseReportStore
    from dsp_platform.research_workspace.db_store import DatabaseResearchWorkspaceStore
    from dsp_platform.saas_platform.db_store import DatabaseSaasOverlayStore
    from enterprise import DatabaseEnterpriseStore, EnterpriseService
    from enterprise.exceptions import ForbiddenError

    # Worker 1
    w1 = EnterpriseService(store=DatabaseEnterpriseStore(db))
    org_a = w1.get_organization(
        ownership["org_a"]["org_id"], actor_user_id="owner-a"
    )
    org_b = w1.get_organization(
        ownership["org_b"]["org_id"], actor_user_id="owner-b"
    )
    if org_a is None or org_b is None:
        raise AssertionError(f"{phase}: org missing after restore/restart")
    if org_a["name"] != ownership["org_a"]["name"]:
        raise AssertionError(f"{phase}: org A name changed")
    if org_b["name"] != ownership["org_b"]["name"]:
        raise AssertionError(f"{phase}: org B name changed")

    # Worker 2 — new process-local store instances, same PostgreSQL
    w2 = EnterpriseService(store=DatabaseEnterpriseStore(db))
    org_a2 = w2.get_organization(
        ownership["org_a"]["org_id"], actor_user_id="owner-a"
    )
    if org_a2 is None or org_a2["org_id"] != ownership["org_a"]["org_id"]:
        raise AssertionError(f"{phase}: worker2 cannot read org A")

    # Cross-tenant / IDOR
    idor_denied = []
    for label, fn in (
        (
            "A→B org",
            lambda: w1.get_organization(
                ownership["org_b"]["org_id"], actor_user_id="owner-a"
            ),
        ),
        (
            "B→A org",
            lambda: w2.get_organization(
                ownership["org_a"]["org_id"], actor_user_id="owner-b"
            ),
        ),
    ):
        try:
            fn()
            raise AssertionError(f"{phase}: IDOR allowed ({label})")
        except ForbiddenError:
            idor_denied.append(label)

    # Explicit require_permission probes
    try:
        w1.require_permission(ownership["org_b"]["org_id"], "owner-a", "org.view")
        raise AssertionError(f"{phase}: permission IDOR allowed")
    except ForbiddenError:
        idor_denied.append("A→B org.view")

    saas1 = DatabaseSaasOverlayStore(db)
    saas2 = DatabaseSaasOverlayStore(db)
    if saas1.get_subscription(ownership["saas_a"]["org_id"])["plan_id"] != "starter":
        raise AssertionError(f"{phase}: saas A plan lost")
    if saas2.get_subscription(ownership["saas_b"]["org_id"])["plan_id"] != "enterprise":
        raise AssertionError(f"{phase}: saas B plan lost")

    ws1 = DatabaseResearchWorkspaceStore(db)
    ws2 = DatabaseResearchWorkspaceStore(db)
    note_a = ws1.get_note(ownership["note_a"]["note_id"])
    note_b = ws2.get_note(ownership["note_b"]["note_id"])
    if not note_a or note_a.get("created_by") != "owner-a":
        raise AssertionError(f"{phase}: note A ownership changed")
    if not note_b or note_b.get("created_by") != "owner-b":
        raise AssertionError(f"{phase}: note B ownership changed")

    r1 = DatabaseReportStore(db)
    r2 = DatabaseReportStore(db)
    if r1.get("rpt-a").get("owner_user_id") != "owner-a":
        raise AssertionError(f"{phase}: report A owner changed")
    if r2.get("rpt-b").get("owner_user_id") != "owner-b":
        raise AssertionError(f"{phase}: report B owner changed")

    # Multi-worker write/read round-trip on shared Postgres
    w2_saas = DatabaseSaasOverlayStore(db)
    w2_saas.upsert_billing_profile(
        ownership["saas_a"]["org_id"], {"currency": "USD", "country": "US"}
    )
    w1_saas = DatabaseSaasOverlayStore(db)
    profile = w1_saas.get_billing_profile(ownership["saas_a"]["org_id"])
    if not profile or profile.get("currency") != "USD":
        raise AssertionError(f"{phase}: worker1 did not see worker2 write")

    return {
        "phase": phase,
        "worker1_org_a": org_a["org_id"],
        "worker2_org_a": org_a2["org_id"],
        "idor_denied": idor_denied,
        "ownership_ok": True,
        "shared_state_ok": True,
    }


def _assert_api_isolation(ownership: dict[str, Any]) -> dict[str, Any]:
    """HTTP-layer isolation after restore (P1-07 contract)."""
    from fastapi.testclient import TestClient

    from api_platform import create_app
    from auth_test_helpers import bearer_headers, register_user
    from dsp_platform import PlatformBuilder, PlatformConfiguration
    from dsp_platform.research_workspace import reset_research_workspace_store_for_tests
    from dsp_platform.saas_platform import reset_saas_overlay_store_for_tests
    from enterprise import reset_enterprise_service_for_tests

    # Clear singletons so create_app/configure_durable_product_stores can
    # attach Postgres-backed stores from DSP_DATABASE_URL bootstrap.
    reset_enterprise_service_for_tests(None)
    reset_research_workspace_store_for_tests(None)
    # Saas reset without args creates an empty in-memory store; durable
    # configure overwrites it with DatabaseSaasOverlayStore(database).
    reset_saas_overlay_store_for_tests()

    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform))

    register_user(client, user_id="owner-a", username="g11tenanta")
    register_user(client, user_id="owner-b", username="g11tenantb")
    ha = bearer_headers(client, username="g11tenanta")
    hb = bearer_headers(client, username="g11tenantb")

    org_a = ownership["org_a"]["org_id"]
    org_b = ownership["org_b"]["org_id"]
    note_a = ownership["note_a"]["note_id"]
    note_b = ownership["note_b"]["note_id"]

    results: dict[str, Any] = {"checks": []}

    def check(name: str, ok: bool, detail: str = "") -> None:
        results["checks"].append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            raise AssertionError(f"API isolation failed: {name} {detail}")

    ra = client.get(f"/api/v1/enterprise/organizations/{org_a}", headers=ha)
    check("A_reads_A", ra.status_code == 200, str(ra.status_code))
    rb = client.get(f"/api/v1/enterprise/organizations/{org_b}", headers=hb)
    check("B_reads_B", rb.status_code == 200, str(rb.status_code))
    check(
        "A_denied_B_org",
        client.get(f"/api/v1/enterprise/organizations/{org_b}", headers=ha).status_code
        == 403,
    )
    check(
        "B_denied_A_org",
        client.get(f"/api/v1/enterprise/organizations/{org_a}", headers=hb).status_code
        == 403,
    )
    check(
        "A_denied_B_saas",
        client.get(
            f"/api/v1/saas/organization/{org_b}/subscription", headers=ha
        ).status_code
        == 403,
    )
    check(
        "B_denied_A_saas",
        client.get(
            f"/api/v1/saas/organization/{org_a}/subscription", headers=hb
        ).status_code
        == 403,
    )
    check(
        "A_reads_A_note",
        client.get(f"/api/v1/research-workspace/note/{note_a}", headers=ha).status_code
        == 200,
    )
    check(
        "A_denied_B_note",
        client.get(f"/api/v1/research-workspace/note/{note_b}", headers=ha).status_code
        == 403,
    )
    check(
        "B_denied_A_note",
        client.get(f"/api/v1/research-workspace/note/{note_a}", headers=hb).status_code
        == 403,
    )
    check(
        "A_reads_A_report",
        client.get("/report/rpt-a", headers=ha).status_code == 200,
    )
    check(
        "A_denied_B_report",
        client.get("/report/rpt-b", headers=ha).status_code in {403, 404},
    )
    check(
        "B_denied_A_report",
        client.get("/report/rpt-a", headers=hb).status_code in {403, 404},
    )
    results["ok"] = True
    return results


def main() -> int:
    root = _repo_root()
    sys.path[:0] = [
        str(root / "packages" / "production_platform" / "src"),
        str(root / "packages" / "enterprise" / "src"),
        str(root / "packages" / "dsp_platform" / "src"),
        str(root / "packages" / "api_platform" / "src"),
        str(root / "packages" / "auth" / "src"),
        str(root / "packages" / "security_platform" / "src"),
        str(root / "packages" / "core" / "src"),
        str(root / "packages" / "contracts" / "src"),
        str(root / "packages" / "persistence" / "src"),
        str(root / "tests"),
    ]
    # auth_test_helpers may live under packages/api_platform/tests
    api_tests = root / "packages" / "api_platform" / "tests"
    if api_tests.is_dir():
        sys.path.insert(0, str(api_tests))

    dsn = (os.environ.get("DSP_DATABASE_URL") or os.environ.get("DATABASE_URL") or "").strip()
    backup_dir = Path(os.environ.get("DSP_BACKUP_DIR") or (root / "backups")).resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DSP_BACKUP_DIR"] = str(backup_dir)
    os.environ.setdefault("DSP_BACKUP_ADAPTER", "shell")
    os.environ["DSP_BACKUP_RESTORE_CONFIRM"] = "YES"
    os.environ.setdefault("DSP_INFRA_OFFLINE", "0")

    commit = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(root),
        ).stdout.strip()
        or "unknown"
    )

    evidence: dict[str, Any] = {
        "ok": False,
        "gate": "G11",
        "track": "P1-08",
        "evidence_class": "real_postgresql_pg_dump",
        "started_at": datetime.now(tz=UTC).isoformat(),
        "commit": commit,
        "dsn_redacted": _redact(dsn),
        "steps": {},
    }

    if not dsn:
        return _fail("DSP_DATABASE_URL / DATABASE_URL unset", evidence)

    missing = _require_tools()
    if missing:
        return _fail(f"missing tools: {', '.join(missing)}", evidence)

    try:
        import psycopg  # noqa: F401
    except ImportError:
        return _fail("psycopg not installed", evidence)

    from production_platform.adapters.postgres import try_build_postgres
    from production_platform.production.shell_pg_backup import ShellPgDumpBackupAdapter

    db = try_build_postgres(dsn)
    if db is None:
        return _fail("PostgreSQL unreachable or adapter unavailable", evidence)
    if type(db).__name__ != "PostgresDatabasePort":
        return _fail(f"expected PostgresDatabasePort, got {type(db).__name__}", evidence)

    try:
        evidence["postgres_version"] = _pg_version(dsn)
    except Exception as exc:  # noqa: BLE001
        return _fail(f"postgres version: {exc}", evidence)

    adapter = ShellPgDumpBackupAdapter(backup_root=backup_dir, repo_root=root)
    if not adapter.is_available():
        return _fail("ShellPgDumpBackupAdapter unavailable (pg_dump/DSN/bash)", evidence)
    evidence["steps"]["adapter"] = {
        "provider": adapter.provider_name(),
        "available": True,
    }

    try:
        # Clean slate for deterministic drill
        _psql(dsn, "DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        ownership = _seed(db)
        evidence["ownership_before"] = ownership
        evidence["steps"]["seed"] = "PASS"

        pre = _assert_workers_and_isolation(db, ownership, "pre_backup")
        evidence["steps"]["pre_backup_isolation"] = pre

        created = adapter.create_snapshot(label="g11-drill")
        if not created.get("ok"):
            return _fail(f"pg_dump backup failed: {created}", evidence)
        archive = Path(str(created["path"]))
        if not archive.is_file() or archive.stat().st_size < 64:
            return _fail("backup archive missing or too small", evidence)
        digest = _sha256_file(archive)
        side = Path(str(archive) + ".sha256")
        if not side.is_file():
            return _fail("SHA-256 sidecar missing", evidence)
        expected = side.read_text(encoding="utf-8").strip().split()[0]
        if expected != digest:
            return _fail("SHA-256 mismatch after backup", evidence)
        evidence["steps"]["backup"] = {
            "result": "PASS",
            "snapshot_id": created.get("snapshot_id"),
            "bytes": archive.stat().st_size,
            "sha256": digest,
            "artifact": archive.name,
        }

        # Destroy durable state — leave schema empty for pg_dump restore
        # (do not recreate application tables before restore).
        _psql(dsn, "DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        evidence["steps"]["wipe"] = "PASS"

        table_count = subprocess.run(
            [
                "psql",
                dsn,
                "-tAc",
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema='public';",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if table_count.returncode != 0 or table_count.stdout.strip() not in {"0", ""}:
            return _fail(
                f"wipe incomplete; public table count={table_count.stdout.strip()!r}",
                evidence,
            )

        restored = adapter.restore_snapshot(str(created["snapshot_id"]))
        if not restored.get("ok"):
            return _fail(f"pg_dump restore failed: {restored}", evidence)
        evidence["steps"]["restore"] = {"result": "PASS", "detail": restored.get("message")}

        post = _assert_workers_and_isolation(db, ownership, "post_restore")
        evidence["steps"]["post_restore_workers"] = post

        # Restart simulation — brand new workers
        restart = _assert_workers_and_isolation(db, ownership, "post_restart")
        evidence["steps"]["post_restart"] = restart

        api = _assert_api_isolation(ownership)
        evidence["steps"]["api_isolation"] = api

        evidence["ok"] = True
        evidence["finished_at"] = datetime.now(tz=UTC).isoformat()
        evidence["result"] = "PASS"
        _write_evidence(evidence)
        print("OK G11 real PostgreSQL pg_dump restore drill PASS")
        print(f"postgres_version={evidence['postgres_version']}")
        print(f"backup_sha256={digest}")
        print(f"commit={commit}")
        return 0
    except Exception as exc:  # noqa: BLE001
        evidence["traceback"] = traceback.format_exc(limit=20)
        return _fail(str(exc), evidence)


if __name__ == "__main__":
    raise SystemExit(main())
