#!/usr/bin/env python3
"""EPIC-P7.2 — Create release notes from changelog + manifests (ops only)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _section_for_version(changelog: str, version: str) -> str:
    # Match ## [2.0.0] ... until next ## [
    pattern = rf"(?ms)^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)"
    m = re.search(pattern, changelog)
    if not m:
        return f"_No changelog section found for [{version}]._\n"
    return m.group(1).strip() + "\n"


def create_notes(
    frontend_version: str,
    backend_version: str,
    api_contract: str,
    out_path: Path,
) -> Path:
    changelog = (ROOT / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")
    prod = json.loads(
        (ROOT / "PRODUCTION_VERSION_MANIFEST.json").read_text(encoding="utf-8")
    )
    body_fe = _section_for_version(changelog, frontend_version)
    body_be = _section_for_version(changelog, backend_version)

    text = f"""# Release Notes — DSP AI Indicator

**Date:** {date.today().isoformat()}  
**Frontend:** `{frontend_version}`  
**Backend:** `dsp_platform {backend_version}`  
**API contract:** `{api_contract}`  
**Channel:** `{prod.get("channel", "ga-candidate")}`  
**Milestone:** `{prod.get("milestone", "P8.0")}`

## Summary

{prod.get("architectureNote", "Repository / release engineering release.")}

## Frontend {frontend_version}

{body_fe}

## Backend {backend_version}

{body_be if body_be.strip() != body_fe.strip() else "_See frontend section (joint commercial channel notes)._" }

## Compatibility

- Analytical engines and `/api/v1` analyse behaviour are **unchanged**.
- Thin client preserved — no browser-side valuation or AI reasoning.
- Research Mode / User Trust Standard remain in force.

## Upgrade

1. Validate: `python scripts/release/validate_release.py`
2. Deploy: `./scripts/deploy_production.sh` (P7.0 stack)
3. Smoke health endpoints and HTTPS
4. Archive `release/` artifacts with checksums

## Links

- `docs/VERSION_MATRIX.md`
- `docs/P7_PRODUCTION_DEPLOYMENT.md`
- `docs/ENGINEERING_STATUS.md`
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(f"[OK] wrote {out_path}")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend", default="2.0.0")
    parser.add_argument("--backend", default="2.0.0")
    parser.add_argument("--api", default="v1.0.0")
    parser.add_argument(
        "--out",
        default=str(ROOT / "release" / "RELEASE_NOTES.md"),
    )
    args = parser.parse_args(argv)
    create_notes(args.frontend, args.backend, args.api, Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
