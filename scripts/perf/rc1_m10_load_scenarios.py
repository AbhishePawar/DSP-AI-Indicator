#!/usr/bin/env python3
"""RC1 Milestone 10 — load scenario pointer script.

Does not invent a new load engine. Invokes existing scripts/perf helpers
against production-ops and core research surfaces when a base URL is set.

Usage:
  DSP_LOAD_BASE_URL=http://127.0.0.1:8000 python scripts/perf/rc1_m10_load_scenarios.py
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request

SCENARIOS = (
    ("ops_health", "/api/v1/ops/health"),
    ("ops_status", "/api/v1/ops/status"),
    ("ops_version", "/api/v1/ops/version"),
    ("ops_dependencies", "/api/v1/ops/dependencies"),
    ("health_ready", "/api/v1/health/ready"),
    ("metrics", "/api/v1/metrics"),
)


def main() -> int:
    base = (os.environ.get("DSP_LOAD_BASE_URL") or "").rstrip("/")
    if not base:
        print("DSP_LOAD_BASE_URL unset — skipping live load (see scripts/perf/).")
        print("Existing tools: load_test.py, k6_health_load.js, soak_test.py")
        return 0

    failures = 0
    for name, path in SCENARIOS:
        url = f"{base}{path}"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                code = resp.getcode()
                print(f"PASS {name} {code} {url}")
                if code >= 500:
                    failures += 1
        except urllib.error.HTTPError as exc:
            print(f"HTTP {name} {exc.code} {url}")
            if exc.code >= 500:
                failures += 1
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {name} {url} :: {exc}")
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
