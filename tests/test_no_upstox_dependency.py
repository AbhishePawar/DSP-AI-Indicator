"""Current-tree Upstox dependency must stay at ACTIVE_DEPENDENCY = 0."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SCANNER = _REPO / "scripts" / "ops" / "assert_no_upstox_dependency.py"
_CLOUDBUILD = _REPO / "cloudbuild.yaml"
_ENV_EXAMPLE = _REPO / ".env.example"
_ENV_PROD = _REPO / ".env.production.example"


def test_scanner_reports_zero_active_upstox_dependencies() -> None:
    proc = subprocess.run(
        [sys.executable, str(_SCANNER), "--json"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    assert report["ACTIVE_DEPENDENCY"] == 0, report
    assert report["ACTIVE_UPSTOX_REFERENCES"] == 0, report


def test_no_upstox_source_modules_on_disk() -> None:
    src = _REPO / "packages" / "data_engine" / "src" / "data_engine"
    leftovers = sorted(src.glob("upstox*.py"))
    assert leftovers == []


def test_cloudbuild_has_no_upstox_runtime() -> None:
    text = _CLOUDBUILD.read_text(encoding="utf-8")
    assert "DSP_INVESTMENT_DATA_PROVIDER=none" in text
    assert "DSP_INVESTMENT_DATA_PROVIDER=upstox" not in text
    assert "--remove-secrets=DSP_UPSTOX_ANALYTICS_TOKEN" in text
    assert "dsp-upstox-analytics-token" not in text
    assert "api.upstox.com" not in text
    update_secrets = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("- --update-secrets=")
    ]
    assert update_secrets
    assert all("DSP_UPSTOX_ANALYTICS_TOKEN=" not in line for line in update_secrets)


def test_env_examples_have_no_upstox_secrets() -> None:
    for path in (_ENV_EXAMPLE, _ENV_PROD):
        text = path.read_text(encoding="utf-8")
        assert "DSP_UPSTOX_" not in text
        assert "api.upstox.com" not in text
