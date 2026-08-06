"""P1.1 — Production deployment certification (ops only)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_dsp_platform_version_is_2_0_0() -> None:
    from dsp_platform import __version__

    assert __version__ == "2.0.0"


def test_certify_p11_script_passes() -> None:
    script = ROOT / "scripts" / "ops" / "certify_p11.py"
    assert script.is_file()
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_production_manifest_decision() -> None:
    import json

    data = json.loads((ROOT / "PRODUCTION_VERSION_MANIFEST.json").read_text(encoding="utf-8"))
    assert data["backendVersion"] == "2.0.0"
    assert data["frontendVersion"] == "2.0.0"
    assert data["decision"] == "GO_WITH_CONDITIONS"
    assert data["apiContract"] == "v1.0.0"
