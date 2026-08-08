# EPIC-V100 — Migration Guide · 0.22.0 → 1.0.0

## Summary

**No application migration required.**

This release is a semantic version promotion and certification of the existing
`dsp_platform` 0.22.0 behaviour surface.

## Actions

| Consumer | Action |
|---|---|
| Python imports of `dsp_platform` | Optional: pin / expect `__version__ == "1.0.0"` |
| HTTP `/api/v1` clients | None — contract remains **v1.0.0-rc1** |
| Auth `/auth/rbac/*` | None |
| Admin `/admin/*` | None |
| Persistence `/persistence/*` | None |

## Breaking changes

None.

## Rollback

Redeploy prior artifact tagged `dsp_platform==0.22.0` if required. No data
migration applies (in-memory persistence default; metadata-only stores).
