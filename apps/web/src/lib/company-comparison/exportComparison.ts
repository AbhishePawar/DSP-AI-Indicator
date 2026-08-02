/**
 * Institutional export helpers — serialize comparison model only.
 * No recalculation. PDF/DOCX via browser print (existing pattern).
 */

import type { ComparisonWorkspaceModel } from "./types";

export function comparisonToJson(model: ComparisonWorkspaceModel): string {
  return JSON.stringify(
    {
      exportedAt: new Date().toISOString(),
      source: "dsp_platform institutional company comparison (client-orchestrated /analyse)",
      note: "Display snapshot only — no client-side scoring or investment decisions.",
      kind: model.kind,
      version: model.version,
      disclaimer: model.disclaimer,
      buffettDisclaimer: model.buffettDisclaimer,
      symbols: model.symbols,
      executive: model.executive,
      winnerMatrix: model.winnerMatrix,
      tradeOffs: model.tradeOffs,
      valuation: model.valuation,
      qualityModules: model.qualityModules,
      evidence: model.evidence,
      explainability: model.explainability,
      intelligence: model.intelligence,
      buffettPreference: model.buffettPreference,
      heatmap: model.heatmap,
      scenarios: model.scenarios,
      portfolioFit: model.portfolioFit,
      coverageNotes: model.coverageNotes,
    },
    null,
    2,
  );
}

function csvEscape(value: string): string {
  if (/[",\n]/.test(value)) return `"${value.replace(/"/g, '""')}"`;
  return value;
}

export function comparisonToCsv(model: ComparisonWorkspaceModel): string {
  const header = ["dimension", ...model.symbols];
  const rows: string[][] = [header];

  for (const row of model.winnerMatrix) {
    const bySymbol = new Map(row.cells.map((c) => [c.symbol, c.display]));
    rows.push([
      row.label,
      ...model.symbols.map((s) => bySymbol.get(s) ?? "Data unavailable."),
    ]);
  }

  rows.push([]);
  rows.push(["field", "value"]);
  rows.push(["winnerSummary", model.executive.winnerSummary]);
  rows.push(["confidence", model.executive.confidence]);
  rows.push(["coverage", model.executive.coverage]);
  rows.push(["buffettDisclaimer", model.buffettDisclaimer]);

  return rows.map((r) => r.map((c) => csvEscape(String(c))).join(",")).join("\n");
}

export function comparisonToHtml(model: ComparisonWorkspaceModel): string {
  const matrixRows = model.winnerMatrix
    .map((row) => {
      const cells = model.symbols
        .map((sym) => {
          const cell = row.cells.find((c) => c.symbol === sym);
          const medal = cell?.medal ? ` [${cell.medal}]` : "";
          return `<td>${cell?.display ?? "Data unavailable."}${medal}</td>`;
        })
        .join("");
      return `<tr><th scope="row">${row.label}</th>${cells}</tr>`;
    })
    .join("");

  const tradeOffs = model.tradeOffs
    .map((t) => `<li><strong>${t.dimension}:</strong> ${t.summary}</li>`)
    .join("");

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Institutional Company Comparison — ${model.symbols.join(" vs ")}</title>
<style>
  body { font-family: Georgia, serif; margin: 2rem; color: #111; }
  h1,h2 { font-family: system-ui, sans-serif; }
  table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
  th, td { border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left; }
  .disclaimer { font-size: 0.85rem; color: #444; max-width: 60rem; }
  @media print { body { margin: 1rem; } }
</style>
</head>
<body>
<h1>Institutional Company Comparison</h1>
<p class="disclaimer">${model.disclaimer}</p>
<p class="disclaimer">${model.buffettDisclaimer}</p>
<h2>Executive Summary</h2>
<p>${model.executive.overall}</p>
<p>${model.executive.institutionalSummary}</p>
<p><strong>Winners:</strong> ${model.executive.winnerSummary}</p>
<h2>Winner Matrix</h2>
<table>
<thead><tr><th>Dimension</th>${model.symbols.map((s) => `<th>${s}</th>`).join("")}</tr></thead>
<tbody>${matrixRows}</tbody>
</table>
<h2>Trade-offs</h2>
<ul>${tradeOffs || "<li>Data unavailable.</li>"}</ul>
<p><em>Exported ${model.generatedAt}. Print this page for PDF.</em></p>
</body>
</html>`;
}

export function downloadText(filename: string, content: string, mime: string) {
  if (typeof document === "undefined") return;
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
