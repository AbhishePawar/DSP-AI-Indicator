"""P8.0 — Operations / observability certification tests (ops only)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_dsp_platform_version_is_2_0_0() -> None:
    from dsp_platform import __version__

    assert __version__ == "2.0.0"


def test_certify_p7_4_script_passes() -> None:
    script = ROOT / "scripts" / "ops" / "certify_p7_4.py"
    assert script.is_file()
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_operations_docs_exist() -> None:
    for name in [
        "OPERATIONS_DASHBOARD.md",
        "ALERTING_CONFIGURATION.md",
        "DISASTER_RECOVERY.md",
        "OPERATIONS_RUNBOOK.md",
        "LOGGING_REPORT.md",
        "OPERATIONAL_READINESS.md",
        "PRODUCTION_RISK_REGISTER.md",
        "P7_4_OPERATIONS_REPORT.md",
    ]:
        path = ROOT / "docs" / name
        assert path.is_file() and path.stat().st_size > 200


def test_alert_rules_cover_required_classes() -> None:
    text = (ROOT / "docker" / "prometheus" / "alerts.yml").read_text(encoding="utf-8")
    for name in [
        "DspApiUnavailable",
        "DspHighLatency",
        "DspHighErrorRate",
        "DspDatabaseUnavailable",
        "DspRedisUnavailable",
        "DspLowDiskSpace",
        "DspHighCpu",
        "DspHighMemory",
    ]:
        assert name in text
