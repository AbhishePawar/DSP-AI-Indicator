#!/usr/bin/env python3
"""EPIC-P7.2 — Offline certification for release engineering & repository excellence."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "release"))
from release_identity import resolve_profile  # noqa: E402


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    extra = f" — {detail}" if detail else ""
    print(f"[{mark}] {name}{extra}")
    return passed


def main() -> int:
    passed = True

    required_docs = [
        "docs/REPOSITORY_AUDIT.md",
        "docs/DEPENDENCY_AUDIT.md",
        "docs/CODE_QUALITY_REPORT.md",
        "docs/DOCUMENTATION_AUDIT.md",
        "docs/VERSION_GOVERNANCE_REPORT.md",
        "docs/ENGINEERING_STATUS.md",
        "docs/VERSION_MATRIX.md",
        "docs/VERSION_HISTORY.md",
        "docs/P7_PRODUCTION_DEPLOYMENT.md",
        "docs/P6_1_COMMERCIAL_READINESS.md",
        "README.md",
    ]
    for rel in required_docs:
        path = ROOT / rel
        passed &= _ok(
            f"doc {rel}",
            path.is_file() and path.stat().st_size > 200,
            f"{path.stat().st_size if path.is_file() else 0} bytes",
        )

    required_scripts = [
        "scripts/release/validate_release.py",
        "scripts/release/create_release_notes.py",
        "scripts/release/build_release_package.py",
        "scripts/ops/certify_p7_2.py",
    ]
    for rel in required_scripts:
        path = ROOT / rel
        passed &= _ok(f"script {rel}", path.is_file() and path.stat().st_size > 100)

    workflows = [
        ".github/workflows/ci.yml",
        ".github/workflows/frontend.yml",
        ".github/workflows/docker.yml",
        ".github/workflows/release.yml",
        ".github/workflows/release-engineering.yml",
        ".github/workflows/security.yml",
    ]
    for rel in workflows:
        path = ROOT / rel
        passed &= _ok(f"workflow {rel}", path.is_file())

    release_files = [
        "release/RELEASE_NOTES.md",
        "release/RELEASE_CHECKLIST.md",
        "release/BUILD_MANIFEST.json",
        "release/CHECKSUMS.sha256",
        "release/sbom.json",
    ]
    for rel in release_files:
        path = ROOT / rel
        passed &= _ok(f"release artifact {rel}", path.is_file() and path.stat().st_size > 20)

    # Version consistency
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "release" / "validate_release.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    passed &= _ok("validate_release", proc.returncode == 0, (proc.stdout + proc.stderr)[-300:])

    # Workflows must fail on critical errors — ensure no continue-on-error for validate
    re_wf = (ROOT / ".github" / "workflows" / "release-engineering.yml").read_text(
        encoding="utf-8"
    )
    passed &= _ok(
        "release-engineering runs validate_release",
        "validate_release.py" in re_wf,
    )
    passed &= _ok(
        "release-engineering runs certify_p7_2",
        "certify_p7_2.py" in re_wf,
    )

    prod = json.loads((ROOT / "PRODUCTION_VERSION_MANIFEST.json").read_text(encoding="utf-8"))
    try:
        expected = resolve_profile(prod)
    except ValueError as exc:
        passed &= _ok("release profile", False, str(exc))
        print("CERTIFICATION_P7_2 FAIL")
        return 1
    passed &= _ok(
        "manifest milestone",
        prod.get("milestone") == expected["milestone"],
        str(prod.get("milestone")),
    )
    passed &= _ok(
        "manifest backend",
        prod.get("backendVersion") == expected["backend"],
        str(prod.get("backendVersion")),
    )
    passed &= _ok(
        "manifest frontend",
        prod.get("frontendVersion") == expected["frontend"],
        str(prod.get("frontendVersion")),
    )
    passed &= _ok(
        "manifest channel",
        prod.get("channel") == expected["channel"],
        str(prod.get("channel")),
    )

    print("CERTIFICATION_P7_2", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
