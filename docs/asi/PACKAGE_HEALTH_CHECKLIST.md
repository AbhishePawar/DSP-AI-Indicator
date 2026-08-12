# Package Health Checklist (ASI)

| Field | Value |
|---|---|
| **Template version** | `1.0.0` |
| **Rule** | Every modified package must score **PASS** on all applicable rows before task COMPLETE |

Duplicate this section once per modified package in the ASI task brief.

---

## Checklist — Package: `<package_name>`

| Field | Value |
|---|---|
| **ASI task** | ASI-00N |
| **Date** | YYYY-MM-DD |
| **Unlock scope** | (paths allowed) |
| **Overall Health** | **PASS** \| **FAIL** |

| Dimension | Status | Evidence / notes |
|---|---|---|
| **Repository Integrity** | PASS / FAIL / N/A | Discoverable; registered; no orphan refs |
| **Documentation** | PASS / FAIL / N/A | README accurate; freeze/non-goals clear |
| **Architecture** | PASS / FAIL / N/A | Boundaries; Tier-0 CV; **RS-001…RS-010** if research report packages touched |
| **Dependencies** | PASS / FAIL / N/A | Allowed deps only; no new illegal edges |
| **Public API** | PASS / FAIL / N/A | Exports stable; no unintended surface growth |
| **Testing** | PASS / FAIL / N/A | Relevant tests pass; additive only |
| **Architecture Tests** | PASS / FAIL / N/A | `test_architecture` present/updated as scoped |
| **CI** | PASS / FAIL / N/A | Covered by CI or explicitly deferred to ASI-007 |
| **Versioning** | PASS / FAIL / N/A | Version consistent with matrix/pyproject |
| **Metadata** | PASS / FAIL / N/A | name/description/python requires sane |
| **Overall Health** | **PASS** / **FAIL** | FAIL if any required row is FAIL |

### Scoring rules

- **PASS** — criterion met with cited evidence.  
- **FAIL** — criterion unmet; task cannot COMPLETE.  
- **N/A** — not in this task’s unlock scope; must justify.

### Fail disposition

If FAIL: either fix within unlock scope, or register as **Deferred Debt** / **Accepted Debt** with ADR when acceptance is architectural — then obtain human approval before COMPLETE.
