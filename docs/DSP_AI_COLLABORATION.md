# DSP AI Collaboration

| Field | Value |
|---|---|
| **Version** | `1.2.1` |
| **Status** | **Active** (Living) |
| **Last updated** | 2026-07-23 |
| **Audience** | Cursor · ChatGPT · directing humans |

## Purpose

**Canonical** AI operating contract: safety checklist, context rules, prompts.  
Load order → [DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md) §2.  
Protection / recovery / Git / approvals → [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) (do not fork those policies here).

**Project integrity has higher priority than feature development.**

---

## 0. PROJECT PROTECTION RULE (before any sprint)

| # | Must |
|---|---|
| 1 | Read [DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md) |
| 2 | Read [DSP_STATUS.md](DSP_STATUS.md) |
| 3 | Verify sprint scope |
| 4 | Verify protected modules |
| 5 | Refuse to modify production-certified modules unless explicitly unlocked |
| 6 | Create or recommend a checkpoint before major architectural work |

Canonical copy → [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) §0. If uncertain → **DO NOT IMPLEMENT**.

---

## 1. Default context (reminder)

**Always:** Master Protocol (P1) + Status (P2).  
**Before implementation:** [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) (Sprint Safety + Cursor AI Rules).  
**Then:** Architecture / Roadmap / this file / Coding Standards **only if needed**.  
**Never by default:** `docs/archive/**`, full PR1 dumps, all epic sprint folders.

Priority classes → Master Protocol §3.

---

## 2. AI Safety Checklist (mandatory before any code change)

Answer **Yes/No**. If any answer is **uncertain → DO NOT MODIFY**.

| # | Check |
|---|---|
| 1 | Is the target module **frozen / protected**? ([DSP_STATUS.md](DSP_STATUS.md) §Protected) |
| 2 | Is the change **in declared scope**? (Presentation \| Domain \| Research \| Decision \| Portfolio \| Infrastructure \| Documentation) |
| 3 | Is the **change approval level** satisfied? ([DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) §9) |
| 4 | Does similar logic **already exist**? (search before inventing) |
| 5 | Does it violate **architecture / ownership / thin client**? ([DSP_ARCHITECTURE.md](DSP_ARCHITECTURE.md)) |
| 6 | Does it break **backward compatibility** of `/api/v1` or public façades? |
| 7 | Does it affect **production-certified / completed** modules without an explicit unlock? |
| 8 | Would it invent figures, Street consensus, or Buy/Sell UI against Research Mode? |
| 9 | Is the user request **documentation-only** but you are about to edit code (or vice versa)? |
| 10 | Is **Last Safe Checkpoint** known if the change is risky? ([DSP_STATUS.md](DSP_STATUS.md) §Project Health) |

**If frozen and user did not explicitly instruct an override → stop.**

Sprint Safety Rules (scope · package · frozen · deps) → [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) §3.

---

## 3. Cursor AI Rules (mandatory — summary)

Full table → [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) §6.

- Never refactor outside scope.  
- Never rewrite completed / protected modules.  
- Never rename public APIs without Breaking approval.  
- Never delete working code “for cleanup”.  
- Stop and ask if scope is unclear.  
- Docs-only tasks must not touch application code.  
- Never delete historical docs — archive only.  
- Do not commit/push unless asked.

---

## 4. Implementation contract

1. Obey sprint **DO NOT MODIFY** lists and protected-module list.  
2. No backend/API/engine edits under a Presentation sprint.  
3. No fabricated financial figures.  
4. No Buy/Sell/Official Target Price unless flags allow.  
5. Improve-in-place > rewrite.  
6. No commit/push unless asked.  
7. No unsolicited markdown (except when the task **is** documentation).  
8. After Python package edits → prove **GREEN** ([DSP_CODING_STANDARDS.md](DSP_CODING_STANDARDS.md)).  
9. On damage → recover per [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) §7; do not compound with rewrites.

---

## 5. Context efficiency

| Do | Don’t |
|---|---|
| Grep/Glob for symbols | Read whole packages “to be safe” |
| Cite `path` + lines | Paste multi-thousand-line files |
| Reuse builders/components | Parallel “v2” trees |
| One sprint brief | Load L1+V2+M1+M2+EQ1 together |
| Ask when freeze is ambiguous | “Quick engine tweak” |
| Restore from checkpoint | “Rewrite the module cleanly” after a mistake |

---

## 6. Prompt patterns

**Feature**

```text
Epic: <id>  Sprint: <n>  Scope: <one of 7>
Approval level: Documentation|Presentation|Domain|Architecture|Breaking
DO NOT MODIFY: <list>
Protected check: completed
Last Safe Checkpoint: <ref or none>
Implement: <scope>
Return: <validation>
```

**Documentation**

```text
Update docs/DSP_*.md only. No application code.
Cross-link; one canonical source per topic.
Respect DSP_PROJECT_PROTECTION (archive ≠ delete).
```

**Bugfix**

```text
Reproduce → owner package → minimal fix → GREEN
If protected: require explicit unlock or restore
```

**Recovery**

```text
Incident: <type>
Restore from: <STATUS Last Safe Checkpoint | tag>
Prove GREEN; do not force-push main
```

---

## 7. Handoff template

```text
Scope: <class>
Approval level: <level>
Changed: <paths>
Protected untouched: <yes/no>
Safety checklist: <pass>
GREEN: <command + result | N/A>
STATUS health updated: <yes/no | N/A>
Docs: <updated | N/A>
Risks: <one line>
```

---

## 8. Anti-patterns

- Loading all of `docs/` or `docs/archive/` without request  
- Duplicating architecture/roadmap/standards/protection into sprint notes  
- Client-side “temporary” scoring engines  
- Silent redesign when docs conflict with convenience  
- Deleting working code or historical docs  
- Continuing after a bad AI edit instead of recovering  

---

## 9. Related

[DSP_MASTER_PROTOCOL.md](DSP_MASTER_PROTOCOL.md) · [DSP_STATUS.md](DSP_STATUS.md) · [DSP_PROJECT_PROTECTION.md](DSP_PROJECT_PROTECTION.md) · [DSP_CODING_STANDARDS.md](DSP_CODING_STANDARDS.md) · `.cursor/rules/`
