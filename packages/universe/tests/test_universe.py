"""InvestmentUniverse membership tests."""

from __future__ import annotations

from contracts import AssetClass, Instrument
from universe import InvestmentUniverse, UniverseError, instrument_identity_key

from .conftest import make_instrument


class TestInvestmentUniverse:
    def test_empty_universe(self) -> None:
        universe = InvestmentUniverse(name="watchlist")
        assert len(universe) == 0
        assert universe.instruments() == ()
        assert not universe

    def test_add_remove_list(self) -> None:
        universe = InvestmentUniverse(name="banks")
        a = make_instrument("HDFCBANK", sector="Financials")
        b = make_instrument("ICICIBANK", sector="Financials")
        assert universe.add(a) is True
        assert universe.add(b) is True
        assert universe.add(a) is False  # duplicate
        assert len(universe) == 2
        assert universe.contains(a)
        assert universe.remove(a) is True
        assert universe.remove(a) is False
        assert universe.instruments() == (b,)

    def test_deterministic_ordering(self) -> None:
        universe = InvestmentUniverse(name="u")
        for symbol in ("ZEE", "AA", "MM", "BB"):
            universe.add(make_instrument(symbol))
        assert [i.symbol for i in universe.instruments()] == [
            "AA",
            "BB",
            "MM",
            "ZEE",
        ]

    def test_duplicate_identity_ignores_display_name(self) -> None:
        universe = InvestmentUniverse(name="u")
        first = make_instrument("AXISBANK")
        second = Instrument(
            symbol="AXISBANK",
            asset_class=AssetClass.EQUITY,
            currency="INR",
            name="Axis Bank Ltd",
            country="IN",
        )
        assert instrument_identity_key(first) == instrument_identity_key(second)
        assert universe.add(first) is True
        assert universe.add(second) is False
        assert len(universe) == 1

    def test_different_exchange_are_distinct(self) -> None:
        universe = InvestmentUniverse(name="u")
        assert universe.add(make_instrument("AAPL", exchange="NSE")) is True
        assert universe.add(make_instrument("AAPL", exchange="BSE")) is True
        assert len(universe) == 2

    def test_tags_normalized(self) -> None:
        universe = InvestmentUniverse(name="u")
        universe.add(make_instrument("BAJFINANCE"), tags={" Watchlist ", "BANK"})
        entry = universe.entries()[0]
        assert entry.tags == frozenset({"watchlist", "bank"})

    def test_require_non_empty(self) -> None:
        universe = InvestmentUniverse(name="u")
        try:
            universe.require_non_empty()
            raise AssertionError("expected UniverseError")
        except UniverseError:
            pass
