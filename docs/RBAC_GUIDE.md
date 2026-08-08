# EPIC-A009 — RBAC Guide

## Built-in roles

| Role | Typical permissions |
|---|---|
| `administrator` | All permissions |
| `research_analyst` | read/create research, edit drafts, submit workflow |
| `senior_analyst` | analyst + approve workflow + view audit |
| `reviewer` | read, approve/reject workflow, view audit |
| `compliance_officer` | review + manage roles |
| `investment_committee` | review + publish research |
| `portfolio_manager` | read, view audit, submit workflow |
| `read_only` | read research |

Roles are configurable via `AuthService.upsert_role` / `POST /auth/rbac/roles`.

## Permissions

- `read_research`
- `create_research`
- `edit_drafts`
- `submit_workflow`
- `approve_workflow`
- `reject_workflow`
- `publish_research`
- `view_audit`
- `manage_users`
- `manage_roles`
- `configure_platform`

Permissions are independent of business/valuation logic.

## Evaluation

```python
svc.evaluate_permission(user_id, "approve_workflow")
# → {allowed, roles, permissions, ...}

svc.protect(access_token, "manage_users")  # raises AuthorizationError if denied
```
