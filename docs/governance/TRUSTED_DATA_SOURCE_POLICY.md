# GOV-001 — Institutional Trusted Data Source Policy

| Field | Value |
|---|---|
| Document ID | **GOV-001** |
| Title | Institutional Trusted Data Source Policy |
| Status | **Active** — Data Governance Foundation |
| Version | 1.0.0 |
| Effective date | 2026-08-01 |
| Owner | Platform Governance / Data Stewardship |
| Scope | All DSP AI Indicator data ingestion, validation, citation, explainability, and research presentation |
| Change control | Governance review required for any amendment or new approved source |
| Related | `docs/USER_TRUST_STANDARD.md` · Tier-0 CV-001…CV-010 · REP-002 · Research Mode · Thin client `/api/v1` |

---

## 1. Purpose

This policy establishes the official **Institutional Trusted Data Source** rules for DSP AI Indicator.

DSP is an investment **research** platform operating in **Research Mode**. Data authenticity is non-negotiable. Analytical outputs, UI presentation, AI-mediated language, and explainability surfaces must rest on an explicit, ordered, and auditable source hierarchy.

### Goals

| Goal | Meaning |
|---|---|
| **Accuracy** | Prefer authoritative official and regulated sources over secondary aggregation |
| **Traceability** | Every material research value should be attributable to a source, document, and period |
| **Explainability** | Users can see *where* a fact came from and *why* a conflicting value was rejected |
| **Transparency** | Missing, stale, or disputed data is disclosed — never silently filled |
| **Repeatability** | The same inputs and source rules produce the same research outcomes (CV-004) |
| **Institutional trust** | Desks can defend research under audit using this policy |

### Non-goals

- This document does **not** implement adapters, APIs, or engines.
- This document does **not** approve commercial entitlement or licensing terms for any vendor beyond the governance posture stated herein.
- This document does **not** authorize client-side calculation, valuation, or recommendation fabrication.

---

## 2. Data Source Hierarchy

Sources are classified into four tiers. Higher tiers outrank lower tiers for the same fact domain.

### Tier 1 — Official Sources

Authoritative issuer and regulator-facing company disclosures.

**Examples**

- Company Annual Reports
- Quarterly Reports / financial results
- Investor Presentations (as company-issued materials)
- Earnings Releases
- NSE / BSE company filings
- Official Corporate Announcements
- SEC Filings (where applicable for cross-listed or foreign issuers)

**Rule:** Official filings and issuer disclosures always have the **highest priority** for company fundamentals, financial statements, and company-stated metrics.

### Tier 2 — Regulated Market Sources

Exchange, regulator, and government statistical publications.

**Examples**

- NSE
- BSE
- RBI
- SEBI
- MOSPI
- Other applicable government publications

**Rule:** Used for market microstructure, regulated reference series, policy rates, official statistics, and exchange-published corporate action / price reference data when not superseded by a Tier 1 document for the same company-stated fact.

### Tier 3 — Approved Financial Data Providers

Licensed or publicly usable aggregators **explicitly approved** by governance.

**Initially approved**

| Provider | Role |
|---|---|
| **Screener.in** | Primary approved aggregator (Tier 3) |

**Rule:** Future providers may be added **only** through the Future Source Approval process (Section 10).  
**Do not** automatically approve any other provider. Unlisted aggregators are **not** trusted sources under this policy.

### Tier 4 — Reputable News

Journalistic sources used for event context only.

**Examples**

- Reuters
- Bloomberg
- Business Standard
- Economic Times

**Allowed use**

- Timeline construction
- Material event awareness
- Corporate announcement *context* (not as the ledger of record for audited numbers)

**Rule:** News **never** overrides audited financial data, official filings, or exchange-authoritative figures for the same metric.

### Out of tier (not approved by default)

| Class | Treatment |
|---|---|
| Unlisted data vendors / scrapers / blogs / social media | **Not approved** — do not ingest as research facts |
| Model-estimated or AI-inferred “facts” | **Not sources** — inference layer only (see Trust Standard) |
| Manual operator entry | Allowed only as an explicit **Manual Entry** path below news in priority, with Low confidence and mandatory audit metadata |

---

## 3. Source Priority

When selecting a value for a research field, apply this order:

```
Official Filing (Tier 1)
        ↓
Exchange / Regulated Filing or Publication (Tier 2)
        ↓
Approved Aggregator (Tier 3 — e.g. Screener.in)
        ↓
Reputable News (Tier 4 — events/context only)
        ↓
Manual Entry (audited, Low confidence)
```

### Conflict rule (summary)

**When conflicts exist, the official / higher-tier source wins.**  
Lower-tier values must not silently replace higher-tier values.

### Domain notes

| Domain | Prefer |
|---|---|
| Financial statement line items | Tier 1 → Tier 2 → Tier 3 |
| Prices / quotes | Tier 2 exchange reference (then approved market feeds if later approved) |
| Corporate actions | Tier 1 / Tier 2 announcements before aggregator |
| Shareholding patterns | Tier 1 / Tier 2 filings before aggregator |
| Material events / timeline | Tier 4 news + Tier 1/2 announcements; numbers still from Tier 1/2/3 |
| Macro / policy rates | Tier 2 government / RBI / SEBI publications |

---

## 4. Conflict Resolution Policy

If multiple sources disagree on the same field for the same reporting context:

### Step 1 — Prefer official

Use the Tier 1 official filing (or Tier 2 exchange/regulator publication when the fact is exchange-/regulator-authoritative and no Tier 1 issuer document applies).

### Step 2 — Log discrepancy

Record at minimum:

- Field identifier
- Conflicting values
- Source identifiers and tiers
- Observation / ingestion timestamp
- Reporting period (if applicable)

Discrepancy logs support auditability (CV-007) and must not be discarded.

### Step 3 — Mark verification status

Surface a verification state such as:

| Status | Meaning |
|---|---|
| `verified_official` | Aligned with Tier 1 (or applicable Tier 2 authority) |
| `discrepancy_logged` | Conflict observed; official/higher tier retained |
| `unverified_aggregator` | Tier 3 only; no official cross-check yet |
| `provisional` | Temporary pending filing availability |
| `rejected_lower_tier` | Lower-tier value discarded due to conflict |

### Hard rules

- **Never** silently overwrite official data with aggregator or news values.
- **Never** average conflicting sources to invent a blended “truth.”
- **Never** promote news-derived numbers into financial statement fields.
- If official data is missing and only a lower tier exists, disclose tier and verification status — do not present lower-tier data as official.

---

## 5. Missing Data Policy

Aligned with **CV-001** (Data Authenticity First) and **CV-005** (Transparency over confidence).

### Never fabricate

- No invented prices, ratios, scores, filings, or citations.
- No silent substitution of a related metric for a missing one.
- No client-side valuation or recommendation math to “fill gaps.”

### Required presentation language

When a required value cannot be authenticated under this policy, display one of:

| Phrase | Use |
|---|---|
| **Data unavailable.** | Fact missing or not authenticated |
| **Unable to calculate.** | Calculation blocked by missing/incomplete mandatory inputs (CV-002 / CV-005) |
| **Coverage unavailable.** | Instrument, market, or research coverage not in scope |

### Substitution ban

If Revenue is missing, do **not** show Gross Profit, estimates, or peer averages in its place under the Revenue label. Leave the field unavailable and explain coverage if needed.

---

## 6. Field-Level Citation Standard

Every analytical value should **eventually** support the following citation metadata (implementation may be phased; the standard is normative):

| Attribute | Description |
|---|---|
| **Source** | Named publisher / system (e.g. Company AR FY24, NSE, Screener.in) |
| **Document** | Document title, filing ID, or URL/identifier where applicable |
| **Reporting Period** | Fiscal period / as-of date for the fact |
| **Publication Date** | When the source published the document or series |
| **Last Verified** | When DSP last verified the value against the source |
| **Source Tier** | Tier 1–4 or Manual Entry |

### Presentation expectations

- Research Mode surfaces should prefer showing source tier and freshness over false precision.
- Explainability and audit modules should be able to answer: *What is the source? What period? When verified?*
- Thin clients must **display** server-provided citation metadata; they must not invent citations.

---

## 7. Source Confidence

Source confidence describes **source quality only**. It is **not** investment recommendation confidence, model confidence, or AI certainty.

| Level | Applies to |
|---|---|
| **High** | Official filing (Tier 1); Exchange / regulated filing or publication (Tier 2) |
| **Medium** | Approved aggregator (Tier 3) |
| **Low** | Manual entry |
| **Experimental** | Provisional pipelines, pilot feeds, or sources under governance trial — **not** for production research claims without disclosure |

### Rules

- Source confidence must not be conflated with Research Mode recommendation confidence or committee confidence scores.
- Downgrade displayed source confidence when verification status is `discrepancy_logged`, `unverified_aggregator`, or `provisional`.
- Experimental sources require explicit UI/API disclosure and cannot silently sit beside High-tier facts.

---

## 8. Data Freshness

### Expectations (normative targets)

Exact SLAs may be refined operationally; the following are policy expectations for Research Mode honesty:

| Domain | Freshness expectation | Stale treatment |
|---|---|---|
| **Financial Statements** | As published for the latest available reporting period; re-verify after new results | Show reporting period; if superseded filing exists and not applied → disclose lag |
| **Corporate Actions** | Near real-time relative to exchange/company announcements | Mark pending / unverified until Tier 1/2 confirmation |
| **Prices** | Session-appropriate exchange reference; disclose as-of timestamp | Show last known as-of; never invent ticks |
| **Shareholding** | Latest filed pattern / applicable quarter | Show period; do not extrapolate |
| **News / Material Events** | Timely for timeline; not a substitute for filings | Timestamp events; isolate from statement numbers |

### Freshness indicators (conceptual)

Surfaces should eventually support indicators such as:

| Indicator | Meaning |
|---|---|
| **Current** | Within expected freshness window for the domain |
| **As-of dated** | Valid but explicitly time-bound |
| **Stale** | Outside expected window — still show value only with disclosure |
| **Unknown** | Freshness metadata missing → prefer **Data unavailable.** for time-critical fields or disclose unknown |

Missing freshness metadata is itself a trust defect: disclose **Unknown** rather than implying live data.

---

## 9. Approved Source Registry

Authoritative registry of sources recognized under GOV-001.  
**Only listed sources with Status = Approved (or Trial with disclosure) may feed research facts.**

| Source | Category | Tier | Status | Owner | Review Frequency |
|---|---|---|---|---|---|
| Company Annual Reports | Official issuer disclosure | 1 | Approved | Data Stewardship | Per reporting cycle / annual policy review |
| Company Quarterly Reports / Results | Official issuer disclosure | 1 | Approved | Data Stewardship | Per results season / annual policy review |
| Investor Presentations | Official issuer materials | 1 | Approved | Data Stewardship | Annual |
| Earnings Releases | Official issuer disclosure | 1 | Approved | Data Stewardship | Per results season |
| NSE Filings / Announcements | Exchange / official | 1–2 | Approved | Data Stewardship | Annual |
| BSE Filings / Announcements | Exchange / official | 1–2 | Approved | Data Stewardship | Annual |
| Official Corporate Announcements | Official issuer | 1 | Approved | Data Stewardship | Annual |
| SEC Filings (where applicable) | Official regulator filing | 1 | Approved | Data Stewardship | Annual |
| NSE (market / reference) | Regulated market | 2 | Approved | Data Stewardship | Annual |
| BSE (market / reference) | Regulated market | 2 | Approved | Data Stewardship | Annual |
| RBI publications | Regulator / government | 2 | Approved | Data Stewardship | Annual |
| SEBI publications | Regulator | 2 | Approved | Data Stewardship | Annual |
| MOSPI publications | Government statistics | 2 | Approved | Data Stewardship | Annual |
| Other applicable government publications | Government | 2 | Approved (class) | Data Stewardship | Annual |
| **Screener.in** | Financial data aggregator | 3 | **Approved** (primary aggregator) | Data Stewardship | Semi-annual |
| Reuters | Reputable news | 4 | Approved (events/timeline only) | Data Stewardship | Annual |
| Bloomberg | Reputable news | 4 | Approved (events/timeline only) | Data Stewardship | Annual |
| Business Standard | Reputable news | 4 | Approved (events/timeline only) | Data Stewardship | Annual |
| Economic Times | Reputable news | 4 | Approved (events/timeline only) | Data Stewardship | Annual |
| Manual Entry | Operator-supplied | Manual | Allowed (Low confidence; audited) | Research Ops | Continuous audit sampling |
| *Any unlisted provider* | — | — | **Not approved** | — | Requires Section 10 |

Registry amendments require governance review and a version bump of this policy or an annexed registry change record.

---

## 10. Future Source Approval

Any new data source, vendor feed, scraper, or aggregator requires **governance review** before research use.

### Minimum approval checklist

1. Licensing / terms of use reviewed (Section 11)
2. Tier assignment proposed (1–4 or reject)
3. Conflict behaviour vs Tier 1/2 defined
4. Freshness and failure modes documented
5. Citation metadata capability assessed
6. Trial period with **Experimental** confidence (if needed)
7. Explicit registry update and owner assignment

### Hard rule

**Do not automatically add providers.**  
Product, engineering, or AI suggestions cannot promote a source to Approved without governance sign-off.

---

## 11. Licensing & Attribution

- Use only **licensed** or **publicly available** information in accordance with applicable terms of use, exchange policies, and copyright.
- Redistribution, caching, and display must respect provider and exchange constraints.
- Attribution should follow source requirements where mandated.
- **Official filings remain the authoritative reference** for company fundamentals regardless of aggregator convenience.
- DSP Research Mode outputs must not imply brokerage, exchange, or regulator endorsement.

---

## 12. Relationship to Trust Standard

| Framework | How GOV-001 supports it |
|---|---|
| **Research Mode** | Facts come from approved tiers; recommendations remain research-oriented, not buy/sell instructions |
| **User Trust Standard** | Source-before-score; authenticity and disclosure over confidence theatre |
| **CV-001…CV-010** | Especially CV-001 (no fabrication), CV-002 (source before score), CV-005 (unable to calculate), CV-006/007 (trace/audit) |
| **REP-002** | Ontology fields must bind to authenticated facts; missing ontology inputs stay unavailable |
| **Thin Client Architecture** | Browser displays server-authenticated values and citations only; no local source invention |
| **Explainability** | Field citations, tiers, conflicts, and freshness make inference inspectable |
| **RS-002 / RS-010** | Authenticated market data and audit/provenance depend on this hierarchy |

### Epistemic layering (reminder)

```
Facts          ← GOV-001 sources & tiers
Analysis       ← derived under engine rules from authenticated facts
Inference      ← AI / committee language over analysis
Recommendation ← Research Mode output; never invents facts
```

GOV-001 governs the **Facts** layer. It does not authorize inference to rewrite facts.

---

## 13. Validation Checklist

| Check | Result |
|---|---|
| Clear source hierarchy (Tiers 1–4 + Manual) | ✓ |
| No conflicting priority rules | ✓ — single cascade; official wins |
| Official filings highest priority | ✓ — Tier 1 |
| Honest missing data language | ✓ — Data unavailable / Unable to calculate / Coverage unavailable |
| Conflict resolution defined | ✓ — prefer official → log → mark status; no silent overwrite |
| Future extensibility | ✓ — Section 10 + registry Status model |
| Screener.in sole initial Tier 3 approval | ✓ |
| News cannot override audited financials | ✓ |
| Aligns with Trust Standard / thin client / REP-002 | ✓ — Section 12 |

---

## 14. Document Control

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-01 | Initial GOV-001 Institutional Trusted Data Source Policy |

Amendments require governance review. Implementation epics must cite GOV-001 when adding ingestion, validation, or citation behaviour.
