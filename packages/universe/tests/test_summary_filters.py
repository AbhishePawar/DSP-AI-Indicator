"""Comparable summary and filter/group tests."""

from __future__ import annotations

from contracts import AssetClass
from universe import (
    InvestmentUniverse,
    filter_entries,
    group_entries,
    summarize_decision_pack,
)

from .conftest import make_instrument, make_pack


class TestComparableSummary:
    def test_summary_preserves_decision_fields(self) -> None:
        instrument = make_instrument("HDFCBANK", sector="Financials")
        pack = make_pack(instrument)
        summary = summarize_decision_pack(pack)
        assert summary.instrument.symbol == "HDFCBANK"
        assert summary.action is pack.recommendation.action
        assert summary.assurance_level is pack.assurance.assurance_level
        assert summary.guidance is pack.assurance.investor_guidance.stance
        assert summary.agreement_quality == pack.assurance.agreement_quality.value
        assert summary.mos_ratio == (
            None
            if pack.recommendation.margin_of_safety is None
            or not pack.recommendation.margin_of_safety.available
            else pack.recommendation.margin_of_safety.ratio
        )
        assert summary.headline == pack.brief.headline


class TestFiltersAndGroups:
    def test_filter_by_sector_and_tag(self) -> None:
        universe = InvestmentUniverse(name="banks")
        universe.add(
            make_instrument("HDFCBANK", sector="Financials", industry="Banks"),
            tags={"nifty-bank"},
        )
        universe.add(
            make_instrument("TCS", sector="Technology", industry="IT"),
            tags={"nifty-it"},
        )
        universe.add(
            make_instrument("ICICIBANK", sector="Financials", industry="Banks"),
            tags={"nifty-bank", "core"},
        )
        banks = filter_entries(universe, sector="Financials")
        assert [e.instrument.symbol for e in banks] == ["HDFCBANK", "ICICIBANK"]
        tagged = filter_entries(universe, tag="nifty-bank")
        assert [e.instrument.symbol for e in tagged] == ["HDFCBANK", "ICICIBANK"]
        core = filter_entries(universe, tags_all={"nifty-bank", "core"})
        assert [e.instrument.symbol for e in core] == ["ICICIBANK"]

    def test_group_by_sector(self) -> None:
        universe = InvestmentUniverse(name="u")
        universe.add(make_instrument("AA", sector="Financials"))
        universe.add(make_instrument("BB", sector="Technology"))
        universe.add(make_instrument("CC"))  # unspecified
        groups = group_entries(universe, by="sector")
        assert set(groups) == {"financials", "technology", "unspecified"}
        assert [e.instrument.symbol for e in groups["financials"]] == ["AA"]

    def test_group_by_asset_class(self) -> None:
        universe = InvestmentUniverse(name="u")
        universe.add(make_instrument("AA"))
        groups = group_entries(universe, by="asset_class")
        assert list(groups) == [AssetClass.EQUITY.value]

    def test_no_sector_inference_from_name(self) -> None:
        universe = InvestmentUniverse(name="u")
        universe.add(make_instrument("HDFCBANK"))  # no sector set
        banks = filter_entries(universe, sector="Financials")
        assert banks == ()
