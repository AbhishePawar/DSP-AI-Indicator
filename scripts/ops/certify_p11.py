#!/usr/bin/env python3
"""Offline certification checks — living baseline (P6.1 commercial RC versions)."""

from __future__ import annotations

import json
import os
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

    required_files = [
        ROOT / "docker" / "backend" / "Dockerfile",
        ROOT / "docker" / "frontend" / "Dockerfile",
        ROOT / "docker" / "docker-compose.yml",
        ROOT / "docker" / "docker-compose.prod.yml",
        ROOT / ".env.production.example",
        ROOT / "scripts" / "validate_env.py",
        ROOT / "docs" / "P1_1_PRODUCTION_DEPLOYMENT_CERTIFICATION.md",
        ROOT / "docs" / "P5_1_CLOSED_BETA_LAUNCH.md",
        ROOT / "docs" / "P5_2_BETA_STABILISATION.md",
        ROOT / "docs" / "P6_1_COMMERCIAL_READINESS.md",
        ROOT / "PRODUCTION_VERSION_MANIFEST.json",
        ROOT / "apps" / "web" / "VERSION_MANIFEST.json",
        ROOT / "packages" / "admin" / "src" / "admin" / "beta_programme.py",
    ]
    for path in required_files:
        passed &= _ok(f"artifact exists: {path.relative_to(ROOT)}", path.is_file())

    init_py = (
        ROOT / "packages" / "dsp_platform" / "src" / "dsp_platform" / "__init__.py"
    ).read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', init_py)
    be_ver = m.group(1) if m else ""
    passed &= _ok("dsp_platform version", be_ver == "1.6.0", be_ver)

    fe_manifest = json.loads(
        (ROOT / "apps" / "web" / "VERSION_MANIFEST.json").read_text(encoding="utf-8")
    )
    passed &= _ok(
        "frontend manifest 2.0.0-rc",
        fe_manifest.get("appVersion") == "2.0.0-rc"
        and fe_manifest.get("foundationEpic") == "P6.1",
        str(fe_manifest.get("appVersion")),
    )

    prod_manifest = json.loads(
        (ROOT / "PRODUCTION_VERSION_MANIFEST.json").read_text(encoding="utf-8")
    )
    passed &= _ok(
        "production manifest backend 1.6.0",
        prod_manifest.get("backendVersion") == "1.6.0",
        str(prod_manifest.get("backendVersion")),
    )
    passed &= _ok(
        "production manifest frontend 2.0.0-rc",
        prod_manifest.get("frontendVersion") == "2.0.0-rc",
        str(prod_manifest.get("frontendVersion")),
    )

    env = os.environ.copy()
    env.update(
        {
            "DSP_ENVIRONMENT": "production",
            "DSP_JWT_SECRET": "unit-test-strong-secret-key-32b",
            "DSP_CORS_ORIGINS": "https://app.example.com",
            "DSP_ENABLE_SECURITY": "true",
            "DSP_REQUIRE_ADMIN_AUTH": "true",
            "DSP_RATE_LIMIT_ENABLED": "true",
            "DSP_HSTS_ENABLED": "true",
            "DSP_INDIA_TIMEZONE": "Asia/Kolkata",
            "DSP_INDIA_CURRENCY": "INR",
            "DSP_APP_VERSION": "1.6.0",
        }
    )
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_env.py"), "production"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    passed &= _ok("validate_env production synthetic", proc.returncode == 0)

    print("CERTIFICATION", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
