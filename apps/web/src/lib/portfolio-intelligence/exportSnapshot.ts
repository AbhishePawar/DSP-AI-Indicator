/**
 * EPIC-F006 — Export session holdings snapshot only.
 * No portfolio value / return / risk calculations.
 */

import type { PortfolioActivity, PortfolioHolding } from "@/lib/portfolio/model";

export type PortfolioExportSnapshot = {
  exportedAt: string;
  source: string;
  note: string;
  portfolioId: string;
  portfolioName: string;
  holdingsCount: number;
  watchlistCount: number;
  holdings: Array<{
    ticker: string;
    company: string;
    sector: string;
    recommendation: string;
    researchAvailable: boolean;
  }>;
  watchlist: string[];
  activities: PortfolioActivity[];
};

export function buildPortfolioExportSnapshot(args: {
  portfolioId: string;
  portfolioName: string;
  holdings: PortfolioHolding[];
  watchlist: string[];
  activities: PortfolioActivity[];
}): PortfolioExportSnapshot {
  return {
    exportedAt: new Date().toISOString(),
    source: "session UserPortfolio holdings — no /api/v1 portfolio analytics",
    note: "Display snapshot only. Allocation %, returns, and risk are not computed here.",
    portfolioId: args.portfolioId,
    portfolioName: args.portfolioName,
    holdingsCount: args.holdings.length,
    watchlistCount: args.watchlist.length,
    holdings: args.holdings.map((h) => ({
      ticker: h.ticker,
      company: h.company,
      sector: h.sector,
      recommendation: h.recommendation,
      researchAvailable: h.researchAvailable,
    })),
    watchlist: args.watchlist,
    activities: args.activities.slice(0, 50),
  };
}

export function portfolioSnapshotToJson(snapshot: PortfolioExportSnapshot): string {
  return JSON.stringify(snapshot, null, 2);
}

function csvEscape(value: string): string {
  if (/[",\n]/.test(value)) return `"${value.replace(/"/g, '""')}"`;
  return value;
}

export function portfolioSnapshotToCsv(snapshot: PortfolioExportSnapshot): string {
  const rows: string[][] = [
    ["ticker", "company", "sector", "recommendation", "researchAvailable"],
    ...snapshot.holdings.map((h) => [
      h.ticker,
      h.company,
      h.sector,
      h.recommendation,
      String(h.researchAvailable),
    ]),
  ];
  return rows.map((r) => r.map(csvEscape).join(",")).join("\n");
}

export function portfolioSnapshotToHtml(snapshot: PortfolioExportSnapshot): string {
  const rows = snapshot.holdings
    .map(
      (h) =>
        `<tr><td>${h.ticker}</td><td>${h.company}</td><td>${h.sector}</td><td>${h.recommendation}</td><td>${h.researchAvailable}</td></tr>`,
    )
    .join("");
  return `<!doctype html><html><head><meta charset="utf-8"/><title>${snapshot.portfolioName}</title>
<style>body{font-family:system-ui,sans-serif;padding:24px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:6px;text-align:left}</style>
</head><body>
<h1>${snapshot.portfolioName}</h1>
<p>${snapshot.note}</p>
<p>Holdings: ${snapshot.holdingsCount} · Watchlist: ${snapshot.watchlistCount}</p>
<table><thead><tr><th>Ticker</th><th>Company</th><th>Sector</th><th>Recommendation</th><th>Research</th></tr></thead>
<tbody>${rows || "<tr><td colspan=5>Data unavailable.</td></tr>"}</tbody></table>
</body></html>`;
}

export function downloadText(
  filename: string,
  content: string,
  mime: string,
): void {
  if (typeof window === "undefined") return;
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
