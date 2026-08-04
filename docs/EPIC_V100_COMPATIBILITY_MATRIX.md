# EPIC-V100 — Compatibility Matrix

| Component | Compatible with `dsp_platform` 1.0.0 | Notes |
|---|---|---|
| HTTP API RC | **v1.0.0-rc1** | Frozen; unchanged |
| `api_platform` | 0.2.0 | Additive A008–A010 routers |
| `security_platform` | 0.2.0 | Legacy `/auth/login` unchanged |
| `production_platform` | 0.3.0 | Feature flags / config viewers optional |
| `persistence` | 0.1.0 | A008 |
| `auth` | 0.1.0 | A009 |
| `admin` | 0.1.0 | A010 |
| Research / valuation / financial | frozen package versions | No behaviour change |
| Web UI (if present) | Web notes separate | See `RELEASE_NOTES_v1.0.0.md` (web) |

## Forward compatibility

Additive institutional routes under `/api/v1` remain the extension model.
Breaking HTTP changes require a new API RC — not part of V100.
