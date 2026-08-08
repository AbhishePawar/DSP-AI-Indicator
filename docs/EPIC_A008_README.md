# EPIC-A008 — Institutional Persistence Layer

Status: **COMPLETE** · Priority: P0

## Summary

Deterministic persistence infrastructure for research metadata, workflow records,
audit trails, citations, and provenance. Research artifact payloads are never
stored or mutated. Default provider is in-memory; storage port supports future
PostgreSQL / SQLite / DuckDB / object storage without API changes.

## Docs

| Doc | Path |
|---|---|
| Architecture | [EPIC_A008_PERSISTENCE_ARCHITECTURE.md](EPIC_A008_PERSISTENCE_ARCHITECTURE.md) |
| Repository Guide | [EPIC_A008_REPOSITORY_GUIDE.md](EPIC_A008_REPOSITORY_GUIDE.md) |
| Transaction Guide | [EPIC_A008_TRANSACTION_GUIDE.md](EPIC_A008_TRANSACTION_GUIDE.md) |
| Storage Guide | [EPIC_A008_STORAGE_GUIDE.md](EPIC_A008_STORAGE_GUIDE.md) |
| Developer Guide | [EPIC_A008_DEVELOPER_GUIDE.md](EPIC_A008_DEVELOPER_GUIDE.md) |

## Final

**PASS** — production-ready Institutional Persistence Layer (`dsp_platform` **0.20.0**).
