# Data Usage Policy — DSP Platform Web 1.6.0

**Effective:** 2026-07-28

## Data sources

Primary research inputs arrive from the DSP backend via frozen `/api/v1`. Underlying sources may include financial statements, calculated metrics, valuation engine outputs, AI committee narratives, and external consensus when supplied by the backend. The thin client does not invent valuations, recommendations, or AI reasoning in the browser.

## Update frequency

Market quotes refresh per client cache TTLs and backend availability. Full research reports refresh when analyse is requested. Exact upstream cadences are provider/backend-controlled; where unknown, DSP does not invent a cadence.

## Unavailable data

Missing fields, stages, or metrics are labelled **Unavailable** (or an equivalent honest category). The client must not fabricate substitutes.

## Confidence methodology

Confidence values shown in the UI are those returned by the backend (for example `confidence_summary` and stage confidence). The client maps and explains them; it does not recompute institutional scores.

## Report versioning

Reports expose metadata such as `api_version`, `platform_version`, `pipeline_version`, `correlation_id`, and stage execution order when present. Frontend foundation version appears in the status bar for supportability and does not alter backend contracts.

## User rights

Account management, access, deletion, contact, and complaints are described in the Privacy Policy.
