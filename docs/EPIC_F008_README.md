# EPIC-F008 — Enterprise Administration Console

Status: **COMPLETE** · Priority: P0 · Frontend Foundation **v0.9.0**

## Summary

Enterprise Administration Console at `/admin`. Consumes frozen A010
`/api/v1/admin/*` APIs only. Display-only operational visibility for
identity, audit, platform health, metrics, workflow metadata, and
research archive references. No client-side administration logic.

## Docs

| Doc | Path |
|---|---|
| Architecture | [EPIC_F008_ADMIN_ARCHITECTURE.md](EPIC_F008_ADMIN_ARCHITECTURE.md) |
| Developer Guide | [EPIC_F008_DEVELOPER_GUIDE.md](EPIC_F008_DEVELOPER_GUIDE.md) |

## Success

- Backend untouched · API unchanged
- No client administration logic
- Ready for **F009 — Settings & User Preferences** (complete → see F009)

## Final

**PASS** — Enterprise Administration Console production-ready.

## Next

**F010 — Responsive Design & Accessibility Validation**
