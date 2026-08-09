#!/usr/bin/env python3
"""P1-10 — run authenticity hard-fail suite and exit non-zero on any violation.

Aggregates P0/P1 authenticity contracts + dedicated P1-10 codes.
Reuses P1-09 API critical journey (does not claim G2 live evidence).

Soft-fail / swallowed failures are forbidden.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "artifacts" / "p110_authenticity_ci_summary.json"

# Curated authenticity hard-fail modules (merge/release blocking).
TARGETS = [
    "packages/api_platform/tests/test_p110_authenticity_hard_fail.py",
    "packages/api_platform/tests/test_p103_connector_boot.py",
    "packages/data_engine/tests/test_p103_production_connectors.py",
    "packages/api_platform/tests/test_p005_authz.py",
    "packages/api_platform/tests/test_p105_buffett_authority.py",
    "packages/api_platform/tests/test_p106_investment_provenance.py",
    "packages/dsp_platform/tests/test_p101_authenticated_valuation.py",
    "packages/dsp_platform/tests/test_p105_buffett_authority.py",
    "packages/api_platform/tests/test_p109_critical_investment_journey.py",
]


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *TARGETS,
        "-q",
        "--tb=short",
        "--import-mode=importlib",
        "-p",
        "no:cov",
    ]
    print("P1-10 authenticity hard-fail suite:", file=sys.stderr)
    for target in TARGETS:
        print(f"  - {target}", file=sys.stderr)
    print(" ".join(cmd), file=sys.stderr)

    completed = subprocess.run(cmd, cwd=ROOT, check=False)
    ok = completed.returncode == 0

    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "ok": ok,
        "gate": "P1-10",
        "g2_claim": False,
        "evidence_class_note": "fixture/dev paths remain test_fixture; never live vendor",
        "exit_code": completed.returncode,
        "targets": TARGETS,
        "hard_fail": True,
        "soft_fail_forbidden": True,
    }
    EVIDENCE.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if not ok:
        print(
            "AUTHENTICITY VIOLATION — CI FAIL — RELEASE BLOCKED (P1-10)",
            file=sys.stderr,
        )
        return completed.returncode or 1

    print("P1-10 authenticity hard-fail suite PASS", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
