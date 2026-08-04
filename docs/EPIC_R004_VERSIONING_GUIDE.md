# EPIC-R004 — Versioning Guide

## Lineage

Each snapshot belongs to a `lineage_id`. First archive creates version `1`
(no parent). Subsequent versions pass `parent_snapshot_id`; the service:

1. Loads the parent (must exist, same kind)
2. Sets `version_number = parent.version_number + 1`
3. Inherits the parent `lineage_id`

## Integrity

`content_sha256 = SHA-256(canonical_json(payload))` where canonical JSON uses
`sort_keys=True` and compact separators. Retrieval re-validates the hash.

## History

`GET /research/archive/lineages/{lineage_id}/history` returns snapshots ordered
by `version_number` ascending.

## Comparison

`POST /research/archive/compare` returns whether two snapshots share kind,
lineage, and content hash — plus version numbers and timestamps. It does **not**
mutate or rewrite payloads.

## Determinism

Fixed `snapshot_id` + `archived_at` + identical payload → identical snapshot
dict (including hash).
