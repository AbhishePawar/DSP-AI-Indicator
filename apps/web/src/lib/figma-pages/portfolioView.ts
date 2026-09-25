/**
 * Figma `Portfolio.tsx` view-model over the server portfolio contract
 * (`GET /api/v1/workspace/portfolio`).
 *
 * Every figure is computed server-side (`invested = qty × avg`, `current =
 * qty × cmp`, `pnl`, `return`, `weight`, sector allocation) and copied here
 * for formatting only. When the server reports the portfolio as incomplete
 * (a holding has no authenticated CMP) the dependent totals stay honestly
 * unavailable (CV-005). Nothing is derived in the browser.
 */

import type {
  PortfolioHoldingRow,
  PortfolioResponse,
  SectorAllocationRow,
} from "@/lib/api/workspaceTypes";
import { formatQuoteChange } from "./dashboardView";

export type PortfolioSortKey = "value" | "gain" | "symbol";

export const PORTFOLIO_SORT_KEYS: readonly PortfolioSortKey[] = ["value", "gain", "symbol"];

export type PortfolioSummaryCard = {
  label: string;
  value: string;
  tone: "fg" | "muted" | "profit" | "risk";
  note?: string;
};

export type HoldingRow = {
  symbol: string;
  company: string;
  sector: string;
  quantity: string;
  averageCost: string;
  cmp: string;
  cmpDirection: "up" | "down" | "flat" | null;
  pnl: string;
  pnlDirection: "up" | "down" | "flat" | null;
  returnPct: string;
  rating: string;
  weight: string;
  priced: boolean;
};

export type SectorSlice = { name: string; percent: number; colorVar: string };

/** Figma SECTOR_DATA palette order. */
const SECTOR_COLORS = [
  "var(--c-revenue)",
  "var(--c-profit)",
  "var(--c-risk)",
  "var(--c-valuation)",
  "var(--c-cashflow)",
  "var(--c-dsp)",
  "var(--c-debt)",
];

const UNAVAILABLE = "Data unavailable.";

/** Indian-market compact money: ₹x.xL / ₹x.xK — Figma summary-card format. */
export function formatCompactInr(
  value: number,
  { signed = false }: { signed?: boolean } = {},
): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? "−" : signed && value > 0 ? "+" : "";
  if (abs >= 1e7) return `${sign}₹${(abs / 1e7).toFixed(2)}Cr`;
  if (abs >= 1e5) return `${sign}₹${(abs / 1e5).toFixed(1)}L`;
  if (abs >= 1e3) return `${sign}₹${(abs / 1e3).toFixed(1)}K`;
  return `${sign}₹${abs.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function formatMoney(value: number | null | undefined, currency: string | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return UNAVAILABLE;
  const code = currency?.trim().toUpperCase();
  if (code && /^[A-Z]{3}$/.test(code)) {
    try {
      return value.toLocaleString("en-IN", { style: "currency", currency: code, maximumFractionDigits: 2 });
    } catch {
      /* unknown code → bare number */
    }
  }
  return value.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function formatPercent(value: number | null | undefined, signed = true): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return UNAVAILABLE;
  const pct = value * 100;
  const sign = signed && pct > 0 ? "+" : "";
  return `${sign}${pct.toLocaleString(undefined, { maximumFractionDigits: 1 })}%`;
}

function direction(value: number | null | undefined): "up" | "down" | "flat" | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return value > 0 ? "up" : value < 0 ? "down" : "flat";
}

export function buildPortfolioSummaryCards(
  response: PortfolioResponse | null | undefined,
): PortfolioSummaryCard[] {
  const s = response?.summary;
  if (!s || s.holdings === 0) {
    return [
      { label: "Current Value", value: UNAVAILABLE, tone: "fg", note: "Add holdings to begin." },
      { label: "Total Invested", value: UNAVAILABLE, tone: "muted" },
      { label: "Total Gain", value: UNAVAILABLE, tone: "muted" },
      { label: "Returns", value: UNAVAILABLE, tone: "muted" },
    ];
  }
  const incompleteNote = s.complete
    ? undefined
    : `${s.holdings - s.priced_holdings} of ${s.holdings} holdings have no authenticated price.`;
  const gainTone: PortfolioSummaryCard["tone"] =
    typeof s.total_pnl === "number" ? (s.total_pnl >= 0 ? "profit" : "risk") : "muted";
  return [
    {
      label: "Current Value",
      value: typeof s.current_value === "number" ? formatCompactInr(s.current_value) : UNAVAILABLE,
      tone: "fg",
      note: incompleteNote,
    },
    {
      label: "Total Invested",
      value: formatCompactInr(s.total_invested),
      tone: "muted",
      note: "quantity × average cost",
    },
    {
      label: "Total Gain",
      value: typeof s.total_pnl === "number" ? formatCompactInr(s.total_pnl, { signed: true }) : UNAVAILABLE,
      tone: gainTone,
      note: incompleteNote,
    },
    {
      label: "Returns",
      value: formatPercent(s.return_pct),
      tone: gainTone,
      note: incompleteNote,
    },
  ];
}

export function mapHoldingRow(h: PortfolioHoldingRow): HoldingRow {
  const change = formatQuoteChange({ change: h.quote.change, change_percent: h.quote.change_percent });
  const priced = typeof h.cmp === "number";
  return {
    symbol: h.symbol.toUpperCase(),
    company: h.company_name ?? h.symbol.toUpperCase(),
    sector: h.sector ?? "Sector unavailable",
    quantity: h.quantity.toLocaleString("en-IN", { maximumFractionDigits: 4 }),
    averageCost: formatMoney(h.average_cost, h.quote.currency ?? "INR"),
    cmp: formatMoney(h.cmp, h.quote.currency),
    cmpDirection: priced ? change.direction : null,
    pnl: typeof h.pnl === "number" ? formatCompactInr(h.pnl, { signed: true }) : UNAVAILABLE,
    pnlDirection: direction(h.pnl),
    returnPct: formatPercent(h.return_pct),
    rating: h.rating ?? "—",
    weight: typeof h.weight === "number" ? formatPercent(h.weight, false) : UNAVAILABLE,
    priced,
  };
}

/** Figma sort keys on server-computed values; unpriced rows sink to the bottom. */
export function sortHoldings(
  holdings: readonly PortfolioHoldingRow[],
  sortBy: PortfolioSortKey,
): PortfolioHoldingRow[] {
  const copy = [...holdings];
  if (sortBy === "symbol") return copy.sort((a, b) => a.symbol.localeCompare(b.symbol));
  const key = (h: PortfolioHoldingRow) =>
    sortBy === "value" ? h.current_value : h.return_pct;
  return copy.sort((a, b) => {
    const av = key(a);
    const bv = key(b);
    if (av === null && bv === null) return a.symbol.localeCompare(b.symbol);
    if (av === null) return 1;
    if (bv === null) return -1;
    return bv - av;
  });
}

export function buildSectorSlices(allocation: readonly SectorAllocationRow[] | null | undefined): SectorSlice[] {
  return (allocation ?? [])
    .filter((s) => typeof s.weight === "number" && Number.isFinite(s.weight) && s.weight > 0)
    .map((s, i) => ({
      name: s.sector ?? "Unclassified",
      percent: (s.weight as number) * 100,
      colorVar: SECTOR_COLORS[i % SECTOR_COLORS.length],
    }));
}

/** SVG donut arcs (presentation geometry only). */
export function donutSegments(
  slices: readonly SectorSlice[],
  radius = 80,
  inner = 50,
): { slice: SectorSlice; path: string }[] {
  const total = slices.reduce((a, s) => a + s.percent, 0);
  if (total <= 0) return [];
  let angle = -Math.PI / 2;
  const gap = slices.length > 1 ? 0.05 : 0;
  return slices.map((slice) => {
    const sweep = (slice.percent / total) * Math.PI * 2 - gap;
    const start = angle + gap / 2;
    const end = start + Math.max(0, sweep);
    angle += (slice.percent / total) * Math.PI * 2;
    const large = end - start > Math.PI ? 1 : 0;
    const p = (r: number, a: number) => `${(r * Math.cos(a)).toFixed(2)} ${(r * Math.sin(a)).toFixed(2)}`;
    const path = [
      `M${p(radius, start)}`,
      `A${radius} ${radius} 0 ${large} 1 ${p(radius, end)}`,
      `L${p(inner, end)}`,
      `A${inner} ${inner} 0 ${large} 0 ${p(inner, start)}`,
      "Z",
    ].join(" ");
    return { slice, path };
  });
}
