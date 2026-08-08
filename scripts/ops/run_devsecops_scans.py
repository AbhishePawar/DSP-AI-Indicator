#!/usr/bin/env python3
"""EPIC-019A — DevSecOps scan orchestrator (local + CI).

Runs available tools; writes markdown/json under docs/devsecops/.
Missing tools are recorded honestly — never invents PASS for absent scanners.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "devsecops"
OUT.mkdir(parents=True, exist_ok=True)


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 600) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError as exc:
        return 127, str(exc)
    except subprocess.TimeoutExpired as exc:
        return 124, f"timeout: {exc}"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    ts = datetime.now(timezone.utc).isoformat()
    summary: dict = {
        "epic": "019A",
        "generated_at": ts,
        "tools": {},
        "artifacts": [],
    }

    # --- CycloneDX / lite SBOM via existing generator ---
    code, out = run([sys.executable, str(ROOT / "scripts" / "ops" / "generate_sbom.py")])
    summary["tools"]["generate_sbom"] = {"exit": code}
    summary["artifacts"].append("docs/security/SBOM_GENERATION_REPORT.md")

    # --- npm CycloneDX if npx available ---
    npm = shutil.which("npx")
    if npm:
        cdx_out = OUT / "sbom-web.cdx.json"
        code, out = run(
            [
                npm,
                "--yes",
                "@cyclonedx/cyclonedx-npm@1.19.3",
                "--output-file",
                str(cdx_out),
                "--ignore-npm-errors",
            ],
            cwd=ROOT / "apps" / "web",
            timeout=900,
        )
        summary["tools"]["cyclonedx_npm"] = {"exit": code, "available": True}
        if cdx_out.exists():
            summary["artifacts"].append(str(cdx_out.relative_to(ROOT)))
    else:
        summary["tools"]["cyclonedx_npm"] = {"available": False}

    # --- Trivy fs scan ---
    trivy = shutil.which("trivy")
    trivy_json = OUT / "trivy-fs.json"
    trivy_md = OUT / "TRIVY_REPORT.md"
    if trivy:
        code, out = run(
            [
                trivy,
                "fs",
                "--scanners",
                "vuln,secret,misconfig",
                "--format",
                "json",
                "--output",
                str(trivy_json),
                str(ROOT),
            ],
            timeout=900,
        )
        summary["tools"]["trivy"] = {"exit": code, "available": True}
        # human report
        code2, out2 = run(
            [
                trivy,
                "fs",
                "--scanners",
                "vuln,secret,misconfig",
                "--format",
                "table",
                str(ROOT),
            ],
            timeout=900,
        )
        write(
            trivy_md,
            "\n".join(
                [
                    "# TRIVY REPORT — EPIC-019A",
                    "",
                    f"| Field | Value |",
                    f"|---|---|",
                    f"| Generated | {ts} |",
                    f"| Tool | trivy (local/CI) |",
                    f"| Exit (json) | {code} |",
                    f"| Exit (table) | {code2} |",
                    f"| JSON artefact | `docs/devsecops/trivy-fs.json` |",
                    "",
                    "## Table output",
                    "",
                    "```",
                    out2[:20000],
                    "```",
                    "",
                ]
            ),
        )
        summary["artifacts"].extend(
            ["docs/devsecops/trivy-fs.json", "docs/devsecops/TRIVY_REPORT.md"]
        )
    else:
        summary["tools"]["trivy"] = {"available": False}
        write(
            trivy_md,
            "\n".join(
                [
                    "# TRIVY REPORT — EPIC-019A",
                    "",
                    f"| Field | Value |",
                    f"|---|---|",
                    f"| Generated | {ts} |",
                    f"| Tool | **trivy not installed on this host** |",
                    f"| Status | DEFERRED to CI workflow `.github/workflows/devsecops.yml` |",
                    "",
                    "## How to run locally",
                    "",
                    "```bash",
                    "# Install: https://aquasecurity.github.io/trivy/",
                    "trivy fs --scanners vuln,secret,misconfig --format json -o docs/devsecops/trivy-fs.json .",
                    "python scripts/ops/run_devsecops_scans.py",
                    "```",
                    "",
                    "## CI",
                    "",
                    "GitHub Actions job `trivy-fs` / `trivy-image` uploads SARIF and writes this report path.",
                    "",
                    "**Do not claim container image PASS without Trivy evidence.**",
                    "",
                ]
            ),
        )

    # --- pip-audit / npm audit snapshots ---
    pip_audit = shutil.which("pip-audit")
    if pip_audit:
        code, out = run([pip_audit, "--format", "json", "-o", str(OUT / "pip-audit.json")])
        summary["tools"]["pip_audit"] = {"exit": code, "available": True}
    else:
        code, out = run([sys.executable, "-m", "pip_audit", "--format", "json", "-o", str(OUT / "pip-audit.json")])
        summary["tools"]["pip_audit"] = {
            "exit": code,
            "available": code != 127,
            "via": "python -m pip_audit",
        }

    npm_bin = shutil.which("npm")
    if npm_bin:
        code, out = run([npm_bin, "audit", "--json"], cwd=ROOT / "apps" / "web")
        write(OUT / "npm-audit.json", out if out.strip().startswith("{") else json.dumps({"raw": out[:50000]}))
        summary["tools"]["npm_audit"] = {"exit": code, "available": True}

    # --- SBOM report pointer ---
    write(
        OUT / "SBOM_REPORT.md",
        "\n".join(
            [
                "# SBOM REPORT — EPIC-019A",
                "",
                f"| Field | Value |",
                f"|---|---|",
                f"| Generated | {ts} |",
                f"| Lite SBOM script | `scripts/ops/generate_sbom.py` (exit {summary['tools'].get('generate_sbom', {}).get('exit')}) |",
                f"| CycloneDX npm | {summary['tools'].get('cyclonedx_npm')} |",
                "",
                "## Artefacts",
                "",
                "- `docs/security/sbom-python-lite.json` / `sbom-web-lite.json` (lite)",
                "- `docs/devsecops/sbom-web.cdx.json` (CycloneDX when tool available)",
                "- CI: `.github/workflows/devsecops.yml` job `sbom-cyclonedx`",
                "",
                "## Local commands",
                "",
                "```bash",
                "python scripts/ops/generate_sbom.py",
                "python scripts/ops/run_devsecops_scans.py",
                "```",
                "",
                "Syft (optional): `syft dir:. -o cyclonedx-json=docs/devsecops/sbom-syft.cdx.json`",
                "",
            ]
        ),
    )

    write(OUT / "scan-summary.json", json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
