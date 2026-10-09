"""Tests for Upstox dynamic instrument resolution."""

from __future__ import annotations

import pytest
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.upstox.instrument_resolver import (
    UpstoxInstrumentRecord,
    UpstoxInstrumentResolver,
    UpstoxResolutionResult,
    get_upstox_resolver,
)


def test_resolver_with_authorized_records() -> None:
    records = [
        UpstoxInstrumentRecord(
            instrument_key="NSE_EQ|INE848E01016",
            symbol="NHPC",
            name="NHPC Limited",
            exchange="NSE",
            instrument_type="EQUITY",
            isin="INE848E01016",
            segment="NSE_EQ",
        ),
        UpstoxInstrumentRecord(
            instrument_key="BSE_EQ|533098",
            symbol="NHPC",
            name="NHPC Limited",
            exchange="BSE",
            instrument_type="EQUITY",
            isin="INE848E01016",
            segment="BSE_EQ",
        ),
        UpstoxInstrumentRecord(
            instrument_key="MCX_COMM|425890",
            symbol="GOLD",
            name="Gold Futures",
            exchange="MCX",
            instrument_type="FUTCOM",
            lot_size=1,
            segment="MCX_FO",
        ),
    ]

    resolver = UpstoxInstrumentResolver(records=records)
    assert resolver.record_count == 3

    # Resolve by symbol + exchange
    inst_nse = Instrument(
        symbol="NHPC",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    res_nse = resolver.resolve(inst_nse)
    assert res_nse.is_resolved
    assert res_nse.instrument_key == "NSE_EQ|INE848E01016"
    assert res_nse.isin == "INE848E01016"
    assert res_nse.exchange == "NSE"

    # Resolve by BSE
    inst_bse = Instrument(
        symbol="NHPC",
        exchange="BSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    res_bse = resolver.resolve(inst_bse)
    assert res_bse.is_resolved
    assert res_bse.instrument_key == "BSE_EQ|533098"

    # Resolve Commodity on MCX
    inst_gold = Instrument(
        symbol="GOLD",
        exchange="MCX",
        asset_class=AssetClass.COMMODITY,
        currency="INR",
    )
    res_gold = resolver.resolve(inst_gold)
    assert res_gold.is_resolved
    assert res_gold.instrument_key == "MCX_COMM|425890"


def test_resolver_handles_ambiguity() -> None:
    records = [
        UpstoxInstrumentRecord(
            instrument_key="NSE_EQ|INE848E01016",
            symbol="NHPC",
            name="NHPC Limited",
            exchange="NSE",
            instrument_type="EQUITY",
        ),
        UpstoxInstrumentRecord(
            instrument_key="BSE_EQ|533098",
            symbol="NHPC",
            name="NHPC Limited",
            exchange="BSE",
            instrument_type="EQUITY",
        ),
    ]

    resolver = UpstoxInstrumentResolver(records=records)

    # Query with no exchange specified matches both NSE and BSE
    inst_ambiguous = Instrument(
        symbol="NHPC",
        exchange="",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    res = resolver.resolve(inst_ambiguous)
    assert res.is_ambiguous
    assert not res.is_resolved
    assert len(res.candidate_keys) == 2
    assert "Ambiguous instrument" in (res.detail or "")


def test_resolver_unresolved_when_not_in_records() -> None:
    resolver = UpstoxInstrumentResolver(records=[])
    inst = Instrument(
        symbol="NONEXISTENT_XYZ",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    res = resolver.resolve(inst)
    assert not res.is_resolved
    assert res.instrument_key is None
    assert "No matching instrument found" in (res.detail or "")


def test_resolver_does_not_generate_keys_by_string_concatenation() -> None:
    # An empty resolver must never invent a key like NSE_EQ|RANDOM
    resolver = UpstoxInstrumentResolver(records=[])
    inst = Instrument(
        symbol="RANDOM_TICKER",
        exchange="NSE",
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )
    res = resolver.resolve(inst)
    assert not res.is_resolved
    assert res.instrument_key is None
