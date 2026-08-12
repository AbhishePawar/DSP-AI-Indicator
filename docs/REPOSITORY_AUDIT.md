# Repository Audit — EPIC-P7.2

**Date:** 2026-07-29  
**Scope:** Repository engineering only (no analytical changes)

## Folder structure (top level)

```text
apps/web/              Thin Next.js client
packages/              Python monorepo (~45 domain/platform packages)
scripts/               CI, ops, release engineering
docs/                  Governance, epics, runbooks (~555 markdown files)
docker/                Compose, Caddy, Prometheus, Dockerfiles
.github/workflows/     CI / frontend / docker / release / security / release-engineering
configs/, data/, tests/, services/   Support trees
```

## Large files

| Observation | Recommendation |
|---|---|
| `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/` present locally | Keep gitignored; do not commit |
| No tracked source files >2MB observed | OK |
| `package-lock.json` large but required | Keep |

## Dead / deprecated / cleanup candidates

| Item | Notes |
|---|---|
| `packages/data-ingestion/` | Empty orphan scaffold (documented in VERSION_MATRIX) — leave marked unregistered |
| Root `VERSION` historically `v1.0.0-rc1` | Updated to `v1.0.0` in P7.2 |
| Duplicate epic docs density | Many EPIC_* guides — retain for audit trail; index via ENGINEERING_STATUS |
| Local caches (`.mypy_cache`, coverage) | Cleanup via ignore; not release artefacts |

## Duplicate documentation themes

- Multiple privacy/terms versions (`v1.0.0` and `v1.6.0`) — **keep** latest linked from app; older retained for legal history
- Release notes series (`RELEASE_NOTES_v*`) — expected; channel history
- RC1 ops handbook vs P7 production guide — complementary (RC vs production stack)

## Missing documentation (addressed in P7.2)

| Gap | Resolution |
|---|---|
| Release engineering automation docs | `scripts/release/*` + this audit set |
| Engineering status dashboard | `docs/ENGINEERING_STATUS.md` |
| Dependency / code quality audits | `docs/DEPENDENCY_AUDIT.md`, `docs/CODE_QUALITY_REPORT.md` |

## Build artefacts

Should remain untracked: `.next/`, `node_modules/`, `.venv/`, `dist/`, `coverage.xml`, `*.egg-info/`, `backups/`, `.env.production`.

## Cleanup recommendations

1. Periodically prune local caches; do not commit them.  
2. Prefer linking living docs (`VERSION_MATRIX`, `ENGINEERING_STATUS`) from README over duplicating status.  
3. Keep `data-ingestion` scaffold explicit as unregistered.  
4. Run `python scripts/release/validate_release.py` before every tag.

**Repository audit score:** **8.5 / 10**
