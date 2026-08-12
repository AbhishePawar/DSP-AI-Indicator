# AUDIT_MANIFEST

| Field | Value |
|---|---|
| Package name | `DSP_AI_INDICATOR_AUDIT_PACKAGE` |
| Generator version | 1.0.0 |
| Product version | See `manifests/VERSION` (expected **1.0.0**) |
| Commercial posture | Closed-beta / institutional pilot **GO**; Commercial GA **REJECTED** |
| Location | `tools/audit-package/DSP_AI_INDICATOR_AUDIT_PACKAGE/` |

---

## Contents checklist

| Artefact | Present when regenerated |
|---|---|
| Guides `00`–`09` | Yes (from `tools/audit-package/templates/`) |
| This manifest | Yes |
| `docs/` copies | Yes |
| `source/web` + `source/packages` | Yes (gitignored in repo; regenerate locally) |
| `configs/` | Yes (gitignored; regenerate) |
| `workflows/` | Yes (gitignored; regenerate) |
| `manifests/` | Yes |
| `archives/*.zip` | Yes (gitignored; regenerate) |
| `reports/AUDIT_PACKAGE_REPORT.md` | Yes |

---

## Exclusions (mandatory)

Do not include: `.next`, `node_modules`, `.git`, `coverage`, `dist`, `build`, `out`, `.cache`, `.turbo`, `playwright-report`, `test-results`, `logs`, `tmp`, `.idea`, `.vscode`, `*.cache`, `*.log`, `*.tsbuildinfo`, `__pycache__`, `.venv`, `*.egg-info`, and similar generated artefacts.

---

## Regeneration

```powershell
pwsh -File tools/audit-package/generate-audit-package.ps1
```

```bash
bash tools/audit-package/generate-audit-package.sh
```

One-command regenerate is the supported release-process path for auditors who need a full source tree + ZIPs.

---

## Git policy (repository hygiene)

Committed under `tools/audit-package/`:

- Generator scripts (`.ps1`, `.sh`)
- Narrative templates + package guide copies (`00`–`09`, `AUDIT_MANIFEST`)
- `AUDIT_PACKAGE_REPORT.md`
- Lightweight `manifests/` summaries when present

Typically **not** committed (see `tools/audit-package/.gitignore`):

- `archives/*.zip`
- Full `source/` tree copy
- Bulk `configs/` / `workflows/` / nested `docs/*` copies

Rationale: reproducible without bloating the main project; auditors run the generator for a complete offline package.
