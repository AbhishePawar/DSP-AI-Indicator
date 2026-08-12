#!/usr/bin/env python3
"""Offline certification checks — living production baseline (RC-aware).

Version expectations follow scripts/release/release_identity.py based on
PRODUCTION_VERSION_MANIFEST.channel (currently rc / EPS-003).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "release"))
from release_identity import resolve_profile  # noqa: E402


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
        ROOT / "docker" / "docker-compose.production.yml",
        ROOT / "docker" / "Caddyfile",
        ROOT / "docker" / "prometheus.yml",
        ROOT / ".env.production.example",
        ROOT / "scripts" / "validate_env.py",
        ROOT / "scripts" / "deploy_production.sh",
        ROOT / "scripts" / "rollback_production.sh",
        ROOT / "scripts" / "backup_database.sh",
        ROOT / "scripts" / "restore_database.sh",
        ROOT / "docs" / "P1_1_PRODUCTION_DEPLOYMENT_CERTIFICATION.md",
        ROOT / "docs" / "P6_1_COMMERCIAL_READINESS.md",
        ROOT / "docs" / "P7_PRODUCTION_DEPLOYMENT.md",
        ROOT / "docs" / "P7_PRODUCTION_CERTIFICATION.md",
        ROOT / "PRODUCTION_VERSION_MANIFEST.json",
        ROOT / "apps" / "web" / "VERSION_MANIFEST.json",
    ]
    for path in required_files:
        passed &= _ok(f"artifact exists: {path.relative_to(ROOT)}", path.is_file())

    prod_manifest = json.loads(
        (ROOT / "PRODUCTION_VERSION_MANIFEST.json").read_text(encoding="utf-8")
    )
    try:
        expected = resolve_profile(prod_manifest)
    except ValueError as exc:
        passed &= _ok("release profile", False, str(exc))
        print("CERTIFICATION FAIL")
        return 1

    passed &= _ok(
        f"living channel {expected['channel']}",
        True,
        f"{expected['epic']} / {expected['frontend']}",
    )

    init_py = (
        ROOT / "packages" / "dsp_platform" / "src" / "dsp_platform" / "__init__.py"
    ).read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', init_py)
    be_ver = m.group(1) if m else ""
    passed &= _ok("dsp_platform version", be_ver == expected["backend"], be_ver)

    fe_manifest = json.loads(
        (ROOT / "apps" / "web" / "VERSION_MANIFEST.json").read_text(encoding="utf-8")
    )
    passed &= _ok(
        "frontend manifest appVersion",
        fe_manifest.get("appVersion") == expected["frontend"],
        str(fe_manifest.get("appVersion")),
    )
    passed &= _ok(
        "frontend manifest epic",
        fe_manifest.get("foundationEpic") == expected["epic"],
        str(fe_manifest.get("foundationEpic")),
    )

    passed &= _ok(
        "production manifest backend",
        prod_manifest.get("backendVersion") == expected["backend"],
        str(prod_manifest.get("backendVersion")),
    )
    passed &= _ok(
        "production manifest frontend",
        prod_manifest.get("frontendVersion") == expected["frontend"],
        str(prod_manifest.get("frontendVersion")),
    )
    passed &= _ok(
        "production manifest channel",
        prod_manifest.get("channel") == expected["channel"],
        str(prod_manifest.get("channel")),
    )
    passed &= _ok(
        "api contract",
        prod_manifest.get("apiContract") == expected["api_contract"],
        str(prod_manifest.get("apiContract")),
    )

    caddy = (ROOT / "docker" / "Caddyfile").read_text(encoding="utf-8")
    passed &= _ok("Caddy HSTS", "Strict-Transport-Security" in caddy)
    passed &= _ok("Caddy gzip", "encode gzip" in caddy)
    passed &= _ok("Caddy reverse_proxy api", "reverse_proxy api:8000" in caddy)

    env = os.environ.copy()
    env.update(
        {
            "DSP_ENVIRONMENT": "production",
            "DSP_JWT_SECRET": "unit-test-strong-secret-key-32b-ok",
            "DSP_CORS_ORIGINS": "https://app.example.com",
            "DSP_ENABLE_SECURITY": "true",
            "DSP_REQUIRE_ADMIN_AUTH": "true",
            "DSP_RATE_LIMIT_ENABLED": "true",
            "DSP_HSTS_ENABLED": "true",
            "DSP_INDIA_TIMEZONE": "Asia/Kolkata",
            "DSP_INDIA_CURRENCY": "INR",
            "DSP_APP_VERSION": expected["frontend"],
            "DSP_DATABASE_URL": "postgresql://dsp:strongpass@postgres:5432/dsp",
            "DSP_PUBLIC_DOMAIN": "app.example.com",
            "DSP_SEED_ADMIN_PASSWORD": "unit-test-admin-password-ok",
            "POSTGRES_PASSWORD": "unit-test-db-password-ok",
        }
    )
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_env.py"), "production"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    passed &= _ok("validate_env production synthetic", proc.returncode == 0, proc.stderr)

    # Compose requires ../.env.production (gitignored). For offline CI/cert only,
    # materialize a temporary stub from the committed example — never commit secrets.
    env_prod = ROOT / ".env.production"
    env_example = ROOT / ".env.production.example"
    stub_created = False
    if not env_prod.is_file() and env_example.is_file():
        shutil.copyfile(env_example, env_prod)
        stub_created = True
        print(
            "[INFO] materialized temporary .env.production from "
            ".env.production.example for compose config validation"
        )
    try:
        try:
            cfg = subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    str(ROOT / "docker" / "docker-compose.production.yml"),
                    "config",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
            if cfg.returncode == 0:
                passed &= _ok("docker compose production config", True)
            else:
                passed &= _ok(
                    "docker compose production config",
                    False,
                    (cfg.stderr or cfg.stdout)[:200],
                )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            print(f"[WARN] docker compose unavailable — skipped ({exc})")
    finally:
        if stub_created and env_prod.is_file():
            env_prod.unlink()
            print("[INFO] removed temporary .env.production stub")

    print("CERTIFICATION", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
