#!/usr/bin/env python3
"""EPIC-P8.0 — Offline GA certification & release-freeze gate.

Governance only. No analytical / API behaviour changes.
PASS requires prior living certifications, GA docs, freeze, and version alignment.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# GA-only certification — intentionally does NOT accept living RC identity.
sys.path.insert(0, str(ROOT / "scripts" / "release"))
from release_identity import GA_PROFILE  # noqa: E402

EXPECTED_BE = GA_PROFILE["backend"]
EXPECTED_FE = GA_PROFILE["frontend"]
EXPECTED_API = GA_PROFILE["api_contract"]
EXPECTED_EPIC = GA_PROFILE["epic"]
EXPECTED_CHANNEL = GA_PROFILE["channel"]
EXPECTED_DECISION = GA_PROFILE["decision"]


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    extra = f" — {detail}" if detail else ""
    print(f"[{mark}] {name}{extra}")
    return passed


def _run(script: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, out[-400:]


def main() -> int:
    passed = True

    docs = [
        "docs/GA_ARCHITECTURE_CERTIFICATION.md",
        "docs/GA_TECHNICAL_DEBT.md",
        "docs/RELEASE_FREEZE.md",
        "docs/P8_GENERAL_AVAILABILITY.md",
        "docs/OPERATIONAL_READINESS.md",
        "docs/PRODUCTION_RISK_REGISTER.md",
        "docs/P7_4_OPERATIONS_REPORT.md",
        "docs/P7_3_PERFORMANCE_REPORT.md",
        "docs/P7_PRODUCTION_CERTIFICATION.md",
        "docs/P6_1_COMMERCIAL_READINESS.md",
        "docs/ARCHITECTURE_GOVERNANCE.md",
        "docs/PRODUCT_CONSTITUTION.md",
        "docs/USER_TRUST_STANDARD.md",
        "docs/VERSION_MATRIX.md",
        "docs/VERSION_HISTORY.md",
        "README.md",
    ]
    for rel in docs:
        path = ROOT / rel
        passed &= _ok(f"doc {rel}", path.is_file() and path.stat().st_size > 200)

    freeze = (ROOT / "docs" / "RELEASE_FREEZE.md").read_text(encoding="utf-8")
    for needle in (
        "Frozen modules",
        "Permitted hotfix",
        "Version policy",
        "Branch strategy",
        "Emergency fix",
        "v2.0.0",
    ):
        passed &= _ok(f"freeze mentions {needle}", needle in freeze)

    debt = (ROOT / "docs" / "GA_TECHNICAL_DEBT.md").read_text(encoding="utf-8")
    for cat in ("Critical", "High", "Medium", "Low", "Deferred"):
        passed &= _ok(f"debt category {cat}", f"**{cat}**" in debt or f"| **{cat}**" in debt)

    ga = (ROOT / "docs" / "P8_GENERAL_AVAILABILITY.md").read_text(encoding="utf-8")
    for needle in (
        "Platform Audit",
        "Overall Engineering Score",
        "GA Readiness Score",
        "GO WITH CONDITIONS",
        "PASS WITH CONDITIONS",
    ):
        passed &= _ok(f"GA report mentions {needle}", needle in ga)

    arch = (ROOT / "docs" / "GA_ARCHITECTURE_CERTIFICATION.md").read_text(encoding="utf-8")
    for needle in (
        "Thin Client",
        "API Freeze",
        "Research Mode",
        "Product Constitution",
        "User Trust Standard",
    ):
        passed &= _ok(f"architecture cert {needle}", needle in arch)

    # Versions
    init_py = (
        ROOT / "packages" / "dsp_platform" / "src" / "dsp_platform" / "__init__.py"
    ).read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', init_py)
    passed &= _ok("backend 2.0.0", (m.group(1) if m else "") == EXPECTED_BE)

    fe = json.loads((ROOT / "apps" / "web" / "VERSION_MANIFEST.json").read_text(encoding="utf-8"))
    passed &= _ok("frontend 2.0.0", fe.get("appVersion") == EXPECTED_FE)
    passed &= _ok("epic P8.0", fe.get("foundationEpic") == EXPECTED_EPIC)
    passed &= _ok("api v1.0.0", fe.get("apiContract") == EXPECTED_API)
    passed &= _ok("channel ga-candidate", fe.get("channel") == EXPECTED_CHANNEL)

    ver_ts = (ROOT / "apps" / "web" / "src" / "foundation" / "version.ts").read_text(
        encoding="utf-8"
    )
    passed &= _ok(
        "API_CONTRACT_TARGET frozen",
        f'API_CONTRACT_TARGET = "{EXPECTED_API}"' in ver_ts,
    )
    passed &= _ok(
        "backend target 2.0.0",
        f'BACKEND_PLATFORM_TARGET = "dsp_platform@{EXPECTED_BE}"' in ver_ts,
    )

    prod = json.loads((ROOT / "PRODUCTION_VERSION_MANIFEST.json").read_text(encoding="utf-8"))
    passed &= _ok("prod milestone P8.0", prod.get("milestone") == EXPECTED_EPIC)
    passed &= _ok("prod backend 2.0.0", prod.get("backendVersion") == EXPECTED_BE)
    passed &= _ok("prod frontend 2.0.0", prod.get("frontendVersion") == EXPECTED_FE)
    passed &= _ok("prod channel ga-candidate", prod.get("channel") == EXPECTED_CHANNEL)
    passed &= _ok(
        f"prod decision {EXPECTED_DECISION}",
        prod.get("decision") == EXPECTED_DECISION,
        str(prod.get("decision")),
    )

    # Prior living certifications
    prior = [
        "scripts/ops/certify_p7.py",
        "scripts/ops/certify_p7_2.py",
        "scripts/ops/certify_p7_3.py",
        "scripts/ops/certify_p7_4.py",
        "scripts/release/validate_release.py",
    ]
    for rel in prior:
        ok, detail = _run(ROOT / rel)
        passed &= _ok(f"prior {rel}", ok, detail.replace("\n", " ")[:180])

    # Perf / ops artifacts still present (no regressions of evidence)
    for rel in (
        "docs/perf/api_benchmark.json",
        "docs/perf/load_test_results.json",
        "docker/prometheus/alerts.yml",
        "docker/grafana/dashboards/dsp-operations.json",
        "docs/RELEASE_FREEZE.md",
    ):
        path = ROOT / rel
        passed &= _ok(f"artifact {rel}", path.is_file() and path.stat().st_size > 40)

    print("CERTIFICATION_P8", "PASS" if passed else "FAIL")
    print(
        "GA_DECISION",
        "PASS_WITH_CONDITIONS" if passed else "FAIL",
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
