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
  useRef,
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
import { useDashboardPrefsStore } from "@/lib/dashboard";
import {
  analysisPath,
  hasExactListingIdentity,
  identityFromSearchParams,
  type SecurityListingView,
} from "@/lib/securities/identity";
import { useCollapsePanelsBelowLg } from "@/lib/a11y";
import { loadAuthenticatedAnalyseRequest } from "@/lib/research/buildAnalyseRequest";
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

function listingFromIdentity(identity: {
  ticker: string;
  exchange: string;
  isin: string;
  mic: string;
}): SecurityListingView | null {
  if (!identity.ticker) return null;
  return {
    ticker: identity.ticker,
    company_name: identity.ticker,
    exchange: identity.exchange,
    isin: identity.isin,
    mic: identity.mic,
    security_type: "equity",
    eligibility: true,
  };
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
    if (error.message === "Data unavailable.") {
      return "Security identified successfully. Investment data is currently unavailable. No valuation was calculated.";
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

  // RC3-003 — no silent default company; require explicit Security Master identity.
  const urlIdentity = identityFromSearchParams(searchParams);
  const urlSymbol = urlIdentity.ticker;
  const urlExchange = urlIdentity.exchange;
  const urlIsin = urlIdentity.isin;
  const urlMic = urlIdentity.mic;
  const [symbol, setSymbol] = useState(urlSymbol);
  const [query, setQuery] = useState(urlSymbol);
  const [identityError, setIdentityError] = useState<string | null>(null);
  const [listing, setListing] = useState<SecurityListingView | null>(() =>
    listingFromIdentity(urlIdentity),
  );
  const [view, setView] = useState<ResearchView | null>(null);
  const [analysedAt, setAnalysedAt] = useState<string | null>(null);
  const [lastAnalyseRequest, setLastAnalyseRequest] =
    useState<AnalyseRequest | null>(null);
  const [lastAnalyseResponse, setLastAnalyseResponse] =
    useState<AnalyseResponse | null>(null);
  /** Monotonic generation — drop stale analyse responses after symbol change. */
  const analyseGeneration = useRef(0);

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

  const catalogue = useMemo(() => {
    if (!listing?.ticker && !symbol) return undefined;
    return {
      name: listing?.company_name || symbol,
      ticker: listing?.ticker || symbol,
      exchange: listing?.exchange || urlExchange || "",
      sector: "",
      industry: "",
      marketCap: "",
      marketCapBucket: "large" as const,
      researchAvailable: true,
      featured: false,
      screening: {
        roe: 0,
        roce: 0,
        debtToEquity: 0,
        revenueGrowth: 0,
        profitGrowth: 0,
        dividend: false,
        style: "blend" as const,
        quality: "medium" as const,
      },
    };
  }, [listing, symbol, urlExchange]);

  useEffect(() => {
    setSymbol((prev) => {
      if (prev === urlSymbol) return prev;
      analyseGeneration.current += 1;
      setView(null);
      setLastAnalyseRequest(null);
      setLastAnalyseResponse(null);
      setAnalysedAt(null);
      setIdentityError(null);
      return urlSymbol;
    });
    setQuery(urlSymbol);
    setListing((prev) => {
      const next = listingFromIdentity({
        ticker: urlSymbol,
        exchange: urlExchange,
        isin: urlIsin,
        mic: urlMic,
      });
      if (
        prev?.ticker === next?.ticker &&
        prev?.exchange === next?.exchange &&
        prev?.isin === next?.isin &&
        prev?.mic === next?.mic
      ) {
        return prev;
      }
      return next;
    });
  }, [urlSymbol, urlExchange, urlIsin, urlMic]);

  const selectSymbol = useCallback(
    (next: SecurityListingView | string) => {
      if (typeof next === "string") {
        const normalized = next.trim().toUpperCase();
        if (!normalized) return;
        setSymbol(normalized);
        setQuery(normalized);
        recordSearch(normalized);
        router.replace(`/analysis?symbol=${encodeURIComponent(normalized)}`);
        return;
      }
      if (!next.ticker) return;
      setSymbol(next.ticker);
      setQuery(next.ticker);
      setListing(next);
      setIdentityError(null);
      recordSearch(next.ticker);
      router.replace(analysisPath(next));
    },
    [recordSearch, router],
  );

  const analyseMutation = useMutation({
    mutationFn: async () => {
      const generation = ++analyseGeneration.current;
      const requestedSymbol = symbol;
      const exchange = listing?.exchange || urlExchange || null;
      const isin = listing?.isin || urlIsin || null;
      if (!exchange) {
        throw new Error("AMBIGUOUS");
      }
      const body = await loadAuthenticatedAnalyseRequest(requestedSymbol, {
        exchange,
        isin,
        mic: listing?.mic || urlMic || null,
        company: listing?.company_name,
        loadStatements: () =>
          api.financialStatements(requestedSymbol, {
            token,
            limit: 1,
            exchange,
          }),
        loadQuote: () => api.marketQuote(requestedSymbol, { token, exchange }),
      });
      const response = await api.analyse(body, { token });
      return { body, response, generation, requestedSymbol };
    },
    onSuccess: ({ body, response, generation, requestedSymbol }) => {
      // Drop stale responses after navigation / newer analyse.
      if (generation !== analyseGeneration.current) return;
      if (body.ticker.toUpperCase() !== requestedSymbol.toUpperCase()) return;
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
      const serverIv = (
        response.payload as {
          server_valuation?: { intrinsic_value_per_share?: number | null };
        }
      )?.server_valuation?.intrinsic_value_per_share;
      const valuationOk =
        response.ok === true &&
        typeof serverIv === "number" &&
        Number.isFinite(serverIv);
      if (valuationOk) {
        success(`Analysis loaded for ${body.ticker.toUpperCase()}`, "Analyse");
      } else {
        notifyError(
          "Analysis completed with unavailable valuation or incomplete data",
          "Analyse",
        );
      }
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
    const exchange = listing?.exchange || urlExchange;
    if (!exchange) {
      if (!token) {
        setIdentityError("Sign in required for Security Master search.");
        return;
      }
      void api
        .resolveSecurity(normalized, { token })
        .then((payload) => {
          if (payload.status === "RESOLVED" && payload.identity) {
            selectSymbol(payload.identity);
            return;
          }
          setIdentityError(payload.status || "UNKNOWN");
        })
        .catch(() => setIdentityError("UNKNOWN"));
      return;
    }
    if (normalized !== symbol) {
      selectSymbol({
        ticker: normalized,
        company_name: listing?.company_name || normalized,
        exchange,
        isin: listing?.isin || urlIsin,
        mic: listing?.mic || urlMic,
        security_type: "equity",
        eligibility: true,
      });
      return;
    }
    runWithDisclaimer(() => {
      analyseMutation.mutate();
    });
  }, [
    analyseMutation,
    listing,
    query,
    runWithDisclaimer,
    selectSymbol,
    symbol,
    token,
    urlExchange,
    urlIsin,
    urlMic,
  ]);

  // Auto-run only when the URL already has an exact listing (no silent NSE/BSE pick).
  useEffect(() => {
    if (!symbol || !token) return;
    if (!hasExactListingIdentity(urlIdentity) && !urlExchange) return;
    runWithDisclaimer(() => {
      analyseMutation.mutate();
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional identity-driven refresh
  }, [symbol, urlExchange, urlIsin, urlMic, token]);

  const marketQuery = useQuery({
    queryKey: ["company-analysis", "market", symbol, urlExchange],
    queryFn: () =>
      api.marketQuote(symbol, { token, exchange: urlExchange || listing?.exchange }),
    enabled: Boolean(token && symbol && (urlExchange || listing?.exchange)),
    retry: false,
    staleTime: 60_000,
  });

  const financialStatementsQuery = useQuery({
    queryKey: ["company-analysis", "financial-statements", symbol, urlExchange],
    queryFn: () =>
      api.financialStatements(symbol, {
        token,
        limit: 1,
        exchange: urlExchange || listing?.exchange,
      }),
    enabled: Boolean(token && symbol && (urlExchange || listing?.exchange)),
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
            identityLabel={
              listing?.isin && listing.mic
                ? `${listing.ticker} · ${listing.exchange} · ${listing.isin} · ${listing.mic}`
                : urlIsin && urlMic
                  ? `${symbol} · ${urlExchange} · ${urlIsin} · ${urlMic}`
                  : identityError
            }
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
              title="Investment data is currently unavailable."
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
              title={
                hasExactListingIdentity(urlIdentity)
                  ? "Investment data is currently unavailable."
                  : "Data unavailable."
              }
              description={
                identityError
                  ? identityError
                  : hasExactListingIdentity(urlIdentity)
                    ? "Security identified successfully. No valuation was calculated."
                    : symbol
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
