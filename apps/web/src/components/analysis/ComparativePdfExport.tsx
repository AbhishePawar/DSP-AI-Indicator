"use client";

import { useCallback, useEffect } from "react";
import type { BatchEntry } from "@/components/analysis/BatchAnalysisQueue";
import type { AnalysisWorkspaceView } from "@/lib/analysis/types";

const COMP_PRINT_STYLE_ID = "dsp-comparative-print-style";

const COMP_PRINT_CSS = `
@media print {
  /* Hide everything except the comparative print report */
  body > *:not(#dsp-comparative-print-root) {
    display: none !important;
  }
  #dsp-comparative-print-root {
    display: block !important;
  }

  @page {
    size: A3 landscape;
    margin: 15mm 14mm 15mm 14mm;
  }

  #dsp-comparative-print-root * {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
    box-sizing: border-box;
  }

  #dsp-comparative-print-root {
    font-family: 'Sora', 'Inter', system-ui, sans-serif;
    font-size: 8pt;
    line-height: 1.5;
    color: #1a1a1a;
    background: #ffffff;
  }

  /* Page breaks */
  .cpdf-section {
    page-break-inside: avoid;
    break-inside: avoid;
  }
  .cpdf-page-break {
    page-break-before: always;
    break-before: always;
  }

  /* Report header */
  .cpdf-report-header {
    margin-bottom: 12pt;
  }
  .cpdf-report-meta {
    font-size: 6.5pt;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #6b7280;
    margin-bottom: 3pt;
  }
  .cpdf-report-title {
    font-size: 18pt;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #111111;
    margin: 0 0 2pt 0;
  }
  .cpdf-report-subtitle {
    font-size: 8pt;
    color: #6b7280;
  }

  /* Heavy rule */
  .cpdf-rule-heavy {
    border: none;
    border-top: 2pt solid #1a1a1a;
    margin: 8pt 0 10pt 0;
  }
  .cpdf-rule {
    border: none;
    border-top: 0.5pt solid #d1d5db;
    margin: 6pt 0;
  }

  /* Section heading */
  .cpdf-section-heading {
    font-size: 9pt;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: #111111;
    padding-bottom: 4pt;
    border-bottom: 1pt solid #d1d5db;
    margin-bottom: 6pt;
  }
  .cpdf-group-label {
    font-size: 6pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #9ca3af;
    margin-bottom: 4pt;
  }

  /* Peer comparison table */
  .cpdf-peer-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
  }
  .cpdf-peer-table th {
    font-size: 7pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #6b7280;
    padding: 4pt 6pt;
    border-bottom: 1pt solid #1a1a1a;
    text-align: left;
    background: #f9fafb;
  }
  .cpdf-peer-table th.cpdf-metric-col {
    width: 18%;
    color: #374151;
  }
  .cpdf-peer-table td {
    padding: 3.5pt 6pt;
    font-size: 8pt;
    vertical-align: top;
    border-bottom: 0.5pt solid #e5e7eb;
  }
  .cpdf-peer-table td.cpdf-metric-label {
    color: #6b7280;
    font-size: 7.5pt;
  }
  .cpdf-peer-table td.cpdf-value {
    font-weight: 600;
    color: #111111;
    font-variant-numeric: tabular-nums;
  }
  .cpdf-peer-table tr:last-child td {
    border-bottom: none;
  }

  /* Signal summary row */
  .cpdf-signal-row {
    display: flex;
    gap: 0;
    margin-bottom: 10pt;
  }
  .cpdf-signal-cell {
    flex: 1;
    padding: 6pt 8pt;
    border: 0.5pt solid #e5e7eb;
    border-right: none;
  }
  .cpdf-signal-cell:last-child {
    border-right: 0.5pt solid #e5e7eb;
  }
  .cpdf-signal-ticker {
    font-size: 9pt;
    font-weight: 700;
    font-family: 'Courier New', monospace;
    color: #111111;
    margin-bottom: 2pt;
  }
  .cpdf-signal-rec {
    font-size: 8pt;
    font-weight: 600;
    color: #1a1a1a;
  }
  .cpdf-signal-quality {
    font-size: 7pt;
    color: #6b7280;
    margin-top: 1pt;
  }
  .cpdf-signal-confidence {
    font-size: 7pt;
    color: #9ca3af;
  }

  /* Positioning section */
  .cpdf-positioning-grid {
    display: grid;
    gap: 10pt;
  }
  .cpdf-company-block {
    padding: 6pt 8pt;
    border: 0.5pt solid #e5e7eb;
  }
  .cpdf-company-name {
    font-size: 8pt;
    font-weight: 700;
    color: #111111;
    margin-bottom: 3pt;
  }
  .cpdf-thesis-text {
    font-size: 7.5pt;
    color: #374151;
    line-height: 1.5;
    border-left: 1.5pt solid #2d6a4f;
    padding-left: 5pt;
  }
  .cpdf-bullet-list {
    list-style: none;
    padding: 0;
    margin: 3pt 0 0 0;
  }
  .cpdf-bullet-list li {
    font-size: 7pt;
    color: #374151;
    line-height: 1.4;
    margin-bottom: 2pt;
    display: flex;
    gap: 4pt;
  }
  .cpdf-bullet-list li::before {
    content: '—';
    color: #9ca3af;
    flex-shrink: 0;
  }

  /* Footer */
  .cpdf-footer {
    margin-top: 14pt;
    padding-top: 5pt;
    border-top: 0.5pt solid #d1d5db;
    font-size: 6pt;
    color: #9ca3af;
    line-height: 1.4;
  }

  /* Spacing helpers */
  .cpdf-mt-8  { margin-top: 8pt; }
  .cpdf-mt-12 { margin-top: 12pt; }
  .cpdf-mb-4  { margin-bottom: 4pt; }
}
`;

function injectCompPrintStyle() {
  if (document.getElementById(COMP_PRINT_STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = COMP_PRINT_STYLE_ID;
  style.textContent = COMP_PRINT_CSS;
  document.head.appendChild(style);
}

function removeCompPrintStyle() {
  document.getElementById(COMP_PRINT_STYLE_ID)?.remove();
}

// ─── Metric extraction helpers ──────────────────────────────────────────────

function getVal(field: { value: string | null } | null | undefined): string {
  return field?.value ?? "—";
}

function getArrVal(field: { value: string[] | null } | null | undefined): string[] {
  return field?.value ?? [];
}

type PeerMetricRow = {
  label: string;
  values: string[];
};

function buildPeerMetrics(views: AnalysisWorkspaceView[]): PeerMetricRow[] {
  return [
    {
      label: "Recommendation",
      values: views.map((v) => getVal(v.dashboard.researchConclusion)),
    },
    {
      label: "Business Quality",
      values: views.map((v) => getVal(v.dashboard.businessScore)),
    },
    {
      label: "Confidence",
      values: views.map((v) => getVal(v.dashboard.researchConfidence)),
    },
    {
      label: "Intrinsic Value Range",
      values: views.map((v) => getVal(v.conclusion.intrinsicValueRange)),
    },
    {
      label: "Margin of Safety",
      values: views.map((v) => getVal(v.conclusion.marginOfSafety)),
    },
    {
      label: "Current Price",
      values: views.map((v) => getVal(v.valuation.currentPrice)),
    },
    {
      label: "Research Health",
      values: views.map((v) => getVal(v.conclusion.researchHealth)),
    },
    {
      label: "Investment Horizon",
      values: views.map((v) => getVal(v.conclusion.investmentHorizon)),
    },
    {
      label: "Primary Opportunity",
      values: views.map((v) => getVal(v.conclusion.primaryOpportunity)),
    },
    {
      label: "Primary Risk",
      values: views.map((v) => getVal(v.conclusion.primaryRisk)),
    },
    {
      label: "Coverage %",
      values: views.map((v) => `${v.coverage.coveragePercent}%`),
    },
    {
      label: "Confidence Matrix",
      values: views.map((v) => v.confidenceMatrix.overall.replace(/_/g, " ")),
    },
  ];
}

// ─── Component ──────────────────────────────────────────────────────────────

interface Props {
  entries: BatchEntry[];
  generatedAt: string;
}

export function ComparativePdfExport({ entries, generatedAt }: Props) {
  const doneEntries = entries.filter((e) => e.status === "done" && e.view);

  useEffect(() => {
    injectCompPrintStyle();
    return () => removeCompPrintStyle();
  }, []);

  const handleExport = useCallback(() => {
    injectCompPrintStyle();
    window.print();
  }, []);

  if (doneEntries.length < 2) return null;

  const views = doneEntries.map((e) => e.view!);
  const tickers = doneEntries.map((e) => e.ticker);
  const peerMetrics = buildPeerMetrics(views);

  // Column widths: first col is metric label, rest are per-company
  const colWidth = `${Math.floor(80 / tickers.length)}%`;

  return (
    <>
      {/* ── Export button ── */}
      <button
        type="button"
        onClick={handleExport}
        className="inline-flex items-center gap-1.5 rounded border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-medium text-[var(--fg)] hover:bg-[var(--surface-hover)] transition-colors print:hidden"
        aria-label="Export comparative PDF"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-3.5 w-3.5 text-[var(--muted)]"
          aria-hidden
        >
          <path
            fillRule="evenodd"
            d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5zm4.75 6.75a.75.75 0 011.5 0v2.546l.943-1.048a.75.75 0 111.114 1.004l-2.25 2.5a.75.75 0 01-1.114 0l-2.25-2.5a.75.75 0 111.114-1.004l.943 1.048V8.75z"
            clipRule="evenodd"
          />
        </svg>
        Export Comparative PDF ({doneEntries.length} companies)
      </button>

      {/* ── Print-only comparative report ── */}
      <div
        id="dsp-comparative-print-root"
        style={{ display: "none" }}
        aria-hidden="true"
      >
        {/* Report header */}
        <div className="cpdf-report-header cpdf-section">
          <p className="cpdf-report-meta">DSP AI Indicator · Peer Comparison Report</p>
          <h1 className="cpdf-report-title">
            Comparative Analysis: {tickers.join(" vs ")}
          </h1>
          <p className="cpdf-report-subtitle">
            Generated {generatedAt} · {doneEntries.length} companies analysed
          </p>
        </div>

        <hr className="cpdf-rule-heavy" />

        {/* ── Signal summary row ── */}
        <div className="cpdf-section cpdf-mb-4">
          <p className="cpdf-group-label">Positioning Summary</p>
          <div className="cpdf-signal-row">
            {doneEntries.map((entry) => {
              const v = entry.view!;
              return (
                <div key={entry.ticker} className="cpdf-signal-cell">
                  <p className="cpdf-signal-ticker">{entry.ticker}</p>
                  <p className="cpdf-signal-rec">
                    {getVal(v.dashboard.researchConclusion)}
                  </p>
                  <p className="cpdf-signal-quality">
                    {getVal(v.dashboard.businessScore)}
                  </p>
                  <p className="cpdf-signal-confidence">
                    Confidence: {getVal(v.dashboard.researchConfidence)}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Peer metrics table ── */}
        <div className="cpdf-section cpdf-mt-12">
          <p className="cpdf-section-heading">Peer Metrics</p>
          <table className="cpdf-peer-table">
            <thead>
              <tr>
                <th className="cpdf-metric-col">Metric</th>
                {tickers.map((t) => (
                  <th key={t} style={{ width: colWidth }}>
                    {t}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {peerMetrics.map((row) => (
                <tr key={row.label}>
                  <td className="cpdf-metric-label">{row.label}</td>
                  {row.values.map((val, i) => (
                    <td key={tickers[i]} className="cpdf-value">
                      {val}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* ── Positioning section ── */}
        <div className="cpdf-section cpdf-page-break cpdf-mt-12">
          <p className="cpdf-section-heading">Investment Positioning</p>
          <div
            className="cpdf-positioning-grid"
            style={{
              gridTemplateColumns: `repeat(${Math.min(tickers.length, 3)}, 1fr)`,
            }}
          >
            {doneEntries.map((entry) => {
              const v = entry.view!;
              const strengths = getArrVal(v.thesis.keyStrengths).slice(0, 4);
              const concerns = getArrVal(v.thesis.keyConcerns).slice(0, 3);
              const thesis = getVal(v.thesis.longTermThesis);
              return (
                <div key={entry.ticker} className="cpdf-company-block">
                  <p className="cpdf-company-name">{entry.ticker}</p>
                  {thesis !== "—" && (
                    <p className="cpdf-thesis-text">{thesis}</p>
                  )}
                  {strengths.length > 0 && (
                    <div style={{ marginTop: "4pt" }}>
                      <p
                        style={{
                          fontSize: "6pt",
                          fontWeight: 700,
                          textTransform: "uppercase",
                          letterSpacing: "0.06em",
                          color: "#065f46",
                          marginBottom: "2pt",
                        }}
                      >
                        Strengths
                      </p>
                      <ul className="cpdf-bullet-list">
                        {strengths.map((s) => (
                          <li key={s.slice(0, 40)}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {concerns.length > 0 && (
                    <div style={{ marginTop: "4pt" }}>
                      <p
                        style={{
                          fontSize: "6pt",
                          fontWeight: 700,
                          textTransform: "uppercase",
                          letterSpacing: "0.06em",
                          color: "#991b1b",
                          marginBottom: "2pt",
                        }}
                      >
                        Concerns
                      </p>
                      <ul className="cpdf-bullet-list">
                        {concerns.map((c) => (
                          <li key={c.slice(0, 40)}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Footer ── */}
        <div className="cpdf-footer">
          <p>
            <strong>DSP AI Indicator</strong> — Comparative peer analysis generated by the DSP
            composition pipeline. Provided for informational purposes only. Does not constitute
            investment advice. All values are DSP-calculated; no values have been fabricated or
            derived in the client. Past performance is not indicative of future results.
          </p>
          <p style={{ marginTop: "2pt" }}>
            Generated: {generatedAt} · Tickers: {tickers.join(", ")}
          </p>
        </div>
      </div>
    </>
  );
}
