# EPIC-R003 — Institutional Export Specification

Status: **COMPLETE**  
Priority: P0 · Research Infrastructure  
Schema: **1.0.0**  
Source: **Institutional Report (R002) only**

## Goal

Production Export Engine that projects Institutional Reports into downloadable
artifacts. Export only — no calculations, scoring, valuation, or AI.

## Formats

| Format | Content type | Notes |
|---|---|---|
| `json` | `application/json` | Full report dict; `sort_keys` for byte stability |
| `csv` | `text/csv` | Flat summary rows (section/rs_id/field/value/…) |
| `xlsx` | OOXML spreadsheet | Same summary rows; stdlib ZIP/XML |
| `pdf` | `application/pdf` | Text projection; PDF escaping only |

Alias: `excel` → `xlsx`.

## Artifact

Every export returns metadata + version + `content_base64` + `content_sha256`.
JSON also includes `structured_json` (identical research content).

Missing report values remain `"Data unavailable."` — never invent.

## Non-goals

- Do not modify R001 / R002 / D001–D005 / engines
- Do not reformat research values beyond transport encoding
