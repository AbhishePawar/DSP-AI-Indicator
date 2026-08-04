#!/usr/bin/env python3
"""EPIC-019A — Synthetic soak harness for ops / CI evidence.

Default duration is short (CI-safe). For 8–24h ops runs:

  python scripts/perf/soak_test.py --hours 8 --interval-seconds 15

Honest metrics only — never invents 8h results. Samples /health (and optional
extra paths), records RSS approx when psutil available, writes JSON + summary.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "perf"))
from _path import bootstrap_monorepo  # noqa: E402

bootstrap_monorepo()


def _rss_mb() -> float | None:
    try:
        import psutil  # type: ignore

        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:
        return None


def _sample_health(client: Any, path: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        resp = client.get(path)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return {
            "ok": resp.status_code < 500,
            "status": resp.status_code,
            "elapsed_ms": round(elapsed_ms, 2),
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 — soak must continue
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return {
            "ok": False,
            "status": None,
            "elapsed_ms": round(elapsed_ms, 2),
            "error": str(exc),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="DSP synthetic soak test")
    parser.add_argument("--hours", type=float, default=0.05, help="Duration hours (default ~3 min)")
    parser.add_argument("--minutes", type=float, default=None, help="Override duration in minutes")
    parser.add_argument("--interval-seconds", type=float, default=5.0)
    parser.add_argument(
        "--paths",
        default="/health,/health/ready,/health/live",
        help="Comma-separated paths relative to app",
    )
    parser.add_argument(
        "--out",
        default=str(ROOT / "docs" / "testing" / "soak_test_results_epic019a.json"),
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="If set, use HTTP against live URL instead of in-process TestClient",
    )
    args = parser.parse_args()

    duration_s = (
        args.minutes * 60.0 if args.minutes is not None else args.hours * 3600.0
    )
    paths = [p.strip() for p in args.paths.split(",") if p.strip()]
    started = datetime.now(timezone.utc)
    deadline = time.monotonic() + duration_s

    samples: list[dict[str, Any]] = []
    failures = 0
    client: Any
    mode: str

    if args.base_url:
        import urllib.request

        mode = "http"
        base = args.base_url.rstrip("/")

        class _HttpClient:
            def get(self, path: str) -> Any:
                url = f"{base}{path}"
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310

                    class R:
                        status_code = resp.status

                    return R()

        client = _HttpClient()
    else:
        mode = "testclient"
        from fastapi.testclient import TestClient

        from api_platform.api.app import create_app

        app = create_app()
        client = TestClient(app)

    tracemalloc.start()
    rss_start = _rss_mb()
    current_start, peak_start = tracemalloc.get_traced_memory()

    while time.monotonic() < deadline:
        row: dict[str, Any] = {
            "t": datetime.now(timezone.utc).isoformat(),
            "paths": {},
            "rss_mb": _rss_mb(),
        }
        for path in paths:
            result = _sample_health(client, path)
            row["paths"][path] = result
            if not result["ok"]:
                failures += 1
        samples.append(row)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(args.interval_seconds, max(0.1, remaining)))

    current_end, peak_end = tracemalloc.get_traced_memory()
    rss_end = _rss_mb()
    ended = datetime.now(timezone.utc)
    wall_s = (ended - started).total_seconds()

    report = {
        "epic": "019A",
        "mode": mode,
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "requested_duration_seconds": duration_s,
        "wall_seconds": round(wall_s, 2),
        "interval_seconds": args.interval_seconds,
        "paths": paths,
        "sample_count": len(samples),
        "failures": failures,
        "live_cluster": False,
        "redis_observed": False,
        "postgres_observed": False,
        "memory": {
            "tracemalloc_current_start_kb": round(current_start / 1024, 2),
            "tracemalloc_current_end_kb": round(current_end / 1024, 2),
            "tracemalloc_peak_kb": round(peak_end / 1024, 2),
            "rss_start_mb": rss_start,
            "rss_end_mb": rss_end,
        },
        "honest_claim": (
            "PARTIAL synthetic soak — not multi-node 8–24h production certification"
            if wall_s < 8 * 3600
            else "Long soak wall-clock met locally; still not live cluster certification"
        ),
        "samples": samples,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(out),
                "wall_seconds": report["wall_seconds"],
                "sample_count": report["sample_count"],
                "failures": failures,
                "honest_claim": report["honest_claim"],
            },
            indent=2,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
