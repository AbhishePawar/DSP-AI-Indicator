/**
 * EPIC-014 — Research Workspace Search (client-side over available data).
 * Route jumps only — no fabricated match scores.
 */

import { COMPANY_CATALOGUE } from "@/lib/companies/catalogue";
import { loadRecentAnalyses } from "@/lib/analysis/recentAnalyses";
import { listRecentReports } from "@/lib/recentReports";
import type { NotebookEntry } from "./notebookStore";
import { CANVAS_TABS } from "./sections";

export type CanvasSearchHit = {
  id: string;
  label: string;
  group:
    | "Companies"
    | "Research"
    | "Notes"
    | "Reports"
    | "Comparisons"
    | "Timeline"
    | "Committee"
    | "Tabs";
  href: string;
  detail?: string;
};

export type CanvasSearchInput = {
  query: string;
  notebookEntries?: NotebookEntry[];
  comparisonSymbols?: string[];
  savedComparisonTitles?: { title: string; symbols: string[]; href: string }[];
};

export function searchResearchCanvas(input: CanvasSearchInput): CanvasSearchHit[] {
  const q = input.query.trim().toLowerCase();
  if (!q) return [];

  const hits: CanvasSearchHit[] = [];

  for (const c of COMPANY_CATALOGUE) {
    if (
      c.ticker.toLowerCase().includes(q) ||
      c.name.toLowerCase().includes(q) ||
      (c.sector ?? "").toLowerCase().includes(q)
    ) {
      hits.push({
        id: `co-${c.ticker}`,
        label: `${c.ticker} · ${c.name}`,
        group: "Companies",
        href: `/research/canvas?symbol=${encodeURIComponent(c.ticker)}`,
        detail: c.sector || undefined,
      });
    }
  }

  for (const recent of loadRecentAnalyses()) {
    if (
      recent.ticker.toLowerCase().includes(q) ||
      recent.company.toLowerCase().includes(q)
    ) {
      hits.push({
        id: `ra-${recent.ticker}-${recent.analysedAt}`,
        label: `${recent.ticker} · recent analysis`,
        group: "Research",
        href: `/analysis?symbol=${encodeURIComponent(recent.ticker)}`,
        detail: recent.recommendation || "Data unavailable.",
      });
    }
  }

  for (const entry of input.notebookEntries ?? []) {
    if (
      entry.text.toLowerCase().includes(q) ||
      (entry.symbol ?? "").toLowerCase().includes(q) ||
      entry.kind.includes(q)
    ) {
      hits.push({
        id: `nb-${entry.id}`,
        label: entry.text.slice(0, 80),
        group: "Notes",
        href: entry.symbol
          ? `/research/canvas?symbol=${encodeURIComponent(entry.symbol)}&tab=notes`
          : "/research/canvas?tab=notes",
        detail: entry.kind,
      });
    }
  }

  for (const report of listRecentReports()) {
    const hay = `${report.reportId} ${report.symbol ?? ""}`.toLowerCase();
    if (hay.includes(q)) {
      hits.push({
        id: `rp-${report.reportId}`,
        label: report.reportId,
        group: "Reports",
        href: report.symbol
          ? `/research/institutional?symbol=${encodeURIComponent(report.symbol)}`
          : "/research/institutional",
        detail: report.symbol ?? undefined,
      });
    }
  }

  for (const saved of input.savedComparisonTitles ?? []) {
    const hay = `${saved.title} ${saved.symbols.join(" ")}`.toLowerCase();
    if (hay.includes(q)) {
      hits.push({
        id: `cmp-${saved.title}`,
        label: saved.title,
        group: "Comparisons",
        href: saved.href,
        detail: saved.symbols.join(", "),
      });
    }
  }

  for (const tab of CANVAS_TABS) {
    if (
      tab.label.toLowerCase().includes(q) ||
      tab.description.toLowerCase().includes(q) ||
      tab.id.toLowerCase().includes(q)
    ) {
      hits.push({
        id: `tab-${tab.id}`,
        label: tab.label,
        group: "Tabs",
        href: tab.href(null),
        detail: tab.description,
      });
    }
  }

  if ("timeline".includes(q) || "history".includes(q) || q.includes("timeline")) {
    hits.push({
      id: "tl-hint",
      label: "Research Timeline",
      group: "Timeline",
      href: "/research/canvas?tab=timeline",
      detail: "Compose local history + RI when available",
    });
  }

  if ("committee".includes(q) || q.includes("committee") || q.includes("ai")) {
    hits.push({
      id: "cm-hint",
      label: "AI Committee",
      group: "Committee",
      href: "/research/canvas?tab=committee",
      detail: "Open committee surface for active symbol",
    });
  }

  return hits.slice(0, 40);
}
