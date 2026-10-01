# Commercial financial-data decommissioning

Latest user request: “one suggestion remove all dependecies on upstock, fmp etc. rest is same.”
Clarification offered commercial-vendor removal with official filings/disclosures retained, all external retrieval removed, or only two vendors removed. User replied “ok”; proceeding assumption was explicitly stated: remove commercial vendor dependencies, retain existing official sources and neutral interfaces.

## Runtime changes
- Quote/statement factories accept only `auto`/`http`; obsolete vendor selections fail configuration checks.
- Removed FMP factory imports, single-key selection and the production credential-validation bypass.
- News, ESG, transcripts, filings, ownership and insider default registries no longer register FMP, Polygon, Alpha Vantage, Yahoo or Screener from old credentials/flags.
- Existing SEC EDGAR, NSE and BSE disclosure registrations retained, still opt-in.
- Legacy PlatformConfig no longer defaults to or automatically registers Yahoo market/fundamental adapters. The canonical `/analyse` verified-source path remains authoritative. FRED public economic adapter is retained and now uses the neutral HTTP client.
- Removed commercial providers from control-center defaults and financial-vendor secret requests from environment templates, CI live-evidence workflow and G2 diagnostics/release messaging.
- Source-neutral authenticated HTTP ports remain; they are interfaces, not new configured data services. Missing verified financial statements/quotes still fail closed in production, and preview shows explicit unavailable states.

## Protected and unchanged
DSP scoring, valuation formulae, deterministic stages, source-governance policy, evidence validation/hierarchy, recommendation authority, and AI verification contracts were not modified.

## Scope notes
Legacy vendor adapter implementation classes and their standalone unit fixtures remain in source for now, but are disconnected from application factories/default registries. This change removes automatic runtime dependencies, not every historical mention or standalone implementation. No vendor SDK was present in dependency manifests, so no package removal was needed.
Official source availability still depends on endpoint coverage/access and configuration. This change does not manufacture replacement financial data or claim live quote/statement coverage.

## Verification required
Test old vendor keys/flags cannot activate default adapters, retired provider selector rejection, source-neutral HTTP contracts, official registration contracts, auth boot independent of source availability, and authoritative DSP regressions. See test_reports for current results.
