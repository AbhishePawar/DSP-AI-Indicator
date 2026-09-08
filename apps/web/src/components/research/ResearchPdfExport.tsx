"use client";

import { useCallback, useEffect, useRef } from "react";
import type { ResearchView } from "@/lib/research/mapResearchView";

/**
 * ResearchPdfExport
 *
 * Renders a hidden, print-optimised version of the research report and
 * triggers window.print() when the user clicks "Export PDF".
 *
 * Uses the browser's native print-to-PDF capability — no external library
 * required. A dedicated <style> block is injected into <head> for the
 * duration of the print job and removed afterwards.
 */

const PRINT_STYLE_ID = "dsp-research-print-style";

const PRINT_CSS = `
@media print {
  /* Hide everything except the print report */
  body > *:not(#dsp-print-root) {
    display: none !important;
  }
  #dsp-print-root {
    display: block !important;
  }

  /* Page setup */
  @page {
    size: A4 portrait;
    margin: 20mm 18mm 20mm 18mm;
  }

  /* Reset */
  #dsp-print-root * {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
    box-sizing: border-box;
  }

  /* Typography */
  #dsp-print-root {
    font-family: 'Sora', 'Inter', system-ui, sans-serif;
    font-size: 9pt;
    line-height: 1.55;
    color: #1a1a1a;
    background: #ffffff;
  }

  /* Page breaks */
  .pdf-section {
    page-break-inside: avoid;
    break-inside: avoid;
  }
  .pdf-section-break {
    page-break-before: always;
    break-before: always;
  }

  /* Headings */
  .pdf-h1 {
    font-size: 20pt;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.2;
    color: #111111;
    margin: 0 0 4pt 0;
  }
  .pdf-h2 {
    font-size: 12pt;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: #111111;
    margin: 0 0 3pt 0;
    padding-bottom: 4pt;
    border-bottom: 1pt solid #d1d5db;
  }
  .pdf-h3 {
    font-size: 7pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #6b7280;
    margin: 0 0 4pt 0;
  }

  /* Dividers */
  .pdf-rule {
    border: none;
    border-top: 1pt solid #d1d5db;
    margin: 8pt 0;
  }
  .pdf-rule-heavy {
    border: none;
    border-top: 2pt solid #1a1a1a;
    margin: 6pt 0 10pt 0;
  }

  /* Header block */
  .pdf-header {
    margin-bottom: 14pt;
  }
  .pdf-header-meta {
    font-size: 7pt;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #6b7280;
    margin-bottom: 4pt;
  }
  .pdf-ticker {
    font-family: 'Courier New', monospace;
    font-size: 8pt;
    color: #6b7280;
    margin-top: 2pt;
  }
  .pdf-timestamp {
    font-size: 7pt;
    color: #9ca3af;
    margin-top: 2pt;
  }

  /* Signal row */
  .pdf-signals {
    display: flex;
    gap: 24pt;
    margin-top: 8pt;
    padding-top: 8pt;
    border-top: 1pt solid #e5e7eb;
  }
  .pdf-signal-label {
    font-size: 6.5pt;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #6b7280;
    margin-bottom: 2pt;
  }
  .pdf-signal-value {
    font-size: 11pt;
    font-weight: 700;
    color: #111111;
    letter-spacing: -0.01em;
  }

  /* Thesis block */
  .pdf-thesis {
    border-left: 2pt solid #2d6a4f;
    padding-left: 8pt;
    margin: 8pt 0;
  }
  .pdf-thesis p {
    font-size: 9pt;
    line-height: 1.6;
    color: #1a1a1a;
    margin: 0;
  }

  /* Two-column grid */
  .pdf-grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16pt;
    margin-top: 6pt;
  }

  /* Bullet lists */
  .pdf-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .pdf-list li {
    display: flex;
    gap: 5pt;
    font-size: 8.5pt;
    line-height: 1.5;
    color: #1a1a1a;
    margin-bottom: 3pt;
  }
  .pdf-list li::before {
    content: '—';
    color: #9ca3af;
    flex-shrink: 0;
    font-size: 8pt;
  }

  /* Metric table */
  .pdf-metric-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 4pt;
  }
  .pdf-metric-table tr {
    border-bottom: 0.5pt solid #e5e7eb;
  }
  .pdf-metric-table tr:last-child {
    border-bottom: none;
  }
  .pdf-metric-table td {
    padding: 3.5pt 0;
    font-size: 8.5pt;
    vertical-align: baseline;
  }
  .pdf-metric-table td:first-child {
    color: #6b7280;
    width: 45%;
  }
  .pdf-metric-table td:last-child {
    font-weight: 600;
    color: #111111;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  /* Stage badge */
  .pdf-badge {
    display: inline-block;
    font-size: 6.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 1pt 4pt;
    border-radius: 2pt;
    border: 0.5pt solid #d1d5db;
    color: #374151;
    margin-left: 6pt;
    vertical-align: middle;
  }
  .pdf-badge-success { border-color: #6ee7b7; color: #065f46; }
  .pdf-badge-danger  { border-color: #fca5a5; color: #991b1b; }

  /* Footer */
  .pdf-footer {
    margin-top: 16pt;
    padding-top: 6pt;
    border-top: 1pt solid #d1d5db;
    font-size: 6.5pt;
    color: #9ca3af;
    line-height: 1.4;
  }

  /* Spacing helpers */
  .pdf-mt-6  { margin-top: 6pt; }
  .pdf-mt-10 { margin-top: 10pt; }
  .pdf-mt-14 { margin-top: 14pt; }
  .pdf-mb-4  { margin-bottom: 4pt; }
}
`;

function injectPrintStyle() {
  if (document.getElementById(PRINT_STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = PRINT_STYLE_ID;
  style.textContent = PRINT_CSS;
  document.head.appendChild(style);
}

function removePrintStyle() {
  document.getElementById(PRINT_STYLE_ID)?.remove();
}

interface Props {
  view: ResearchView;
  analysedAtLabel: string;
}

export function ResearchPdfExport({ view, analysedAtLabel }: Props) {
  const printRootRef = useRef<HTMLDivElement>(null);

  // Inject print CSS once on mount; clean up on unmount
  useEffect(() => {
    injectPrintStyle();
    return () => removePrintStyle();
  }, []);

  const handleExport = useCallback(() => {
    injectPrintStyle();
    window.print();
  }, []);

  const sections: Array<{ id: string; title: string; section: ResearchView["businessQuality"] | undefined }> = [
    { id: "business-quality",    title: "Business Quality",    section: view.businessQuality },
    { id: "financial-strength",  title: "Financial Strength",  section: view.financialStrength },
    { id: "management",          title: "Management Quality",  section: view.management },
    { id: "earnings",            title: "Earnings Quality",    section: view.earnings },
    { id: "growth",              title: "Growth Quality",      section: view.growth },
  ];

  const valuationMetrics = [
    { label: "Intrinsic Value",   value: view.valuation.intrinsicValue },
    { label: "Current Price",     value: view.valuation.currentPrice },
    { label: "Margin of Safety",  value: view.valuation.marginOfSafety },
    { label: "Valuation Method",  value: view.valuation.method },
    { label: "Confidence",        value: view.valuation.confidence },
  ];

  const committeeMetrics = [
    { label: "Committee Decision",      value: view.committeeDecision },
    { label: "Confidence",              value: view.committee.confidence },
    { label: "Final Recommendation",    value: view.committee.finalRecommendation },
  ];

  return (
    <>
      {/* Trigger button — visible on screen, hidden in print */}
      <button
        onClick={handleExport}
        className="inline-flex items-center gap-1.5 rounded border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-medium text-[var(--fg)] hover:bg-[var(--surface-hover)] transition-colors print:hidden"
        aria-label="Export research report as PDF"
        type="button"
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
        Export PDF
      </button>

      {/* ─── Print-only report ─────────────────────────────────────────── */}
      <div
        id="dsp-print-root"
        ref={printRootRef}
        style={{ display: "none" }}
        aria-hidden="true"
      >
        {/* ── Company Header ── */}
        <div className="pdf-header pdf-section">
          <p className="pdf-header-meta">DSP AI Indicator · Equity Research</p>
          <h1 className="pdf-h1">{view.company}</h1>
          <p className="pdf-ticker">
            {view.ticker}
            {view.exchange ? ` · ${view.exchange}` : ""}
          </p>
          <p className="pdf-timestamp">Analysis as of {analysedAtLabel}</p>

          <div className="pdf-signals">
            <div>
              <p className="pdf-signal-label">Recommendation</p>
              <p className="pdf-signal-value">{view.recommendation}</p>
            </div>
            <div>
              <p className="pdf-signal-label">Business Quality</p>
              <p className="pdf-signal-value">{view.businessQualityLabel}</p>
            </div>
            <div>
              <p className="pdf-signal-label">Confidence</p>
              <p className="pdf-signal-value">
                {view.recommendationConfidence != null
                  ? `${Math.round(Number(view.recommendationConfidence) * 100)}%`
                  : "—"}
              </p>
            </div>
          </div>
        </div>

        <hr className="pdf-rule-heavy" />

        {/* ── Executive Summary ── */}
        <div className="pdf-section pdf-mt-10">
          <h2 className="pdf-h2">Executive Summary</h2>

          {(view.committeeConsensus || view.recommendation) ? (
            <div className="pdf-thesis pdf-mt-6">
              <p className="pdf-h3 pdf-mb-4">Investment Thesis</p>
              <p>{view.committeeConsensus || view.recommendation}</p>
            </div>
          ) : null}

          <div className="pdf-grid-2 pdf-mt-6">
            <div>
              <p className="pdf-h3">Key Highlights</p>
              {view.strengths.length ? (
                <ul className="pdf-list">
                  {view.strengths.slice(0, 6).map((s) => (
                    <li key={s.slice(0, 40)}>{s}</li>
                  ))}
                </ul>
              ) : (
                <p style={{ fontSize: "8pt", color: "#9ca3af" }}>None reported</p>
              )}
            </div>
            <div>
              <p className="pdf-h3">Key Risks</p>
              {(view.risks.length || view.weaknesses.length) ? (
                <ul className="pdf-list">
                  {[...view.risks, ...view.weaknesses].slice(0, 6).map((r) => (
                    <li key={r.slice(0, 40)}>{r}</li>
                  ))}
                </ul>
              ) : (
                <p style={{ fontSize: "8pt", color: "#9ca3af" }}>None reported</p>
              )}
            </div>
          </div>
        </div>

        <hr className="pdf-rule" />

        {/* ── Analysis Sections ── */}
        {sections.map(({ id, title, section }) => (
          <div key={id} className="pdf-section pdf-mt-10">
            <h2 className="pdf-h2">
              {title}
              {section ? (
                <span
                  className={`pdf-badge ${
                    section.status === "succeeded" ?"pdf-badge-success"
                      : section.status === "failed" ?"pdf-badge-danger" :""
                  }`}
                >
                  {section.status}
                </span>
              ) : null}
            </h2>

            {section?.metrics.length ? (
              <table className="pdf-metric-table pdf-mt-6">
                <tbody>
                  {section.metrics.map((m) => (
                    <tr key={m.label}>
                      <td>{m.label}</td>
                      <td>{m.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : null}

            {section?.error ? (
              <p style={{ fontSize: "8pt", color: "#991b1b", marginTop: "4pt" }}>
                {section.error}
              </p>
            ) : null}
          </div>
        ))}

        <hr className="pdf-rule" />

        {/* ── Valuation ── */}
        <div className="pdf-section pdf-mt-10">
          <h2 className="pdf-h2">Valuation</h2>
          <table className="pdf-metric-table pdf-mt-6">
            <tbody>
              {valuationMetrics.map((m) => (
                <tr key={m.label}>
                  <td>{m.label}</td>
                  <td>{m.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <hr className="pdf-rule" />

        {/* ── Investment Committee ── */}
        <div className="pdf-section pdf-section-break pdf-mt-14">
          <h2 className="pdf-h2">Investment Committee</h2>

          <table className="pdf-metric-table pdf-mt-6">
            <tbody>
              {committeeMetrics.map((m) => (
                <tr key={m.label}>
                  <td>{m.label}</td>
                  <td>{m.value}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {view.committeeConsensus ? (
            <div className="pdf-thesis pdf-mt-6">
              <p className="pdf-h3 pdf-mb-4">Committee Consensus</p>
              <p>{view.committeeConsensus}</p>
            </div>
          ) : null}

          <div className="pdf-grid-2 pdf-mt-6">
            <div>
              <p className="pdf-h3">Supporting Reasons</p>
              {view.committee.supportingReasons.length ? (
                <ul className="pdf-list">
                  {view.committee.supportingReasons.map((r) => (
                    <li key={r.slice(0, 40)}>{r}</li>
                  ))}
                </ul>
              ) : (
                <p style={{ fontSize: "8pt", color: "#9ca3af" }}>None reported</p>
              )}
            </div>
            <div>
              <p className="pdf-h3">Opposing Reasons</p>
              {view.committee.opposingReasons.length ? (
                <ul className="pdf-list">
                  {view.committee.opposingReasons.map((r) => (
                    <li key={r.slice(0, 40)}>{r}</li>
                  ))}
                </ul>
              ) : (
                <p style={{ fontSize: "8pt", color: "#9ca3af" }}>None reported</p>
              )}
            </div>
          </div>
        </div>

        {/* ── Footer / Disclaimer ── */}
        <div className="pdf-footer">
          <p>
            <strong>DSP AI Indicator</strong> — This report is generated by the
            DSP composition pipeline and is provided for informational purposes
            only. It does not constitute investment advice. All values are
            DSP-calculated; no values have been fabricated or derived in the
            client. Past performance is not indicative of future results.
          </p>
          <p style={{ marginTop: "3pt" }}>
            Generated: {analysedAtLabel} · Ticker: {view.ticker}
            {view.exchange ? ` · ${view.exchange}` : ""}
          </p>
        </div>
      </div>
    </>
  );
}
