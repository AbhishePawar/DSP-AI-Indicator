# /api/v1 Composition — Endpoint Guide (EPIC-002)

| Field | Value |
|---|---|
| **API package** | `api_platform` **0.2.0** |
| **Contract RC** | `v1.0.0-rc1` surface + composition routes |
| **OpenAPI** | `/openapi.json` |

## Versioning

- **API version label:** `v1` (path prefix `/api/v1`)
- **API package version:** `api_platform.__version__`
- **Platform / pipeline:** from `GET /api/v1/version`
- **Docs suite:** returned as `docs_version`

Composition routes are additive; existing K1.1 routes remain.

## Migration notes

- Prefer `POST /api/v1/analyse` for full intelligence composition.
- Existing `POST /api/v1/analyze/company` is unchanged (legacy analysis path).
- Clients must send JSON financial statements + valuation signals/price; the API
  does not fetch market data.

## Endpoints

### `POST /api/v1/analyse`

Runs `DSPPlatform.compose_intelligence`.

**Example request**

```json
{
  "ticker": "ACM",
  "exchange": "NYSE",
  "company": "Acme",
  "financial_statements": {
    "period": {
      "period_type": "annual",
      "period_end": "2024-12-31",
      "fiscal_year": 2024,
      "currency": "USD"
    },
    "income_statement": { "revenue": 1000.0, "net_income": 210.0 },
    "balance_sheet": { "total_assets": 1000.0, "total_equity": 600.0 },
    "cash_flow": { "operating_cash_flow": 250.0, "free_cash_flow": 170.0 }
  },
  "valuation_signals": {
    "intrinsic_value_per_share": 100.0,
    "current_market_price": 70.0,
    "confidence": 0.7
  }
}
```

**Example response (shape)**

```json
{
  "ok": true,
  "capability": "compose_intelligence",
  "payload": {
    "ok": true,
    "metadata": { "pipeline_version": "1.0.0-epic-001", "ok": true },
    "stage_summaries": [],
    "recommendation_summary": {},
    "committee_summary": {},
    "has_investment_committee": true
  },
  "pipeline_version": "1.0.0-epic-001",
  "api_version": "v1",
  "correlation_id": "…"
}
```

### `POST /api/v1/validate`

Same body as `/analyse`. Returns `{ valid, errors, warnings }` — no execution.

### `GET /api/v1/health`

Returns `status`, `ready`, `platform_version`, `pipeline_version`,
`repository_version`, checks.

### `GET /api/v1/version`

Returns API / platform / pipeline / docs / package versions.

### `GET /api/v1/capabilities`

Returns analytical modules, supported reports, pipeline stages, metadata.

## Error catalogue

| error_code | HTTP | When |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Business validation (`ticker`, valuation, statements) |
| `REQUEST_VALIDATION_ERROR` | 422 | Pydantic / OpenAPI schema failure |
| `COMPOSITION_INPUT_ERROR` | 422 | Platform adapter rejected statements/signals |
| `COMPOSITION_EMPTY` | 502 | Platform returned empty payload |
| `PLATFORM_ERROR` | 502 | Platform orchestration failure |
| `INTERNAL_ERROR` | 500 | Unexpected (message sanitized) |

Error body fields: `error_code`, `message`, `pipeline_stage`,
`validation_errors`, `correlation_id`, `timestamp`, `status_code`.

Internal exception text is not exposed on 500/502 platform mappings.
