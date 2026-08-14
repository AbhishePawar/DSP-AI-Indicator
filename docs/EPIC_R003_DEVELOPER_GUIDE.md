# EPIC-R003 — Developer Guide

```python
from dsp_platform.institutional_export import export_institutional_report, export_artifact_to_dict

artifact = export_institutional_report(
    report_dict_or_object,
    format="xlsx",  # json | csv | xlsx | pdf
    export_id="exp-fixed",
    exported_at="2026-07-28T12:00:00+00:00",
)
payload = export_artifact_to_dict(artifact)
# payload["content_base64"] → file bytes
```

## HTTP

```http
POST /api/v1/research/export
{
  "report": { "...": "Institutional Report v1.0.0" },
  "format": "pdf",
  "export_id": "optional",
  "exported_at": "optional"
}
```

```http
GET /api/v1/research/export/schema
```

## Rules

1. Supply a complete Institutional Report — R003 never builds one.
2. Research values are exported as-is (including `"Data unavailable."`).
3. Use fixed `export_id` / `exported_at` for deterministic tests.
