# api_platform

## 1. Package Purpose

DSP API Platform — FastAPI HTTP surface over dsp_platform (K1.1)

## 2. Responsibilities

- Provide the `api_platform` domain façade for DSP AI Indicator.
- Expose stable public exports via `__all__`.
- Remain within architecture allowlists (ASI-003).

## 3. Package Status

**Active · EPIC-002 composition** · Epic K + EPIC-002  
Version: **0.2.0**  
Canonical versions → [VERSION_MATRIX.md](../../docs/VERSION_MATRIX.md) · [DSP_STATUS.md](../../docs/DSP_STATUS.md)

## 4. Public API

- Package version: `0.2.0`
- `app`
- `create_app`
- `__version__`

Composition routes (via `create_app`):
`POST /api/v1/analyse` · `POST /api/v1/validate` · `GET /api/v1/health|version|capabilities`

Guide → [API_V1_COMPOSITION.md](../../docs/API_V1_COMPOSITION.md)

## 5. Package Structure

```
packages/api_platform/
├── README.md
├── pyproject.toml (if present)
├── src/api_platform/
│   └── …
└── tests/
```

## 6. Dependencies

Declared in `pyproject.toml`:

- `dsp_platform`
- `contracts`
- `fastapi>=0.115.0`
- `uvicorn>=0.30.0`
- `httpx>=0.27.0`

## 7. Architecture Notes

- Feature freeze: do not add product behaviour under ASI documentation tasks.
- Forbidden imports are enforced by `tests/test_architecture.py` where present.
- Thin-client / platform rules → [ARCHITECTURE_GOVERNANCE.md](../../docs/ARCHITECTURE_GOVERNANCE.md).

## 8. Usage Examples

```python
from api_platform import app
```

## 9. Testing

```bash
pytest packages/api_platform/tests -q --import-mode=importlib -p no:cov
```

## 10. Governance

- Ownership → [PACKAGE_OWNERSHIP_MATRIX.md](../../docs/PACKAGE_OWNERSHIP_MATRIX.md)
- Governance standard → [PACKAGE_GOVERNANCE.md](../../docs/PACKAGE_GOVERNANCE.md)
- ASI framework → [ASI_IMPLEMENTATION_FRAMEWORK.md](../../docs/ASI_IMPLEMENTATION_FRAMEWORK.md)

## 11. Limitations

- Documents **current** implementation only.
- Does not embed upstream report payloads or re-run foreign domain math.
- Not a substitute for epic freeze docs under `docs/`.

## 12. Future Extensions (future only)

Any new analytics, providers, or API shapes require an approved epic and ADR. **Not implemented in this package README.**
