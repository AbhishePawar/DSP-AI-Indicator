#!/usr/bin/env python3
"""EPIC-017 offline validation — deploy artefacts, docs, architecture freeze checks.

Usage:
  python scripts/ops/validate_epic017.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DOCS = [
    "docs/operations/Production_Deployment_Guide.md",
    "docs/operations/Production_Runbook.md",
    "docs/operations/Monitoring_Guide.md",
    "docs/operations/Disaster_Recovery.md",
    "docs/operations/Incident_Response.md",
    "docs/operations/Performance_Report.md",
    "docs/operations/Scalability_Report.md",
    "docs/operations/EPIC_017_COMPLETION_REPORT.md",
]

REQUIRED_DEPLOY = [
    "deploy/docker/README.md",
    "deploy/docker/compose.production.yml",
    "deploy/k8s/base/kustomization.yaml",
    "deploy/k8s/base/api-deployment.yaml",
    "deploy/k8s/base/web-deployment.yaml",
    "deploy/k8s/base/configmap.yaml",
    "deploy/helm/dsp/Chart.yaml",
    "deploy/helm/dsp/values.yaml",
    "deploy/helm/dsp/values-production.yaml",
    "deploy/observability/otel/otel-collector-config.yaml",
    "deploy/observability/prometheus/production_alerts.yml",
    "docker/backend/Dockerfile",
    "docker/frontend/Dockerfile",
    "docker/docker-compose.production.yml",
]

# Paths that must NOT be modified by this epic's validation (existence only)
ENGINE_MARKERS = [
    "packages/dsp_platform",
    "packages/api_platform/src/api_platform/api/routers",
]


def main() -> int:
    failures: list[str] = []
    for rel in REQUIRED_DOCS + REQUIRED_DEPLOY:
        if not (ROOT / rel).exists():
            failures.append(f"missing: {rel}")

    # Dockerfile multi-stage sanity
    api_df = (ROOT / "docker/backend/Dockerfile").read_text(encoding="utf-8")
    web_df = (ROOT / "docker/frontend/Dockerfile").read_text(encoding="utf-8")
    if "AS builder" not in api_df and "AS runtime" not in api_df:
        failures.append("backend Dockerfile missing multi-stage markers")
    if "FROM node:" not in web_df or "AS runner" not in web_df:
        failures.append("frontend Dockerfile missing multi-stage markers")
    if "USER dsp" not in api_df:
        failures.append("backend Dockerfile should run as non-root USER dsp")

    for marker in ENGINE_MARKERS:
        if not (ROOT / marker).exists():
            failures.append(f"engine path missing (unexpected): {marker}")

    result = {
        "epic": "017",
        "ok": not failures,
        "checks": len(REQUIRED_DOCS) + len(REQUIRED_DEPLOY) + 3,
        "failures": failures,
    }
    print(json.dumps(result, indent=2))
    out = ROOT / "docs" / "operations" / "epic017_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
