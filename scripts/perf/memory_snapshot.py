#!/usr/bin/env python3
"""EPIC-P7.3 — Startup import + memory snapshot (cross-platform)."""

from __future__ import annotations

import argparse
import json
import time
import tracemalloc
from pathlib import Path

from _path import ROOT, bootstrap_monorepo


def _rss_mb() -> float | None:
    try:
        import resource  # Unix

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if usage > 10_000_000:
            return round(usage / (1024 * 1024), 2)
        return round(usage / 1024, 2)
    except Exception:
        try:
            import psutil  # optional

            return round(psutil.Process().memory_info().rss / (1024 * 1024), 2)
        except Exception:
            return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(ROOT / "docs" / "perf" / "memory_snapshot.json"),
    )
    args = parser.parse_args()

    bootstrap_monorepo()
    tracemalloc.start()
    t0 = time.perf_counter()
    from api_platform.api.app import create_app  # noqa: WPS433

    import_ms = (time.perf_counter() - t0) * 1000.0
    t1 = time.perf_counter()
    app = create_app()
    create_ms = (time.perf_counter() - t1) * 1000.0
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    growth = []
    baseline = peak
    for _i in range(3):
        tracemalloc.start()
        create_app()
        _c, p = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        growth.append(round((p - baseline) / (1024 * 1024), 3))

    payload = {
        "epic": "P7.3",
        "import_app_module_ms": round(import_ms, 2),
        "create_app_ms": round(create_ms, 2),
        "tracemalloc_current_mb": round(current / (1024 * 1024), 3),
        "tracemalloc_peak_mb": round(peak / (1024 * 1024), 3),
        "rss_max_mb_approx": _rss_mb(),
        "repeat_create_peak_delta_mb": growth,
        "routes_registered": len(getattr(app, "routes", [])),
        "notes": [
            "No analyse engines invoked.",
            "RSS optional on Windows without psutil.",
            "Large positive deltas across repeats warrant leak investigation.",
        ],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"[OK] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
