# Unified multi-source research architecture

## Status

Feature-branch implementation only. This document does not authorize production
configuration changes, service restarts, or deployment. P1-03 remains unchanged.

## Market-data path

The DSP API continues to use the existing vendor-neutral
`ConfiguredHttpQuoteAdapter`. An optional private gateway is introduced as the
HTTP endpoint behind that adapter:

`DSP API -> ConfiguredHttpQuoteAdapter -> internal market-data gateway -> Upstox`

The intended priority is Upstox first for supported Indian-equity quotes,
followed by a separately configured approved HTTP fallback. The centralized
source-governance helper approves Upstox only for market-data purposes
(`market_quote`, `historical_series`, and `historical_market_data`). It remains
excluded from the financial-statement `DataProvenance` allowlist. The gateway
validates a usable price before returning it. If no approved source is available,
it returns an explicit 503; it does not invent or silently reuse a price.

The gateway requires a private bearer key, reads Upstox credentials only from
server-side environment variables, disables public API documentation, and
returns sanitized errors. Its separate Dockerfile and Compose file are optional
and do not alter the production Compose stack. The Compose file assumes an
existing external Docker network; verify the actual network name before use.

### Explicit limitations

- The gateway currently covers quotes only. Historical candles still use the
  existing historical-series adapter and need their own gateway route before
  production can use Upstox for candles under P1-03.
- The gateway currently covers quotes only. Although the source-governance
  helper permits Upstox for market-data purposes, production must still use the
  gateway through the existing vendor-neutral HTTP adapter and must not inject
  direct Upstox credentials into the DSP API container.
- Upstox token refresh is not implemented. The gateway uses the configured
  server-side access token and requires an operational token lifecycle plan.
- A configured approved HTTP fallback is required for quote failover. Without
  it, both-source failure correctly reports quote unavailability.
- Statement/fundamental providers remain independent of the quote gateway.

## AI research reconciliation

When both AI provider results independently pass the existing schema, citation,
privacy, and deterministic DSP validation, the orchestrator now merges their
unique evidence citations, risks, and qualitative section summaries rather than
discarding one model's entire result. Deterministic valuation and recommendation
fields remain from an independently validated result and are not merged from AI
narrative. Different qualitative summaries are retained and an explicit
limitation asks reviewers to inspect the cited evidence; the merger does not
pretend to resolve factual conflicts automatically.

A single successful provider remains usable under the existing policy. If both
providers fail, the existing fail-closed behavior remains unchanged. This
reconciliation change does not activate the legacy `/api/v1/research/company`
endpoint.

## Fundamental inputs

Shares outstanding must come from validated, identity-matched financial
statements, filings, or another approved fundamental source. The quote gateway
does not synthesize shares. The current authenticated valuation bundle must
continue to reject missing or invalid required share counts until a separately
validated source adapter provides them.

## Required verification before deployment

1. Run the targeted llm_adapters dual-verification tests, new
   `test_complementary_reconciliation.py`, data-engine quote-adapter tests,
   production P1-03 tests, and the full CI suite.
2. Test Upstox success, expired token, timeout, throttling, malformed payload,
   no quote, fallback success, fallback failure, and NSE/BSE identity mapping.
3. Verify gateway/API bearer-key agreement without logging either key.
4. Confirm the external Docker network name and service DNS resolution in a
   non-production environment.
5. Implement and test the historical-series gateway and a secure Upstox token
   refresh/rotation plan before enabling those capabilities in production.
6. Review and approve all changes before any production configuration or
   deployment action.
