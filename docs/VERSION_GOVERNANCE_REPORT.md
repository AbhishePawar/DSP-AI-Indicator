# Version Governance Report — EPIC-P8.0

**Date:** 2026-07-29  
**Living baseline:** Backend **2.0.0** · Frontend **2.0.0** · API **v1.0.0** · Channel **`ga-candidate`**

## Alignment table

| Surface | Expected |
|---|---|
| `packages/dsp_platform` `__version__` / pyproject | `2.0.0` |
| `apps/web` foundation + package.json + VERSION_MANIFEST | `2.0.0` / epic `P8.0` / channel `ga-candidate` |
| `PRODUCTION_VERSION_MANIFEST.json` | `2.0.0` / `2.0.0` / `v1.0.0` / freeze true |
| `docs/VERSION_MATRIX.md` | pins `**2.0.0**` |
| `docs/VERSION_HISTORY.md` | includes P8.0 GA candidate row |
| Docker compose defaults | `dsp-api:2.0.0` · `dsp-web:2.0.0` |

## Gates

- `scripts/release/validate_release.py` EXPECTED = 2.0.0 / 2.0.0 / P8.0 / ga-candidate
- `scripts/ops/certify_p8.py` GA + prior cert chain
- Living certs track GA baseline

## Suggested git tags

- `v2.0.0` (aligned commercial GA-candidate)
- `api-v1.0.0` (contract label — behaviour frozen)

## Notes

- Interim tags 1.7.x / 2.0.1–2.0.4 retained historically; commercial GA-candidate aligns at **2.0.0**.
- Release freeze active — no analytical drift.

**Version governance:** **PASS** (after P8.0 alignment)
