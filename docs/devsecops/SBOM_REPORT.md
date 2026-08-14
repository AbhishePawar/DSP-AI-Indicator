# SBOM REPORT — EPIC-019A

| Field | Value |
|---|---|
| Generated | 2026-08-04T06:25:30.983773+00:00 |
| Lite SBOM script | `scripts/ops/generate_sbom.py` (exit 0) |
| CycloneDX npm | {'exit': 0, 'available': True} |

## Artefacts

- `docs/security/sbom-python-lite.json` / `sbom-web-lite.json` (lite)
- `docs/devsecops/sbom-web.cdx.json` (CycloneDX when tool available)
- CI: `.github/workflows/devsecops.yml` job `sbom-cyclonedx`

## Local commands

```bash
python scripts/ops/generate_sbom.py
python scripts/ops/run_devsecops_scans.py
```

Syft (optional): `syft dir:. -o cyclonedx-json=docs/devsecops/sbom-syft.cdx.json`
