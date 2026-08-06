# Dependency Audit — EPIC-P7.2

**Date:** 2026-07-29  
**Policy:** Audit only — **do not** auto-upgrade packages in this epic.

## Python (monorepo)

| Area | Status |
|---|---|
| Install surface | Root `pyproject.toml` extras `[dev]` |
| Platform package | `dsp_platform==1.7.2` |
| Tooling | pytest, ruff, black, mypy (CI) |
| Security gate | `.github/workflows/security.yml` → `pip-audit` |

### Observations

- Monorepo uses many internal packages under `packages/` with pinned own versions in each `pyproject.toml`.
- No automatic bulk upgrade performed (constraint).
- Operators should run `pip-audit` in CI and triage high/critical CVEs without silent majors.

### Upgrade recommendations (manual)

1. Review `pip-audit` CI failures before merging.  
2. Prefer patch upgrades for security; avoid engine-touching dependency jumps.  
3. Keep Python CI matrix on 3.11 + 3.12.

## Frontend (`apps/web`)

| Area | Status |
|---|---|
| Package manager | npm (`package-lock.json` present) |
| App version | `2.0.2` |
| Runtime | Next.js App Router, React 19 line (lockfile) |
| Security gate | `npm audit --audit-level=high` in Security workflow |

### Observations

- Lockfile is the source of truth for reproducible installs (`npm ci`).  
- Duplicate React copies were not forced-resolved in this epic.  
- Unused dependency detection should use `depcheck` / Knip in a future cleanup epic — not auto-applied here.

### Upgrade recommendations (manual)

1. Address `npm audit` high+ findings intentionally.  
2. Avoid Next major bumps without a dedicated frontend epic.  
3. Keep `NEXT_PUBLIC_*` free of secrets.

## Licence review

| Class | Notes |
|---|---|
| Project | See root `LICENSE` |
| Python deps | Review via `pip-licenses` when packaging commercially |
| npm deps | Review via `license-checker` before redistribution |

No licence auto-rewrites performed.

## Duplicate dependencies

- Internal packages intentionally duplicate thin façade patterns — by architecture, not accident.  
- Watch for duplicate HTTP/JWT stacks between `security_platform` and gateway middleware.

**Dependency audit score:** **8.0 / 10** (gates present; no forced upgrades)
