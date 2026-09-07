"""SIMPLE-13 Security Master — official universe identity, not a five-stock list."""

from __future__ import annotations

import json

import pytest

from dsp_platform.security_master.http import SecurityMasterHttp
from dsp_platform.security_master.ingest import ingest_documents
from dsp_platform.security_master.models import (
    EligibilityStatus,
    ListingStatus,
    ResolutionStatus,
    SecurityType,
    SnapshotStatus,
    SourceDocument,
)
from dsp_platform.security_master.search import resolve_exact, search_snapshot
from dsp_platform.security_master.sources import OfficialSource
from dsp_platform.security_master.store import (
    MemorySecurityMasterStore,
    reset_security_master_store_for_tests,
)
from production_platform.production.database import InMemoryDatabasePort


def _doc(
    source_id: str,
    exchange: str,
    kind: str,
    body: bytes,
    *,
    last_modified: str = "Sun, 06 Sep 2026 21:35:03 GMT",
    retrieved_at: str = "2026-09-07T12:00:00+00:00",
    uri: str = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
) -> SourceDocument:
    return SourceDocument(
        source_id=source_id,
        exchange=exchange,
        document_kind=kind,
        uri=uri,
        body=body,
        retrieved_at=retrieved_at,
        last_modified=last_modified,
        content_type="text/csv",
        status=200,
    )


def _fixture_docs() -> tuple[SourceDocument, ...]:
    equity = b"""SYMBOL,NAME OF COMPANY,SERIES,DATE OF LISTING,PAID UP VALUE,MARKET LOT,ISIN NUMBER,FACE VALUE
20MICRONS,20 Microns Limited,EQ,06-OCT-2008,5,1,INE144J01027,5
AAKASH,Aakash Exploration Services Limited,EQ,29-SEP-2020,1,1,INE087Z01024,1
WIPRO,Wipro Limited,EQ,08-NOV-1995,2,1,INE075A01022,2
TCS,Tata Consultancy Services Limited,EQ,25-AUG-2004,1,1,INE467B01029,1
AMBIGCO,Ambiguous Name One Limited,EQ,01-JAN-2000,10,1,INE111A01019,10
AMBIGTWO,Ambiguous Name Two Limited,EQ,01-JAN-2001,10,1,INE222A01016,10
BADROW,Bad Row Limited,EQ,01-JAN-2000,1,1,,1
DUPA,Duplicate Isin Alpha Limited,EQ,01-JAN-2002,1,1,INE888A01012,1
DUPB,Duplicate Isin Beta Limited,EQ,01-JAN-2003,1,1,INE888A01012,1
"""
    sme = b"""SYMBOL,NAME OF COMPANY,SERIES,ISIN NUMBER
ASHUTOSH,Ashutosh Paper Mills Limited,ST,INE19FR01012
"""
    etf = b"""SYMBOL,NAME OF COMPANY,SERIES,ISIN NUMBER
NIFTYBEES,Nippon India ETF Nifty BeES,EQ,INF204KB14I2
"""
    reit = b"""SYMBOL,NAME OF COMPANY,SERIES,ISIN NUMBER
EMBASSY,Embassy Office Parks REIT,RR,INE041025019
"""
    invit = b"""SYMBOL,NAME OF COMPANY,SERIES,ISIN NUMBER
IRBINVIT,IRB InvIT Fund,IV,INE183W23014
"""
    pref = b"""SYMBOL,NAME OF COMPANY,SERIES
PREFFAKE,Fake Preference Limited,P
"""
    warrant = b"""SYMBOL,NAME OF COMPANY,SERIES
WARRFAKE,Fake Warrant Limited,W
"""
    bse_active = json.dumps(
        [
            {
                "scrip_id": "20MICRONS",
                "Issuer_Name": "20 Microns Ltd",
                "ISIN_NUMBER": "INE144J01027",
                "SCRIP_CD": "533022",
                "GROUP": "B",
                "Status": "Active",
            },
            {
                "scrip_id": "ANDHRAPET",
                "Issuer_Name": "Andhra Petrochemicals Ltd",
                "ISIN_NUMBER": "INE714B01016",
                "SCRIP_CD": "500012",
                "GROUP": "X",
                "Status": "Active",
            },
            {
                "scrip_id": "WIPRO",
                "Issuer_Name": "Wipro Limited",
                "ISIN_NUMBER": "INE075A01022",
                "SCRIP_CD": "507685",
                "GROUP": "A",
                "Status": "Active",
            },
            {
                "scrip_id": "TCS",
                "Issuer_Name": "Tata Consultancy Services Limited",
                "ISIN_NUMBER": "INE467B01029",
                "SCRIP_CD": "532540",
                "GROUP": "A",
                "Status": "Active",
            },
            {
                "scrip_id": "NOISINCO",
                "Issuer_Name": "Missing Isin Company",
                "ISIN_NUMBER": "",
                "SCRIP_CD": "999001",
                "GROUP": "B",
                "Status": "Active",
            },
            {
                "scrip_id": "SMESCRIP",
                "Issuer_Name": "BSE SME Sample Ltd",
                "ISIN_NUMBER": "INE321B01018",
                "SCRIP_CD": "543210",
                "GROUP": "M",
                "Status": "Active",
            },
        ]
    ).encode("utf-8")
    bse_suspended = json.dumps(
        [
            {
                "scrip_id": "SUSPCO",
                "Issuer_Name": "Suspended Sample Ltd",
                "ISIN_NUMBER": "INE555A01014",
                "SCRIP_CD": "500999",
                "GROUP": "Z",
                "Status": "Suspended",
            }
        ]
    ).encode("utf-8")
    bse_delisted = json.dumps(
        [
            {
                "scrip_id": "DELISTCO",
                "Issuer_Name": "Delisted Sample Ltd",
                "ISIN_NUMBER": "INE666A01011",
                "SCRIP_CD": "500998",
                "GROUP": "B",
                "Status": "Delisted",
            }
        ]
    ).encode("utf-8")
    return (
        _doc("nse_equity", "NSE", "equity", equity),
        _doc("nse_sme", "NSE", "sme_equity", sme),
        _doc("nse_etf", "NSE", "etf", etf),
        _doc("nse_reit", "NSE", "reit", reit),
        _doc("nse_invit", "NSE", "invit", invit),
        _doc("nse_preference", "NSE", "preference", pref),
        _doc("nse_warrant", "NSE", "warrant", warrant),
        _doc(
            "bse_active",
            "BSE",
            "equity_active",
            bse_active,
            uri="https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?status=Active",
        ),
        _doc(
            "bse_suspended",
            "BSE",
            "equity_suspended",
            bse_suspended,
            uri="https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?status=Suspended",
        ),
        _doc(
            "bse_delisted",
            "BSE",
            "equity_delisted",
            bse_delisted,
            uri="https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?status=Delisted",
        ),
    )


def get_store() -> MemorySecurityMasterStore:
    from dsp_platform.security_master.store import get_security_master_store

    return get_security_master_store()


@pytest.fixture
def snapshot():
    reset_security_master_store_for_tests(MemorySecurityMasterStore())
    ingest_documents(_fixture_docs())
    return get_store().current_snapshot()


def test_source_date_is_not_retrieved_at(snapshot) -> None:
    assert snapshot.source_date == "2026-09-06"
    assert snapshot.retrieved_at.startswith("2026-09-07")
    assert snapshot.status is SnapshotStatus.ACCEPTED


def test_wipro_is_not_a_five_stock_fixture(snapshot) -> None:
    hits = search_snapshot(snapshot, "WIPRO")
    assert hits.resolution is ResolutionStatus.DUAL_LISTING_CANDIDATES
    assert {hit.record.exchange for hit in hits.candidates} == {"NSE", "BSE"}
    assert {hit.record.isin for hit in hits.candidates} == {"INE075A01022"}
    assert {hit.record.mic for hit in hits.candidates} == {"XNSE", "XBOM"}


def test_nse_only_aakash(snapshot) -> None:
    hits = search_snapshot(snapshot, "AAKASH")
    assert hits.resolution is ResolutionStatus.EXACT
    assert hits.candidates[0].record.exchange == "NSE"
    assert hits.candidates[0].record.isin == "INE087Z01024"


def test_bse_only_andhrapet(snapshot) -> None:
    hits = search_snapshot(snapshot, "ANDHRAPET")
    assert hits.resolution is ResolutionStatus.EXACT
    row = hits.candidates[0].record
    assert row.exchange == "BSE"
    assert row.exchange_security_code == "500012"
    assert row.dsp_eligible is True


def test_sme_classified_not_dropped(snapshot) -> None:
    hits = search_snapshot(snapshot, "ASHUTOSH")
    assert hits.candidates[0].record.security_type is SecurityType.SME_EQUITY
    assert hits.candidates[0].record.dsp_eligible is True
    bse_sme = search_snapshot(snapshot, "SMESCRIP")
    assert bse_sme.candidates[0].record.security_type is SecurityType.SME_EQUITY


def test_etf_reit_invit_pref_warrant_unsupported(snapshot) -> None:
    etf = search_snapshot(snapshot, "NIFTYBEES").candidates[0].record
    assert etf.security_type is SecurityType.ETF
    assert etf.eligibility_status is EligibilityStatus.UNSUPPORTED_SECURITY_TYPE
    assert etf.dsp_eligible is False
    reit = search_snapshot(snapshot, "EMBASSY").candidates[0].record
    assert reit.security_type is SecurityType.REIT
    invit = search_snapshot(snapshot, "IRBINVIT").candidates[0].record
    assert invit.security_type is SecurityType.INVIT
    pref = search_snapshot(snapshot, "PREFFAKE").candidates[0].record
    assert pref.security_type is SecurityType.PREFERENCE
    assert pref.identity_ok is False
    warrant = search_snapshot(snapshot, "WARRFAKE").candidates[0].record
    assert warrant.security_type is SecurityType.WARRANT


def test_suspended_and_delisted(snapshot) -> None:
    susp = search_snapshot(snapshot, "SUSPCO").candidates[0].record
    assert susp.listing_status is ListingStatus.SUSPENDED
    assert susp.dsp_eligible is False
    gone = search_snapshot(snapshot, "DELISTCO").candidates[0].record
    assert gone.listing_status is ListingStatus.DELISTED
    assert gone.eligibility_status is EligibilityStatus.DELISTED


def test_ambiguous_name_is_not_auto_selected(snapshot) -> None:
    hits = search_snapshot(snapshot, "Ambiguous")
    assert hits.resolution is ResolutionStatus.AMBIGUOUS
    assert len(hits.candidates) >= 2
    assert {hit.record.isin for hit in hits.candidates} == {
        "INE111A01019",
        "INE222A01016",
    }


def test_unknown_ticker_and_isin_fail_closed(snapshot) -> None:
    unknown_ticker = search_snapshot(snapshot, "ZZZZNOTALISTED")
    assert unknown_ticker.resolution is ResolutionStatus.UNKNOWN
    assert unknown_ticker.candidates == ()
    unknown_isin = search_snapshot(snapshot, "INE000A01018")
    assert unknown_isin.resolution is ResolutionStatus.UNKNOWN


def test_duplicate_symbol_across_exchanges_is_dual_listing(snapshot) -> None:
    hits = search_snapshot(snapshot, "20MICRONS")
    assert hits.resolution is ResolutionStatus.DUAL_LISTING_CANDIDATES
    assert len({hit.record.listing_id for hit in hits.candidates}) == 2


def test_malformed_row_is_retained(snapshot) -> None:
    bad = [row for row in snapshot.records if row.trading_symbol == "BADROW"]
    assert len(bad) == 1
    assert bad[0].identity_ok is False
    assert bad[0].eligibility_status is EligibilityStatus.IDENTITY_INCOMPLETE
    missing = [row for row in snapshot.records if row.trading_symbol == "NOISINCO"]
    assert missing[0].identity_ok is False


def test_duplicate_isin_mic_flagged(snapshot) -> None:
    dups = [row for row in snapshot.records if row.isin == "INE888A01012"]
    assert len(dups) == 2
    assert any("duplicate_isin_mic" in row.uniqueness_flags for row in dups)
    assert all(row.dsp_eligible is False for row in dups if row.uniqueness_flags)


def test_exact_isin_resolution(snapshot) -> None:
    hits = search_snapshot(snapshot, "INE087Z01024")
    assert hits.resolution is ResolutionStatus.EXACT
    assert hits.candidates[0].record.trading_symbol == "AAKASH"


def test_security_code_search(snapshot) -> None:
    hits = search_snapshot(snapshot, "500012")
    assert hits.resolution is ResolutionStatus.EXACT
    assert hits.candidates[0].record.trading_symbol == "ANDHRAPET"


def test_empty_query_does_not_dump_universe(snapshot) -> None:
    hits = search_snapshot(snapshot, "   ")
    assert hits.candidates == ()
    assert hits.available is True


def test_unavailable_snapshot_fails_closed() -> None:
    hits = search_snapshot(None, "WIPRO")
    assert hits.resolution is ResolutionStatus.UNAVAILABLE
    assert hits.message == "Data unavailable."


def test_historical_snapshot_not_overwritten() -> None:
    store = MemorySecurityMasterStore()
    first = ingest_documents(_fixture_docs(), store=store)
    old_id = first.snapshot_id
    changed = list(_fixture_docs())
    equity = changed[0].body.replace(b"WIPRO,Wipro Limited", b"WIPROX,Wipro Limited")
    changed[0] = SourceDocument(
        source_id=changed[0].source_id,
        exchange=changed[0].exchange,
        document_kind=changed[0].document_kind,
        uri=changed[0].uri,
        body=equity,
        retrieved_at="2026-09-08T12:00:00+00:00",
        last_modified="Mon, 07 Sep 2026 21:35:03 GMT",
        content_type="text/csv",
        status=200,
    )
    second = ingest_documents(tuple(changed), store=store)
    assert second.snapshot_id != old_id
    historic = store.get_snapshot(old_id)
    assert historic is not None
    assert any(row.trading_symbol == "WIPRO" for row in historic.records)
    current = store.current_snapshot()
    assert current is not None
    assert current.snapshot_id == second.snapshot_id
    assert any(row.trading_symbol == "WIPROX" for row in current.records)


def test_failed_ingest_does_not_replace_current(snapshot) -> None:
    store = get_store()
    current_id = snapshot.snapshot_id
    failed = ingest_documents(
        (
            SourceDocument(
                source_id="nse_equity",
                exchange="NSE",
                document_kind="equity",
                uri="https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
                body=b"",
                retrieved_at="2026-09-07T13:00:00+00:00",
                last_modified="",
                content_type="",
                status=200,
                error="",
            ),
        ),
        store=store,
    )
    assert failed.status is SnapshotStatus.FAILED
    assert store.current_snapshot().snapshot_id == current_id


def test_database_store_keeps_history() -> None:
    from dsp_platform.security_master.db_store import DatabaseSecurityMasterStore

    db_store = DatabaseSecurityMasterStore(InMemoryDatabasePort())
    first = ingest_documents(_fixture_docs(), store=db_store)
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
    second = ingest_documents(tuple(second_docs), store=db_store)
    assert db_store.get_snapshot(first.snapshot_id) is not None
    assert db_store.current_snapshot().snapshot_id == second.snapshot_id
    assert len(db_store.list_snapshots()) == 2


def test_counts_are_exact_not_estimated(snapshot) -> None:
    counts = snapshot.counts.to_dict()
    assert counts["nse_source_rows"] == 15
    assert counts["malformed_retained"] >= 1
    assert counts["dual_listed"] == 3
    assert counts["etf"] == 1
    assert counts["sme"] >= 2
    for value in counts.values():
        assert isinstance(value, int)


def test_resolve_exact_listing(snapshot) -> None:
    row = search_snapshot(snapshot, "AAKASH").candidates[0].record
    resolved = resolve_exact(snapshot, listing_id=row.listing_id)
    assert resolved.resolution is ResolutionStatus.EXACT


def test_http_rejects_non_frozen_locator() -> None:
    http = SecurityMasterHttp()
    fake = OfficialSource(
        source_id="evil",
        exchange="NSE",
        document_kind="equity",
        uri="https://example.com/steal",
        referer="https://www.nseindia.com/",
        accept="*/*",
        required=False,
    )
    doc = http.get_document(fake)
    assert doc.body == b""
    assert "frozen official source" in doc.error


def test_listed_equity_fixture_catalog_is_not_this_universe() -> None:
    from dsp_platform.share_count_acquisition.universe import iter_listed_equities

    symbols = {row.identity.symbol for row in iter_listed_equities()}
    assert symbols == {"TCS", "INFY", "RELIANCE", "HDFCBANK", "ICICIBANK"}
    reset_security_master_store_for_tests(MemorySecurityMasterStore())
    ingest_documents(_fixture_docs())
    universe_symbols = {
        row.trading_symbol for row in get_store().current_snapshot().records
    }
    assert "WIPRO" in universe_symbols
    assert "AAKASH" in universe_symbols
    assert universe_symbols != symbols
