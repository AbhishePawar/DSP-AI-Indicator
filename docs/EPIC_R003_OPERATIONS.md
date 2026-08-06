# EPIC-R003 — Operations

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/research/export/schema` | Schema discovery |
| POST | `/api/v1/research/export` | Export report artifact |

## Runtime

- No additional environment variables
- Stdlib-only renderers (no openpyxl/reportlab required)
- CPU-bound; suitable behind existing API rate limits

## Artifact handling

- Prefer `content_base64` for binary formats (`pdf`, `xlsx`)
- Verify integrity with `content_sha256` (SHA-256 hex of raw bytes)
- Filenames: `{ticker}_institutional_report_{report_id}.{ext}`

## Failure modes

| Condition | HTTP | Behavior |
|---|---|---|
| Missing `report` | 422 | Validation error |
| Unsupported format | 400 | `"Data unavailable."` message body |
| Invalid report structure | 400/503 | Honest error; no fabricated export |

## Observability

Export metadata includes `export_id`, `report_id`, `research_object_id`,
`exported_at`, format, and byte length for audit trails (RS-010 preserved).
