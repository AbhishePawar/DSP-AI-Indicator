"""P8.0 — GA certification tests (governance only)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_dsp_platform_version_is_2_0_0() -> None:
    from dsp_platform import __version__

    assert __version__ == "2.0.0"


def test_certify_p8_script_passes() -> None:
    script = ROOT / "scripts" / "ops" / "certify_p8.py"
    assert script.is_file()
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_release_freeze_document() -> None:
    text = (ROOT / "docs" / "RELEASE_FREEZE.md").read_text(encoding="utf-8")
    assert "Frozen modules" in text
    assert "Emergency fix" in text
    assert "v2.0.0" in text


def test_production_manifest_ga() -> None:
    data = json.loads((ROOT / "PRODUCTION_VERSION_MANIFEST.json").read_text(encoding="utf-8"))
    assert data["milestone"] == "P8.0"
    assert data["backendVersion"] == "2.0.0"
    assert data["frontendVersion"] == "2.0.0"
    assert data["channel"] == "ga-candidate"
    assert data["releaseFreeze"] is True
    assert data["decision"] == "GO_WITH_CONDITIONS"
