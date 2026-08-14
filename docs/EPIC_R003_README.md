# EPIC-R003 — Institutional Export Engine

Status: **COMPLETE** · Priority: P0

## Summary

Read-only export of Institutional Reports (R002) to **JSON**, **CSV**,
**Excel (.xlsx)**, and **PDF**. No calculations or research reformatting.

## Docs

| Doc | Path |
|---|---|
| Specification | [EPIC_R003_EXPORT_SPEC.md](EPIC_R003_EXPORT_SPEC.md) |
| Architecture | [EPIC_R003_ARCHITECTURE.md](EPIC_R003_ARCHITECTURE.md) |
| Developer Guide | [EPIC_R003_DEVELOPER_GUIDE.md](EPIC_R003_DEVELOPER_GUIDE.md) |
| Operations | [EPIC_R003_OPERATIONS.md](EPIC_R003_OPERATIONS.md) |

## API

- `GET /api/v1/research/export/schema`
- `POST /api/v1/research/export`

## Compliance

| Check | Result |
|---|---|
| CV-001 / CV-002 / CV-003 | PASS |
| RS-001…RS-010 preserved in export | PASS |
| Institutional Report only | PASS |
| R001/R002/D001–D005 unchanged | PASS |
| No breaking changes | PASS |

## Final

**PASS** — production-ready Institutional Export Engine.
