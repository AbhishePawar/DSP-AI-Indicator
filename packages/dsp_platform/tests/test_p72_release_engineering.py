"""P7.2 — Release engineering certification tests (ops only)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_validate_release_passes() -> None:
    script = ROOT / "scripts" / "release" / "validate_release.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_certify_p7_2_passes() -> None:
    script = ROOT / "scripts" / "ops" / "certify_p7_2.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_release_package_artifacts_exist() -> None:
    for name in [
        "RELEASE_NOTES.md",
        "RELEASE_CHECKLIST.md",
        "BUILD_MANIFEST.json",
        "CHECKSUMS.sha256",
        "sbom.json",
    ]:
        path = ROOT / "release" / name
        assert path.is_file() and path.stat().st_size > 20
