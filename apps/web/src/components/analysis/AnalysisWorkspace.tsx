"use client";

import { memo } from "react";

import { AiChallengeSection } from "@/components/analysis/AiChallengeSection";
import {
  AnalysisSectionShell,
  AnalysisToc,
} from "@/components/analysis/AnalysisSectionShell";
import { AnalystConsensusSection } from "@/components/analysis/AnalystConsensusSection";
import { AssumptionExplorerSection } from "@/components/analysis/AssumptionCard";
import {
  BusinessQualitySection,
  FinancialStrengthSection,
} from "@/components/analysis/BusinessQualitySection";
import { CompanySnapshotCard } from "@/components/analysis/CompanySnapshotCard";
import { CompetitiveAdvantageSection } from "@/components/analysis/CompetitiveAdvantageSection";
import { ConfidenceBreakdown } from "@/components/analysis/ConfidenceBreakdown";
import { ConfidenceMatrix } from "@/components/analysis/ConfidenceMatrix";
import { DecisionDashboard } from "@/components/analysis/DecisionDashboard";
import { DecisionTraceSection } from "@/components/analysis/DecisionTraceCard";
import { DspVsStreetSection } from "@/components/analysis/DspVsStreetSection";
import { EvidenceExplorerSection } from "@/components/analysis/EvidenceExplorerSection";
import { ExecutiveSummaryCard } from "@/components/analysis/ExecutiveSummaryCard";
import { GrowthAnalysisSection } from "@/components/analysis/GrowthAnalysisSection";
import { SectionDivider } from "@/components/analysis/InsightCard";
import { InvestmentThesisCard } from "@/components/analysis/InvestmentThesisCard";
import { KnowledgeGraphWorkspace } from "@/components/analysis/KnowledgeGraphWorkspace";
import { ManagementSection } from "@/components/analysis/ManagementSection";
import { MarketIntelligenceSection } from "@/components/analysis/MarketIntelligenceSection";
import {
  MethodologyCard,
  TransparencyPanel,
} from "@/components/analysis/MethodologyCard";
import { ReasoningFlowSection } from "@/components/analysis/ReasoningFlow";
import { ReportCenterWorkspace } from "@/components/analysis/ReportCenterWorkspace";
import { SavedAnalysisWorkspace } from "@/components/analysis/SavedAnalysisWorkspace";
import { ResearchConclusionCard } from "@/components/analysis/ResearchConclusionCard";
import {
  ResearchCoverageCard,
  ResearchFreshnessCard,
} from "@/components/analysis/ResearchCoverageCard";
import { ResearchLimitationsCard } from "@/components/analysis/ResearchLimitationsCard";
import { ResearchTimeline } from "@/components/analysis/ResearchTimeline";
import { RiskAnalysisSection } from "@/components/analysis/RiskAnalysisSection";
import { ValuationSection } from "@/components/analysis/ValuationSection";
import { CopilotProvider } from "@/components/analysis/copilot/CopilotContext";
import { ResearchCopilotWorkspace } from "@/components/analysis/copilot/ResearchCopilotWorkspace";
import { Alert } from "@/components/ui/Alert";
import { Skeleton } from "@/components/ui/Skeleton";
import type { AnalysisWorkspaceView } from "@/lib/analysis/types";
import { presentFieldLabel } from "@/lib/terminology";

function AnalysisWorkspaceImpl({
  view,
  loading,
  onRefresh,
  onShare,
  onReopenSaved,
}: {
  view: AnalysisWorkspaceView;
  loading: boolean;
  onRefresh: () => void;
  onShare: () => void;
  onReopenSaved: (
    view: AnalysisWorkspaceView,
    meta: { ticker: string; name: string },
  ) => void;
}) {
  if (loading) {
    return (
      <div className="space-y-4" aria-busy="true" aria-label="Loading analysis">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-40 w-full" />
        <div className="grid gap-4 sm:grid-cols-2">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    );
  }

  return (
    <CopilotProvider view={view}>
      <AnalysisWorkspaceBody
        view={view}
        onRefresh={onRefresh}
        onShare={onShare}
        onReopenSaved={onReopenSaved}
      />
    </CopilotProvider>
  );
}

function AnalysisWorkspaceBody({
  view,
  onRefresh,
  onShare,
  onReopenSaved,
}: {
  view: AnalysisWorkspaceView;
  onRefresh: () => void;
  onShare: () => void;
  onReopenSaved: (
    view: AnalysisWorkspaceView,
    meta: { ticker: string; name: string },
  ) => void;
}) {
  return (
    <div className="relative pb-20">
      <div className="sticky top-14 z-20 mb-4 space-y-2 border-b border-[var(--border)] bg-[var(--surface)]/95 p-3 backdrop-blur motion-reduce:backdrop-blur-none lg:hidden">
        <p className="text-xs text-[var(--muted)]">
          {presentFieldLabel("recommendation")}
        </p>
        <p className="font-medium">
          {view.dashboard.researchConclusion.value ?? "Unavailable"}
        </p>
        <p className="text-xs text-[var(--muted)]">
          Coverage {view.coverage.coveragePercent}% · Matrix{" "}
          {view.confidenceMatrix.overall.replace(/_/g, " ")}
        </p>
        <div className="flex flex-wrap gap-3 text-xs">
          <a href="#saved_workspace" className="text-[var(--accent)] underline">
            Workspace
          </a>
          <a href="#report_center" className="text-[var(--accent)] underline">
            Reports
          </a>
          <a href="#knowledge_graph" className="text-[var(--accent)] underline">
            Graph
          </a>
          <a href="#decision_trace" className="text-[var(--accent)] underline">
            Trace
          </a>
          <a href="#evidence_explorer" className="text-[var(--accent)] underline">
            Evidence
          </a>
        </div>
      </div>

      {!view.apiOk && view.errors.length > 0 ? (
        <Alert tone="warning" title="Envelope reported issues">
          {view.errors.join(" · ")}
        </Alert>
      ) : null}

      <div className="flex gap-8">
        <AnalysisToc />
        <div className="min-w-0 flex-1 space-y-2">
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
            <ResearchCoverageCard coverage={view.coverage} />
            <ResearchFreshnessCard freshness={view.freshness} />
          </div>
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
            <ConfidenceMatrix matrix={view.confidenceMatrix} />
            <ResearchTimeline timeline={view.researchTimeline} />
          </div>
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
            <MethodologyCard methodology={view.methodologyPanel} />
            <TransparencyPanel panel={view.transparencyPanel} />
          </div>

          <SectionDivider label="Core story" />

          <AnalysisSectionShell id="company_snapshot" title="Company Snapshot">
            <CompanySnapshotCard
              snapshot={view.snapshot}
              onRefresh={onRefresh}
              onShare={onShare}
            />
          </AnalysisSectionShell>
          <AnalysisSectionShell id="research_conclusion" title="Research Conclusion">
            <ResearchConclusionCard conclusion={view.conclusion} />
          </AnalysisSectionShell>
          <AnalysisSectionShell id="executive_summary" title="Executive Summary">
            <ExecutiveSummaryCard summary={view.executiveSummary} />
          </AnalysisSectionShell>
          <AnalysisSectionShell id="investment_thesis" title="Investment Thesis">
            <InvestmentThesisCard thesis={view.thesis} />
          </AnalysisSectionShell>
          <AnalysisSectionShell id="business_quality" title="Business Quality">
            <BusinessQualitySection metrics={view.businessQuality} />
          </AnalysisSectionShell>
          <AnalysisSectionShell id="financial_strength" title="Financial Strength">
            <FinancialStrengthSection metrics={view.financialStrength} />
          </AnalysisSectionShell>
          <AnalysisSectionShell id="valuation" title="Valuation">
            <ValuationSection valuation={view.valuation} />
          </AnalysisSectionShell>

          <SectionDivider label="Business intelligence" />

          <AnalysisSectionShell id="growth" title="Growth Analysis" defaultOpen={false}>
            <GrowthAnalysisSection items={view.growth} />
          </AnalysisSectionShell>
          <AnalysisSectionShell id="risk" title="Risk Analysis" defaultOpen={false}>
            <RiskAnalysisSection risks={view.risks} />
          </AnalysisSectionShell>
          <AnalysisSectionShell id="management" title="Management Quality" defaultOpen={false}>
            <ManagementSection items={view.management} />
          </AnalysisSectionShell>
          <AnalysisSectionShell
            id="competitive_advantage"
            title="Competitive Advantage"
            defaultOpen={false}
          >
            <CompetitiveAdvantageSection items={view.moat} />
          </AnalysisSectionShell>

          <SectionDivider label="Market intelligence" />

          <AnalysisSectionShell
            id="market_intelligence"
            title="Market Intelligence"
            defaultOpen={false}
          >
            <MarketIntelligenceSection market={view.marketIntelligence} />
          </AnalysisSectionShell>
          <AnalysisSectionShell
            id="analyst_consensus"
            title="Analyst Consensus"
            defaultOpen={false}
          >
            <AnalystConsensusSection consensus={view.analystConsensus} />
          </AnalysisSectionShell>
          <AnalysisSectionShell id="dsp_vs_street" title="DSP vs Street" defaultOpen={false}>
            <DspVsStreetSection rows={view.streetComparison} />
          </AnalysisSectionShell>
          <AnalysisSectionShell id="ai_challenge" title="AI Challenge Mode" defaultOpen={false}>
            <AiChallengeSection challenge={view.aiChallenge} />
          </AnalysisSectionShell>

          <SectionDivider label="Explainability" />

          <AnalysisSectionShell id="decision_trace" title="Decision Trace" defaultOpen={false}>
            <DecisionTraceSection trace={view.decisionTrace} />
          </AnalysisSectionShell>
          <AnalysisSectionShell
            id="evidence_explorer"
            title="Evidence Explorer"
            defaultOpen={false}
          >
            <EvidenceExplorerSection view={view.evidenceExplorer} />
          </AnalysisSectionShell>
          <AnalysisSectionShell
            id="assumption_explorer"
            title="Assumption Explorer"
            defaultOpen={false}
          >
            <AssumptionExplorerSection view={view.assumptionExplorer} />
          </AnalysisSectionShell>
          <AnalysisSectionShell id="reasoning_flow" title="Reasoning Flow" defaultOpen={false}>
            <ReasoningFlowSection flow={view.reasoningFlow} />
          </AnalysisSectionShell>
          <AnalysisSectionShell
            id="confidence_breakdown"
            title="Confidence Breakdown"
            defaultOpen={false}
          >
            <ConfidenceBreakdown breakdown={view.confidenceBreakdown} />
          </AnalysisSectionShell>
          <AnalysisSectionShell
            id="research_limitations"
            title="Research Limitations"
            defaultOpen={false}
          >
            <ResearchLimitationsCard limitations={view.researchLimitations} />
          </AnalysisSectionShell>

          <SectionDivider label="Knowledge graph" />

          <AnalysisSectionShell
            id="knowledge_graph"
            title="Knowledge Graph"
            defaultOpen={false}
          >
            <KnowledgeGraphWorkspace graph={view.knowledgeGraph} />
          </AnalysisSectionShell>

          <SectionDivider label="Reports & export" />

          <AnalysisSectionShell
            id="report_center"
            title="Reports & Export"
            defaultOpen={false}
          >
            <ReportCenterWorkspace view={view} />
          </AnalysisSectionShell>

          <SectionDivider label="Workspace" />

          <AnalysisSectionShell
            id="saved_workspace"
            title="Workspace"
            defaultOpen={false}
          >
            <SavedAnalysisWorkspace view={view} onReopen={onReopenSaved} />
          </AnalysisSectionShell>

          <SectionDivider label="Summary" />

          <AnalysisSectionShell id="decision_dashboard" title="Decision Dashboard">
            <DecisionDashboard dashboard={view.dashboard} />
          </AnalysisSectionShell>

          {view.reportId ? (
            <p className="text-xs text-[var(--muted)]">
              Report id <code>{view.reportId}</code>
            </p>
          ) : null}
        </div>
      </div>

      <ResearchCopilotWorkspace />
    </div>
  );
}

export const AnalysisWorkspace = memo(AnalysisWorkspaceImpl);
