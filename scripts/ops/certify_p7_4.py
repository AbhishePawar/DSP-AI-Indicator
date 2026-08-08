#!/usr/bin/env python3
"""EPIC-P8.0 — Offline certification for production operations & observability."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    extra = f" — {detail}" if detail else ""
    print(f"[{mark}] {name}{extra}")
    return passed


def main() -> int:
    passed = True

    docs = [
        "docs/OPERATIONS_DASHBOARD.md",
        "docs/ALERTING_CONFIGURATION.md",
        "docs/DISASTER_RECOVERY.md",
        "docs/OPERATIONS_RUNBOOK.md",
        "docs/LOGGING_REPORT.md",
        "docs/OPERATIONAL_READINESS.md",
        "docs/PRODUCTION_RISK_REGISTER.md",
        "docs/P7_4_OPERATIONS_REPORT.md",
    ]
    for rel in docs:
        path = ROOT / rel
        passed &= _ok(f"doc {rel}", path.is_file() and path.stat().st_size > 200)

    configs = [
        "docker/prometheus.yml",
        "docker/prometheus/alerts.yml",
        "docker/alertmanager.yml",
        "docker/grafana/dashboards/dsp-operations.json",
        "docker/grafana/provisioning/datasources/datasource.yml",
        "docker/grafana/provisioning/dashboards/dashboards.yml",
    ]
    for rel in configs:
        path = ROOT / rel
        passed &= _ok(f"config {rel}", path.is_file() and path.stat().st_size > 50)

    scripts = [
        "scripts/ops/certify_p7_4.py",
        "scripts/ops/validate_recovery.py",
        "scripts/ops/backup_postgres_incremental.sh",
        "scripts/backup_database.sh",
        "scripts/restore_database.sh",
        "scripts/rollback_production.sh",
        "scripts/deploy_production.sh",
    ]
    for rel in scripts:
        passed &= _ok(f"script {rel}", (ROOT / rel).is_file())

    # Monitoring / alerting content gates
    alerts = (ROOT / "docker" / "prometheus" / "alerts.yml").read_text(encoding="utf-8")
    for needle in [
        "DspApiUnavailable",
        "DspHighLatency",
        "DspHighErrorRate",
        "DspDatabaseUnavailable",
        "DspRedisUnavailable",
        "DspLowDiskSpace",
        "DspHighCpu",
        "DspHighMemory",
    ]:
        passed &= _ok(f"alert {needle}", needle in alerts)

    prom = (ROOT / "docker" / "prometheus.yml").read_text(encoding="utf-8")
    passed &= _ok("prometheus rule_files", "alerts.yml" in prom)
    passed &= _ok("prometheus alertmanagers", "alertmanager" in prom)

    compose = (ROOT / "docker" / "docker-compose.production.yml").read_text(
        encoding="utf-8"
    )
    for svc in ("grafana:", "alertmanager:", "postgres-exporter:", "redis-exporter:"):
        passed &= _ok(f"compose {svc}", svc in compose)

    dash = (ROOT / "docker" / "grafana" / "dashboards" / "dsp-operations.json").read_text(
        encoding="utf-8"
    )
    for panel_hint in (
        "System Health",
        "CPU",
        "Memory",
        "Disk",
        "API Requests",
        "Response Time",
        "dsp_http_errors_total",
    ):
        passed &= _ok(f"dashboard mentions {panel_hint}", panel_hint in dash)

    readiness = (ROOT / "docs" / "OPERATIONAL_READINESS.md").read_text(encoding="utf-8")
    passed &= _ok("readiness has PASS/FAIL", "**PASS**" in readiness and "**FAIL" in readiness)

    risk = (ROOT / "docs" / "PRODUCTION_RISK_REGISTER.md").read_text(encoding="utf-8")
    passed &= _ok("risk register rows", risk.count("| OPS-") >= 10)

    dr = (ROOT / "docs" / "DISASTER_RECOVERY.md").read_text(encoding="utf-8")
    passed &= _ok("DR RPO", "RPO" in dr)
    passed &= _ok("DR RTO", "RTO" in dr)

    # Version alignment — living release profile (RC today; GA when promoted)
    sys.path.insert(0, str(ROOT / "scripts" / "release"))
    from release_identity import resolve_profile

    prod = json.loads(
        (ROOT / "PRODUCTION_VERSION_MANIFEST.json").read_text(encoding="utf-8")
    )
    try:
        expected = resolve_profile(prod)
    except ValueError as exc:
        passed &= _ok("release profile", False, str(exc))
        print("CERTIFICATION_P7_4 FAIL")
        return 1

    init_py = (
        ROOT / "packages" / "dsp_platform" / "src" / "dsp_platform" / "__init__.py"
    ).read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', init_py)
    passed &= _ok("backend", (m.group(1) if m else "") == expected["backend"])

    fe = json.loads((ROOT / "apps" / "web" / "VERSION_MANIFEST.json").read_text(encoding="utf-8"))
    passed &= _ok("frontend", fe.get("appVersion") == expected["frontend"])
    passed &= _ok("epic", fe.get("foundationEpic") == expected["epic"])
    passed &= _ok("api", fe.get("apiContract") == expected["api_contract"])

    ver_ts = (ROOT / "apps" / "web" / "src" / "foundation" / "version.ts").read_text(
        encoding="utf-8"
    )
    passed &= _ok(
        "API_CONTRACT_TARGET frozen",
        f'API_CONTRACT_TARGET = "{expected["api_contract"]}"' in ver_ts,
    )

    # No analyse contract markers altered in foundation
    passed &= _ok(
        "backend target",
        f'BACKEND_PLATFORM_TARGET = "dsp_platform@{expected["backend"]}"' in ver_ts,
    )

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "release" / "validate_release.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    passed &= _ok("validate_release", proc.returncode == 0, (proc.stdout + proc.stderr)[-200:])

    print("CERTIFICATION_P7_4", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
