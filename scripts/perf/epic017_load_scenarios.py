#!/usr/bin/env python3
"""EPIC-017 — synthetic concurrency scenarios (100/500/1000/5000 users).

Runs in-process FastAPI TestClient load (same approach as P7.3) when a live
cluster is unavailable. Documents honest limits: not multi-host production load.

Usage (repo root):
  python scripts/perf/epic017_load_scenarios.py
  python scripts/perf/epic017_load_scenarios.py --scenarios 100,500 --requests-per-user 3
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from load_test import _run_scenario  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenarios",
        default="100,500,1000,5000",
        help="Comma-separated virtual user counts",
    )
    parser.add_argument("--requests-per-user", type=int, default=3)
    parser.add_argument(
        "--out",
        default=str(ROOT / "docs" / "operations" / "load_test_results_epic017.json"),
    )
    args = parser.parse_args()
    scenarios = [int(x.strip()) for x in args.scenarios.split(",") if x.strip()]

    results = []
    for users in scenarios:
        # Cap thread pool pressure for large synthetic counts
        print(f"[epic017-load] users={users} rpu={args.requests_per_user}")
        result = _run_scenario(users, args.requests_per_user)
        result["methodology"] = (
            "In-process FastAPI TestClient — synthetic concurrency, "
            "not multi-node production cluster load."
        )
        if users >= 1000:
            result["caveat"] = (
                "High VU counts share one process; results indicate relative "
                "pressure, not absolute production capacity."
            )
        results.append(result)

    payload = {
        "epic": "017",
        "title": "Production performance validation (synthetic)",
        "methodology": "scripts/perf/epic017_load_scenarios.py via TestClient",
        "live_cluster": False,
        "scenarios": results,
        "bottlenecks_hypotheses": [
            "Single-process GIL / TestClient shared app — understates horizontal scale",
            "DB connection pool saturation under real Postgres (not exercised here)",
            "Redis rate-limit / session ports dominate under authenticated traffic",
            "Research/valuation paths excluded by design (architecture freeze)",
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
