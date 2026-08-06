# AUDIT_PACKAGE_REPORT

| Field | Value |
|---|---|
| Generator | `tools/audit-package/generate-audit-package.ps1` v1.0.0 |
| Generated (UTC) | 2026-08-02T11:38:00Z |
| Product VERSION | **v1.0.0** |
| Git | `cursor/p6-1-commercial-readiness` @ `3ad829f` (`3ad829fae490c750a29e7c2bd39cb633ccb55256`) |
| Package path | `tools/audit-package/DSP_AI_INDICATOR_AUDIT_PACKAGE/` |
| Pilot posture | **GO** (closed-beta / institutional pilot) |
| Commercial GA | **REJECTED** |

---

## 1. Executive Summary

This report documents a reproducible **Enterprise Audit Package** for DSP AI Indicator Version **v1.0.0**. The package assembles narrative audit guides, authoritative documentation (including GA certification), thin-client web source, backend/research packages, build configs, and CI workflows with generated artefacts excluded.

**Release honesty (authoritative):** Closed-beta / institutional pilot is **GO** (PASS WITH CONDITIONS). Unrestricted **Commercial GA is REJECTED** per `docs/releases/GA_CERTIFICATION_REPORT.md` and `RELEASE_BOARD.md`. Limitations are not hidden.

**Architecture:** Thin client - browser presentation only; analytics / valuation / recommendation / AI reasoning owned by backend `/api/v1` and `packages/*`.

---

## 2. Files Included (summary)

| Area | Count / notes |
|---|---|
| Narrative guides | 11 |
| docs/project (key) | 21 files |
| docs/design | 16 files |
| docs/governance | 1 files |
| docs/research | 25 files |
| docs/releases | 17 files |
| docs/reviews | 7 files |
| source/web | 758 files (+ public 0) |
| source/packages | 44 packages / 1281 files |
| workflows | 6 files |
| Total package files | 2175 |

Root docs copied when present: README, CONTRIBUTING, LICENSE, CHANGELOG.

---

## 3. Files Excluded

Mandatory exclusions enforced by generator filters:

`node_modules`, `.next`, `.git`, `coverage`, `dist`, `build`, `out`, `.cache`, `.turbo`, `playwright-report`, `test-results`, `logs`, `tmp`, IDE folders, virtualenvs, `__pycache__`, `*.egg-info`, `*.log`, `*.tsbuildinfo`, `*.pyc`, and similar generated artefacts.

Secrets (`.env` family) are not copied; only `.env.example` / `.env.production.example` when present.

---

## 4. Generated Documents

| Document | Role |
|---|---|
| `00_START_HERE.md` | Orientation |
| `01_PROJECT_OVERVIEW.md` | Product overview |
| `02_ARCHITECTURE.md` | Thin client / backend ownership |
| `03_MODULE_INDEX.md` | Module index |
| `04_FEATURE_MATRIX.md` | Pilot feature scope |
| `05_RELEASE_STATUS.md` | Pilot GO / Commercial GA REJECTED |
| `06_KNOWN_LIMITATIONS.md` | Honest limitations |
| `07_REPOSITORY_MAP.md` | Repo to package map |
| `08_DEPENDENCY_REPORT.md` | Dependency guidance |
| `09_AUDIT_GUIDE.md` | Audit procedure |
| `AUDIT_MANIFEST.md` | Inventory / regen policy |
| `manifests/*` | VERSION, inventory, dependency summary, meta |

---

## 5. Validation

| Check | Result |
|---|---|
| Exclusion validation | PASS |
| guides | PASS |
| docs | PASS |
| source | PASS |
| configs | PASS |
| workflows | PASS |

---

## 6. Package Size

| Component | Size |
|---|---|
| Total | 10.80 MB |
| source/ | 9.46 MB |
| docs/ | 932.86 KB |
| configs/ | 384.45 KB |
| workflows/ | 10.66 KB |
| Split threshold | 350 MB |

---

## 7. ZIP Archives

| Archive | Size |
|---|---|
| `audit-docs.zip` | 308.57 KB |
| `audit-source.zip` | 2.81 MB |
| `audit-config.zip` | 84.97 KB |
| `audit-workflows.zip` | 4.68 KB |
| `audit-guides.zip` | 17.24 KB |
| `DSP_AI_INDICATOR_AUDIT_PACKAGE_FULL.zip` | 3.25 MB |

Archives are written under `DSP_AI_INDICATOR_AUDIT_PACKAGE/archives/` and are gitignored by default (regenerate for upload).

---

## 8. Recommendations

1. Distribute ZIPs from `archives/` to external auditors / AI review tools.
2. Cite GA Certification Report when discussing Commercial GA - do not soften **REJECTED**.
3. Re-run this generator after any release-board or VERSION change.
4. Keep `source/` and ZIPs out of git if they bloat the monorepo; commit scripts + guides + this report.
5. For Commercial GA re-evaluation, require GA-C1...GA-C7 evidence - not package regeneration alone.

---

## 9. Regeneration

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/audit-package/generate-audit-package.ps1
```

```bash
bash tools/audit-package/generate-audit-package.sh
```
