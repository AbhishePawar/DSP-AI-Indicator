# Documentation Archive

| Field | Value |
|---|---|
| **Status** | **Active** (policy folder) |
| **Last updated** | 2026-07-23 |
| **Authority** | [DSP_FOLDER_STRUCTURE.md](../DSP_FOLDER_STRUCTURE.md) §5 · [DSP_MASTER_PROTOCOL.md](../DSP_MASTER_PROTOCOL.md) §9 |

## Purpose

Store **Historical / Archived** specifications that must not be deleted and must not enter AI default context.

## Rules

1. Move obsolete specs here; do not delete.  
2. Prefer a stub at the old path pointing here.  
3. Front-matter: `Status: Archived` · `Superseded-by: <active path>`.  
4. **AI agents: do not load this folder unless the user explicitly asks for Historical context.**  
5. Active guidance remains the `docs/DSP_*.md` suite and current epic briefs.

## Contents

Place superseded long-form specs, retired sprint blueprints, and superseded ADRs here as they are retired. Initial population may be empty; policy is in force as of Docs Suite **v1.1.0**.
