/**
 * Presentation mapper for POST /api/v1/portfolio/intelligence.
 * Display only — never recalculates MoS, quality, or weights.
 */

export type PortfolioIntelligenceView = {
  ok: boolean;
  resultId: string;
  schemaVersion: string;
  holdingCount: string;
  linkedResearchCount: string;
  missingResearchCount: string;
  weightsProvidedCount: string;
  uniqueSectorCount: string;
  sectors: string[];
  sectorAllocationNote: string;
  sectorRows: { sector: string; detail: string }[];
  concentrationNote: string;
  topHoldings: { symbol: string; detail: string }[];
  riskNote: string;
  riskAvailableCount: string;
  riskUnavailableCount: string;
  riskPositions: { symbol: string; detail: string }[];
  mosNote: string;
  mosAvailableCount: string;
  mosUnavailableCount: string;
  mosPositions: { symbol: string; marginOfSafety: string }[];
  qualityNote: string;
  qualityAvailableCount: string;
  qualityUnavailableCount: string;
  qualityPositions: { symbol: string; detail: string }[];
  missingResearch: { symbol: string; message: string }[];
  watchlistSymbolCount: string;
  rawNotes: string[];
};

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Data unavailable.";
  }
  return String(value);
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export function mapPortfolioIntelligenceResult(
  payload: unknown,
): PortfolioIntelligenceView | null {
  const root = asRecord(payload);
  const result = asRecord(root.result ?? payload);
  if (!Object.keys(result).length) return null;

  const summary = asRecord(result.portfolio_summary);
  const diversification = asRecord(result.diversification_summary);
  const sectorAlloc = asRecord(result.sector_allocation);
  const concentration = asRecord(result.position_concentration);
  const risk = asRecord(result.portfolio_risk_summary);
  const mos = asRecord(result.margin_of_safety_summary);
  const quality = asRecord(result.quality_summary);
  const watch = asRecord(result.watchlist_summary);

  const sectors = asArray(diversification.sectors).map((s) => display(s));

  const sectorRows = asArray(sectorAlloc.by_sector).map((row) => {
    const r = asRecord(row);
    return {
      sector: display(r.sector ?? r.name ?? r.label),
      detail: display(
        r.weight ?? r.weight_sum ?? r.count ?? r.holding_count ?? r.message,
      ),
    };
  });

  const topHoldings = asArray(concentration.top_holdings_by_weight).map((row) => {
    const r = asRecord(row);
    return {
      symbol: display(r.symbol ?? r.ticker),
      detail: display(r.weight ?? r.message ?? r.note),
    };
  });

  const riskPositions = asArray(risk.positions).map((row) => {
    const r = asRecord(row);
    return {
      symbol: display(r.symbol ?? r.ticker),
      detail: display(
        r.overall ?? r.summary ?? r.message ?? (r.available === false ? "Data unavailable." : r),
      ),
    };
  });

  const mosPositions = asArray(mos.positions).map((row) => {
    const r = asRecord(row);
    return {
      symbol: display(r.symbol ?? r.ticker),
      marginOfSafety: display(r.margin_of_safety),
    };
  });

  const qualityPositions = asArray(quality.positions).map((row) => {
    const r = asRecord(row);
    return {
      symbol: display(r.symbol ?? r.ticker),
      detail: display(
        r.summary ?? r.label ?? r.message ?? "Data unavailable.",
      ),
    };
  });

  const missingResearch = asArray(result.missing_research).map((row) => {
    const r = asRecord(row);
    return {
      symbol: display(r.symbol ?? r.ticker),
      message: display(r.message),
    };
  });

  const notes = [
    display(sectorAlloc.note),
    display(concentration.note),
    display(risk.note),
    display(mos.note),
    display(quality.note),
    display(diversification.note),
  ].filter((n) => n !== "Data unavailable.");

  return {
    ok: root.ok !== false,
    resultId: display(result.result_id),
    schemaVersion: display(result.schema_version),
    holdingCount: display(summary.holding_count),
    linkedResearchCount: display(summary.linked_research_count),
    missingResearchCount: display(summary.missing_research_count),
    weightsProvidedCount: display(summary.weights_provided_count),
    uniqueSectorCount: display(diversification.unique_sector_count),
    sectors,
    sectorAllocationNote: display(sectorAlloc.note),
    sectorRows,
    concentrationNote: display(concentration.note),
    topHoldings,
    riskNote: display(risk.note),
    riskAvailableCount: display(risk.available_count),
    riskUnavailableCount: display(risk.unavailable_count),
    riskPositions,
    mosNote: display(mos.note),
    mosAvailableCount: display(mos.available_count),
    mosUnavailableCount: display(mos.unavailable_count),
    mosPositions,
    qualityNote: display(quality.note),
    qualityAvailableCount: display(quality.available_count),
    qualityUnavailableCount: display(quality.unavailable_count),
    qualityPositions,
    missingResearch,
    watchlistSymbolCount: display(watch.symbol_count),
    rawNotes: notes,
  };
}

export function buildPortfolioIntelligenceRequest(input: {
  portfolioId: string;
  holdings: { ticker: string; allocationPercent?: number }[];
  watchlist: string[];
}) {
  return {
    portfolio: {
      portfolio_id: input.portfolioId,
      holdings: input.holdings.map((h) => ({
        symbol: h.ticker,
        weight:
          typeof h.allocationPercent === "number" &&
          Number.isFinite(h.allocationPercent)
            ? h.allocationPercent / 100
            : null,
      })),
    },
    watchlist: {
      watchlist_id: `${input.portfolioId}-watchlist`,
      symbols: input.watchlist,
    },
    // Research objects must come from the server/archive — client does not fabricate them.
    research_objects: null,
    reports: null,
    snapshots: null,
  };
}
