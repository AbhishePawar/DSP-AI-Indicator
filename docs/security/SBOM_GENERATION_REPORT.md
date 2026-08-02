# SBOM Generation Report (EPIC-017)

Generated: `2026-08-02T17:12:01.407243+00:00`

## Artifacts

- `docs\security\sbom-python-lite.json`
- `docs\security\sbom-web-lite.json`

## Tool status

```json
{
  "pip_freeze": {
    "ok": true
  },
  "npm_lock": {
    "ok": true,
    "count": 641
  },
  "syft": {
    "ok": false,
    "detail": "not installed"
  }
}
```

## How to regenerate (full CycloneDX)

```bash
syft packages dir:. -o cyclonedx-json=docs/security/sbom-syft.cdx.json
cd apps/web && npx @cyclonedx/cyclonedx-npm --output-file ../../docs/security/sbom-web.cdx.json
```

## Vulnerability / license audit

```bash
# Python
pip-audit --format json -o docs/security/pip-audit.json
# Node
cd apps/web && npm audit --json > ../../docs/security/npm-audit.json
# Container image (example)
trivy image dsp-api:2.0.0
```
