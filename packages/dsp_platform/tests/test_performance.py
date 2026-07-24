"""Basic performance smoke checks (fake providers, offline)."""

from __future__ import annotations

import time
import tracemalloc
from datetime import date

from contracts.domain.instrument import Instrument
from dsp_platform import DSPPlatform


class TestPerformanceSmoke:
    def test_startup_and_analyze_latency(
        self, instrument: Instrument, build_platform
    ) -> None:
        start = time.perf_counter()
        platform: DSPPlatform = build_platform()
        startup_s = time.perf_counter() - start

        request = platform.make_request(
            instrument, date(2024, 1, 1), date(2024, 6, 1)
        )
        analyze_start = time.perf_counter()
        result = platform.analyze(request)
        analyze_s = time.perf_counter() - analyze_start

        # Generous offline bounds — document typical values in README.
        assert startup_s < 2.0
        assert analyze_s < 1.0
        assert result is not None

    def test_basic_memory_footprint(
        self, instrument: Instrument, build_platform
    ) -> None:
        tracemalloc.start()
        platform = build_platform()
        platform.analyze(
            platform.make_request(instrument, date(2024, 1, 1), date(2024, 6, 1))
        )
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        # Offline fake pipeline should stay well under 50 MiB peak delta.
        assert peak < 50 * 1024 * 1024
