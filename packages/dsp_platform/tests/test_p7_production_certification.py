"""P7.0 — Production infrastructure certification (ops only)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_dsp_platform_version_is_2_0_0() -> None:
    from dsp_platform import __version__

    assert __version__ == "2.0.0"


def test_certify_p7_script_passes() -> None:
    script = ROOT / "scripts" / "ops" / "certify_p7.py"
    assert script.is_file()
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_production_artifacts_exist() -> None:
    for rel in [
        ("docker", "docker-compose.production.yml"),
        ("docker", "Caddyfile"),
        ("docker", "prometheus.yml"),
        ("scripts", "deploy_production.sh"),
        ("scripts", "rollback_production.sh"),
        ("scripts", "backup_database.sh"),
        ("scripts", "restore_database.sh"),
        ("docs", "P7_PRODUCTION_DEPLOYMENT.md"),
        ("docs", "P7_PRODUCTION_CERTIFICATION.md"),
    ]:
        path = ROOT.joinpath(*rel)
        assert path.is_file(), path
        assert path.stat().st_size > 100


def test_caddyfile_security_headers() -> None:
    text = (ROOT / "docker" / "Caddyfile").read_text(encoding="utf-8")
    assert "Strict-Transport-Security" in text
    assert "X-Content-Type-Options" in text
    assert "reverse_proxy api:8000" in text
