# Epic M1.0 Sprint M1.5 — Shareholder Alignment & Capital Stewardship

**Web:** `2.1.0` · **MIE:** `0.5.0-shareholder-alignment`

## Mission

Evaluate whether management acts in the long-term interests of shareholders using objective ownership, compensation, capital return, dilution, and stewardship evidence. **Category score only** — overall Management Score remains disabled (`finalScoringEnabled=false`).

Maps to MIE score category `ownership_alignment`.

## Modules

| File | Role |
|------|------|
| `shareholderAlignmentModels.ts` | Domain types (metrics · OwnershipTrend · events · evidence · score · risks) |
| `shareholderAlignmentEvidence.ts` | Evidence mapping / indexing / quality×confidence |
| `shareholderAlignmentScoring.ts` | Metric · evidence · confidence · category scores + risk detection |
| `shareholderAlignmentBuilders.ts` | Analysis builders + demo fixture + explainability |
| `shareholderAlignmentSelectors.ts` | Pure selectors + ManagementScore mapping |
| `shareholderAlignmentValidators.ts` | Structural validation + conclusion↔evidence checks |
| `shareholderAlignmentEngine.ts` | Facade (`analyze` · `demo` · `mergeIntoManagementAnalysis`) |

## Metrics (22)

Promoter Shareholding / Buying / Selling · Insider Buying / Selling · Institutional / FII / DII / Retail Ownership · Employee Ownership · ESOP Dilution · Share Dilution · Buyback History · Dividend Payout / Growth / Consistency · Capital Return Ratio · Executive Comp Growth · Comp vs Performance · Comp Structure · LTI Alignment · Historical Stewardship Trend

Configurable lookback: **3 | 5 | 7 | 10** years.

## Stewardship events

Dividend Policy · Share Buybacks · Equity Issuance · Capital Raising · ESOP Programs · Promoter / Insider Transactions · Treasury Share Management · Minority Shareholder Protection · Capital Return Discipline

## Risks detected

Promoter Exit · Promoter Dilution · Excessive ESOP Dilution · Compensation Misalignment · Aggressive Equity Issuance · Weak Dividend Policy · Unsustainable Buybacks · Minority Shareholder Risk · Ownership Concentration · Stewardship Deterioration

## Usage

```ts
import { shareholderAlignmentEngine, managementEngine } from "@/lib/management";

const sa = shareholderAlignmentEngine.demo();
const mie = managementEngine.applyShareholderAlignment(sa);

shareholderAlignmentEngine.info.finalScoringEnabled; // false
managementEngine.overallManagementScore(); // null
```

## Trust

- Published weights in `SHAREHOLDER_ALIGNMENT_METRIC_WEIGHTS` (sum = 1)
- Every conclusion in `conclusionEvidenceMap` links evidence ids
- No AI opinions · no hidden scoring · no Overall Management Score

## Non-goals (this sprint)

Dashboard UI · Charts · Radar · Overall Management Score · Capital Allocation / Governance / Execution changes · Strategy · Report / Research Engine integration
