# Rollback Template (ASI)

| Field | Value |
|---|---|
| **Template version** | `1.0.0` |
| **Rule** | No ASI task is COMPLETE without a filled rollback plan |

Copy into the task brief or save as `docs/asi/rollback/ASI-00N.md`.

---

```markdown
# Rollback Plan — ASI-00N <Task Title>

| Field | Value |
|---|---|
| **ASI task** | ASI-00N |
| **Date** | YYYY-MM-DD |
| **Author** | |
| **Checkpoint / tag before change** | (branch tip SHA or tag) |
| **Status** | Draft \| Ready \| Executed \| Not needed (justify) |

## 1. Change Inventory

### Files Modified
| Path | Nature of change |
|---|---|
| | |

### Files Added
| Path | Purpose |
|---|---|
| | |

### Files Removed
| Path | Disposition (archive location if any) |
|---|---|
| | |

## 2. Rollback Procedure

Ordered steps to restore the pre-task state:

1. Ensure working tree is clean or stash unrelated work.
2. Identify checkpoint: `<sha-or-tag>`.
3. Restore paths (prefer path-scoped restore over hard reset on shared branches):
   - `git checkout <checkpoint> -- <path> …` **or**
   - Revert the task commit(s) with `git revert` if already on main.
4. Remove added files that should not remain.
5. Restore any archived docs from `docs/archive/` if applicable.
6. Re-apply freeze notes in STATUS if unlock was opened.

**Forbidden without explicit user order:** `git reset --hard` on shared `main`, force-push.

## 3. Validation after Rollback

| Check | Command / method | Pass criteria |
|---|---|---|
| Working tree | `git status` | Expected files only |
| Regression | `pytest --import-mode=importlib -p no:cov -q` | GREEN vs pre-task baseline |
| Architecture (if touched) | package `test_architecture` | PASS |
| Docs consistency | STATUS / CHANGELOG / matrix | No dangling ASI unlock |
| Freeze posture | STATUS Protected | Re-frozen |

## 4. Residual Risk After Rollback

What may still be wrong (e.g. remote CI cache, local venv). Mitigation.

## 5. Sign-off

| Role | Name | Date |
|---|---|---|
| Author | | |
| Reviewer (optional) | | |
```

---

## Guidance

- Prefer **revert commits** over history rewrite when the task already landed on `main`.  
- Path-scoped checkout is safest for partial rollback during a multi-file task.  
- Always record the **pre-task SHA** before unlocking files.
