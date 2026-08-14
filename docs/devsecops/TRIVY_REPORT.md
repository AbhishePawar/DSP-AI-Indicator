# TRIVY REPORT — EPIC-019A

| Field | Value |
|---|---|
| Generated | 2026-08-04T06:25:30.983773+00:00 |
| Tool | **trivy not installed on this host** |
| Status | DEFERRED to CI workflow `.github/workflows/devsecops.yml` |

## How to run locally

```bash
# Install: https://aquasecurity.github.io/trivy/
trivy fs --scanners vuln,secret,misconfig --format json -o docs/devsecops/trivy-fs.json .
python scripts/ops/run_devsecops_scans.py
```

## CI

GitHub Actions job `trivy-fs` / `trivy-image` uploads SARIF and writes this report path.

**Do not claim container image PASS without Trivy evidence.**
