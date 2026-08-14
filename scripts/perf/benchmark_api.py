#!/usr/bin/env python3
"""EPIC-P7.3 — API latency benchmark (health surfaces only; no analyse contract changes)."""

from __future__ import annotations

import argparse
import json
import statistics
import time
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


def _bench_testclient(iterations: int) -> dict:
    bootstrap_monorepo()
    from fastapi.testclient import TestClient

    from api_platform.api.app import create_app

    app = create_app()
    client = TestClient(app)
    paths = ["/health", "/health/live", "/health/ready", "/metrics"]
    results: dict[str, list[float]] = {p: [] for p in paths}

    for _ in range(5):
        client.get("/health")

    for _ in range(iterations):
        for path in paths:
            t0 = time.perf_counter()
            resp = client.get(path)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            assert resp.status_code == 200, f"{path} -> {resp.status_code}"
            results[path].append(elapsed_ms)

    summary = {}
    for path, samples in results.items():
        ordered = sorted(samples)
        summary[path] = {
            "n": len(ordered),
            "mean_ms": round(statistics.fmean(ordered), 3),
            "p50_ms": round(_percentile(ordered, 50), 3),
            "p95_ms": round(_percentile(ordered, 95), 3),
            "p99_ms": round(_percentile(ordered, 99), 3),
            "max_ms": round(max(ordered), 3),
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument(
        "--out",
        default=str(ROOT / "docs" / "perf" / "api_benchmark.json"),
    )
    args = parser.parse_args()

    summary = _bench_testclient(args.iterations)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "epic": "P7.3",
        "mode": "fastapi_testclient",
        "iterations": args.iterations,
        "endpoints": summary,
    }
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"[OK] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
