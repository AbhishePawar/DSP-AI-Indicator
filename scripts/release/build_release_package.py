#!/usr/bin/env python3
"""EPIC-P7.2 — Build release/ package: checklist, notes, manifest, checksums, SBOM."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "release"

BACKEND = "2.0.0"
FRONTEND = "2.0.0"
API = "v1.0.0"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"[OK] {path.relative_to(ROOT)}")


def main() -> int:
    RELEASE.mkdir(parents=True, exist_ok=True)

    # Release notes
    notes_rc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "release" / "create_release_notes.py"),
            "--frontend",
            FRONTEND,
            "--backend",
            BACKEND,
            "--api",
            API,
            "--out",
            str(RELEASE / "RELEASE_NOTES.md"),
        ],
        cwd=str(ROOT),
        check=False,
    )
    if notes_rc.returncode != 0:
        return notes_rc.returncode

    checklist = f"""# Release Checklist — {FRONTEND} / {BACKEND}

- [ ] `python scripts/release/validate_release.py` PASS
- [ ] `python scripts/ops/certify_p7_2.py` PASS
- [ ] `python scripts/ops/certify_p7.py` PASS (infra)
- [ ] CI workflows green on release branch
- [ ] Frontend `npm test` green
- [ ] Backend architecture + smoke green
- [ ] Docker images tagged `dsp-api:{BACKEND}` / `dsp-web:{FRONTEND}`
- [ ] `PRODUCTION_VERSION_MANIFEST.json` matches tags
- [ ] Changelog section present for `{FRONTEND}`
- [ ] No secrets in commit (`.env.production` absent)
- [ ] Deploy dry-run documented
- [ ] Backup + rollback scripts present
- [ ] Legal / Research Mode disclaimer still linked
- [ ] SBOM + checksums attached under `release/`

**API contract:** `{API}` (behaviour frozen)
"""
    _write(RELEASE / "RELEASE_CHECKLIST.md", checklist)

    build_manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "epic": "P8.0",
        "backendVersion": BACKEND,
        "frontendVersion": FRONTEND,
        "apiContract": API,
        "images": {
            "api": f"dsp-api:{BACKEND}",
            "web": f"dsp-web:{FRONTEND}",
        },
        "artifacts": [
            "release/RELEASE_NOTES.md",
            "release/RELEASE_CHECKLIST.md",
            "release/BUILD_MANIFEST.json",
            "release/CHECKSUMS.sha256",
            "release/sbom.json",
        ],
        "constraints": [
            "No analytical engine changes",
            "No API behaviour changes",
            "Thin client preserved",
        ],
    }
    _write(RELEASE / "BUILD_MANIFEST.json", json.dumps(build_manifest, indent=2) + "\n")

    # Lightweight SBOM (CycloneDX-inspired JSON; not a full scanner dump)
    web_pkg = json.loads((ROOT / "apps" / "web" / "package.json").read_text(encoding="utf-8"))
    root_py = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": {
                "type": "application",
                "name": "dsp-ai-indicator",
                "version": FRONTEND,
            },
        },
        "components": [
            {
                "type": "library",
                "name": "dsp_platform",
                "version": BACKEND,
                "purl": f"pkg:pypi/dsp-platform@{BACKEND}",
            },
            {
                "type": "application",
                "name": "dsp-web",
                "version": web_pkg.get("version"),
                "purl": f"pkg:npm/dsp-web@{web_pkg.get('version')}",
            },
        ],
        "dependencies_note": (
            "Full transitive SBOM should be generated in CI with "
            "cyclonedx-bom / syft when available. This file is the "
            "release-channel bill of materials anchor for P8.0."
        ),
        "root_pyproject_present": "name" in root_py or "[project]" in root_py,
    }
    _write(RELEASE / "sbom.json", json.dumps(sbom, indent=2) + "\n")

    # Checksums for release artifacts (except CHECKSUMS itself)
    lines: list[str] = []
    for path in sorted(RELEASE.glob("*")):
        if not path.is_file() or path.name == "CHECKSUMS.sha256":
            continue
        lines.append(f"{_sha256(path)}  {path.name}")
    _write(RELEASE / "CHECKSUMS.sha256", "\n".join(lines) + "\n")

    print("[OK] release package built")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
