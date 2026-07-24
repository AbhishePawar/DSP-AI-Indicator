# DSP Project Protection Framework

| Field | Value |
|---|---|
| **Version** | `1.1.0` |
| **Status** | **Stable** (permanent) |
| **Last updated** | 2026-07-23 |
| **Audience** | Humans · Cursor · ChatGPT · maintainers |
| **AI load** | **High** — load before any implementation; cite from Master Protocol |

## Purpose

Permanent protection system so **production-certified progress is never accidentally lost** to AI mistakes, refactoring, scope creep, doc churn, human error, or technical failure.

This framework is part of DSP forever. Future AI sessions **must** respect it.

**Project integrity has higher priority than feature development.**

Canonical live health fields → [DSP_STATUS.md](DSP_STATUS.md) §Project Health.  
Canonical protected-module table → [DSP_STATUS.md](DSP_STATUS.md) §Protected (kept in sync with §2 below).

---

## 0. PROJECT PROTECTION RULE (mandatory — before any sprint)

Before implementing **any** sprint, AI **must**:

| # | Action |
|---|---|
| 1 | Read [DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md) |
| 2 | Read [DSP_STATUS.md](DSP_STATUS.md) |
| 3 | Verify **sprint scope** (exactly one scope class) |
| 4 | Verify **protected modules** (STATUS §Protected) |
| 5 | **Refuse** to modify production-certified modules unless **explicitly unlocked** |
| 6 | **Create or recommend a checkpoint** before major architectural work |

If any step fails or is uncertain → **DO NOT IMPLEMENT**. Integrity > features.

Also run Sprint Safety Rules (§3) and the AI Safety Checklist ([DSP_AI_COLLABORATION.md](DSP_AI_COLLABORATION.md)).

---

## 1. Project Protection Policy

1. **Protect all production-certified work.** Completed modules are **frozen** until explicitly unlocked.  
2. **Unlock requires explicit human instruction** naming the module/epic — implied permission is invalid.  
3. **Improve-in-place inside active scope only.** No drive-by refactors of frozen surfaces.  
4. **Prefer recovery over rewrite.** Restore from checkpoint/tag before redesigning.  
5. **Documentation never deletes history** — archive only ([§8](#8-documentation-safety)).  
6. **If uncertain → DO NOT MODIFY** ([DSP_AI_COLLABORATION.md](DSP_AI_COLLABORATION.md) Safety Checklist).  
7. **Recoverability is a first-class requirement** — every milestone must be restorable via Git + remote + STATUS checkpoint.  
8. **Integrity > features** — never trade frozen progress for sprint velocity.

---

## 2. Protected Modules

AI **must never modify** the following without **explicit** unlock instructions.

| Module | Examples / surfaces | Default |
|---|---|---|
| **Research Platform** | Research packages · Research Mode · compliance terminology ports | **Frozen** |
| **Management Intelligence Engine (MIE / M1)** | Certified M1 domain + presentation | **Frozen** |
| **Economic Moat Intelligence Engine (EMI / M2)** | Certified moat domain + presentation | **Frozen** |
| **Earnings Quality Intelligence Engine (EQI / EQ1)** | Certified EQ domain + presentation | **Frozen** |
| **Completed Web Sprints** | Closed L1.2 / V* / M* / EQ* deliverables | **Frozen** |
| **Decision / valuation / recommendation math** | Python engine cores | **Frozen** (epic-gated) |
| **Public API `/api/v1`** | HTTP contracts · public façades | **Frozen** (RC/major only) |
| **PR1.0–PR1.2 freezes** | Research Mode · PXB · VLIS | **Frozen** (implement within contract) |

**Living copy** of this table (plus health fields) → [DSP_STATUS.md](DSP_STATUS.md). When certifying a new module, update **both** STATUS and this section.

**Unlock protocol**

```text
1. User explicitly names module + reason + epic
2. Agent records unlock intent in handoff
3. Changes stay inside declared scope
4. Prove GREEN before complete
5. Re-freeze when epic closes; update STATUS
```

---

## 3. Sprint Safety Rules

Before **every** implementation (code or structural docs):

| # | Verify | Fail action |
|---|---|---|
| 1 | **Sprint scope** — exactly one scope class declared | Stop · ask |
| 2 | **Target package / path** — matches epic DO NOT MODIFY | Stop |
| 3 | **Frozen modules** — target not protected, or unlock given | Stop |
| 4 | **Dependency impact** — no upward/circular/forbidden deps | Stop · ADR |
| 5 | **Change approval level** ([§9](#9-change-approval-levels)) satisfied | Escalate |
| 6 | **Last Safe Checkpoint** known ([DSP_STATUS.md](DSP_STATUS.md)) | Create checkpoint first |

Full AI checklist → [DSP_AI_COLLABORATION.md](DSP_AI_COLLABORATION.md).

---

## 4. Git Strategy

| Mechanism | Purpose | Rule |
|---|---|---|
| **Feature branches** | Isolate sprint/epic work | `feat/<epic>-<short>` or `docs/<topic>`; no direct force-push to `main`/`master` |
| **Checkpoint commits** | Recoverable save points during a sprint | After GREEN slices; message states checkpoint intent; **only when user asks to commit** |
| **Milestone tags** | Epic / sprint completion markers | `milestone/<epic>-sN` (e.g. `milestone/L1.2-s8`) |
| **Release tags** | Ship / RC markers | SemVer / RC (e.g. `v1.0.0-rc1`, `web-2.x.x`) |
| **No history rewrite on shared branches** | Protect collaborators | No `push --force` to main; no destructive reset unless user explicitly orders recovery |

Agents: **do not commit or push unless the user asks.** Document the intended Git action in the handoff.

---

## 5. Backup Strategy

| Cadence | What | Where |
|---|---|---|
| **Daily** | Working tree + committed history | Local Git; push to remote when user allows |
| **Weekly** | Full repo snapshot preference | Remote + optional offline zip of clean tree (human-owned) |
| **Remote repository** | Authoritative off-machine copy | Configured `origin` (GitHub/GitLab/etc.) |
| **Milestone / release** | Tag + push tags | Remote tags = recovery anchors |

**Recovery procedure (backup)**

```text
1. Identify Last Safe Checkpoint (STATUS) or tag
2. Ensure remote is reachable; fetch tags
3. Create recovery branch from checkpoint/tag (do not destroy main)
4. Verify GREEN on recovery branch
5. Merge or replace only with explicit human approval
```

Humans own remote credentials and offline media. Agents never delete remotes or force-update protected branches.

---

## 6. Cursor AI Rules (mandatory)

| Rule | Behavior |
|---|---|
| **Scope lock** | Never refactor outside the declared sprint scope |
| **No rewrite of completed modules** | Never rewrite protected / production-certified modules |
| **No public API renames** | Never rename `/api/v1` routes or public façades without Breaking-level approval |
| **No deletion of working code** | Never delete working code “for cleanliness”; archive or leave; prefer reverse via Git |
| **Unclear scope** | **Stop and ask** — do not guess |
| **Docs ≠ code** | Documentation tasks must not touch application code |
| **Archive ≠ delete** | Never delete historical docs |
| **Checkpoint awareness** | Before risky work, note Last Safe Checkpoint from STATUS |

Detail + safety checklist → [DSP_AI_COLLABORATION.md](DSP_AI_COLLABORATION.md).

---

## 7. Recovery Procedure

| Incident | First response | Then |
|---|---|---|
| **Bad AI changes (uncommitted)** | `git status` · discard or restore specific files from HEAD / checkpoint | Re-run Safety Checklist; do not “fix forward” blindly |
| **Bad commits** | Revert commit(s) on a recovery branch; avoid rewriting shared history | Prove GREEN; user approves merge |
| **Deleted files** | Restore from Git history or remote tag | If docs: check `docs/archive/` |
| **Merge mistakes** | Abort if in progress; else recovery branch from pre-merge checkpoint | Re-merge with smaller scope |
| **Corrupted documentation** | Restore last good `docs/` tree from tag/checkpoint; **never** invent replacements for freezes | Re-apply only intentional doc edits |
| **Protected module touched by mistake** | Immediately restore those paths from Last Safe Checkpoint | Report in handoff; re-freeze |

**Priority:** restore known-good state → verify GREEN → continue. Do not compound damage with large rewrites.

---

## 8. Documentation Safety

1. Historical documents **must never be deleted**.  
2. Move obsolete specs to `docs/archive/` ([DSP_FOLDER_STRUCTURE.md](DSP_FOLDER_STRUCTURE.md) §Archive).  
3. Prefer stubs at old paths → “Moved to archive…”.  
4. AI **must not** load `docs/archive/**` unless explicitly requested.  
5. Suite edits stay cross-linked; one canonical source per topic ([DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md) §11).  
6. Corrupted suite files → recover from Git (§7), then re-apply.

---

## 9. Change Approval Levels

| Level | Examples | Required before implementation |
|---|---|---|
| **Documentation** | `DSP_*` suite, sprint notes, archive moves | Task says docs-only; no code; Safety Checklist N/A for code paths |
| **Presentation** | `apps/web` view-models / UI within epic | Scope = Presentation; protected UI untouched unless unlock; no API/engine edits |
| **Domain** | Package engine / scoring / aggregates | Explicit Domain epic; dependency check; GREEN full regression when engines touched |
| **Architecture** | Ownership, ports, stack order, new packages | ADR Proposed/Accepted; Master + Architecture loaded; lead/human confirm |
| **Breaking** | `/api/v1` breaks, façade renames, RC bump | Explicit Breaking approval; VERSION_MATRIX / RC plan; ADR; no silent breaks |

Higher levels subsume lower review. Unclear level → treat as **Architecture** and stop for confirmation.

---

## 10. Project Health (STATUS contract)

[DSP_STATUS.md](DSP_STATUS.md) **must always** track:

| Field | Meaning |
|---|---|
| **Current Version** | Backend RC / suite / notable client versions |
| **Active Sprint** | Epic + sprint id or `none` |
| **Production Modules** | Pointer / summary of protected certified set |
| **Regression Status** | GREEN / NOT GREEN / unknown (with last proof) |
| **Project Health** | `Healthy` · `At Risk` · `Recovering` |
| **Last Safe Checkpoint** | Git ref, tag, or commit description + date |

Agents updating STATUS after a milestone must refresh these fields. Do not leave stale “Last Safe Checkpoint”.

---

## 11. Related

[DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md) · [DSP_STATUS.md](DSP_STATUS.md) · [DSP_AI_COLLABORATION.md](DSP_AI_COLLABORATION.md) · [DSP_DECISION_RECORDS.md](DSP_DECISION_RECORDS.md) · [DSP_CODING_STANDARDS.md](DSP_CODING_STANDARDS.md) · [DSP_FOLDER_STRUCTURE.md](DSP_FOLDER_STRUCTURE.md)
