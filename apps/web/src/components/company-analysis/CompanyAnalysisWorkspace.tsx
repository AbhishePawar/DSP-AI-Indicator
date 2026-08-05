"use client";

/**
 * P9.4 / EPIC-005 — Flagship Company Analysis Workspace.
 * Consumes frozen /api/v1/analyse (+ optional market quote). Display only.
 */

import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ComponentType,
} from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";

import { Button, ErrorState } from "@/components/ds";
import { useResearchDisclaimerGate } from "@/components/legal/useResearchDisclaimerGate";
import { api } from "@/lib/api/client";
import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";
import { ApiClientError } from "@/lib/api/types";
import {
  ANALYSIS_SECTIONS,
  isAnalysisSectionId,
  useWorkspacePrefsStore,
  type AnalysisSectionId,
} from "@/lib/company-analysis";
import { useAuth } from "@/lib/auth/AuthProvider";
import { pushRecentAnalysis } from "@/lib/analysis/recentAnalyses";
import { COMPANY_CATALOGUE } from "@/lib/companies/catalogue";
import { useDashboardPrefsStore } from "@/lib/dashboard";
import { useCollapsePanelsBelowLg } from "@/lib/a11y";
import { buildAnalyseRequestForTicker } from "@/lib/research/buildAnalyseRequest";
import {
  mapResearchView,
  type ResearchView,
} from "@/lib/research/mapResearchView";
import { saveResearchSession } from "@/lib/research/sessionStore";
import { useNotifications } from "@/providers/NotificationProvider";
import { cn } from "@/lib/utils";
import { WorkspaceLeftNav } from "./WorkspaceLeftNav";
import { WorkspaceRightPanel } from "./WorkspaceRightPanel";
import { WorkspaceToolbar } from "./WorkspaceChrome";
import {
  ExportSection,
  SummarySection,
} from "./WorkspaceSections";
import { mapReportTransparency } from "@/lib/report-transparency";
import {
  WorkspaceEmpty,
  WorkspaceSkeleton,
} from "./WorkspacePrimitives";

const ValuationSection = lazy(() =>
  import("./WorkspaceSections").then((m) => ({ default: m.ValuationSection })),
);
const QualitySection = lazy(() =>
  import("./WorkspaceSections").then((m) => ({ default: m.QualitySection })),
);
const AiSection = lazy(() =>
  import("./WorkspaceSections").then((m) => ({ default: m.AiSection })),
);
const ComplianceSection = lazy(() =>
  import("./WorkspaceSections").then((m) => ({ default: m.ComplianceSection })),
);
const ResearchSection = lazy(() =>
  import("./WorkspaceSections").then((m) => ({ default: m.ResearchSection })),
);
const TimelineSection = lazy(() =>
  import("./WorkspaceSections").then((m) => ({ default: m.TimelineSection })),
);
const ManagementSection = lazy(() =>
  import("./FlagshipSections").then((m) => ({ default: m.ManagementSection })),
);
const MoatSection = lazy(() =>
  import("./FlagshipSections").then((m) => ({ default: m.MoatSection })),
);
const RiskSection = lazy(() =>
  import("./FlagshipSections").then((m) => ({ default: m.RiskSection })),
);
const FinancialSection = lazy(() =>
  import("./FlagshipSections").then((m) => ({ default: m.FinancialSection })),
);
const ExplainabilitySection = lazy(() =>
  import("./FlagshipSections").then((m) => ({
    default: m.ExplainabilitySection,
  })),
);
const EvidenceSection = lazy(() =>
  import("./FlagshipSections").then((m) => ({ default: m.EvidenceSection })),
);
const BuffettIndicatorSection = lazy(() =>
  import("./BuffettIndicatorSection").then((m) => ({
    default: m.BuffettIndicatorSection,
  })),
);
const InstitutionalRatingsSection = lazy(() =>
  import("./InstitutionalRatingsSection").then((m) => ({
    default: m.InstitutionalRatingsSection,
  })),
);
const ValuationTransparencySection = lazy(() =>
  import("./ValuationTransparencySection").then((m) => ({
    default: m.ValuationTransparencySection,
  })),
);
const PeersSection = lazy(() =>
  import("./sections/PeersSection").then((m) => ({ default: m.PeersSection })),
);
const OwnershipSection = lazy(() =>
  import("./sections/OwnershipSection").then((m) => ({
    default: m.OwnershipSection,
  })),
);
const DocumentsSection = lazy(() =>
  import("./sections/DocumentsSection").then((m) => ({
    default: m.DocumentsSection,
  })),
);
const NewsSection = lazy(() =>
  import("./sections/NewsSection").then((m) => ({ default: m.NewsSection })),
);
const SettingsSection = lazy(() =>
  import("./sections/SettingsSection").then((m) => ({
    default: m.SettingsSection,
  })),
);
const AiCopilotSection = lazy(() =>
  import("./sections/AiCopilotSection").then((m) => ({
    default: m.AiCopilotSection,
  })),
);

function resolveCatalogue(ticker: string) {
  return COMPANY_CATALOGUE.find(
    (c) => c.ticker.toUpperCase() === ticker.trim().toUpperCase(),
  );
}

function describeAnalyseError(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 401) {
      return "Permission denied — sign in required for /api/v1/analyse. No fabricated research is shown.";
    }
    if (error.status === 403) {
      return "Permission denied — this account cannot run analyse for the requested symbol.";
    }
    if (error.status === 404) {
      return "No coverage — analyse returned not found for this symbol. Data unavailable.";
    }
    if (error.status === 408 || error.status === 504) {
      return "Network timeout — the analyse request did not complete. Retry when the API is available.";
    }
    if (error.status >= 500) {
      return `API unavailable (${error.status}) — ${error.message}. Data unavailable.`;
    }
    return error.message || "Data unavailable.";
  }
  if (error instanceof Error) {
    const msg = error.message.toLowerCase();
    if (msg.includes("timeout") || msg.includes("network")) {
      return "Network timeout or connectivity failure — Data unavailable. Retry when online.";
    }
    return error.message;
  }
  return "Data unavailable.";
}

function SectionFallback() {
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <WorkspaceSkeleton />
      <p className="text-xs text-[var(--muted)]">Loading section…</p>
    </div>
  );
}

function LazyViewSection({
  Section,
  view,
}: {
  Section: ComponentType<{ view: ResearchView }>;
  view: ResearchView;
}) {
  return (
    <Suspense fallback={<SectionFallback />}>
      <Section view={view} />
    </Suspense>
  );
}

export function CompanyAnalysisWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session } = useAuth();
  const token = session?.accessToken;
  const { success, error: notifyError } = useNotifications();

  // RC3-003 — no silent default company; require explicit symbol selection.
  const urlSymbol = (searchParams.get("symbol") || "").trim().toUpperCase();
  const [symbol, setSymbol] = useState(urlSymbol);
  const [query, setQuery] = useState(urlSymbol);
  const [view, setView] = useState<ResearchView | null>(null);
  const [analysedAt, setAnalysedAt] = useState<string | null>(null);
  const [lastAnalyseRequest, setLastAnalyseRequest] =
    useState<AnalyseRequest | null>(null);
  const [lastAnalyseResponse, setLastAnalyseResponse] =
    useState<AnalyseResponse | null>(null);

  const activeSection = useWorkspacePrefsStore((s) => s.activeSection);
  const setActiveSection = useWorkspacePrefsStore((s) => s.setActiveSection);
  const leftOpen = useWorkspacePrefsStore((s) => s.leftOpen);
  const rightOpen = useWorkspacePrefsStore((s) => s.rightOpen);
  const toggleLeft = useWorkspacePrefsStore((s) => s.toggleLeft);
  const toggleRight = useWorkspacePrefsStore((s) => s.toggleRight);
  const setLeftOpen = useWorkspacePrefsStore((s) => s.setLeftOpen);
  const setRightOpen = useWorkspacePrefsStore((s) => s.setRightOpen);
  const recordSearch = useDashboardPrefsStore((s) => s.recordSearch);
  const { runWithDisclaimer, gate: disclaimerGate } =
    useResearchDisclaimerGate();

  useCollapsePanelsBelowLg(setLeftOpen, setRightOpen);

  const catalogue = useMemo(() => resolveCatalogue(symbol), [symbol]);

  useEffect(() => {
    const next = (searchParams.get("symbol") || "").trim().toUpperCase();
    setSymbol(next);
    setQuery(next);
    if (!next) setView(null);
  }, [searchParams]);

  const selectSymbol = useCallback(
    (next: string) => {
      const normalized = next.trim().toUpperCase();
      if (!normalized) return;
      setSymbol(normalized);
      setQuery(normalized);
      recordSearch(normalized);
      router.replace(`/analysis?symbol=${encodeURIComponent(normalized)}`);
    },
    [recordSearch, router],
  );

  const analyseMutation = useMutation({
    mutationFn: async () => {
      const match = resolveCatalogue(symbol);
      const body = buildAnalyseRequestForTicker(symbol, {
        exchange: match?.exchange,
        company: match?.name,
      });
      const response = await api.analyse(body, { token });
      return { body, response };
    },
    onSuccess: ({ body, response }) => {
      const at = new Date().toISOString();
      setAnalysedAt(at);
      setLastAnalyseRequest(body);
      setLastAnalyseResponse(response);
      const mapped = mapResearchView(response, body, at);
      setView(mapped);
      saveResearchSession({
        ticker: body.ticker,
        exchange: body.exchange ?? null,
        company: body.company ?? null,
        analysedAt: at,
        request: body,
        response,
      });
      pushRecentAnalysis({
        ticker: body.ticker.toUpperCase(),
        company: body.company || body.ticker,
        exchange: body.exchange || "—",
        recommendation: mapped.recommendation,
        analysedAt: at,
      });
      success(`Analysis loaded for ${body.ticker.toUpperCase()}`, "Analyse");
    },
    onError: (err) => {
      const message =
        err instanceof ApiClientError ? err.message : "Analyse failed";
      notifyError(message, "Analyse failed");
    },
  });

  const runAnalyse = useCallback(() => {
    const normalized = (query.trim() || symbol).toUpperCase();
    if (!normalized) return;
    if (normalized !== symbol) {
      selectSymbol(normalized);
      return;
    }
    runWithDisclaimer(() => {
      analyseMutation.mutate();
    });
  }, [analyseMutation, query, runWithDisclaimer, selectSymbol, symbol]);

  // Auto-run only when the user (or deep link) provides an explicit symbol.
  useEffect(() => {
    if (!symbol) return;
    runWithDisclaimer(() => {
      analyseMutation.mutate();
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional symbol-driven refresh
  }, [symbol, token]);

  const marketQuery = useQuery({
    queryKey: ["company-analysis", "market", symbol],
    queryFn: () => api.marketQuote(symbol, { token }),
    enabled: Boolean(token && symbol),
    retry: false,
    staleTime: 60_000,
  });

  // EPIC-D002 — header enrichment only (Market Cap/52wk/ROE); independent of /analyse.
  const financialStatementsQuery = useQuery({
    queryKey: ["company-analysis", "financial-statements", symbol],
    queryFn: () => api.financialStatements(symbol, { token, limit: 1 }),
    enabled: Boolean(token && symbol),
    retry: false,
    staleTime: 60_000,
  });

  const marketStatus = !token
    ? "Sign in for live market status"
    : marketQuery.isLoading
      ? "Checking…"
      : marketQuery.isError
        ? "Data unavailable."
        : marketQuery.data
          ? "Quote loaded"
          : "Data unavailable.";

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typing =
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable);
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        runAnalyse();
        return;
      }
      if (typing) return;
      if (event.key === "[") {
        event.preventDefault();
        toggleLeft();
      } else if (event.key === "]") {
        event.preventDefault();
        toggleRight();
      } else if (/^[0-9a-z]$/i.test(event.key)) {
        const section = ANALYSIS_SECTIONS.find(
          (s) => s.shortcut.toLowerCase() === event.key.toLowerCase(),
        );
        if (section) {
          event.preventDefault();
          setActiveSection(section.id);
        }
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [runAnalyse, setActiveSection, toggleLeft, toggleRight]);

  const section: AnalysisSectionId = isAnalysisSectionId(activeSection)
    ? activeSection
    : "summary";

  return (
    <div className="flex min-h-[70vh] flex-col rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--bg)]">
      {disclaimerGate}
      <WorkspaceToolbar
        onAnalyze={runAnalyse}
        analyzing={analyseMutation.isPending}
        onToggleLeft={toggleLeft}
        onToggleRight={toggleRight}
        leftOpen={leftOpen}
        rightOpen={rightOpen}
      />

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <aside
          className={cn(
            "border-[var(--border)] bg-[var(--surface)] lg:w-72 lg:shrink-0 lg:border-r",
            leftOpen ? "block" : "hidden",
          )}
          aria-label="Company navigation"
        >
          <WorkspaceLeftNav
            symbol={symbol}
            query={query}
            onQueryChange={setQuery}
            onSelectSymbol={selectSymbol}
            onAnalyze={runAnalyse}
            analyzing={analyseMutation.isPending}
          />
        </aside>

        <div
          role="region"
          className="min-w-0 flex-1 overflow-y-auto scroll-smooth p-4 motion-reduce:scroll-auto"
          id="company-analysis-main"
          tabIndex={-1}
          aria-label="Main analysis area"
        >
          {analyseMutation.isPending && !view ? <WorkspaceSkeleton /> : null}

          {analyseMutation.isError && !view ? (
            <ErrorState
              title="Analysis failed"
              description={describeAnalyseError(analyseMutation.error)}
              action={
                <Button size="sm" variant="secondary" onClick={runAnalyse}>
                  Retry
                </Button>
              }
            />
          ) : null}

          {!analyseMutation.isPending && !analyseMutation.isError && !view ? (
            <WorkspaceEmpty
              description={
                symbol
                  ? "Run analysis to load backend research outputs for this symbol."
                  : "Select a ticker to begin company analysis. No company is pre-selected."
              }
              action={
                symbol ? (
                  <Button size="sm" onClick={runAnalyse}>
                    Analyze {symbol}
                  </Button>
                ) : undefined
              }
            />
          ) : null}

          {view ? (
            <div className="space-y-4">
              {analyseMutation.isPending ? (
                <p className="text-xs text-[var(--muted)]" aria-live="polite">
                  Refreshing analysis…
                </p>
              ) : null}
              {section === "summary" ? (
                <SummarySection
                  view={view}
                  catalogue={catalogue}
                  marketStatus={marketStatus}
                  marketQuote={marketQuery.data ?? null}
                  financialStatements={financialStatementsQuery.data ?? null}
                />
              ) : null}
              {section === "valuation" ? (
                <LazyViewSection Section={ValuationSection} view={view} />
              ) : null}
              {section === "quality" ? (
                <LazyViewSection Section={QualitySection} view={view} />
              ) : null}
              {section === "management" ? (
                <LazyViewSection Section={ManagementSection} view={view} />
              ) : null}
              {section === "moat" ? (
                <LazyViewSection Section={MoatSection} view={view} />
              ) : null}
              {section === "risk" ? (
                <LazyViewSection Section={RiskSection} view={view} />
              ) : null}
              {section === "financial" ? (
                <LazyViewSection Section={FinancialSection} view={view} />
              ) : null}
              {section === "ai" ? (
                <LazyViewSection Section={AiSection} view={view} />
              ) : null}
              {section === "explainability" ? (
                <LazyViewSection Section={ExplainabilitySection} view={view} />
              ) : null}
              {section === "evidence" ? (
                <LazyViewSection Section={EvidenceSection} view={view} />
              ) : null}
              {section === "timeline" ? (
                <LazyViewSection Section={TimelineSection} view={view} />
              ) : null}
              {section === "export" ? (
                <ExportSection
                  view={view}
                  analyseRequest={lastAnalyseRequest}
                  analyseResponse={lastAnalyseResponse}
                />
              ) : null}
              {section === "ratings" ? (
                <Suspense fallback={<SectionFallback />}>
                  <InstitutionalRatingsSection
                    ratings={view.ratings}
                    transparency={mapReportTransparency(view, { marketStatus })}
                    explainability={view.explainability}
                  />
                </Suspense>
              ) : null}
              {section === "valuationTransparency" ? (
                <Suspense fallback={<SectionFallback />}>
                  <ValuationTransparencySection
                    transparency={view.valuationTransparency}
                  />
                </Suspense>
              ) : null}
              {section === "research" ? (
                <LazyViewSection Section={ResearchSection} view={view} />
              ) : null}
              {section === "buffett" ? (
                <Suspense fallback={<SectionFallback />}>
                  <BuffettIndicatorSection report={view.buffett} />
                </Suspense>
              ) : null}
              {section === "compliance" ? (
                <LazyViewSection Section={ComplianceSection} view={view} />
              ) : null}
              {section === "ownership" ? (
                <LazyViewSection Section={OwnershipSection} view={view} />
              ) : null}
              {section === "peers" ? (
                <LazyViewSection Section={PeersSection} view={view} />
              ) : null}
              {section === "documents" ? (
                <LazyViewSection Section={DocumentsSection} view={view} />
              ) : null}
              {section === "news" ? (
                <LazyViewSection Section={NewsSection} view={view} />
              ) : null}
              {section === "settings" ? (
                <LazyViewSection Section={SettingsSection} view={view} />
              ) : null}
              {section === "copilot" ? (
                <Suspense fallback={<SectionFallback />}>
                  <AiCopilotSection
                    view={view}
                    analyseRequest={lastAnalyseRequest}
                    analyseResponse={lastAnalyseResponse}
                  />
                </Suspense>
              ) : null}
              <p className="text-[10px] text-[var(--muted)]">
                Last updated: {analysedAt ?? view.analysedAt ?? "Data unavailable."}{" "}
                · Research tools — not investment advice
              </p>
            </div>
          ) : null}
        </div>

        <aside
          className={cn(
            "border-[var(--border)] bg-[var(--surface)] lg:w-72 lg:shrink-0 lg:border-l",
            rightOpen ? "block" : "hidden",
            "max-lg:border-t",
          )}
          aria-label="Context panel"
        >
          <WorkspaceRightPanel view={view} symbol={symbol} />
        </aside>
      </div>
    </div>
  );
}
