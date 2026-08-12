#!/usr/bin/env python3
"""Validate semantic versions and release manifest consistency.

Selects a STRICT release profile from PRODUCTION_VERSION_MANIFEST.channel:

* rc           → EPS-003 / 2.0.0-rc.1 / RELEASE_CANDIDATE
* ga-candidate → P8.0 / 2.0.0 / GO_WITH_CONDITIONS (future)

Root VERSION is the product channel version (not the API contract).
No analytical / API behaviour changes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Allow `python scripts/release/validate_release.py` without install.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_identity import (  # noqa: E402
    GA_PROFILE,
    RC_PROFILE,
    ReleaseProfile,
    profile_matches_manifest,
    resolve_profile,
)

SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))"
    r"?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


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


def _load_profile(force_channel: str | None) -> tuple[ReleaseProfile, dict]:
    prod_path = ROOT / "PRODUCTION_VERSION_MANIFEST.json"
    prod = json.loads(_read(prod_path))
    if force_channel:
        from release_identity import RELEASE_PROFILES

        if force_channel not in RELEASE_PROFILES:
            raise ValueError(f"Unknown --channel {force_channel!r}")
        return RELEASE_PROFILES[force_channel], prod
    return resolve_profile(prod), prod


def validate(
    strict_tag: str | None = None,
    *,
    force_channel: str | None = None,
) -> int:
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

    try:
        expected, prod = _load_profile(force_channel)
    except ValueError as exc:
        _ok("release profile", False, str(exc))
        print("VALIDATE_RELEASE FAIL")
        return 1

    passed &= _ok(
        f"release profile {expected['channel']}",
        True,
        expected["name"],
    )
    mismatches = profile_matches_manifest(expected, prod)
    passed &= _ok(
        "prod manifest matches profile",
        not mismatches,
        "; ".join(mismatches) if mismatches else expected["channel"],
    )

    be_v = _extract_py_version(_read(be_init))
    toml_v = _extract_toml_version(_read(be_toml))
    passed &= _ok("backend semver", bool(SEMVER.match(be_v)), be_v)
    passed &= _ok("backend == expected", be_v == expected["backend"], be_v)
    passed &= _ok("pyproject matches __version__", be_v == toml_v, f"{be_v} vs {toml_v}")

    fe_text = _read(fe_ver)
    m_fe = re.search(r'FRONTEND_FOUNDATION_VERSION\s*=\s*"([^"]+)"', fe_text)
    m_be = re.search(r'BACKEND_PLATFORM_TARGET\s*=\s*"([^"]+)"', fe_text)
    m_api = re.search(r'API_CONTRACT_TARGET\s*=\s*"([^"]+)"', fe_text)
    m_epic = re.search(r'FRONTEND_FOUNDATION_EPIC\s*=\s*"([^"]+)"', fe_text)
    fe_v = m_fe.group(1) if m_fe else ""
    passed &= _ok("frontend semver", bool(SEMVER.match(fe_v)), fe_v)
    passed &= _ok("frontend == expected", fe_v == expected["frontend"], fe_v)
    passed &= _ok(
        "foundation backend target",
        (m_be.group(1) if m_be else "") == f"dsp_platform@{expected['backend']}",
        m_be.group(1) if m_be else "",
    )
    passed &= _ok(
        "API contract target",
        (m_api.group(1) if m_api else "") == expected["api_contract"],
        m_api.group(1) if m_api else "",
    )
    passed &= _ok(
        "foundation epic",
        (m_epic.group(1) if m_epic else "") == expected["epic"],
        m_epic.group(1) if m_epic else "",
    )

    pkg = json.loads(_read(fe_pkg))
    passed &= _ok("package.json version", pkg.get("version") == expected["frontend"])

    fe_man = json.loads(_read(fe_manifest))
    passed &= _ok(
        "web manifest appVersion", fe_man.get("appVersion") == expected["frontend"]
    )
    passed &= _ok(
        "web manifest backend",
        fe_man.get("backend") == f"dsp_platform@{expected['backend']}",
    )
    passed &= _ok(
        "web manifest apiContract",
        fe_man.get("apiContract") == expected["api_contract"],
    )
    passed &= _ok("web manifest epic", fe_man.get("foundationEpic") == expected["epic"])
    passed &= _ok("web manifest channel", fe_man.get("channel") == expected["channel"])

    # Root VERSION = product channel version (see release_identity module docstring).
    root_ver = _read(version_file).strip()
    passed &= _ok(
        "VERSION product channel",
        root_ver == expected["product_version"],
        root_ver,
    )

    matrix = _read(version_matrix)
    passed &= _ok(
        "VERSION_MATRIX backend pin", f"**{expected['backend']}**" in matrix
    )
    passed &= _ok(
        "VERSION_MATRIX frontend pin", f"**{expected['frontend']}**" in matrix
    )
    passed &= _ok("VERSION_MATRIX api pin", expected["api_contract"] in matrix)
    passed &= _ok(
        "VERSION_MATRIX epic",
        expected["epic"] in matrix,
    )

    if compose_prod.is_file():
        compose = _read(compose_prod)
        # API image default tracks backend package; web image tracks frontend product.
        passed &= _ok(
            "compose default API tag",
            f"DSP_IMAGE_TAG:-{expected['backend']}" in compose
            or f"DSP_IMAGE_TAG:-{expected['frontend']}" in compose
            or f"dsp-api:{expected['backend']}" in compose
            or f"dsp-api:{expected['frontend']}" in compose,
        )
        passed &= _ok(
            "compose default web tag",
            f"DSP_IMAGE_TAG_WEB:-{expected['frontend']}" in compose
            or f"dsp-web:{expected['frontend']}" in compose,
        )

    if strict_tag:
        tag = strict_tag.lstrip("v")
        allowed = {
            expected["backend"],
            expected["frontend"],
            expected["product_version"],
            expected["api_contract"].lstrip("v"),
        }
        passed &= _ok("git tag matches release set", tag in allowed, strict_tag)

    # Preserve discoverability of the alternate profile (not applied unless living).
    alt = GA_PROFILE if expected["channel"] == RC_PROFILE["channel"] else RC_PROFILE
    passed &= _ok(
        f"alternate profile retained ({alt['channel']})",
        alt["frontend"] != expected["frontend"] or alt["channel"] != expected["channel"],
        f"{alt['epic']} / {alt['frontend']}",
    )

    print("VALIDATE_RELEASE", "PASS" if passed else "FAIL")
    return 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default=None, help="Optional git tag to validate")
    parser.add_argument(
        "--channel",
        default=None,
        choices=sorted({RC_PROFILE["channel"], GA_PROFILE["channel"]}),
        help="Force a profile (default: living PRODUCTION_VERSION_MANIFEST.channel)",
    )
    args = parser.parse_args(argv)
    return validate(strict_tag=args.tag, force_channel=args.channel)


if __name__ == "__main__":
    raise SystemExit(main())
