# EPIC-R004 — Research Archive Specification

Status: **COMPLETE**  
Priority: P0 · Research Infrastructure  
Schema: **1.0.0**

## Goal

Immutable Research Archive for versioned snapshots of:

- Research Objects (R001)
- Institutional Reports (R002)
- Export metadata / artifacts (R003)

## Snapshot

| Field | Description |
|---|---|
| snapshot_id | Unique immutable id |
| kind | `research_object` \| `institutional_report` \| `export_metadata` |
| version.lineage_id | Version family |
| version.version_number | Monotonic per lineage |
| version.parent_snapshot_id | Prior snapshot (required when version > 1) |
| content_sha256 | SHA-256 of canonical JSON payload |
| content_schema_version | Embedded R001/R002/R003 schema version |
| archived_at | Timestamp |
| provenance | Archive provenance map |
| payload | Frozen original content |
| retention_hooks | Advisory metadata only |

## Rules

- Overwrite forbidden
- No calculations / scoring / valuation / AI
- Retention hooks evaluate only — never mutate or delete by default
- Comparison returns metadata (hashes, versions, timestamps) only

## Non-goals

Do not modify R001–R003, D001–D005, engines, or breaking APIs.
