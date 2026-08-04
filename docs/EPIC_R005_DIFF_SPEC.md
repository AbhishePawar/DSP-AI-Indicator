# EPIC-R005 — Research Diff Specification

Status: **COMPLETE**  
Priority: P0 · Research Infrastructure  
Schema: **1.0.0**  
Source: **R004 Snapshot A + Snapshot B**

## Goal

Deterministic, read-only structural comparison of immutable Research Archive
snapshots. Comparison only — no recommendations, interpretation, or analytics.

## Diff result

| Block | Content |
|---|---|
| archive_comparison | ids, hashes, lineage, timestamps |
| schema_comparison | archive + content schema versions |
| version_comparison | lineage / version_number |
| sections[] | per-section status + field diffs |
| change_summary | counts only (added/removed/changed/unchanged) |
| provenance | diff engine provenance |

Field statuses: `unchanged` \| `added` \| `removed` \| `changed`  
Unchanged fields are counted but omitted from `field_diffs`.

Missing side values surface as `"Data unavailable."` in left/right display slots.

## Non-goals

No engines, scoring, valuation, AI, mutation of R004 snapshots, or breaking APIs.
