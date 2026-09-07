"""SIMPLE-14 persistence safety — current pointer, transactions, tiny datasets."""

from __future__ import annotations

import json
from contextlib import contextmanager

import pytest

from dsp_platform.security_master.db_store import (
    SECURITY_MASTER_CURRENT_TABLE,
    DatabaseSecurityMasterStore,
)
from dsp_platform.security_master.ingest import ingest_documents
from dsp_platform.security_master.models import SnapshotStatus, SourceDocument
from dsp_platform.security_master.search import search_snapshot
from dsp_platform.security_master.snapshot import MINIMUM_SOURCE_ROWS
from production_platform.production.database import InMemoryDatabasePort, InMemoryTransaction


def _doc(source_id: str, exchange: str, kind: str, body: bytes, uri: str, retrieved_at: str = "2026-09-07T12:00:00+00:00") -> SourceDocument:
    return SourceDocument(
        source_id=source_id,
        exchange=exchange,
        document_kind=kind,
        uri=uri,
        body=body,
        retrieved_at=retrieved_at,
        last_modified="Sun, 06 Sep 2026 21:35:03 GMT",
        content_type="text/csv",
        status=200,
    )


def _fixture_docs() -> tuple[SourceDocument, ...]:
    equity = (
        b"SYMBOL,NAME OF COMPANY,SERIES,ISIN NUMBER\n"
        b"WIPRO,Wipro Limited,EQ,INE075A01022\n"
        b"AAKASH,Aakash Exploration Services Limited,EQ,INE087Z01024\n"
    )
    bse = json.dumps(
        [
            {
                "scrip_id": "WIPRO",
                "Issuer_Name": "Wipro Limited",
                "ISIN_NUMBER": "INE075A01022",
                "SCRIP_CD": "507685",
                "GROUP": "A",
                "Status": "Active",
            }
        ]
    ).encode("utf-8")
    return (
        _doc(
            "nse_equity",
            "NSE",
            "equity",
            equity,
            "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
        ),
        _doc(
            "bse_active",
            "BSE",
            "equity_active",
            bse,
            "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?status=Active",
        ),
    )


def _empty_nse() -> SourceDocument:
    return SourceDocument(
        source_id="nse_equity",
        exchange="NSE",
        document_kind="equity",
        uri="https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
        body=b"",
        retrieved_at="2026-09-07T16:00:00+00:00",
        last_modified="",
        content_type="text/html",
        status=200,
    )


def test_official_minimums_reject_fixture_scale() -> None:
    store = DatabaseSecurityMasterStore(InMemoryDatabasePort())
    failed = ingest_documents(_fixture_docs(), store=store, enforce_minimums=True)
    assert failed.status is SnapshotStatus.FAILED
    assert "unexpectedly tiny dataset" in failed.error
    assert store.current_snapshot() is None
    assert failed.record_count == 0
    assert MINIMUM_SOURCE_ROWS["nse_equity"] == 1000


def test_failed_ingest_keeps_current_pointer() -> None:
    store = DatabaseSecurityMasterStore(InMemoryDatabasePort())
    first = ingest_documents(_fixture_docs(), store=store)
    assert store.current_snapshot().snapshot_id == first.snapshot_id
    failed = ingest_documents((_empty_nse(),), store=store)
    assert failed.status is SnapshotStatus.FAILED
    current = store.current_snapshot()
    assert current is not None
    assert current.snapshot_id == first.snapshot_id
    history = store.list_snapshots()
    assert {row["snapshot_id"] for row in history} >= {first.snapshot_id, failed.snapshot_id}
    assert sum(1 for row in history if row["is_current"]) == 1


def test_repeated_ingest_does_not_duplicate_current_pointer() -> None:
    db = InMemoryDatabasePort()
    store = DatabaseSecurityMasterStore(db)
    first = ingest_documents(_fixture_docs(), store=store)
    second_docs = list(_fixture_docs())
    second_docs[0] = SourceDocument(
        source_id=second_docs[0].source_id,
        exchange=second_docs[0].exchange,
        document_kind=second_docs[0].document_kind,
        uri=second_docs[0].uri,
        body=second_docs[0].body,
        retrieved_at="2026-09-08T00:00:00+00:00",
        last_modified="Mon, 07 Sep 2026 21:35:03 GMT",
        content_type="text/csv",
        status=200,
    )
    second = ingest_documents(tuple(second_docs), store=store)
    pointers = [
        row
        for row in db.fetchall(f"SELECT * FROM {SECURITY_MASTER_CURRENT_TABLE}")
        if str(row.get("pointer_key") or "") == "CURRENT"
    ]
    assert len(pointers) == 1
    assert pointers[0]["snapshot_id"] == second.snapshot_id
    assert store.get_snapshot(first.snapshot_id) is not None
    assert store.get_snapshot(first.snapshot_id).snapshot_id == first.snapshot_id


class _FailingTxn:
    def __init__(self, inner: InMemoryTransaction, *, fail_records: bool) -> None:
        self._inner = inner
        self._fail_records = fail_records

    def execute(self, statement: str, params=None) -> None:
        sql = " ".join(statement.strip().split())
        if self._fail_records and sql.upper().startswith("INSERT INTO SECURITY_MASTER_RECORDS"):
            raise RuntimeError("injected ingest failure")
        self._inner.execute(statement, params)

    def fetchall(self, statement: str, params=None):
        return self._inner.fetchall(statement, params)


class _FailingDatabase(InMemoryDatabasePort):
    def __init__(self) -> None:
        super().__init__()
        self.fail_records = False

    @contextmanager
    def transaction(self):
        txn = InMemoryTransaction(self._tables, self._lock)
        txn.begin()
        wrapped = _FailingTxn(txn, fail_records=self.fail_records)
        try:
            yield wrapped
            if txn._open:  # noqa: SLF001
                txn.commit()
        except Exception:
            if txn._open:  # noqa: SLF001
                txn.rollback()
            raise


def test_mid_write_failure_rolls_back_current_pointer() -> None:
    db = _FailingDatabase()
    store = DatabaseSecurityMasterStore(db)
    first = ingest_documents(_fixture_docs(), store=store)
    db.fail_records = True
    second_docs = list(_fixture_docs())
    second_docs[0] = SourceDocument(
        source_id=second_docs[0].source_id,
        exchange=second_docs[0].exchange,
        document_kind=second_docs[0].document_kind,
        uri=second_docs[0].uri,
        body=second_docs[0].body,
        retrieved_at="2026-09-08T12:00:00+00:00",
        last_modified="Tue, 08 Sep 2026 21:35:03 GMT",
        content_type="text/csv",
        status=200,
    )
    with pytest.raises(RuntimeError, match="injected ingest failure"):
        ingest_documents(tuple(second_docs), store=store)
    current = store.current_snapshot()
    assert current is not None
    assert current.snapshot_id == first.snapshot_id
    pointers = [
        row
        for row in db.fetchall(f"SELECT * FROM {SECURITY_MASTER_CURRENT_TABLE}")
        if str(row.get("pointer_key") or "") == "CURRENT"
    ]
    assert len(pointers) == 1
    assert pointers[0]["snapshot_id"] == first.snapshot_id


def test_empty_query_does_not_dump_universe() -> None:
    store = DatabaseSecurityMasterStore(InMemoryDatabasePort())
    snapshot = ingest_documents(_fixture_docs(), store=store)
    outcome = search_snapshot(snapshot, "   ")
    assert outcome.candidates == ()
    assert outcome.available is True
    assert "Enter a ticker" in outcome.message
