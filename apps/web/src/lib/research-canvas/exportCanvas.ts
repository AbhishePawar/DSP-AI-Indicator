/**
 * EPIC-014 — Research Canvas export helpers.
 * JSON / HTML / print — no native PDF/DOCX engine (honest gaps).
 */

import type { NotebookEntry } from "./notebookStore";
import type { TimelineEvent } from "./timeline";

export type CanvasExportPackage = {
  exportedAt: string;
  symbol: string | null;
  tab: string;
  notebook: NotebookEntry[];
  timeline: TimelineEvent[];
  disclaimer: string;
  gaps: string[];
};

export function buildCanvasExportPackage(input: {
  symbol: string | null;
  tab: string;
  notebook: NotebookEntry[];
  timeline: TimelineEvent[];
}): CanvasExportPackage {
  return {
    exportedAt: new Date().toISOString(),
    symbol: input.symbol,
    tab: input.tab,
    notebook: input.notebook,
    timeline: input.timeline,
    disclaimer:
      "User-authored notebook content is personal research workspace material. It does not overwrite or constitute institutional research outputs. No personalized investment advice.",
    gaps: [
      "Native DOCX export: unavailable in this client.",
      "Native PDF engine: use browser Print → Save as PDF.",
      "IC memo formatting: HTML package only — institutional memo templates require report export surfaces.",
      "Committee package: include committee section via Company Analysis export when linked research exists.",
    ],
  };
}

export function canvasPackageToJson(pkg: CanvasExportPackage): string {
  return JSON.stringify(pkg, null, 2);
}

export function canvasPackageToHtml(pkg: CanvasExportPackage): string {
  const notes = pkg.notebook
    .map(
      (n) =>
        `<li><strong>${escapeHtml(n.kind)}</strong> ${escapeHtml(n.text)} <em>${escapeHtml(n.at)}</em></li>`,
    )
    .join("");
  const timeline = pkg.timeline
    .map(
      (t) =>
        `<li><strong>${escapeHtml(t.title)}</strong> — ${escapeHtml(t.detail)} <em>${escapeHtml(t.at)}</em></li>`,
    )
    .join("");
  const gaps = pkg.gaps.map((g) => `<li>${escapeHtml(g)}</li>`).join("");
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Research Canvas Export${pkg.symbol ? ` · ${escapeHtml(pkg.symbol)}` : ""}</title>
<style>
  body { font-family: Georgia, serif; margin: 2rem; color: #111; }
  h1,h2 { font-family: system-ui, sans-serif; }
  .muted { color: #555; font-size: 0.9rem; }
  @media print { body { margin: 1rem; } }
</style>
</head>
<body>
  <h1>Research Canvas Package</h1>
  <p class="muted">Exported ${escapeHtml(pkg.exportedAt)} · Symbol ${escapeHtml(pkg.symbol ?? "Data unavailable.")} · Tab ${escapeHtml(pkg.tab)}</p>
  <p>${escapeHtml(pkg.disclaimer)}</p>
  <h2>Notebook (user-authored)</h2>
  <ul>${notes || "<li>Data unavailable.</li>"}</ul>
  <h2>Timeline</h2>
  <ul>${timeline || "<li>Data unavailable.</li>"}</ul>
  <h2>Export gaps</h2>
  <ul>${gaps}</ul>
</body>
</html>`;
}

export function downloadText(
  filename: string,
  content: string,
  mimeType: string,
): void {
  if (typeof window === "undefined") return;
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
