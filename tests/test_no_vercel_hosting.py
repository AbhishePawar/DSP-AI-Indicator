"""Current-tree Vercel hosting must stay at ACTIVE_DEPENDENCY = 0."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SCANNER = _REPO / "scripts" / "ops" / "assert_no_vercel_hosting.py"
_PLAYWRIGHT = _REPO / "apps" / "web" / "playwright.config.ts"
_DEVSECOPS = _REPO / ".github" / "workflows" / "devsecops.yml"
_FRONTEND_CI = _REPO / ".github" / "workflows" / "frontend.yml"
_CLOUDBUILD_WEB = _REPO / "cloudbuild-frontend.yaml"
_HOSTING_HINTS = ("vercel.app", "vercel.com")


def _has_hosting_url(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in _HOSTING_HINTS)


def test_scanner_reports_zero_active_dependencies() -> None:
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


def test_playwright_uses_local_ci_server() -> None:
    text = _PLAYWRIGHT.read_text(encoding="utf-8")
    assert 'process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000"' in text
    assert "prepare-standalone-static.mjs" in text
    assert not _has_hosting_url(text)


def test_devsecops_playwright_does_not_wait_on_external_preview() -> None:
    text = _DEVSECOPS.read_text(encoding="utf-8")
    assert "PLAYWRIGHT_BASE_URL: http://127.0.0.1:3000" in text
    assert not _has_hosting_url(text)
    assert "VERCEL_TOKEN" not in text


def test_frontend_ci_has_no_hosting_cli() -> None:
    text = _FRONTEND_CI.read_text(encoding="utf-8")
    assert not _has_hosting_url(text)
    assert "VERCEL_TOKEN" not in text
    assert "npm run build" in text


def test_frontend_deploy_path_is_cloud_run() -> None:
    text = _CLOUDBUILD_WEB.read_text(encoding="utf-8")
    assert "dsp-ai-indicator-web" in text
    assert "gcr.io/cloud-builders/docker" in text
    assert "vercel" not in text.lower()


def test_no_vercel_json_in_repo() -> None:
    assert not (_REPO / "vercel.json").exists()
