# EPIC-R003 — Architecture

```
POST /api/v1/research/export
   { report: <R002 dict>, format }
        ↓
[api_platform] research.router
        ↓
[dsp_platform] export_institutional_report()
        ↓
InstitutionalExportEngine
   ← Institutional Report ONLY
   → json | csv | xlsx | pdf bytes
   → ExportArtifact (base64 + sha256 + metadata)
```

## Package

| Path | Role |
|---|---|
| `institutional_export/engine.py` | Export engine |
| `institutional_export/mapper.py` | Read-only flatten |
| `institutional_export/formats/*` | Format renderers (stdlib) |
| `institutional_export/validation.py` | Format + artifact validator |
| `institutional_export/serde.py` | Artifact serialize/deserialize |
| `institutional_export_facade.py` | Platform helper |

## Boundaries

- Never calls R001 builders, D005, or analysis engines
- Never mutates R002 models
- Additive HTTP only
