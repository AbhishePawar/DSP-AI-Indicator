"""Independent verification tests for P1-08 logical product-state backup/restore adapter."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

import pytest

from production_platform.production.database import InMemoryDatabasePort
from production_platform.production.product_state_backup import (
    LEGACY_PRODUCT_STATE_TABLES,
    PRODUCT_STATE_TABLES,
    RESTORE_CONFIRM_ENV,
    TABLE_ALLOWED_COLUMNS,
    LogicalProductStateBackupAdapter,
)


def _seed_report_and_export_records(db: InMemoryDatabasePort) -> dict[str, Any]:
    report_row = {
        "id": "rec-rpt-001",
        "report_id": "rpt-alpha-42",
        "owner_id": "user-corp-1",
        "tenant_id": "tenant-corp-1",
        "status": "ready",
        "s3_key": "reports/tenant-corp-1/2026/rpt-alpha-42.json",
        "s3_bucket": "dsp-staging-artifacts-private",
        "created_at": "2026-10-18T10:00:00Z",
        "updated_at": "2026-10-18T10:05:00Z",
        "metadata": {
            "format": "v2",
            "score": 94.5,
            "provenance": ["sec_10k", "concall"],
            "encrypted": True,
            "null_field": None,
        },
    }

    export_row = {
        "id": "rec-exp-001",
        "export_id": "exp-csv-99",
        "owner_id": "user-corp-1",
        "tenant_id": "tenant-corp-1",
        "status": "completed",
        "s3_key": "exports/tenant-corp-1/2026/exp-csv-99.csv",
        "s3_bucket": "dsp-staging-artifacts-private",
        "content_type": "text/csv",
        "size_bytes": 1048576,
        "created_at": "2026-10-18T10:06:00Z",
        "metadata": {
            "row_count": 5000,
            "delimiter": ",",
            "columns": ["ticker", "cagr", "moat_score"],
        },
    }

    adapter = LogicalProductStateBackupAdapter(db)
    adapter.ensure_record_tables_schema()

    cols_rpt = list(report_row.keys())
    placeholders_rpt = ", ".join("%s" for _ in cols_rpt)
    db.execute(
        f"INSERT INTO api_report_records ({', '.join(cols_rpt)}) VALUES ({placeholders_rpt})",
        tuple(
            (
                json.dumps(report_row[c], sort_keys=True)
                if isinstance(report_row[c], (dict, list))
                else report_row[c]
            )
            for c in cols_rpt
        ),
    )

    cols_exp = list(export_row.keys())
    placeholders_exp = ", ".join("%s" for _ in cols_exp)
    db.execute(
        f"INSERT INTO api_export_records ({', '.join(cols_exp)}) VALUES ({placeholders_exp})",
        tuple(
            (
                json.dumps(export_row[c], sort_keys=True)
                if isinstance(export_row[c], (dict, list))
                else export_row[c]
            )
            for c in cols_exp
        ),
    )

    return {"report": report_row, "export": export_row}


def test_table_allowlist_inclusion() -> None:
    assert "api_report_records" in PRODUCT_STATE_TABLES
    assert "api_export_records" in PRODUCT_STATE_TABLES
    assert "api_report_snapshots" in PRODUCT_STATE_TABLES
    assert "enterprise_snapshots" in PRODUCT_STATE_TABLES
    assert "enterprise_audit_log" in PRODUCT_STATE_TABLES
    assert "saas_overlay_snapshots" in PRODUCT_STATE_TABLES
    assert "research_workspace_snapshots" in PRODUCT_STATE_TABLES

    for t in LEGACY_PRODUCT_STATE_TABLES:
        assert t in PRODUCT_STATE_TABLES

    for t in PRODUCT_STATE_TABLES:
        assert t in TABLE_ALLOWED_COLUMNS


def test_report_and_export_records_round_trip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = InMemoryDatabasePort()
    seeded = _seed_report_and_export_records(db)

    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    snapshot = adapter.create_snapshot(label="records-roundtrip")
    assert snapshot["ok"] is True
    assert snapshot["tables"]["api_report_records"] == 1
    assert snapshot["tables"]["api_export_records"] == 1

    db.execute("DELETE FROM api_report_records")
    db.execute("DELETE FROM api_export_records")
    assert len(db.fetchall("SELECT * FROM api_report_records")) == 0
    assert len(db.fetchall("SELECT * FROM api_export_records")) == 0

    restored = adapter.restore_snapshot(snapshot["snapshot_id"])
    assert restored["ok"] is True
    assert restored["tables"]["api_report_records"] == 1
    assert restored["tables"]["api_export_records"] == 1

    reports = db.fetchall("SELECT * FROM api_report_records")
    assert len(reports) == 1
    rpt = reports[0]
    assert rpt["id"] == seeded["report"]["id"]
    assert rpt["report_id"] == seeded["report"]["report_id"]
    assert rpt["owner_id"] == seeded["report"]["owner_id"]
    assert rpt["tenant_id"] == seeded["report"]["tenant_id"]
    assert rpt["status"] == seeded["report"]["status"]
    assert rpt["s3_key"] == seeded["report"]["s3_key"]
    assert rpt["s3_bucket"] == seeded["report"]["s3_bucket"]
    assert rpt["created_at"] == seeded["report"]["created_at"]
    assert rpt["updated_at"] == seeded["report"]["updated_at"]

    meta_rpt = rpt["metadata"]
    if isinstance(meta_rpt, str):
        meta_rpt = json.loads(meta_rpt)
    assert meta_rpt == seeded["report"]["metadata"]

    exports = db.fetchall("SELECT * FROM api_export_records")
    assert len(exports) == 1
    exp = exports[0]
    assert exp["id"] == seeded["export"]["id"]
    assert exp["export_id"] == seeded["export"]["export_id"]
    assert exp["owner_id"] == seeded["export"]["owner_id"]
    assert exp["tenant_id"] == seeded["export"]["tenant_id"]
    assert exp["status"] == seeded["export"]["status"]
    assert exp["s3_key"] == seeded["export"]["s3_key"]
    assert exp["s3_bucket"] == seeded["export"]["s3_bucket"]
    assert exp["content_type"] == seeded["export"]["content_type"]
    assert exp["size_bytes"] == seeded["export"]["size_bytes"]
    assert exp["created_at"] == seeded["export"]["created_at"]

    meta_exp = exp["metadata"]
    if isinstance(meta_exp, str):
        meta_exp = json.loads(meta_exp)
    assert meta_exp == seeded["export"]["metadata"]


def test_legacy_backup_restores_cleanly_without_new_tables(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = InMemoryDatabasePort()
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)

    db.execute(
        "INSERT INTO api_report_snapshots (snapshot_key, payload, updated_at) "
        "VALUES ('legacy_key_1', 'payload_blob', '2026-10-01T00:00:00Z')"
    )

    created = adapter.create_snapshot(label="legacy-test")
    assert created["ok"] is True

    archive_path = Path(created["path"])
    data = json.loads(archive_path.read_text(encoding="utf-8"))
    data["tables"].pop("api_report_records", None)
    data["tables"].pop("api_export_records", None)
    data["table_names"] = list(LEGACY_PRODUCT_STATE_TABLES)

    payload = json.dumps(data, separators=(",", ":"), sort_keys=True)
    archive_path.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    Path(str(archive_path) + ".sha256").write_text(
        f"{digest}  {archive_path.name}\n", encoding="utf-8"
    )

    # Restore onto clean database that does not have record tables
    target_db = InMemoryDatabasePort()
    target_adapter = LogicalProductStateBackupAdapter(target_db, backup_root=tmp_path)
    restored = target_adapter.restore_snapshot(created["snapshot_id"])
    assert restored["ok"] is True, restored
    assert "api_report_snapshots" in restored["tables"]
    assert "api_report_records" not in restored["tables"]
    assert "api_export_records" not in restored["tables"]
    assert "api_report_records" not in target_db._tables
    assert "api_export_records" not in target_db._tables

    rows = target_db.fetchall("SELECT * FROM api_report_snapshots")
    assert len(rows) == 1
    assert rows[0]["snapshot_key"] == "legacy_key_1"


def test_incomplete_modern_archive_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = InMemoryDatabasePort()
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    adapter.ensure_record_tables_schema()
    created = adapter.create_snapshot(label="incomplete-modern")

    archive_path = Path(created["path"])
    data = json.loads(archive_path.read_text(encoding="utf-8"))
    del data["tables"]["api_export_records"]

    payload = json.dumps(data, separators=(",", ":"), sort_keys=True)
    archive_path.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    Path(str(archive_path) + ".sha256").write_text(
        f"{digest}  {archive_path.name}\n", encoding="utf-8"
    )

    refused = adapter.restore_snapshot(created["snapshot_id"])
    assert refused["ok"] is False
    assert "Incomplete" in refused["message"]
    assert "api_export_records" in refused["message"]


def test_idempotent_restoration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = InMemoryDatabasePort()
    _seed_report_and_export_records(db)

    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    snapshot = adapter.create_snapshot(label="idempotence-test")
    assert snapshot["ok"] is True

    res1 = adapter.restore_snapshot(snapshot["snapshot_id"])
    assert res1["ok"] is True
    assert len(db.fetchall("SELECT * FROM api_report_records")) == 1
    assert len(db.fetchall("SELECT * FROM api_export_records")) == 1

    res2 = adapter.restore_snapshot(snapshot["snapshot_id"])
    assert res2["ok"] is True
    assert len(db.fetchall("SELECT * FROM api_report_records")) == 1
    assert len(db.fetchall("SELECT * FROM api_export_records")) == 1


def test_missing_required_baseline_table_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = InMemoryDatabasePort()
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    created = adapter.create_snapshot(label="missing-audit")

    archive_path = Path(created["path"])
    data = json.loads(archive_path.read_text(encoding="utf-8"))
    del data["tables"]["enterprise_audit_log"]

    payload = json.dumps(data, separators=(",", ":"), sort_keys=True)
    archive_path.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    Path(str(archive_path) + ".sha256").write_text(
        f"{digest}  {archive_path.name}\n", encoding="utf-8"
    )

    refused = adapter.restore_snapshot(created["snapshot_id"])
    assert refused["ok"] is False
    assert "Incomplete archive; missing tables" in refused["message"]
    assert "enterprise_audit_log" in refused["message"]


def test_unknown_unexpected_table_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = InMemoryDatabasePort()
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    created = adapter.create_snapshot(label="unknown-tbl")

    archive_path = Path(created["path"])
    data = json.loads(archive_path.read_text(encoding="utf-8"))
    data["tables"]["unauthorized_external_table"] = []

    payload = json.dumps(data, separators=(",", ":"), sort_keys=True)
    archive_path.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    Path(str(archive_path) + ".sha256").write_text(
        f"{digest}  {archive_path.name}\n", encoding="utf-8"
    )

    refused = adapter.restore_snapshot(created["snapshot_id"])
    assert refused["ok"] is False
    assert "Archive contains unknown tables" in refused["message"]


def test_disallowed_column_name_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = InMemoryDatabasePort()
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    adapter.ensure_record_tables_schema()
    created = adapter.create_snapshot(label="disallowed-col")

    archive_path = Path(created["path"])
    data = json.loads(archive_path.read_text(encoding="utf-8"))
    data["tables"]["api_report_records"] = [
        {"id": "r1", "malicious_unallowed_column": "value"}
    ]

    payload = json.dumps(data, separators=(",", ":"), sort_keys=True)
    archive_path.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    Path(str(archive_path) + ".sha256").write_text(
        f"{digest}  {archive_path.name}\n", encoding="utf-8"
    )

    refused = adapter.restore_snapshot(created["snapshot_id"])
    assert refused["ok"] is False
    assert "Unknown column(s) for table api_report_records" in refused["message"]


def test_atomic_transactional_rollback_on_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = InMemoryDatabasePort()
    _seed_report_and_export_records(db)

    # Initial state has 1 report record and 1 export record
    assert len(db.fetchall("SELECT * FROM api_report_records")) == 1
    assert len(db.fetchall("SELECT * FROM api_export_records")) == 1

    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    created = adapter.create_snapshot(label="good-snapshot")

    # Corrupt the snapshot payload for the second table
    archive_path = Path(created["path"])
    data = json.loads(archive_path.read_text(encoding="utf-8"))
    # Table 1 has valid rows, Table 2 has a corrupt non-dict row
    data["tables"]["api_report_records"] = [
        {
            "id": "new-r1",
            "report_id": "r1",
            "owner_id": "o1",
            "tenant_id": "t1",
            "status": "ready",
            "s3_key": "k",
            "s3_bucket": "b",
            "created_at": "t",
            "updated_at": "t",
            "metadata": "{}",
        }
    ]
    data["tables"]["api_export_records"] = ["not_a_dict"]

    payload = json.dumps(data, separators=(",", ":"), sort_keys=True)
    archive_path.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    Path(str(archive_path) + ".sha256").write_text(
        f"{digest}  {archive_path.name}\n", encoding="utf-8"
    )

    refused = adapter.restore_snapshot(created["snapshot_id"])
    assert refused["ok"] is False
    assert "Corrupt row in api_export_records" in refused["message"]

    # Transaction rollback MUST have preserved the original database contents!
    # Table 1 must NOT contain "new-r1", and must still have "rec-rpt-001"
    reports = db.fetchall("SELECT * FROM api_report_records")
    assert len(reports) == 1
    assert reports[0]["id"] == "rec-rpt-001"

    exports = db.fetchall("SELECT * FROM api_export_records")
    assert len(exports) == 1
    assert exports[0]["id"] == "rec-exp-001"


def test_empty_database_backup_and_restore(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = InMemoryDatabasePort()
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    adapter.ensure_record_tables_schema()

    created = adapter.create_snapshot(label="empty-db")
    assert created["ok"] is True
    for name in PRODUCT_STATE_TABLES:
        assert created["tables"][name] == 0

    restored = adapter.restore_snapshot(created["snapshot_id"])
    assert restored["ok"] is True
    for name in PRODUCT_STATE_TABLES:
        assert restored["tables"][name] == 0


def test_sql_injection_column_identifier_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = InMemoryDatabasePort()
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    adapter.ensure_record_tables_schema()
    created = adapter.create_snapshot(label="sql-inject")

    archive_path = Path(created["path"])
    data = json.loads(archive_path.read_text(encoding="utf-8"))
    data["tables"]["api_report_records"] = [
        {"id); DROP TABLE api_report_records;--": "malicious"}
    ]

    payload = json.dumps(data, separators=(",", ":"), sort_keys=True)
    archive_path.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    Path(str(archive_path) + ".sha256").write_text(
        f"{digest}  {archive_path.name}\n", encoding="utf-8"
    )

    refused = adapter.restore_snapshot(created["snapshot_id"])
    assert refused["ok"] is False
    assert (
        "Unknown column" in refused["message"] or "Invalid column" in refused["message"]
    )


def test_corrupt_row_or_table_payload_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = InMemoryDatabasePort()
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    adapter.ensure_record_tables_schema()
    created = adapter.create_snapshot(label="corrupt-payload")

    archive_path = Path(created["path"])
    data = json.loads(archive_path.read_text(encoding="utf-8"))
    data["tables"]["api_report_records"] = ["not_a_dict_row"]

    payload = json.dumps(data, separators=(",", ":"), sort_keys=True)
    archive_path.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    Path(str(archive_path) + ".sha256").write_text(
        f"{digest}  {archive_path.name}\n", encoding="utf-8"
    )

    refused = adapter.restore_snapshot(created["snapshot_id"])
    assert refused["ok"] is False
    assert "Corrupt row in api_report_records" in refused["message"]


def test_json_fidelity_types_and_s3_reference(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = InMemoryDatabasePort()
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    adapter.ensure_record_tables_schema()

    complex_metadata = {
        "null_val": None,
        "bool_true": True,
        "bool_false": False,
        "int_num": 42,
        "float_num": 3.14159,
        "nested_dict": {"alpha": "beta", "gamma": [1, 2, 3]},
        "string_with_quotes": "hello 'world' \"test\"",
    }
    s3_key = "reports/tenant_001/year=2026/month=10/day=18/rpt-complex-99.json"
    s3_bucket = "dsp-production-artifacts-private-ap-south-1"

    row = {
        "id": "rec-complex-1",
        "report_id": "rpt-complex-99",
        "owner_id": "user-1",
        "tenant_id": "tenant-1",
        "status": "ready",
        "s3_key": s3_key,
        "s3_bucket": s3_bucket,
        "created_at": "2026-10-18T12:00:00Z",
        "updated_at": "2026-10-18T12:01:00Z",
        "metadata": complex_metadata,
    }

    cols = list(row.keys())
    db.execute(
        f"INSERT INTO api_report_records ({', '.join(cols)}) VALUES ({', '.join('%s' for _ in cols)})",
        tuple(
            (
                json.dumps(row[c], sort_keys=True)
                if isinstance(row[c], (dict, list))
                else row[c]
            )
            for c in cols
        ),
    )

    snapshot = adapter.create_snapshot(label="fidelity-check")
    assert snapshot["ok"] is True

    db.execute("DELETE FROM api_report_records")
    restored = adapter.restore_snapshot(snapshot["snapshot_id"])
    assert restored["ok"] is True

    rows = db.fetchall("SELECT * FROM api_report_records")
    assert len(rows) == 1
    restored_row = rows[0]
    assert restored_row["s3_key"] == s3_key
    assert restored_row["s3_bucket"] == s3_bucket

    meta = restored_row["metadata"]
    if isinstance(meta, str):
        meta = json.loads(meta)
    assert meta == complex_metadata


def _postgres_adapter_port() -> Any:
    import os
    import socket

    dsn = os.environ.get("DSP_TEST_POSTGRES_URL") or os.environ.get("DSP_DATABASE_URL")
    if not dsn:
        try:
            s = socket.create_connection(("127.0.0.1", 54329), timeout=0.2)
            s.close()
            dsn = "postgresql://postgres@127.0.0.1:54329/postgres"
        except Exception:
            return None
    try:
        from production_platform.adapters.postgres import try_build_postgres

        return try_build_postgres(dsn)
    except Exception:
        return None


@pytest.mark.skipif(
    _postgres_adapter_port() is None,
    reason="Isolated local PostgreSQL cluster unavailable",
)
def test_postgres_failed_restore_rolls_back_all_deletes_and_inserts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = _postgres_adapter_port()
    assert db is not None

    # Ensure schema exists on postgres
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    adapter.ensure_record_tables_schema()

    # Seed baseline records
    db.execute("DELETE FROM api_report_records")
    db.execute("DELETE FROM api_export_records")
    db.execute(
        "INSERT INTO api_report_records (id, report_id, owner_id, tenant_id, status, s3_key, s3_bucket, created_at, updated_at, metadata) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            "rec-pg-orig-1",
            "rep-1",
            "user-1",
            "tenant-1",
            "ready",
            "s3://b/k",
            "b",
            "2026-10-18T00:00:00Z",
            "2026-10-18T00:00:00Z",
            "{}",
        ),
    )
    db.execute(
        "INSERT INTO api_export_records (id, export_id, owner_id, tenant_id, status, s3_key, s3_bucket, content_type, size_bytes, created_at, metadata) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            "exp-pg-orig-1",
            "exp-1",
            "user-1",
            "tenant-1",
            "completed",
            "s3://b/e",
            "b",
            "text/csv",
            100,
            "2026-10-18T00:00:00Z",
            "{}",
        ),
    )

    created = adapter.create_snapshot(label="pg-rollback")
    assert created["ok"] is True

    # Tamper payload: table 1 valid with new row, table 2 corrupt (non-dict)
    archive_path = Path(created["path"])
    data = json.loads(archive_path.read_text(encoding="utf-8"))
    data["tables"]["api_report_records"] = [
        {
            "id": "new-pg-rec-99",
            "report_id": "r99",
            "owner_id": "u",
            "tenant_id": "t",
            "status": "ready",
            "s3_key": "k",
            "s3_bucket": "b",
            "created_at": "t",
            "updated_at": "t",
            "metadata": "{}",
        }
    ]
    data["tables"]["api_export_records"] = ["corrupt_non_dict_row"]

    payload = json.dumps(data, separators=(",", ":"), sort_keys=True)
    archive_path.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    Path(str(archive_path) + ".sha256").write_text(
        f"{digest}  {archive_path.name}\n", encoding="utf-8"
    )

    refused = adapter.restore_snapshot(created["snapshot_id"])
    assert refused["ok"] is False
    assert "Corrupt row in api_export_records" in refused["message"]

    # Verify atomic rollback on PostgreSQL: original records remain intact
    rpts = db.fetchall("SELECT * FROM api_report_records")
    exps = db.fetchall("SELECT * FROM api_export_records")
    assert len(rpts) == 1
    assert rpts[0]["id"] == "rec-pg-orig-1"
    assert len(exps) == 1
    assert exps[0]["id"] == "exp-pg-orig-1"


@pytest.mark.skipif(
    _postgres_adapter_port() is None,
    reason="Isolated local PostgreSQL cluster unavailable",
)
def test_postgres_json_metadata_round_trips_as_jsonb(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    db = _postgres_adapter_port()
    assert db is not None

    # Recreate table with explicit JSONB column
    db.execute("DROP TABLE IF EXISTS api_report_records CASCADE")
    db.execute(
        "CREATE TABLE api_report_records ("
        "id TEXT PRIMARY KEY, "
        "report_id TEXT, "
        "owner_id TEXT, "
        "tenant_id TEXT, "
        "status TEXT, "
        "s3_key TEXT, "
        "s3_bucket TEXT, "
        "created_at TEXT, "
        "updated_at TEXT, "
        "metadata JSONB"
        ")"
    )

    complex_metadata = {
        "analysis_mode": "institutional",
        "nested_eval": {"score": 96.5, "passed": True, "flags": ["moat", "growth"]},
        "citations": [
            {"source": "10-K", "year": 2026},
            {"source": "earnings", "quarter": "Q3"},
        ],
        "null_val": None,
    }

    db.execute(
        "INSERT INTO api_report_records (id, report_id, owner_id, tenant_id, status, s3_key, s3_bucket, created_at, updated_at, metadata) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            "rec-jsonb-1",
            "rep-jsonb-1",
            "user-inst",
            "tenant-inst",
            "ready",
            "s3://bucket/reports/rep-jsonb-1.json",
            "bucket",
            "2026-10-18T10:00:00Z",
            "2026-10-18T10:00:00Z",
            json.dumps(complex_metadata),
        ),
    )

    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    created = adapter.create_snapshot(label="pg-jsonb")
    assert created["ok"] is True

    # Wipe table
    db.execute("DELETE FROM api_report_records")
    assert len(db.fetchall("SELECT * FROM api_report_records")) == 0

    # Restore snapshot
    restored = adapter.restore_snapshot(created["snapshot_id"])
    assert restored["ok"] is True

    # Fetch back and assert JSONB deserialized cleanly to dict matching original structure
    rows = db.fetchall("SELECT * FROM api_report_records")
    assert len(rows) == 1
    restored_row = rows[0]
    assert restored_row["id"] == "rec-jsonb-1"
    assert isinstance(restored_row["metadata"], dict)
    assert restored_row["metadata"] == complex_metadata


def test_failed_parameterized_insert_never_retries_interpolated_sql_and_rolls_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    raw_db = InMemoryDatabasePort()
    adapter = LogicalProductStateBackupAdapter(raw_db, backup_root=tmp_path)
    adapter.ensure_record_tables_schema()

    raw_db.execute(
        "INSERT INTO api_report_records (id, report_id, owner_id, tenant_id, status, s3_key, s3_bucket, created_at, updated_at, metadata) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            "orig-r1",
            "rep1",
            "u1",
            "t1",
            "ready",
            "k1",
            "b1",
            "2026-10-18T00:00:00Z",
            "2026-10-18T00:00:00Z",
            "{}",
        ),
    )
    raw_db.execute(
        "INSERT INTO api_export_records (id, export_id, owner_id, tenant_id, status, s3_key, s3_bucket, content_type, size_bytes, created_at, metadata) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            "orig-e1",
            "exp1",
            "u1",
            "t1",
            "completed",
            "k2",
            "b2",
            "text/csv",
            100,
            "2026-10-18T00:00:00Z",
            "{}",
        ),
    )

    created = adapter.create_snapshot(label="sql-fail-test")
    assert created["ok"] is True

    archive_path = Path(created["path"])
    data = json.loads(archive_path.read_text(encoding="utf-8"))
    data["tables"]["api_report_records"] = [
        {
            "id": "new-r1",
            "report_id": "rep-fail-trigger",
            "owner_id": "u",
            "tenant_id": "t",
            "status": "ready",
            "s3_key": "k",
            "s3_bucket": "b",
            "created_at": "t",
            "updated_at": "t",
            "metadata": "{}",
        }
    ]
    payload = json.dumps(data, separators=(",", ":"), sort_keys=True)
    archive_path.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    Path(str(archive_path) + ".sha256").write_text(
        f"{digest}  {archive_path.name}\n", encoding="utf-8"
    )

    executed_calls: list[tuple[str, Any]] = []

    class FailingSpyDatabasePort:
        def __init__(self, inner: InMemoryDatabasePort) -> None:
            self._inner = inner

        def ping(self) -> bool:
            return self._inner.ping()

        def execute(self, statement: str, params: Any = None) -> None:
            executed_calls.append((statement, params))
            self._inner.execute(statement, params=params)

        def fetchall(self, statement: str, params: Any = None) -> list[dict[str, Any]]:
            return self._inner.fetchall(statement, params=params)

        @contextmanager
        def transaction(self) -> Iterator[Any]:
            with self._inner.transaction() as txn:

                class SpyTxn:
                    def __init__(self, inner_txn: Any) -> None:
                        self._inner_txn = inner_txn

                    def execute(self, statement: str, params: Any = None) -> None:
                        executed_calls.append((statement, params))
                        if params is not None and "rep-fail-trigger" in params:
                            raise RuntimeError(
                                "Simulated database failure on parameterized insert"
                            )
                        self._inner_txn.execute(statement, params=params)

                    def fetchall(
                        self, statement: str, params: Any = None
                    ) -> list[dict[str, Any]]:
                        return cast(
                            list[dict[str, Any]],
                            self._inner_txn.fetchall(statement, params=params),
                        )

                yield SpyTxn(txn)

    spy_db = FailingSpyDatabasePort(raw_db)
    spy_adapter = LogicalProductStateBackupAdapter(spy_db, backup_root=tmp_path)
    res = spy_adapter.restore_snapshot(created["snapshot_id"])

    assert res["ok"] is False
    assert "Simulated database failure on parameterized insert" in res["message"]

    insert_calls = [
        call for call in executed_calls if call[0].startswith("INSERT INTO")
    ]
    assert len(insert_calls) > 0
    for stmt, params in insert_calls:
        assert params is not None, f"Unparameterized insert detected: {stmt}"
        assert isinstance(params, tuple)
        assert "rep-fail-trigger" not in stmt
        assert "%s" in stmt

    failing_insert_calls = [
        call
        for call in insert_calls
        if call[1] is not None and "rep-fail-trigger" in call[1]
    ]
    assert (
        len(failing_insert_calls) == 1
    ), "Failed parameterized insert must not be retried with fallback SQL"

    reports = raw_db.fetchall("SELECT * FROM api_report_records")
    exports = raw_db.fetchall("SELECT * FROM api_export_records")
    assert len(reports) == 1
    assert reports[0]["id"] == "orig-r1"
    assert len(exports) == 1
    assert exports[0]["id"] == "orig-e1"


def test_adapter_constructor_does_not_mutate_schema_and_requires_explicit_init(
    tmp_path: Path,
) -> None:
    db = InMemoryDatabasePort()
    assert len(db._tables) == 0

    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)

    for table in LEGACY_PRODUCT_STATE_TABLES:
        assert table in db._tables

    assert "api_report_records" not in db._tables
    assert "api_export_records" not in db._tables

    assert adapter.is_available() is True
    status = adapter.status()
    assert status["available"] is True
    _ = adapter.list_snapshots()
    assert "api_report_records" not in db._tables
    assert "api_export_records" not in db._tables

    adapter.ensure_record_tables_schema()
    assert "api_report_records" in db._tables
    assert "api_export_records" in db._tables

    db2 = InMemoryDatabasePort()
    adapter2 = LogicalProductStateBackupAdapter(db2, backup_root=tmp_path)
    assert "api_report_records" not in db2._tables
    adapter2.ensure_schema(include_records=True)
    assert "api_report_records" in db2._tables
    assert "api_export_records" in db2._tables


def test_modern_restore_refuses_when_record_tables_missing_and_does_not_mutate_schema(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")
    source_db = InMemoryDatabasePort()
    source_adapter = LogicalProductStateBackupAdapter(source_db, backup_root=tmp_path)
    source_adapter.ensure_record_tables_schema()

    source_db.execute(
        "INSERT INTO api_report_snapshots (snapshot_key, payload, updated_at) "
        "VALUES ('snap-key-1', 'payload-1', '2026-10-18T00:00:00Z')"
    )
    source_db.execute(
        "INSERT INTO api_report_records (id, report_id, owner_id, tenant_id, status, s3_key, s3_bucket, created_at, updated_at, metadata) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            "r-001",
            "rep-1",
            "user-1",
            "tenant-1",
            "ready",
            "k1",
            "b1",
            "2026-10-18T00:00:00Z",
            "2026-10-18T00:00:00Z",
            "{}",
        ),
    )
    source_db.execute(
        "INSERT INTO api_export_records (id, export_id, owner_id, tenant_id, status, s3_key, s3_bucket, content_type, size_bytes, created_at, metadata) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            "e-001",
            "exp-1",
            "user-1",
            "tenant-1",
            "completed",
            "k2",
            "b2",
            "text/csv",
            1024,
            "2026-10-18T00:00:00Z",
            "{}",
        ),
    )

    created = source_adapter.create_snapshot(label="modern-full")
    assert created["ok"] is True
    assert created["tables"]["api_report_records"] == 1
    assert created["tables"]["api_export_records"] == 1

    # Target database has only legacy baseline schema provisioned
    target_db = InMemoryDatabasePort()
    target_adapter = LogicalProductStateBackupAdapter(target_db, backup_root=tmp_path)

    target_db.execute(
        "INSERT INTO api_report_snapshots (snapshot_key, payload, updated_at) "
        "VALUES ('existing-target-key', 'orig-target-payload', '2026-10-18T00:00:00Z')"
    )

    assert "api_report_records" not in target_db._tables
    assert "api_export_records" not in target_db._tables

    refused = target_adapter.restore_snapshot(created["snapshot_id"])
    assert refused["ok"] is False
    assert "missing required record tables" in refused["message"]
    assert "api_report_records" in refused["message"]
    assert "api_export_records" in refused["message"]

    # Target database MUST NOT have had tables created automatically
    assert "api_report_records" not in target_db._tables
    assert "api_export_records" not in target_db._tables

    # Existing records in target database MUST remain untouched
    existing_rows = target_db.fetchall("SELECT * FROM api_report_snapshots")
    assert len(existing_rows) == 1
    assert existing_rows[0]["snapshot_key"] == "existing-target-key"
    assert existing_rows[0]["payload"] == "orig-target-payload"

    # Now explicitly provision record tables on target database
    target_adapter.ensure_record_tables_schema()
    assert "api_report_records" in target_db._tables
    assert "api_export_records" in target_db._tables

    # Now restore succeeds and populates all tables
    restored = target_adapter.restore_snapshot(created["snapshot_id"])
    assert restored["ok"] is True
    assert restored["tables"]["api_report_records"] == 1
    assert restored["tables"]["api_export_records"] == 1

    reports = target_db.fetchall("SELECT * FROM api_report_records")
    assert len(reports) == 1
    assert reports[0]["id"] == "r-001"


def test_table_exists_identifies_existing_table(tmp_path: Path) -> None:
    db = InMemoryDatabasePort()
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    # Baseline tables created by constructor
    assert adapter._table_exists("enterprise_snapshots") is True
    assert adapter._table_exists("enterprise_audit_log") is True

    # Record tables absent initially
    assert adapter._table_exists("api_report_records") is False

    # Explicitly provision record tables
    adapter.ensure_record_tables_schema()
    assert adapter._table_exists("api_report_records") is True
    assert adapter._table_exists("api_export_records") is True

    # Custom DB adapter without _tables attribute where fetchall succeeds
    class CustomDatabasePort:
        def ping(self) -> bool:
            return True

        def fetchall(self, statement: str, params: Any = None) -> list[dict[str, Any]]:
            return []

        def execute(self, statement: str, params: Any = None) -> None:
            pass

    custom_adapter = LogicalProductStateBackupAdapter(
        CustomDatabasePort(), backup_root=tmp_path
    )
    assert custom_adapter._table_exists("api_report_records") is True


def test_table_exists_identifies_genuinely_missing_table(tmp_path: Path) -> None:
    db = InMemoryDatabasePort()
    adapter = LogicalProductStateBackupAdapter(db, backup_root=tmp_path)
    assert adapter._table_exists("api_report_records") is False
    assert adapter._table_exists("non_existent_table") is False

    import psycopg.errors

    class MissingTableDatabasePort:
        def ping(self) -> bool:
            return True

        def fetchall(self, statement: str, params: Any = None) -> list[dict[str, Any]]:
            raise psycopg.errors.UndefinedTable(
                'relation "api_report_records" does not exist'
            )

        def execute(self, statement: str, params: Any = None) -> None:
            pass

    pg_adapter = LogicalProductStateBackupAdapter(
        MissingTableDatabasePort(), backup_root=tmp_path
    )
    assert pg_adapter._table_exists("api_report_records") is False

    class SQLiteMissingDatabasePort:
        def ping(self) -> bool:
            return True

        def fetchall(self, statement: str, params: Any = None) -> list[dict[str, Any]]:
            raise RuntimeError("no such table: api_report_records")

        def execute(self, statement: str, params: Any = None) -> None:
            pass

    sqlite_adapter = LogicalProductStateBackupAdapter(
        SQLiteMissingDatabasePort(), backup_root=tmp_path
    )
    assert sqlite_adapter._table_exists("api_report_records") is False


def test_table_exists_propagates_connection_permission_and_query_failures(
    tmp_path: Path,
) -> None:
    import psycopg.errors

    from production_platform.production.exceptions import ProviderError

    # 1. Connection error must propagate
    class BrokenConnectionPort:
        def ping(self) -> bool:
            return False

        def fetchall(self, statement: str, params: Any = None) -> list[dict[str, Any]]:
            raise ProviderError("postgres connect failed: connection refused")

        def execute(self, statement: str, params: Any = None) -> None:
            pass

    broken_adapter = LogicalProductStateBackupAdapter(
        BrokenConnectionPort(), backup_root=tmp_path
    )
    with pytest.raises(ProviderError, match="connection refused"):
        broken_adapter._table_exists("api_report_records")

    # 2. Permission denied must propagate
    class PermissionDeniedPort:
        def ping(self) -> bool:
            return True

        def fetchall(self, statement: str, params: Any = None) -> list[dict[str, Any]]:
            raise psycopg.errors.InsufficientPrivilege(
                "permission denied for table api_report_records"
            )

        def execute(self, statement: str, params: Any = None) -> None:
            pass

    perm_adapter = LogicalProductStateBackupAdapter(
        PermissionDeniedPort(), backup_root=tmp_path
    )
    with pytest.raises(psycopg.errors.InsufficientPrivilege, match="permission denied"):
        perm_adapter._table_exists("api_report_records")

    # 3. Unexpected query failure must propagate
    class QueryFailurePort:
        def ping(self) -> bool:
            return True

        def fetchall(self, statement: str, params: Any = None) -> list[dict[str, Any]]:
            raise RuntimeError("unexpected database lock timeout")

        def execute(self, statement: str, params: Any = None) -> None:
            pass

    query_adapter = LogicalProductStateBackupAdapter(
        QueryFailurePort(), backup_root=tmp_path
    )
    with pytest.raises(RuntimeError, match="database lock timeout"):
        query_adapter._table_exists("api_report_records")

    # 4. Wrapper around InMemoryDatabasePort that fails fetchall must propagate
    raw_db = InMemoryDatabasePort()

    class BrokenWrapperPort:
        def __init__(self, inner: InMemoryDatabasePort) -> None:
            self._inner = inner

        def ping(self) -> bool:
            return self._inner.ping()

        def fetchall(self, statement: str, params: Any = None) -> list[dict[str, Any]]:
            raise ProviderError("wrapper probe failed")

        def execute(self, statement: str, params: Any = None) -> None:
            self._inner.execute(statement, params=params)

    wrapper_adapter = LogicalProductStateBackupAdapter(
        BrokenWrapperPort(raw_db), backup_root=tmp_path
    )
    with pytest.raises(ProviderError, match="wrapper probe failed"):
        wrapper_adapter._table_exists("api_report_records")


def test_modern_restore_fails_safely_when_table_inspection_fails_without_destructive_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from production_platform.production.exceptions import ProviderError

    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")

    source_db = InMemoryDatabasePort()
    source_adapter = LogicalProductStateBackupAdapter(source_db, backup_root=tmp_path)
    source_adapter.ensure_record_tables_schema()
    source_db.execute(
        "INSERT INTO api_report_records (id, report_id, status) VALUES ('r-1', 'rpt-1', 'ready')"
    )
    source_db.execute(
        "INSERT INTO api_export_records (id, export_id, status) VALUES ('e-1', 'exp-1', 'completed')"
    )
    snap = source_adapter.create_snapshot(label="modern")
    assert snap["ok"] is True

    # Setup target DB with pre-existing records in baseline table
    target_db = InMemoryDatabasePort()
    target_adapter = LogicalProductStateBackupAdapter(target_db, backup_root=tmp_path)
    target_db.execute(
        "INSERT INTO enterprise_snapshots (snapshot_key, payload, updated_at) "
        "VALUES ('target-key-orig', 'target-data-orig', '2026-10-18T00:00:00Z')"
    )

    # Monkeypatch _table_exists on target_adapter to simulate database connection failure
    def failing_table_exists(table_name: str) -> bool:
        raise ProviderError("connection to database host timed out")

    monkeypatch.setattr(target_adapter, "_table_exists", failing_table_exists)

    # Attempt restore
    result = target_adapter.restore_snapshot(snap["snapshot_id"])
    assert result["ok"] is False
    assert "Database inspection failed" in result["message"]
    assert "connection to database host timed out" in result["message"]

    # Verify that target DB records are completely untouched (no DELETE executed)
    rows = target_db.fetchall("SELECT * FROM enterprise_snapshots")
    assert len(rows) == 1
    assert rows[0]["snapshot_key"] == "target-key-orig"
    assert rows[0]["payload"] == "target-data-orig"

    # Verify record tables were not created
    assert "api_report_records" not in target_db._tables
    assert "api_export_records" not in target_db._tables


def test_legacy_archive_restore_bypasses_table_exists_inspection_and_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(RESTORE_CONFIRM_ENV, "YES")

    source_db = InMemoryDatabasePort()
    source_adapter = LogicalProductStateBackupAdapter(source_db, backup_root=tmp_path)
    source_db.execute(
        "INSERT INTO enterprise_snapshots (snapshot_key, payload, updated_at) "
        "VALUES ('legacy-key', 'legacy-payload', '2026-10-18T00:00:00Z')"
    )
    snap = source_adapter.create_snapshot(label="legacy-only")
    assert snap["ok"] is True
    assert "api_report_records" not in snap["tables"]
    assert "api_export_records" not in snap["tables"]

    # Target adapter has a failing _table_exists probe to prove it is NOT called for legacy restore
    target_db = InMemoryDatabasePort()
    target_adapter = LogicalProductStateBackupAdapter(target_db, backup_root=tmp_path)

    def should_not_be_called(table_name: str) -> bool:
        raise AssertionError(
            f"_table_exists should not be called for legacy archive: {table_name}"
        )

    monkeypatch.setattr(target_adapter, "_table_exists", should_not_be_called)

    res = target_adapter.restore_snapshot(snap["snapshot_id"])
    assert res["ok"] is True
    assert res["tables"]["enterprise_snapshots"] == 1
    rows = target_db.fetchall("SELECT * FROM enterprise_snapshots")
    assert len(rows) == 1
    assert rows[0]["snapshot_key"] == "legacy-key"
