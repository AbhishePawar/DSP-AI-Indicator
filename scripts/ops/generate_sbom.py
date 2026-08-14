#!/usr/bin/env python3
"""EPIC-017 — Generate lightweight SBOMs for Python + Node when tools available.

Outputs under docs/security/. Never fails the pipeline if optional tools missing;
writes a generation report with instructions instead.

Usage:
  python scripts/ops/generate_sbom.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "security"
OUT.mkdir(parents=True, exist_ok=True)


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            check=False,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def main() -> int:
    report: dict = {
        "epic": "017",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tools": {},
        "artifacts": [],
        "instructions": {
            "syft": "syft packages dir:. -o cyclonedx-json=docs/security/sbom-syft.cdx.json",
            "cyclonedx_npm": "cd apps/web && npx @cyclonedx/cyclonedx-npm --output-file ../../docs/security/sbom-web.cdx.json",
            "pip_audit": "pip-audit -r <(pip freeze) --format json -o docs/security/pip-audit.json",
            "npm_audit": "cd apps/web && npm audit --json > ../../docs/security/npm-audit.json",
        },
    }

    # Python inventory via pip freeze (always available if venv present)
    code, out = _run([sys.executable, "-m", "pip", "freeze"])
    report["tools"]["pip_freeze"] = {"ok": code == 0}
    if code == 0 and out.strip():
        packages = [
            line.strip()
            for line in out.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        sbom = {
            "bomFormat": "DSP-Lite-SBOM",
            "specVersion": "1.0",
            "metadata": {
                "component": {"name": "dsp-ai-indicator", "type": "application"},
                "timestamp": report["generated_at"],
            },
            "components": [
                {
                    "type": "library",
                    "name": p.split("==")[0] if "==" in p else p,
                    "version": p.split("==")[1] if "==" in p else "unknown",
                    "purl": f"pkg:pypi/{p.split('==')[0]}@{p.split('==')[1]}"
                    if "==" in p
                    else f"pkg:pypi/{p}",
                }
                for p in packages
            ],
        }
        path = OUT / "sbom-python-lite.json"
        path.write_text(json.dumps(sbom, indent=2) + "\n", encoding="utf-8")
        report["artifacts"].append(str(path.relative_to(ROOT)))

    # npm package-lock inventory
    lock = ROOT / "apps" / "web" / "package-lock.json"
    if lock.exists():
        try:
            data = json.loads(lock.read_text(encoding="utf-8"))
            pkgs = data.get("packages") or {}
            components = []
            for key, meta in list(pkgs.items())[:5000]:
                if not key or key == "":
                    continue
                name = key.replace("node_modules/", "")
                components.append(
                    {
                        "type": "library",
                        "name": name,
                        "version": meta.get("version", "unknown"),
                    }
                )
            web_sbom = {
                "bomFormat": "DSP-Lite-SBOM",
                "specVersion": "1.0",
                "metadata": {
                    "component": {"name": "dsp-web", "type": "application"},
                    "timestamp": report["generated_at"],
                },
                "components": components,
            }
            path = OUT / "sbom-web-lite.json"
            path.write_text(json.dumps(web_sbom, indent=2) + "\n", encoding="utf-8")
            report["artifacts"].append(str(path.relative_to(ROOT)))
            report["tools"]["npm_lock"] = {"ok": True, "count": len(components)}
        except json.JSONDecodeError as exc:
            report["tools"]["npm_lock"] = {"ok": False, "error": str(exc)}

    # Optional syft / cyclonedx
    if shutil.which("syft"):
        path = OUT / "sbom-syft.cdx.json"
        code, out = _run(
            ["syft", "packages", f"dir:{ROOT}", "-o", f"cyclonedx-json={path}"]
        )
        report["tools"]["syft"] = {"ok": code == 0, "detail": out[-500:]}
        if code == 0:
            report["artifacts"].append(str(path.relative_to(ROOT)))
    else:
        report["tools"]["syft"] = {"ok": False, "detail": "not installed"}

    report_path = OUT / "SBOM_GENERATION_REPORT.md"
    lines = [
        "# SBOM Generation Report (EPIC-017)",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Artifacts",
        "",
    ]
    for a in report["artifacts"]:
        lines.append(f"- `{a}`")
    if not report["artifacts"]:
        lines.append("- None generated in this run")
    lines.extend(
        [
            "",
            "## Tool status",
            "",
            "```json",
            json.dumps(report["tools"], indent=2),
            "```",
            "",
            "## How to regenerate (full CycloneDX)",
            "",
            "```bash",
            report["instructions"]["syft"],
            report["instructions"]["cyclonedx_npm"],
            "```",
            "",
            "## Vulnerability / license audit",
            "",
            "```bash",
            "# Python",
            "pip-audit --format json -o docs/security/pip-audit.json",
            "# Node",
            "cd apps/web && npm audit --json > ../../docs/security/npm-audit.json",
            "# Container image (example)",
            "trivy image dsp-api:2.0.0",
            "```",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    report["artifacts"].append(str(report_path.relative_to(ROOT)))

    summary = OUT / "sbom-generation-summary.json"
    summary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
