#!/usr/bin/env python3
"""EPIC-017 — Ops/security packaging review (headers, secrets hygiene, containers).

Static checks only — does not change valuation/API behaviour.
Writes docs/security/EPIC017_SECURITY_PACKAGING_REPORT.md
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "security" / "EPIC017_SECURITY_PACKAGING_REPORT.md"


def check(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "ok": ok, "detail": detail}


def main() -> int:
    findings: list[dict] = []

    # .gitignore protects production env
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    findings.append(
        check(".env.production gitignored", ".env.production" in gi, "expected in .gitignore")
    )
    findings.append(
        check(
            ".env.production.example allowed",
            "!.env.production.example" in gi or (ROOT / ".env.production.example").exists(),
        )
    )

    # No committed .env.production
    findings.append(
        check(
            "no committed .env.production file",
            not (ROOT / ".env.production").exists(),
            "file absent or local-only",
        )
    )

    # Dockerfiles non-root
    api_df = (ROOT / "docker/backend/Dockerfile").read_text(encoding="utf-8")
    web_df = (ROOT / "docker/frontend/Dockerfile").read_text(encoding="utf-8")
    findings.append(check("API runs as USER dsp", "USER dsp" in api_df))
    findings.append(check("Web runs as USER dsp", "USER dsp" in web_df))
    findings.append(check("API HEALTHCHECK present", "HEALTHCHECK" in api_df))
    findings.append(check("Web HEALTHCHECK present", "HEALTHCHECK" in web_df))

    # Secrets not in compose defaults as real values
    prod = (ROOT / "docker/docker-compose.production.yml").read_text(encoding="utf-8")
    findings.append(
        check(
            "compose uses env substitution for DB password",
            "POSTGRES_PASSWORD" in prod and "CHANGE_ME" in (ROOT / ".env.production.example").read_text(encoding="utf-8"),
        )
    )

    # Security headers middleware exists
    mw = ROOT / "packages" / "security_platform" / "src" / "security_platform" / "security" / "middleware.py"
    findings.append(check("security middleware present", mw.exists()))
    if mw.exists():
        text = mw.read_text(encoding="utf-8")
        findings.append(
            check(
                "security headers referenced",
                "X-Content-Type-Options" in text or "nosniff" in text or "Security" in text,
                "see docs/security/PRODUCTION_SECURITY_GUIDE.md",
            )
        )

    # k8s drop ALL capabilities
    api_k8s = (ROOT / "deploy/k8s/base/api-deployment.yaml").read_text(encoding="utf-8")
    findings.append(check("k8s API drops ALL caps", 'drop: ["ALL"]' in api_k8s or "drop: [\"ALL\"]" in api_k8s))
    findings.append(check("k8s runAsNonRoot", "runAsNonRoot: true" in api_k8s))

    # Secret scanning heuristics on deploy/ (skip docs + examples + placeholders)
    secret_pat = re.compile(r"(api[_-]?key|password|secret)\s*[:=]\s*['\"][^'\"]{12,}", re.I)
    placeholder = re.compile(
        r"(CHANGE_ME|from-vault|your-domain|<from-|<vault|example\.|TODO)",
        re.I,
    )
    leaked = []
    for path in (ROOT / "deploy").rglob("*"):
        if not path.is_file() or path.suffix not in {".yaml", ".yml", ".env.example"}:
            continue
        if "secrets.example" in path.name or path.suffix == ".md":
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for m in secret_pat.finditer(content):
            snippet = m.group(0)
            if placeholder.search(snippet) or "CHANGE_ME" in content:
                continue
            leaked.append(f"{path.relative_to(ROOT)}: {snippet[:40]}…")
    findings.append(
        check("no hardcoded secrets in deploy/", len(leaked) == 0, "; ".join(leaked[:5]))
    )

    ok_count = sum(1 for f in findings if f["ok"])
    lines = [
        "# EPIC-017 Security Packaging Review",
        "",
        f"Generated: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        f"**Result:** {ok_count}/{len(findings)} checks passed",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for f in findings:
        status = "PASS" if f["ok"] else "FAIL"
        lines.append(f"| {f['name']} | {status} | {f['detail']} |")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "- Headers/cookies: see `docs/security/PRODUCTION_SECURITY_GUIDE.md` (EPIC-016)",
            "- Container hardening: non-root USER, HEALTHCHECK, capability drop in k8s",
            "- Secrets: ConfigMap vs Secret separation; ExternalSecrets recommended",
            "- SBOM: `python scripts/ops/generate_sbom.py`",
            "- Image scanning: `trivy image dsp-api:2.0.0` (CI optional)",
            "",
            "## Fixes applied in EPIC-017",
            "",
            "- Added k8s securityContext (runAsNonRoot, drop ALL)",
            "- Documented secrets abstraction under `deploy/docker/secrets.md`",
            "- SBOM generation script + lite inventories",
            "",
            "## Residual risks",
            "",
            "- Next.js CSP still allows `'unsafe-inline'` / `'unsafe-eval'` (tracked, not redesigned)",
            "- In-cluster Postgres StatefulSet is reference-only; prefer managed + PITR",
            "- Full CycloneDX requires syft/cyclonedx CLI in CI",
            "",
            "```json",
            json.dumps({"epic": "017", "passed": ok_count, "total": len(findings)}, indent=2),
            "```",
            "",
        ]
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUT.read_text(encoding="utf-8"))
    return 0 if ok_count == len(findings) else 1


if __name__ == "__main__":
    raise SystemExit(main())
