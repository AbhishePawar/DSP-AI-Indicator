"""P8.0 — GA certification tests (governance only).

Living product is RC (EPS-003). GA certification must remain strict and must
not pass until manifests are promoted to ga-candidate / P8.0.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_dsp_platform_version_is_2_0_0() -> None:
    from dsp_platform import __version__

    assert __version__ == "2.0.0"


def test_ga_release_profile_preserved() -> None:
    sys.path.insert(0, str(ROOT / "scripts" / "release"))
    from release_identity import GA_PROFILE, RC_PROFILE

    assert GA_PROFILE["epic"] == "P8.0"
    assert GA_PROFILE["frontend"] == "2.0.0"
    assert GA_PROFILE["channel"] == "ga-candidate"
    assert GA_PROFILE["decision"] == "GO_WITH_CONDITIONS"
    assert RC_PROFILE["epic"] == "EPS-003"
    assert RC_PROFILE["frontend"] == "2.0.0-rc.1"
    assert RC_PROFILE["channel"] == "rc"


def test_certify_p8_requires_ga_identity() -> None:
    """Living RC must not satisfy GA certification."""
    script = ROOT / "scripts" / "ops" / "certify_p8.py"
    assert script.is_file()
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, out
    assert "CERTIFICATION_P8 FAIL" in out
    assert "GA_DECISION FAIL" in out


def test_release_freeze_document() -> None:
    text = (ROOT / "docs" / "RELEASE_FREEZE.md").read_text(encoding="utf-8")
    assert "Frozen modules" in text
    assert "Emergency fix" in text
    assert "v2.0.0" in text


def test_production_manifest_is_rc_not_ga() -> None:
    data = json.loads(
        (ROOT / "PRODUCTION_VERSION_MANIFEST.json").read_text(encoding="utf-8")
    )
    assert data["milestone"] == "EPS-003"
    assert data["backendVersion"] == "2.0.0"
    assert data["frontendVersion"] == "2.0.0-rc.1"
    assert data["channel"] == "rc"
    assert data["releaseFreeze"] is True
    assert data["decision"] == "RELEASE_CANDIDATE"
