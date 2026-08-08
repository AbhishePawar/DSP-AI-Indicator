/**
 * Sector Context — sector/industry labels when catalogue metadata exists.
 * Sector median / relative position require authenticated API aggregates.
 * Frozen /analyse does not provide sector medians → Data unavailable.
 */

import type { ResearchView } from "@/lib/research/mapResearchView";
import { DATA_UNAVAILABLE } from "./constants";
import type { SectorContextCell } from "./types";

export type CatalogueSectorLookup = {
  ticker: string;
  sector?: string;
  industry?: string;
};

/**
 * Map sector context. Medians/relatives stay Data unavailable. unless a
 * certified API field is supplied (not present on /analyse today).
 */
export function mapSectorContext(
  views: ResearchView[],
  catalogue: CatalogueSectorLookup[] = [],
): SectorContextCell[] {
  const byTicker = new Map(
    catalogue.map((c) => [c.ticker.trim().toUpperCase(), c]),
  );

  return views.map((v) => {
    const cat = byTicker.get(v.ticker.toUpperCase());
    const sector = cat?.sector?.trim() || DATA_UNAVAILABLE;
    const industry = cat?.industry?.trim() || DATA_UNAVAILABLE;

    return {
      symbol: v.ticker,
      sector,
      industry,
      sectorMedian: DATA_UNAVAILABLE,
      industryMedian: DATA_UNAVAILABLE,
      relativePosition: DATA_UNAVAILABLE,
      note:
        "Sector/industry labels may come from catalogue metadata for display. Authenticated sector/industry median and relative research fields are not present on frozen /api/v1/analyse — Data unavailable.",
    };
  });
}
