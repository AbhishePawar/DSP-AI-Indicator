# 09 — Audit Guide

How to perform an enterprise audit using this package **without** redesigning the platform.

---

## 1. Audit objectives

| Objective | Pass criteria (summary) |
|---|---|
| Trust / CV-001 | No fabricated numbers on flagship paths; honest unavailable states |
| Thin client | No browser-side valuation/recommendation/AI reasoning |
| Release honesty | Pilot GO acknowledged; Commercial GA REJECTED not contradicted |
| RS reports | RS-001…RS-010 coverage or explicit validation fail |
| Security posture | Invite-only pilot appropriate; not claiming unrestricted public GA security cert |
| Reproducibility | Package regenerable via scripts; exclusions honored |

---

## 2. Suggested procedure

### Phase A — Orientation (1–2 h)

1. Read `00_START_HERE.md`, `05_RELEASE_STATUS.md`, `06_KNOWN_LIMITATIONS.md`.
2. Skim `docs/releases/GA_CERTIFICATION_REPORT.md` and `RELEASE_BOARD.md`.
3. Confirm VERSION = 1.0.0 in `manifests/VERSION`.

### Phase B — Architecture boundary (2–4 h)

1. Read `02_ARCHITECTURE.md` + `docs/project` Architecture Bible excerpts.
2. Grep `source/web` for valuation/recommendation engine patterns; expect **clients**, not engines.
3. Confirm analytical routers/engines under `source/packages` (`api_platform`, `dsp_platform`, engine packages).

### Phase C — Trust & product honesty (2–4 h)

1. Auth surfaces: Request Access / forgot / reset / verify honesty.
2. Pricing: illustrative / not purchasable.
3. No silent demo ticker defaults in web source.
4. Trust ladder usage vs GA-C3 residual (document, do not “fix” in audit-only mode).

### Phase D — Research & RS (as needed)

1. REP-002 books under `docs/research/`.
2. Report specs / explainability docs.
3. Spot-check that empties prefer **Data unavailable.**

### Phase E — Ops & CI

1. Review `workflows/` and release runbooks under `docs/releases/`.
2. Note open evidence gates (screenshots, Firefox/Safari, LHCI).

### Phase F — Findings

Classify findings as:

| Class | Action |
|---|---|
| CRITICAL trust/fabrication | Must fail commercial claims; escalate |
| GA condition (already known) | Cite GA-C#; do not rebrand as new architecture crisis |
| Pilot-accepted limitation | Record; do not demand silent fill |
| Architecture gap | **STOP & document** — no redesign in audit package |

---

## 3. Out of scope for this package process

- Feature implementation, refactors, redesigns
- Engine/API/scoring/boundary changes
- Inventing Commercial GA approval
- Committing secrets or `node_modules`

---

## 4. Deliverables auditors may produce

- Findings memo referencing package paths + commit/VERSION
- Confirmation that regeneration scripts produce a clean tree
- Explicit statement: pilot GO vs Commercial GA REJECTED

---

## 5. Regeneration & upload

```powershell
pwsh -File tools/audit-package/generate-audit-package.ps1
```

Upload ZIPs from `archives/` to review tools (Claude/Gemini/etc.). Prefer split archives if any single archive exceeds tool limits.
