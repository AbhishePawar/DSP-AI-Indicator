"use client";

/**
 * P9.5 / EPIC-006 — Institutional Portfolio Intelligence Workspace.
 * Session holdings + optional POST /api/v1/portfolio/intelligence.
 * No client-side portfolio scoring, returns, or fabricated research links.
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
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { Button, ErrorState } from "@/components/ds";
import { PortfolioActions } from "@/components/portfolio/PortfolioActions";
import { PortfolioSync } from "@/components/persistence/PortfolioSync";
import { api } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  PORTFOLIO_SECTIONS,
  asPortfolioSectionId,
  buildPortfolioIntelligenceRequest,
  isPortfolioSectionId,
  mapPortfolioIntelligenceResult,
  researchCoverageFacts,
  usePortfolioIntelPrefsStore,
  type PortfolioIntelligenceView,
  type PortfolioSectionId,
} from "@/lib/portfolio-intelligence";
import { usePortfolio } from "@/lib/portfolio/PortfolioProvider";
import { useCollapsePanelsBelowLg } from "@/lib/a11y";
import { COMPANY_CATALOGUE } from "@/lib/companies/catalogue";
import { cn } from "@/lib/utils";
import { PortfolioLeftNav } from "./LeftNav";
import { PortfolioRightPanel } from "./RightPanel";
import {
  ComplianceSection,
  ExportSection,
  HoldingsSection,
  ResearchSection,
} from "./Sections";
import {
  AllocationSection,
  ExecutivePortfolioSummary,
  ExplainabilitySection,
  OpportunitiesSection,
  PerformanceSection,
  PortfolioHeaderCard,
  QualitySection,
  RebalancingSection,
  ResearchActivitySection,
  RiskSection,
  ValuationSection,
  WatchlistSection,
} from "./FlagshipSections";
import { WorkspaceEmpty, WorkspaceSkeleton } from "./Primitives";

const LazyHoldings = lazy(async () => ({ default: HoldingsSection }));
const LazyAllocation = lazy(async () => ({ default: AllocationSection }));
const LazyPerformance = lazy(async () => ({ default: PerformanceSection }));
const LazyQuality = lazy(async () => ({ default: QualitySection }));
const LazyValuation = lazy(async () => ({ default: ValuationSection }));
const LazyRisk = lazy(async () => ({ default: RiskSection }));
const LazyWatchlist = lazy(async () => ({ default: WatchlistSection }));
const LazyOpportunities = lazy(async () => ({ default: OpportunitiesSection }));
const LazyRebalancing = lazy(async () => ({ default: RebalancingSection }));
const LazyExplainability = lazy(async () => ({ default: ExplainabilitySection }));
const LazyResearchActivity = lazy(async () => ({
  default: ResearchActivitySection,
}));
const LazyCompliance = lazy(async () => ({ default: ComplianceSection }));

function SectionFallback() {
  return (
    <div role="status" aria-live="polite">
      <WorkspaceSkeleton />
      <p className="mt-2 text-xs text-[var(--muted)]">Loading section…</p>
    </div>
  );
}

function Toolbar({
  onRefresh,
  leftOpen,
  rightOpen,
  onToggleLeft,
  onToggleRight,
  refreshing,
}: {
  onRefresh: () => void;
  leftOpen: boolean;
  rightOpen: boolean;
  onToggleLeft: () => void;
  onToggleRight: () => void;
  refreshing: boolean;
}) {
  return (
    <div className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] bg-[var(--surface)]/95 px-3 py-2 backdrop-blur motion-reduce:backdrop-blur-none">
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
          Shortcuts: 1–9 / R E H C 0 · [ / ] panels
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="secondary"
          onClick={onRefresh}
          disabled={refreshing}
        >
          {refreshing ? "Refreshing…" : "Refresh intelligence"}
        </Button>
        <Link href="/analysis">
          <Button size="sm">Analyze company</Button>
        </Link>
      </div>
    </div>
  );
}

export function PortfolioIntelligenceWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session } = useAuth();
  const token = session?.accessToken;
  const owner =
    session?.displayName ||
    session?.username ||
    session?.email ||
    "Sign in for owner identity";

  const { holdings, view, isEmpty, addHolding, recordResearchOpened } =
    usePortfolio();

  const activeSection = usePortfolioIntelPrefsStore((s) => s.activeSection);
  const setActiveSection = usePortfolioIntelPrefsStore((s) => s.setActiveSection);
  const leftOpen = usePortfolioIntelPrefsStore((s) => s.leftOpen);
  const rightOpen = usePortfolioIntelPrefsStore((s) => s.rightOpen);
  const toggleLeft = usePortfolioIntelPrefsStore((s) => s.toggleLeft);
  const toggleRight = usePortfolioIntelPrefsStore((s) => s.toggleRight);
  const setLeftOpen = usePortfolioIntelPrefsStore((s) => s.setLeftOpen);
  const setRightOpen = usePortfolioIntelPrefsStore((s) => s.setRightOpen);
  const watchlist = usePortfolioIntelPrefsStore((s) => s.watchlist);
  const touchPortfolio = usePortfolioIntelPrefsStore((s) => s.touchPortfolio);
  const activePortfolioId = usePortfolioIntelPrefsStore(
    (s) => s.activePortfolioId,
  );
  const portfolios = usePortfolioIntelPrefsStore((s) => s.portfolios);
  const portfolioName =
    portfolios.find((p) => p.id === activePortfolioId)?.name ??
    "Primary session portfolio";

  useCollapsePanelsBelowLg(setLeftOpen, setRightOpen);

  useEffect(() => {
    touchPortfolio(activePortfolioId);
  }, [activePortfolioId, touchPortfolio]);

  useEffect(() => {
    const section = searchParams.get("section");
    if (section && isPortfolioSectionId(section)) {
      setActiveSection(section);
    }
  }, [searchParams, setActiveSection]);

  const lastUpdated = useMemo(() => {
    const latest = view.activities[0]?.timestamp;
    return latest ?? null;
  }, [view.activities]);

  const coverage = researchCoverageFacts(holdings);

  const intelQuery = useQuery({
    queryKey: [
      "portfolio-intelligence",
      activePortfolioId,
      holdings.map((h) => h.ticker).join(","),
      watchlist.map((w) => w.symbol).join(","),
      token ?? "anon",
    ],
    queryFn: async () => {
      const body = buildPortfolioIntelligenceRequest({
        portfolioId: activePortfolioId,
        holdings,
        watchlist: watchlist.map((w) => w.symbol),
      });
      const response = await api.portfolioIntelligence(body, { token });
      return mapPortfolioIntelligenceResult(response);
    },
    enabled: Boolean(token) && holdings.length > 0,
    retry: false,
    staleTime: 60_000,
  });

  const intel: PortfolioIntelligenceView | null = intelQuery.data ?? null;
  const intelStatus = !token
    ? "Sign in to load /portfolio/intelligence"
    : holdings.length === 0
      ? "Add holdings to request intelligence"
      : intelQuery.isLoading
        ? "Loading intelligence…"
        : intelQuery.isError
          ? intelQuery.error instanceof ApiClientError
            ? `API error ${intelQuery.error.status}`
            : "Intelligence unavailable"
          : intel
            ? `API linked research ${intel.linkedResearchCount} · schema ${intel.schemaVersion}`
            : "Data unavailable.";

  const addFromSymbol = useCallback(
    (symbol: string) => {
      const sym = symbol.trim().toUpperCase();
      if (!sym) return;
      const match = COMPANY_CATALOGUE.find((c) => c.ticker === sym);
      addHolding({
        ticker: sym,
        company: match?.name ?? sym,
        sector: match?.sector ?? "Unknown",
        researchAvailable: true,
        recommendation: "Data unavailable.",
      });
      recordResearchOpened(sym);
      router.push(`/analysis?symbol=${encodeURIComponent(sym)}`);
    },
    [addHolding, recordResearchOpened, router],
  );

  const goSection = useCallback(
    (id: PortfolioSectionId) => {
      setActiveSection(id);
      router.replace(`/portfolio?section=${id}`);
    },
    [router, setActiveSection],
  );

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typing =
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable);
      if (typing) return;
      if (event.key === "[") {
        event.preventDefault();
        toggleLeft();
      } else if (event.key === "]") {
        event.preventDefault();
        toggleRight();
      } else if (/^[0-9a-z]$/i.test(event.key)) {
        const section = PORTFOLIO_SECTIONS.find(
          (s) => s.shortcut.toLowerCase() === event.key.toLowerCase(),
        );
        if (section) {
          event.preventDefault();
          goSection(section.id);
        }
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [goSection, toggleLeft, toggleRight]);

  const section = asPortfolioSectionId(
    isPortfolioSectionId(activeSection) ? activeSection : "summary",
  );

  const sharePortfolio = useCallback(async () => {
    const url = `${window.location.origin}/portfolio?section=${section}`;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      /* ignore */
    }
  }, [section]);

  function wrapLazy(
    Comp: ComponentType<Record<string, unknown>>,
    props: Record<string, unknown>,
  ) {
    return (
      <Suspense fallback={<SectionFallback />}>
        <Comp {...props} />
      </Suspense>
    );
  }

  return (
    <div className="flex min-h-[70vh] flex-col rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--bg)]">
      <Toolbar
        onRefresh={() => {
          void intelQuery.refetch();
        }}
        refreshing={intelQuery.isFetching}
        leftOpen={leftOpen}
        rightOpen={rightOpen}
        onToggleLeft={toggleLeft}
        onToggleRight={toggleRight}
      />

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <aside
          className={cn(
            "border-[var(--border)] bg-[var(--surface)] lg:w-72 lg:shrink-0 lg:border-r",
            leftOpen ? "block" : "hidden",
          )}
          aria-label="Portfolio navigation"
        >
          <PortfolioLeftNav
            holdingsCount={holdings.length}
            onAddHoldingSymbol={addFromSymbol}
          />
        </aside>

        <div
          role="region"
          className="min-w-0 flex-1 overflow-y-auto scroll-smooth p-4 motion-reduce:scroll-auto"
          id="portfolio-intelligence-main"
          tabIndex={-1}
          aria-label="Main portfolio view"
        >
          <div className="mb-4 space-y-3">
            <PortfolioSync />
            {isEmpty ? <PortfolioActions /> : null}
          </div>

          {intelQuery.isError && token && holdings.length > 0 ? (
            <div className="mb-4">
              <ErrorState
                title="Portfolio intelligence unavailable"
                description={
                  intelQuery.error instanceof ApiClientError
                    ? intelQuery.error.message
                    : "Data unavailable. Session holdings remain visible."
                }
                action={
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => void intelQuery.refetch()}
                  >
                    Retry
                  </Button>
                }
              />
            </div>
          ) : null}

          {section === "summary" ? (
            <div className="space-y-4">
              <PortfolioHeaderCard
                portfolioName={portfolioName}
                owner={owner}
                lastUpdated={lastUpdated}
                holdingsCount={holdings.length}
                researchConfidence={
                  coverage.total
                    ? `${coverage.covered}/${coverage.total} research-available (session)`
                    : intelStatus
                }
                onExport={() => goSection("export")}
                onShare={() => void sharePortfolio()}
              />
              <ExecutivePortfolioSummary
                holdings={holdings}
                intel={intel}
                intelStatus={intelStatus}
              />
            </div>
          ) : null}

          {section === "allocation"
            ? wrapLazy(LazyAllocation as ComponentType<Record<string, unknown>>, {
                holdings,
              })
            : null}
          {section === "performance"
            ? wrapLazy(LazyPerformance as ComponentType<Record<string, unknown>>, {})
            : null}
          {section === "quality"
            ? wrapLazy(LazyQuality as ComponentType<Record<string, unknown>>, {
                holdings,
                intel,
              })
            : null}
          {section === "valuation"
            ? wrapLazy(LazyValuation as ComponentType<Record<string, unknown>>, {
                intel,
              })
            : null}
          {section === "risk"
            ? wrapLazy(LazyRisk as ComponentType<Record<string, unknown>>, {
                intel,
              })
            : null}
          {section === "research"
            ? wrapLazy(
                LazyResearchActivity as ComponentType<Record<string, unknown>>,
                {
                  holdings,
                  activities: view.activities,
                  ResearchBody: ResearchSection,
                },
              )
            : null}
          {section === "watchlist"
            ? wrapLazy(LazyWatchlist as ComponentType<Record<string, unknown>>, {})
            : null}
          {section === "opportunities"
            ? wrapLazy(
                LazyOpportunities as ComponentType<Record<string, unknown>>,
                { holdings, intel },
              )
            : null}
          {section === "rebalancing"
            ? wrapLazy(
                LazyRebalancing as ComponentType<Record<string, unknown>>,
                { holdings, intel },
              )
            : null}
          {section === "explainability"
            ? wrapLazy(
                LazyExplainability as ComponentType<Record<string, unknown>>,
                { holdings, intel },
              )
            : null}
          {section === "export" ? (
            <ExportSection
              holdings={holdings}
              activities={view.activities}
            />
          ) : null}
          {section === "holdings"
            ? wrapLazy(LazyHoldings as ComponentType<Record<string, unknown>>, {
                holdings,
              })
            : null}
          {section === "compliance"
            ? wrapLazy(LazyCompliance as ComponentType<Record<string, unknown>>, {})
            : null}

          {!isEmpty && section === "summary" && holdings.length === 0 ? (
            <WorkspaceEmpty description="Data unavailable." />
          ) : null}

          <p className="mt-4 text-[10px] text-[var(--muted)]">
            Research tools — not investment advice. Session holdings and
            /portfolio/intelligence pass-through only; missing feeds stay Data
            unavailable.
          </p>
        </div>

        <aside
          className={cn(
            "border-[var(--border)] bg-[var(--surface)] lg:w-72 lg:shrink-0 lg:border-l",
            rightOpen ? "block" : "hidden",
            "max-lg:border-t",
          )}
          aria-label="Portfolio context panel"
        >
          <PortfolioRightPanel
            holdings={holdings}
            activities={view.activities}
          />
        </aside>
      </div>
    </div>
  );
}
