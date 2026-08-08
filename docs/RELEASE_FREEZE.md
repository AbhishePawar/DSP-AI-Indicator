# Release Freeze — EPIC-P8.0

**Effective:** 2026-07-29  
**Channel:** General Availability Candidate (`ga-candidate`)  
**Commercial tags:** Backend **`dsp_platform@2.0.0`** · Frontend **`dsp-web@2.0.0`** · API contract **`v1.0.0`**

---

## Release tag

Suggested annotated tags (create at cut):

| Tag | Meaning |
|---|---|
| `v2.0.0` | Aligned commercial GA-candidate release (web + platform packaging) |
| `platform-v2.0.0` | Backend package pin (optional explicit) |
| `api-v1.0.0` | Frozen HTTP analyse contract label (behaviour unchanged) |

Primary release package: `release/` built by `scripts/release/build_release_package.py`.

---

## Frozen modules

The following **must not** change without breaking the freeze (except via Emergency Fix Procedure below):

- Valuation Engine
- Buffett Indicator
- Financial Analysis / Business Quality / Management Quality / Economic Moat
- AI Committee
- Recommendation Engine
- Explainability
- Research Workspace
- Portfolio Intelligence
- Report Engine
- `/api/v1` analyse contracts & response schemas
- Database schema / migrations that alter analytical persistence

Also frozen for GA-candidate polish:

- Broad UI redesign / VLIS retheme
- New product features

---

## Permitted hotfix policy

| Allowed without freeze break | Not allowed |
|---|---|
| Security patches (deps, headers, auth bugs) with no contract change | Valuation / recommendation / AI logic edits |
| Ops config (Alertmanager URLs, Grafana password, scrape targets) | New analytical endpoints |
| Docs / runbook clarifications | Schema-breaking migrations |
| Build/deploy script fixes that do not change runtime analyse behaviour | UI redesign |
| Patch version bumps for CVE-only image rebuilds (`2.0.0+hotfix.N` or `2.0.1` per Version Policy) | Silent behaviour changes to `/analyse` |

Every hotfix requires:

1. Incident or CVE ticket  
2. Rollback plan  
3. `validate_release.py` + relevant `certify_p7*` / `certify_p8.py`  
4. Release notes entry  

---

## Version policy

| Surface | Policy |
|---|---|
| API contract label | Remains **`v1.0.0`** until a versioned `/api/v2` programme |
| Patch (`2.0.x`) | Hotfix / ops / security only |
| Minor (`2.y.0`) | Requires explicit unfreeze + architecture review |
| Major (`3.0.0`) | New programme; not under this freeze |

Frontend and backend commercial majors are aligned at **2.0.0** for GA-candidate. Historical interim tags (1.7.x / 2.0.1–2.0.4) remain in `docs/VERSION_HISTORY.md`.

---

## Branch strategy

| Branch | Role |
|---|---|
| `main` | Freeze trunk; only hotfixes + docs |
| `release/ga-2.0.0` | Optional release cut branch |
| `hotfix/*` | Short-lived emergency fixes → PR to `main` |
| Feature branches | **Blocked** for analytical/UI feature work until unfreeze |

No force-push to `main` / release tags.

---

## Emergency fix procedure

1. Declare severity (S1/S2) per incident runbook.  
2. Prefer **rollback** (`scripts/rollback_production.sh`) over code change.  
3. If code required: branch `hotfix/<ticket>`, minimal diff, no engine edits unless explicitly approved as security-critical with architecture sign-off.  
4. Run `python scripts/ops/certify_p8.py` (and targeted tests).  
5. Tag patch; deploy; validate `/health/ready` + smoke.  
6. Postmortem within 5 business days; update risk register / debt.

---

## Unfreeze

Only Product + Architecture owners may lift freeze via written decision amending this document and `PRODUCTION_VERSION_MANIFEST.json`.
