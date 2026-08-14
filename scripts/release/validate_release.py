#!/usr/bin/env python3
"""EPIC-P7.2 — Validate semantic versions and release manifest consistency.

No analytical / API behaviour changes. Fails on critical mismatches.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))"
    r"?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

EXPECTED = {
    "backend": "2.0.0",
    "frontend": "2.0.0",
    "api_contract": "v1.0.0",
    "epic": "P8.0",
    "channel": "ga-candidate",
}


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    extra = f" — {detail}" if detail else ""
    print(f"[{mark}] {name}{extra}")
    return passed


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_py_version(init_py: str) -> str:
    m = re.search(r'__version__\s*=\s*"([^"]+)"', init_py)
    return m.group(1) if m else ""


def _extract_toml_version(text: str) -> str:
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else ""


def validate(strict_tag: str | None = None) -> int:
    passed = True

    be_init = ROOT / "packages" / "dsp_platform" / "src" / "dsp_platform" / "__init__.py"
    be_toml = ROOT / "packages" / "dsp_platform" / "pyproject.toml"
    fe_ver = ROOT / "apps" / "web" / "src" / "foundation" / "version.ts"
    fe_pkg = ROOT / "apps" / "web" / "package.json"
    fe_manifest = ROOT / "apps" / "web" / "VERSION_MANIFEST.json"
    prod_manifest = ROOT / "PRODUCTION_VERSION_MANIFEST.json"
    version_file = ROOT / "VERSION"
    version_matrix = ROOT / "docs" / "VERSION_MATRIX.md"
    compose_prod = ROOT / "docker" / "docker-compose.production.yml"

    for path in [be_init, be_toml, fe_ver, fe_pkg, fe_manifest, prod_manifest, version_file]:
        passed &= _ok(f"exists {path.relative_to(ROOT)}", path.is_file())

    be_v = _extract_py_version(_read(be_init))
    toml_v = _extract_toml_version(_read(be_toml))
    passed &= _ok("backend semver", bool(SEMVER.match(be_v)), be_v)
    passed &= _ok("backend == expected", be_v == EXPECTED["backend"], be_v)
    passed &= _ok("pyproject matches __version__", be_v == toml_v, f"{be_v} vs {toml_v}")

    fe_text = _read(fe_ver)
    m_fe = re.search(r'FRONTEND_FOUNDATION_VERSION\s*=\s*"([^"]+)"', fe_text)
    m_be = re.search(r'BACKEND_PLATFORM_TARGET\s*=\s*"([^"]+)"', fe_text)
    m_api = re.search(r'API_CONTRACT_TARGET\s*=\s*"([^"]+)"', fe_text)
    m_epic = re.search(r'FRONTEND_FOUNDATION_EPIC\s*=\s*"([^"]+)"', fe_text)
    fe_v = m_fe.group(1) if m_fe else ""
    passed &= _ok("frontend semver", bool(SEMVER.match(fe_v)), fe_v)
    passed &= _ok("frontend == expected", fe_v == EXPECTED["frontend"], fe_v)
    passed &= _ok(
        "foundation backend target",
        (m_be.group(1) if m_be else "") == f"dsp_platform@{EXPECTED['backend']}",
        m_be.group(1) if m_be else "",
    )
    passed &= _ok(
        "API contract target",
        (m_api.group(1) if m_api else "") == EXPECTED["api_contract"],
        m_api.group(1) if m_api else "",
    )
    passed &= _ok(
        "foundation epic",
        (m_epic.group(1) if m_epic else "") == EXPECTED["epic"],
        m_epic.group(1) if m_epic else "",
    )

    pkg = json.loads(_read(fe_pkg))
    passed &= _ok("package.json version", pkg.get("version") == EXPECTED["frontend"])

    fe_man = json.loads(_read(fe_manifest))
    passed &= _ok("web manifest appVersion", fe_man.get("appVersion") == EXPECTED["frontend"])
    passed &= _ok("web manifest backend", fe_man.get("backend") == f"dsp_platform@{EXPECTED['backend']}")
    passed &= _ok("web manifest apiContract", fe_man.get("apiContract") == EXPECTED["api_contract"])
    passed &= _ok("web manifest epic", fe_man.get("foundationEpic") == EXPECTED["epic"])

    prod = json.loads(_read(prod_manifest))
    passed &= _ok("prod manifest backend", prod.get("backendVersion") == EXPECTED["backend"])
    passed &= _ok("prod manifest frontend", prod.get("frontendVersion") == EXPECTED["frontend"])
    passed &= _ok("prod manifest api", prod.get("apiContract") == EXPECTED["api_contract"])
    passed &= _ok("prod manifest channel", prod.get("channel") == EXPECTED["channel"])

    root_ver = _read(version_file).strip()
    passed &= _ok("VERSION file", root_ver in {EXPECTED["api_contract"], EXPECTED["api_contract"].lstrip("v")})

    matrix = _read(version_matrix)
    passed &= _ok("VERSION_MATRIX backend pin", f"**{EXPECTED['backend']}**" in matrix)
    passed &= _ok("VERSION_MATRIX frontend pin", f"**{EXPECTED['frontend']}**" in matrix)
    passed &= _ok("VERSION_MATRIX api pin", EXPECTED["api_contract"] in matrix)

    if compose_prod.is_file():
        compose = _read(compose_prod)
        passed &= _ok(
            "compose default API tag",
            f"DSP_IMAGE_TAG:-{EXPECTED['backend']}" in compose
            or f"dsp-api:{EXPECTED['backend']}" in compose,
        )
        passed &= _ok(
            "compose default web tag",
            f"DSP_IMAGE_TAG_WEB:-{EXPECTED['frontend']}" in compose
            or f"dsp-web:{EXPECTED['frontend']}" in compose,
        )

    if strict_tag:
        tag = strict_tag.lstrip("v")
        # Accept tags like 2.0.2 (frontend) or 1.7.2 (backend) or 1.0.0 (api)
        allowed = {EXPECTED["backend"], EXPECTED["frontend"], EXPECTED["api_contract"].lstrip("v")}
        passed &= _ok("git tag matches release set", tag in allowed, strict_tag)

    print("VALIDATE_RELEASE", "PASS" if passed else "FAIL")
    return 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default=None, help="Optional git tag to validate")
    args = parser.parse_args(argv)
    return validate(strict_tag=args.tag)


if __name__ == "__main__":
    raise SystemExit(main())
