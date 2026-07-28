# RBAC Model (PEP-001)

## Frozen platform roles

| Role | Intent |
|---|---|
| `ADMIN` | Platform administration |
| `ADVISOR` | RIA / advisor workflows |
| `CLIENT` | End-investor (limited) |
| `RESEARCHER` | Research analyst |
| `API` | Service / integration principal |
| `GUEST` | Unauthenticated / anonymous (when allowed) |

Additive future roles (ADR required): `COMPLIANCE_OFFICER`, `ORG_ADMIN`.

## Permissions

| Permission | Typical roles |
|---|---|
| `AnalyzeCompany` | ADMIN, ADVISOR, RESEARCHER, API |
| `CompareCompanies` | ADMIN, ADVISOR, RESEARCHER, API |
| `RunWorkflow` | ADMIN, ADVISOR, API |
| `AskCopilot` | ADMIN, ADVISOR, RESEARCHER, API, CLIENT |
| `ViewReports` | All including GUEST |
| `ManageUsers` | ADMIN |
| `ManagePlatform` | ADMIN |

Exact matrix: `security_platform.ROLE_PERMISSIONS` (source of truth).

## Configurability (PEP-001)

- Default matrix is frozen for RC compatibility.
- `RoleManager` / `PermissionManager` remain the runtime surface.
- `extra_permissions` on `UserRecord` allow additive grants without new roles.
- Organisation role bindings are modelled (`OrgMembership`) but not enforced via RLS until PEP-007.

## Delegated administration (architecture)

```text
ADMIN may grant ManageUsers within org (future)
ORG_ADMIN may manage memberships only in own org (future)
```

No cross-tenant elevation without ADR.

## Enforcement points

1. `SecurityMiddleware` — path → permission map
2. `AuthorizationManager.check(principal, permission)`
3. `SecurityContext.require(permission)`

Engines never perform RBAC.
