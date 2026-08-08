#!/usr/bin/env python3
"""EPIC-P8.0 — Offline certification for performance engineering."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    extra = f" — {detail}" if detail else ""
    print(f"[{mark}] {name}{extra}")
    return passed


def main() -> int:
    passed = True

    docs = [
        "docs/PERFORMANCE_BACKEND.md",
        "docs/PERFORMANCE_FRONTEND.md",
        "docs/DATABASE_PERFORMANCE.md",
        "docs/P7_3_PERFORMANCE_REPORT.md",
        "docs/perf/api_benchmark.json",
        "docs/perf/load_test_results.json",
        "docs/perf/memory_snapshot.json",
    ]
    for rel in docs:
        path = ROOT / rel
        passed &= _ok(f"artifact {rel}", path.is_file() and path.stat().st_size > 50)

    scripts = [
        "scripts/perf/benchmark_api.py",
        "scripts/perf/load_test.py",
        "scripts/perf/memory_snapshot.py",
        "scripts/ops/certify_p7_3.py",
    ]
    for rel in scripts:
        passed &= _ok(f"script {rel}", (ROOT / rel).is_file())

    # Version alignment — living release profile (RC today; GA when promoted)
    sys.path.insert(0, str(ROOT / "scripts" / "release"))
    from release_identity import resolve_profile

    prod = json.loads(
        (ROOT / "PRODUCTION_VERSION_MANIFEST.json").read_text(encoding="utf-8")
    )
    try:
        expected = resolve_profile(prod)
    except ValueError as exc:
        passed &= _ok("release profile", False, str(exc))
        print("CERTIFICATION_P7_3 FAIL")
        return 1

    init_py = (
        ROOT / "packages" / "dsp_platform" / "src" / "dsp_platform" / "__init__.py"
    ).read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', init_py)
    passed &= _ok("backend", (m.group(1) if m else "") == expected["backend"])

    fe = json.loads((ROOT / "apps" / "web" / "VERSION_MANIFEST.json").read_text(encoding="utf-8"))
    passed &= _ok("frontend", fe.get("appVersion") == expected["frontend"])
    passed &= _ok("epic", fe.get("foundationEpic") == expected["epic"])
    passed &= _ok("api", fe.get("apiContract") == expected["api_contract"])

    # No analyse contract drift
    ver_ts = (ROOT / "apps" / "web" / "src" / "foundation" / "version.ts").read_text(
        encoding="utf-8"
    )
    passed &= _ok(
        "API_CONTRACT_TARGET frozen",
        f'API_CONTRACT_TARGET = "{expected["api_contract"]}"' in ver_ts,
    )

    # Benchmark sanity: zero failures in load test + finite p99
    load = json.loads((ROOT / "docs" / "perf" / "load_test_results.json").read_text(encoding="utf-8"))
    scenarios = load.get("scenarios") or []
    passed &= _ok("load scenarios present", len(scenarios) >= 4)
    for sc in scenarios:
        passed &= _ok(
            f"load users={sc.get('users')} zero failures",
            sc.get("failures", 1) == 0,
            str(sc.get("failures")),
        )
        passed &= _ok(
            f"load users={sc.get('users')} p99 finite",
            isinstance(sc.get("p99_ms"), (int, float)) and sc["p99_ms"] > 0,
        )

    api = json.loads((ROOT / "docs" / "perf" / "api_benchmark.json").read_text(encoding="utf-8"))
    ready = (api.get("endpoints") or {}).get("/health/ready") or {}
    passed &= _ok(
        "ready p99 under 100ms (sequential)",
        float(ready.get("p99_ms", 999)) < 100,
        str(ready.get("p99_ms")),
    )

    # Docker runtime optimisation markers
    dockerfile = (ROOT / "docker" / "backend" / "Dockerfile").read_text(encoding="utf-8")
    passed &= _ok("docker uses .[api]", ".[api]" in dockerfile)
    passed &= _ok("PYTHONOPTIMIZE", "PYTHONOPTIMIZE=1" in dockerfile)

    next_cfg = (ROOT / "apps" / "web" / "next.config.ts").read_text(encoding="utf-8")
    passed &= _ok("static cache header", "max-age=31536000" in next_cfg)
    passed &= _ok("optimizePackageImports", "optimizePackageImports" in next_cfg)

    # validate_release living gate
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "release" / "validate_release.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    passed &= _ok("validate_release", proc.returncode == 0, (proc.stdout + proc.stderr)[-200:])

    print("CERTIFICATION_P7_3", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
