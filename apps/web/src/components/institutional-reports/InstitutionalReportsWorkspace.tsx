"use client";

/**
 * P9.6 / EPIC-007 — Institutional Research Reports & Explainability Workspace.
 * Official publishing layer over frozen /api/v1/analyse. Display only.
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
import { ApiClientError } from "@/lib/api/types";
import { pushRecentAnalysis } from "@/lib/analysis/recentAnalyses";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useCollapsePanelsBelowLg } from "@/lib/a11y";
import { COMPANY_CATALOGUE } from "@/lib/companies/catalogue";
import { useDashboardPrefsStore } from "@/lib/dashboard";
import {
  REPORT_SECTIONS,
  asReportMode,
  asReportSectionId,
  isReportSectionId,
  useInstitutionalReportsPrefsStore,
  type ReportSectionId,
} from "@/lib/institutional-reports";
import { loadAuthenticatedAnalyseRequest } from "@/lib/research/buildAnalyseRequest";
import {
  mapResearchView,
  type ResearchView,
} from "@/lib/research/mapResearchView";
import { saveResearchSession } from "@/lib/research/sessionStore";
import { useNotifications } from "@/providers/NotificationProvider";
import { cn } from "@/lib/utils";
import { ReportsLeftNav } from "./LeftNav";
import { ReportsRightPanel } from "./RightPanel";
import {
  AuditModule,
  CoverSection,
  DownloadsModule,
  ExecutiveSummarySection,
} from "./Sections";
import { WorkspaceEmpty, WorkspaceSkeleton } from "./Primitives";

const ValuationModule = lazy(() =>
  import("./ReportModules").then((m) => ({ default: m.ValuationModule })),
);
const BusinessQualityModule = lazy(() =>
  import("./ReportModules").then((m) => ({
    default: m.BusinessQualityModule,
  })),
);
const ManagementModule = lazy(() =>
  import("./ReportModules").then((m) => ({ default: m.ManagementModule })),
);
const MoatModule = lazy(() =>
  import("./ReportModules").then((m) => ({ default: m.MoatModule })),
);
const RiskModule = lazy(() =>
  import("./ReportModules").then((m) => ({ default: m.RiskModule })),
);
const AiCommitteeModule = lazy(() =>
  import("./ReportModules").then((m) => ({ default: m.AiCommitteeModule })),
);
const ExplainabilityModule = lazy(() =>
  import("./Sections").then((m) => ({ default: m.ExplainabilityModule })),
);
const EvidenceModule = lazy(() =>
  import("./Sections").then((m) => ({ default: m.EvidenceModule })),
);
const TimelineModule = lazy(() =>
  import("./Sections").then((m) => ({ default: m.TimelineModule })),
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

function Toolbar({
  onLoad,
  loading,
  leftOpen,
  rightOpen,
  onToggleLeft,
  onToggleRight,
  reportMode,
  onModeChange,
}: {
  onLoad: () => void;
  loading: boolean;
  leftOpen: boolean;
  rightOpen: boolean;
  onToggleLeft: () => void;
  onToggleRight: () => void;
  reportMode: string;
  onModeChange: (mode: "interactive" | "print" | "pdf") => void;
}) {
  return (
    <div className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] bg-[var(--surface)]/95 px-3 py-2 backdrop-blur motion-reduce:backdrop-blur-none print:hidden">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant="ghost"
          onClick={onToggleLeft}
          aria-pressed={leftOpen}
          aria-label={leftOpen ? "Hide navigation panel" : "Show navigation panel"}
        >
          {leftOpen ? "Hide nav" : "Show nav"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={onToggleRight}
          aria-pressed={rightOpen}
          aria-label={rightOpen ? "Hide context panel" : "Show context panel"}
        >
          {rightOpen ? "Hide context" : "Show context"}
        </Button>
        <span className="hidden text-xs text-[var(--muted)] md:inline">
          Shortcuts: 1–9 / E T A 0 · [ / ] panels · Ctrl+Enter load
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <label className="sr-only" htmlFor="report-mode">
          Report mode
        </label>
        <select
          id="report-mode"
          value={reportMode}
          onChange={(e) =>
            onModeChange(asReportMode(e.target.value))
          }
          className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-xs"
        >
          <option value="interactive">Interactive</option>
          <option value="print">Print layout</option>
          <option value="pdf">PDF layout</option>
        </select>
        <Button
          variant="secondary"
          className="min-h-11"
          onClick={onLoad}
          disabled={loading}
        >
          {loading ? "Loading…" : "Load report"}
        </Button>
      </div>
    </div>
  );
}

export function InstitutionalReportsWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session } = useAuth();
  const token = session?.accessToken;
  const preparedBy =
    session?.displayName ||
    session?.username ||
    session?.email ||
    "Data unavailable.";
  const { success, error: notifyError } = useNotifications();

  // RC3-003 — no silent default company.
  const urlSymbol = (
    searchParams.get("symbol") ||
    searchParams.get("ticker") ||
    ""
  )
    .trim()
    .toUpperCase();
  const urlSection = searchParams.get("section") || "";

  const [symbol, setSymbol] = useState(urlSymbol);
  const [query, setQuery] = useState(urlSymbol);
  const [view, setView] = useState<ResearchView | null>(null);
  const [analysedAt, setAnalysedAt] = useState<string | null>(null);

  const activeSection = useInstitutionalReportsPrefsStore(
    (s) => s.activeSection,
  );
  const setActiveSection = useInstitutionalReportsPrefsStore(
    (s) => s.setActiveSection,
  );
  const leftOpen = useInstitutionalReportsPrefsStore((s) => s.leftOpen);
  const rightOpen = useInstitutionalReportsPrefsStore((s) => s.rightOpen);
  const toggleLeft = useInstitutionalReportsPrefsStore((s) => s.toggleLeft);
  const toggleRight = useInstitutionalReportsPrefsStore((s) => s.toggleRight);
  const setLeftOpen = useInstitutionalReportsPrefsStore((s) => s.setLeftOpen);
  const setRightOpen = useInstitutionalReportsPrefsStore((s) => s.setRightOpen);
  const reportMode = useInstitutionalReportsPrefsStore((s) => s.reportMode);
  const setReportMode = useInstitutionalReportsPrefsStore(
    (s) => s.setReportMode,
  );
  const setSelectedTicker = useInstitutionalReportsPrefsStore(
    (s) => s.setSelectedTicker,
  );
  const recordSearch = useDashboardPrefsStore((s) => s.recordSearch);
  const { runWithDisclaimer, gate: disclaimerGate } =
    useResearchDisclaimerGate();

  useCollapsePanelsBelowLg(setLeftOpen, setRightOpen);

  const catalogue = useMemo(() => resolveCatalogue(symbol), [symbol]);
  const readingLayout = reportMode === "print" || reportMode === "pdf";

  useEffect(() => {
    const next = (
      searchParams.get("symbol") ||
      searchParams.get("ticker") ||
      ""
    )
      .trim()
      .toUpperCase();
    setSymbol(next);
    setQuery(next);
    setSelectedTicker(next);
    if (!next) setView(null);
  }, [searchParams, setSelectedTicker]);

  useEffect(() => {
    if (urlSection && isReportSectionId(urlSection)) {
      setActiveSection(urlSection);
    }
  }, [urlSection, setActiveSection]);

  const selectSymbol = useCallback(
    (next: string) => {
      const normalized = next.trim().toUpperCase();
      if (!normalized) return;
      setSymbol(normalized);
      setQuery(normalized);
      setSelectedTicker(normalized);
      recordSearch(normalized);
      const section = activeSection;
      router.replace(
        `/research/institutional?symbol=${encodeURIComponent(normalized)}&section=${section}`,
      );
    },
    [activeSection, recordSearch, router, setSelectedTicker],
  );

  const analyseMutation = useMutation({
    mutationFn: async () => {
      const match = resolveCatalogue(symbol);
      // P0-01 — authenticated statements only; never clone demo ACM financials.
      const body = await loadAuthenticatedAnalyseRequest(symbol, {
        exchange: match?.exchange,
        company: match?.name,
        loadStatements: () =>
          api.financialStatements(symbol, { token, limit: 1 }),
      });
      const response = await api.analyse(body, { token });
      return { body, response };
    },
    onSuccess: ({ body, response }) => {
      const at = new Date().toISOString();
      setAnalysedAt(at);
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
      success(
        `Institutional report loaded for ${body.ticker.toUpperCase()}`,
        "Report",
      );
    },
    onError: (err) => {
      const message =
        err instanceof ApiClientError ? err.message : "Analyse failed";
      notifyError(message, "Report load failed");
    },
  });

  const runLoad = useCallback(() => {
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
    queryKey: ["institutional-reports", "market", symbol],
    queryFn: () => api.marketQuote(symbol, { token }),
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
          target.isContentEditable ||
          target.tagName === "SELECT");
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        runLoad();
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
        const section = REPORT_SECTIONS.find(
          (s) => s.shortcut.toLowerCase() === event.key.toLowerCase(),
        );
        if (section) {
          event.preventDefault();
          setActiveSection(section.id);
          router.replace(
            `/research/institutional?symbol=${encodeURIComponent(symbol)}&section=${section.id}`,
          );
        }
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [
    router,
    runLoad,
    setActiveSection,
    symbol,
    toggleLeft,
    toggleRight,
  ]);

  const section: ReportSectionId = asReportSectionId(activeSection);

  function renderInteractiveSection() {
    if (!view) return null;
    switch (section) {
      case "cover":
        return (
          <CoverSection
            view={view}
            preparedBy={preparedBy}
            marketStatus={marketStatus}
          />
        );
      case "summary":
        return (
          <ExecutiveSummarySection view={view} marketStatus={marketStatus} />
        );
      case "valuation":
        return <LazyViewSection Section={ValuationModule} view={view} />;
      case "quality":
        return <LazyViewSection Section={BusinessQualityModule} view={view} />;
      case "management":
        return <LazyViewSection Section={ManagementModule} view={view} />;
      case "moat":
        return <LazyViewSection Section={MoatModule} view={view} />;
      case "risk":
        return <LazyViewSection Section={RiskModule} view={view} />;
      case "ai":
        return <LazyViewSection Section={AiCommitteeModule} view={view} />;
      case "explainability":
        return <LazyViewSection Section={ExplainabilityModule} view={view} />;
      case "evidence":
        return <LazyViewSection Section={EvidenceModule} view={view} />;
      case "timeline":
        return <LazyViewSection Section={TimelineModule} view={view} />;
      case "export":
        return <DownloadsModule view={view} />;
      case "audit":
        return <AuditModule view={view} marketStatus={marketStatus} />;
      default:
        return null;
    }
  }

  function renderReadingLayout() {
    if (!view) return null;
    return (
      <div className="space-y-8 institutional-report-print">
        <header className="border-b border-[var(--border)] pb-4">
          <p className="text-xs uppercase tracking-wide text-[var(--muted)]">
            DSP AI Indicator · Institutional Research Report ·{" "}
            {reportMode === "pdf" ? "PDF layout" : "Print layout"}
          </p>
          <h1 className="mt-1 text-2xl font-semibold">
            {view.company || view.ticker} ({view.ticker})
          </h1>
          <p className="text-sm text-[var(--muted)]">
            Research date {view.analysedAt ?? "Data unavailable."} · Prepared by{" "}
            {preparedBy}
          </p>
        </header>
        <CoverSection
          view={view}
          preparedBy={preparedBy}
          marketStatus={marketStatus}
        />
        <ExecutiveSummarySection view={view} marketStatus={marketStatus} />
        <Suspense fallback={<SectionFallback />}>
          <ValuationModule view={view} />
          <BusinessQualityModule view={view} />
          <ManagementModule view={view} />
          <MoatModule view={view} />
          <RiskModule view={view} />
          <AiCommitteeModule view={view} />
          <ExplainabilityModule view={view} />
          <EvidenceModule view={view} />
          <TimelineModule view={view} />
        </Suspense>
        <DownloadsModule view={view} />
        <AuditModule view={view} marketStatus={marketStatus} />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex min-h-[70vh] flex-col rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--bg)]",
        readingLayout && "institutional-report-reading",
      )}
      data-report-mode={reportMode}
    >
      {disclaimerGate}
      <Toolbar
        onLoad={runLoad}
        loading={analyseMutation.isPending}
        leftOpen={leftOpen}
        rightOpen={rightOpen}
        onToggleLeft={toggleLeft}
        onToggleRight={toggleRight}
        reportMode={reportMode}
        onModeChange={setReportMode}
      />

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <aside
          className={cn(
            "border-[var(--border)] bg-[var(--surface)] lg:w-72 lg:shrink-0 lg:border-r print:hidden",
            leftOpen && !readingLayout ? "block" : "hidden",
            readingLayout && "hidden",
          )}
          aria-label="Report navigation"
        >
          <ReportsLeftNav
            symbol={symbol}
            query={query}
            onQueryChange={setQuery}
            onSelectSymbol={selectSymbol}
            onLoad={runLoad}
            loading={analyseMutation.isPending}
          />
        </aside>

        <div
          role="region"
          className="min-w-0 flex-1 overflow-y-auto scroll-smooth p-4 motion-reduce:scroll-auto"
          id="institutional-reports-main"
          tabIndex={-1}
          aria-label="Institutional research report"
        >
          {analyseMutation.isPending && !view ? <WorkspaceSkeleton /> : null}

          {analyseMutation.isError && !view ? (
            <ErrorState
              title="Report load failed"
              description={describeAnalyseError(analyseMutation.error)}
              action={
                <Button size="sm" variant="secondary" onClick={runLoad}>
                  Retry
                </Button>
              }
            />
          ) : null}

          {!analyseMutation.isPending && !analyseMutation.isError && !view ? (
            <WorkspaceEmpty
              description={
                symbol
                  ? "Load a report to present backend research outputs for this symbol. No fabricated research is shown."
                  : "Select a ticker to load an institutional research report. No company is pre-selected."
              }
              action={
                symbol ? (
                  <Button size="sm" onClick={runLoad}>
                    Load {symbol}
                  </Button>
                ) : undefined
              }
            />
          ) : null}

          {view ? (
            <div className="space-y-4">
              {analyseMutation.isPending ? (
                <p className="text-xs text-[var(--muted)]" aria-live="polite">
                  Refreshing report…
                </p>
              ) : null}
              {catalogue ? (
                <p className="text-xs text-[var(--muted)] print:hidden">
                  Catalogue: {catalogue.name} · {catalogue.exchange}
                </p>
              ) : null}
              {readingLayout
                ? renderReadingLayout()
                : renderInteractiveSection()}
              <p className="text-[10px] text-[var(--muted)]">
                Last updated:{" "}
                {analysedAt ?? view.analysedAt ?? "Data unavailable."} ·
                Research tools — not investment advice
              </p>
            </div>
          ) : null}
        </div>

        <aside
          className={cn(
            "border-[var(--border)] bg-[var(--surface)] lg:w-72 lg:shrink-0 lg:border-l print:hidden",
            rightOpen && !readingLayout ? "block" : "hidden",
            readingLayout && "hidden",
            "max-lg:border-t",
          )}
          aria-label="Report context panel"
        >
          <ReportsRightPanel view={view} symbol={symbol} />
        </aside>
      </div>
    </div>
  );
}
