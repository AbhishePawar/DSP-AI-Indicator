#!/usr/bin/env python3
"""EPIC-P7.3 — Concurrent load scenarios against health endpoints (ops only)."""

from __future__ import annotations

import argparse
import json
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from _path import ROOT, bootstrap_monorepo


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def _run_scenario(users: int, requests_per_user: int) -> dict:
    bootstrap_monorepo()
    from fastapi.testclient import TestClient

    from api_platform.api.app import create_app

    app = create_app()
    client = TestClient(app)
    lock = threading.Lock()
    latencies: list[float] = []
    failures = 0

    def worker(_: int) -> tuple[list[float], int]:
        local: list[float] = []
        local_fail = 0
        for _i in range(requests_per_user):
            t0 = time.perf_counter()
            try:
                resp = client.get("/health/ready")
                ok = resp.status_code == 200
            except Exception:
                ok = False
            local.append((time.perf_counter() - t0) * 1000.0)
            if not ok:
                local_fail += 1
        return local, local_fail

    t_wall0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=min(users, 64)) as pool:
        futures = [pool.submit(worker, i) for i in range(users)]
        for fut in as_completed(futures):
            samples, fail_n = fut.result()
            with lock:
                latencies.extend(samples)
                failures += fail_n
    wall_s = time.perf_counter() - t_wall0
    ordered = sorted(latencies)
    total = len(ordered) or 1
    return {
        "users": users,
        "requests": total,
        "failures": failures,
        "error_rate": round(failures / total, 4),
        "wall_seconds": round(wall_s, 3),
        "throughput_rps": round(total / wall_s, 2) if wall_s > 0 else 0.0,
        "mean_ms": round(statistics.fmean(ordered), 3) if ordered else 0.0,
        "p50_ms": round(_percentile(ordered, 50), 3),
        "p95_ms": round(_percentile(ordered, 95), 3),
        "p99_ms": round(_percentile(ordered, 99), 3),
        "max_ms": round(max(ordered), 3) if ordered else 0.0,
        "note": "In-process TestClient concurrency (not multi-host).",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests-per-user", type=int, default=5)
    parser.add_argument("--scenarios", default="10,50,100,500")
    parser.add_argument(
        "--out",
        default=str(ROOT / "docs" / "perf" / "load_test_results.json"),
    )
    args = parser.parse_args()
    scenarios = [int(x.strip()) for x in args.scenarios.split(",") if x.strip()]

    results = []
    for users in scenarios:
        print(f"[load] scenario users={users}")
        results.append(_run_scenario(users, args.requests_per_user))

    payload = {"epic": "P7.3", "scenarios": results}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"[OK] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
