"""Performance smoke for synthetic universes (1 / 10 / 50 / 100)."""

from __future__ import annotations

import tracemalloc

import pytest

from universe import (
    BatchStatus,
    InvestmentUniverse,
    MultiStockAnalysisRequest,
    MultiStockAnalysisService,
)

from .conftest import END, START, RecordingAnalyzer, make_instrument


@pytest.mark.parametrize("size", [1, 10, 50, 100])
def test_synthetic_universe_scale(size: int) -> None:
    universe = InvestmentUniverse(name=f"n{size}")
    for i in range(size):
        universe.add(make_instrument(f"S{i:04d}"))

    analyzer = RecordingAnalyzer()
    tracemalloc.start()
    result = MultiStockAnalysisService(analyzer).analyze(
        MultiStockAnalysisRequest(universe=universe, start=START, end=END)
    )
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert result.status is BatchStatus.SUCCESS
    assert len(result.outcomes) == size
    assert len(analyzer.calls) == size
    # Deterministic alphabetical order by symbol S0000.. 
    assert analyzer.calls == sorted(analyzer.calls)
    # Smoke bound: even 100 synthetic packs should stay modest.
    assert peak < 200 * 1024 * 1024


def test_orchestration_calls_equal_universe_size() -> None:
    """Each instrument triggers exactly one analyzer invocation."""
    universe = InvestmentUniverse.from_instruments(
        [make_instrument(f"T{i:02d}") for i in range(10)],
        name="ten",
    )
    analyzer = RecordingAnalyzer()
    MultiStockAnalysisService(analyzer).analyze(
        MultiStockAnalysisRequest(universe=universe, start=START, end=END)
    )
    assert len(analyzer.calls) == 10
    assert len(set(analyzer.calls)) == 10
