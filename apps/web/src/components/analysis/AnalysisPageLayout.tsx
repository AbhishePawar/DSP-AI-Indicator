"use client";

/**
 * AnalysisPageLayout — /analysis?symbol=TCS presentation layer.
 *
 * Information architecture:
 *   1. Company Header
 *   2. Key Metrics
 *   3. AI Investment View
 *   4. Valuation
 *   5. Charts (Market Data)
 *   6. Fundamentals
 *   7. Quality
 *   8. Peers
 *   9. Institutional / MF Activity
 *  10. AI Research
 *
 * Thin client — all data from existing AnalysisWorkspaceView + API endpoints.
 * No client-side scoring, no mock data, no invented endpoints.
 */


import { AnalysisSectionShell } from "@/components/analysis/AnalysisSectionShell";
import { EquityResearchHeader } from "@/components/analysis/EquityResearchHeader";
import { KeyMetricsSection } from "@/components/analysis/KeyMetricsSection";
import { AIInvestmentViewSection } from "@/components/analysis/AIInvestmentViewSection";
import { ValuationSection } from "@/components/analysis/ValuationSection";
import { ChartsSection } from "@/components/analysis/ChartsSection";
import { FundamentalsSection } from "@/components/analysis/FundamentalsSection";
import { QualitySection } from "@/components/analysis/QualitySection";
import { PeersSection } from "@/components/analysis/PeersSection";
import { InstitutionalActivitySection } from "@/components/analysis/InstitutionalActivitySection";
import { AIResearchSection } from "@/components/analysis/AIResearchSection";
import { ComparisonReportSection } from "@/components/analysis/ComparisonReportSection";
import { ExportShareSection } from "@/components/analysis/ExportShareSection";
import { RisksOpportunitiesSection } from "@/components/analysis/RisksOpportunitiesSection";
import { DataFreshnessSection } from "@/components/analysis/DataFreshnessSection";
import { AnalystResearchNotesSection } from "@/components/analysis/AnalystResearchNotesSection";
import { CopilotProvider } from "@/components/analysis/copilot/CopilotContext";
import { ResearchCopilotWorkspace } from "@/components/analysis/copilot/ResearchCopilotWorkspace";

import { Skeleton } from "@/components/ui/Skeleton";
import { useAuth } from "@/lib/auth/AuthProvider";
import type { AnalysisWorkspaceView } from "@/lib/analysis/types";

/* ─── Section anchor nav ─────────────────────────────────────────── */

const SECTION_ANCHORS = [
  { id: "company-header", label: "Company" },
  { id: "key-metrics", label: "Key Metrics" },
  { id: "ai-investment-view", label: "AI View" },
  { id: "valuation", label: "Valuation" },
  { id: "charts", label: "Charts" },
  { id: "fundamentals", label: "Fundamentals" },
  { id: "quality", label: "Quality" },
  { id: "peers", label: "Peers" },
  { id: "institutional-mf", label: "Inst./MF" },
  { id: "ai-research", label: "AI Research" },
  { id: "comparison-report", label: "Comparison" },
  { id: "export-share", label: "Export" },
  { id: "risks-opportunities", label: "Risks & Opps" },
  { id: "data-freshness", label: "Freshness" },
  { id: "analyst-research-notes", label: "Research Notes" },
] as const;

/**
 * SectionNav — sticky horizontal table of contents.
 * Styled as a restrained report navigation bar, not a tab strip.
 */
function SectionNav({ symbol }: { symbol: string }) {
  return (
    <nav
      aria-label="Analysis sections"
      className="sticky top-14 z-20 -mx-4 mb-10 overflow-x-auto border-b border-[var(--border)] bg-[var(--surface)]/95 backdrop-blur motion-reduce:backdrop-blur-none sm:-mx-6 lg:-mx-8"
    >
      <ol className="flex min-w-max items-center gap-0 px-4 py-2 text-xs sm:px-6 lg:px-8">
        {/* Report label */}
        <li className="mr-4 shrink-0 hidden sm:block">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
            Contents
          </span>
        </li>
        {SECTION_ANCHORS.map((s, i) => (
          <li key={s.id} className="flex items-center">
            <a
              href={`#${s.id}`}
              className="inline-flex min-h-[36px] items-center gap-1.5 rounded px-2 py-1.5 text-[var(--muted)] transition-colors hover:text-[var(--fg)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)] sm:px-2.5"
            >
              <span className="font-mono text-[10px] text-[var(--muted)] opacity-50 hidden sm:inline">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span>{s.label}</span>
            </a>
          </li>
        ))}
        <li className="ml-auto pl-4 flex items-center shrink-0 sm:pl-6">
          <span className="font-[family-name:var(--font-display)] text-sm font-semibold text-[var(--fg)]">{symbol}</span>
        </li>
      </ol>
    </nav>
  );
}

/* ─── Main layout ────────────────────────────────────────────────── */

export function AnalysisPageLayout({
  view,
  symbol,
  loading,
  onRefresh,
  onShare,
}: {
  view: AnalysisWorkspaceView;
  symbol: string;
  loading: boolean;
  onRefresh: () => void;
  onShare: () => void;
}) {
  const { session: _session } = useAuth();

  if (loading) {
    return (
      <div className="space-y-6" aria-busy="true" aria-label="Loading analysis">
        <Skeleton className="h-40 w-full" />
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  return (
    <CopilotProvider view={view}>
      <div className="space-y-12 pb-20">
        <SectionNav symbol={symbol} />

        {/* ── 1. Company Header ─────────────────────────────────── */}
        <section id="company-header" aria-labelledby="company-header-heading">
          <EquityResearchHeader view={view} onRefresh={onRefresh} />
        </section>

        {/* ── 2. Key Metrics ────────────────────────────────────── */}
        <section id="key-metrics" aria-labelledby="key-metrics-heading">
          <AnalysisSectionShell id="key-metrics-inner" title="Key Metrics">
            <KeyMetricsSection view={view} />
          </AnalysisSectionShell>
        </section>

        {/* ── 3. AI Investment View ─────────────────────────────── */}
        <section id="ai-investment-view" aria-labelledby="ai-investment-view-heading">
          <AnalysisSectionShell id="ai-investment-view-inner" title="AI Investment View">
            <AIInvestmentViewSection view={view} />
          </AnalysisSectionShell>
        </section>

        {/* ── 4. Valuation ──────────────────────────────────────── */}
        <section id="valuation" aria-labelledby="valuation-heading">
          <AnalysisSectionShell id="valuation-inner" title="Valuation">
            <ValuationSection valuation={view.valuation} />
          </AnalysisSectionShell>
        </section>

        {/* ── 5. Charts (Market Data) ───────────────────────────── */}
        <section id="charts" aria-labelledby="charts-heading">
          <AnalysisSectionShell id="charts-inner" title="Price & Market Charts">
            <ChartsSection view={view} ticker={symbol} />
          </AnalysisSectionShell>
        </section>

        {/* ── 6. Fundamentals ───────────────────────────────────── */}
        <section id="fundamentals" aria-labelledby="fundamentals-heading">
          <AnalysisSectionShell id="fundamentals-inner" title="Fundamentals">
            <FundamentalsSection view={view} />
          </AnalysisSectionShell>
        </section>

        {/* ── 7. Quality ────────────────────────────────────────── */}
        <section id="quality" aria-labelledby="quality-heading">
          <AnalysisSectionShell id="quality-inner" title="Quality">
            <QualitySection view={view} />
          </AnalysisSectionShell>
        </section>

        {/* ── 8. Peers ──────────────────────────────────────────── */}
        <section id="peers" aria-labelledby="peers-heading">
          <AnalysisSectionShell id="peers-inner" title="Peer Comparison">
            <PeersSection view={view} ticker={symbol} />
          </AnalysisSectionShell>
        </section>

        {/* ── 9. Institutional / MF Activity ───────────────────── */}
        <section id="institutional-mf" aria-labelledby="institutional-mf-heading">
          <AnalysisSectionShell id="institutional-mf-inner" title="Institutional & MF Activity">
            <InstitutionalActivitySection symbol={symbol} />
          </AnalysisSectionShell>
        </section>

        {/* ── 10. AI Research ───────────────────────────────────── */}
        <section id="ai-research" aria-labelledby="ai-research-heading" className="space-y-12">
          <AnalysisSectionShell id="ai-research-inner" title="AI Research">
            <AIResearchSection view={view} />
          </AnalysisSectionShell>
          <AnalysisSectionShell id="ai-research-copilot" title="AI Research Copilot">
            <ResearchCopilotWorkspace />
          </AnalysisSectionShell>
        </section>

        {/* ── 11. Comparison Report ─────────────────────────────── */}
        <section id="comparison-report" aria-labelledby="comparison-report-heading">
          <AnalysisSectionShell id="comparison-report-inner" title="Comparison Report">
            <ComparisonReportSection view={view} ticker={symbol} />
          </AnalysisSectionShell>
        </section>

        {/* ── 12. Export / Share Research ───────────────────────── */}
        <section id="export-share" aria-labelledby="export-share-heading">
          <AnalysisSectionShell id="export-share-inner" title="Export / Share Research">
            <ExportShareSection view={view} ticker={symbol} />
          </AnalysisSectionShell>
        </section>

        {/* ── 13. Risks & Opportunities ─────────────────────────── */}
        <section id="risks-opportunities" aria-labelledby="risks-opportunities-heading">
          <AnalysisSectionShell id="risks-opportunities-inner" title="Risks & Opportunities">
            <RisksOpportunitiesSection view={view} />
          </AnalysisSectionShell>
        </section>

        {/* ── 14. Data Freshness & Reliability ──────────────────── */}
        <section id="data-freshness" aria-labelledby="data-freshness-heading">
          <AnalysisSectionShell id="data-freshness-inner" title="Data Freshness & Reliability">
            <DataFreshnessSection view={view} />
          </AnalysisSectionShell>
        </section>

        {/* ── 15. Analyst / Research Notes ──────────────────────── */}
        <section id="analyst-research-notes" aria-labelledby="analyst-research-notes-heading">
          <AnalysisSectionShell id="analyst-research-notes-inner" title="Analyst / Research Notes">
            <AnalystResearchNotesSection view={view} />
          </AnalysisSectionShell>
        </section>
      </div>
    </CopilotProvider>
  );
}
