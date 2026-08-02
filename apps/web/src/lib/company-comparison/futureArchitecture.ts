/**
 * Future Comparison Engine Abstraction (EPIC-012/013 design note).
 *
 * v1 orchestrates N company `/api/v1/analyse` packs in the thin client.
 * The types below document how portfolio / ETF / MF / sector / industry /
 * watchlist subjects can later plug in without redesigning the workspace shell.
 *
 * HARD CONSTRAINT: adapters may only compose existing server research outputs.
 * No new scoring, valuation, or recommendation engines in the browser.
 */

import type {
  ComparisonEngineAdapter,
  ComparisonSubjectKind,
  ComparisonSubjectRef,
} from "./types";

export const COMPARISON_ENGINE_VERSION = "1.1-company";

export const SUPPORTED_SUBJECT_KINDS_V1: readonly ComparisonSubjectKind[] = [
  "company",
] as const;

export const PLANNED_SUBJECT_KINDS: readonly ComparisonSubjectKind[] = [
  "portfolio",
  "etf",
  "mutual_fund",
  "sector",
  "industry",
  "watchlist",
] as const;

/**
 * Company adapter (implemented): resolve ticker → AnalyseRequest → ResearchView.
 * Future adapters would resolve their subject refs to comparable research packs
 * produced by server-side orchestration — still presentation-only on the client.
 */
export const companyComparisonAdapter: ComparisonEngineAdapter = {
  kind: "company",
  describe: () =>
    "CompanyComparisonAdapter — client orchestrates N frozen /api/v1/analyse calls; Winner Matrix / Buffett preference / trade-offs are pure presentation rankings of server fields.",
};

export function describeFutureAdapter(kind: ComparisonSubjectKind): string {
  switch (kind) {
    case "company":
      return companyComparisonAdapter.describe();
    case "portfolio":
      return "Future PortfolioComparisonAdapter — compose portfolio intelligence + constituent analyse packs; no client scoring.";
    case "etf":
      return "Future EtfComparisonAdapter — compose ETF research envelopes when a certified API exists.";
    case "mutual_fund":
      return "Future MutualFundComparisonAdapter — compose MF research envelopes when a certified API exists.";
    case "sector":
      return "Future SectorComparisonAdapter — compose sector aggregates from server research products.";
    case "industry":
      return "Future IndustryComparisonAdapter — compose industry aggregates from server research products.";
    case "watchlist":
      return "Future WatchlistComparisonAdapter — expand watchlist symbols into company packs (same as v1 company path).";
    default:
      return "Unknown adapter kind.";
  }
}

export function subjectRefFromTicker(
  ticker: string,
  label?: string,
  exchange?: string,
): ComparisonSubjectRef {
  const id = ticker.trim().toUpperCase();
  return {
    kind: "company",
    id,
    symbol: id,
    label: label ?? id,
    exchange,
  };
}

export const FUTURE_ARCHITECTURE_NOTES: readonly string[] = [
  "Workspace shell (header, sections, export, personal notes) is subject-kind agnostic.",
  "ComparisonWorkspaceModel.slots already carry status/error/view overlays suitable for non-company packs.",
  "Winner Matrix extractors are keyed by dimension id — future packs can supply the same ResearchView-shaped fields or a thin isomorphic view model.",
  "Do not redesign when adding ETF/MF: add an adapter that returns comparable packs, then reuse mapComparisonWorkspace.",
  "Backend /compare remains orchestration-only today; prefer server composition later if multi-pack latency or auth bundling requires it — still no new scoring.",
];
