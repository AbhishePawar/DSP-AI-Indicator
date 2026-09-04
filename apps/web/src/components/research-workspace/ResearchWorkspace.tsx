"use client";

/**
 * EPIC-F007 — Institutional Research Workspace.
 * Library from local history; viewer via api.analyse + mapResearchView.
 * No client research generation.
 */

import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";

import { Button, Skeleton } from "@/components/ds";
import { useResearchDisclaimerGate } from "@/components/legal/useResearchDisclaimerGate";
import { SurfaceTrustChrome } from "@/components/trust/SurfaceTrustChrome";
import { api } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { researchWorkspaceSurfaceTrust } from "@/lib/trust/surfaceTrust";
import { pushRecentAnalysis } from "@/lib/analysis/recentAnalyses";
import { COMPANY_CATALOGUE } from "@/lib/companies/catalogue";
import { loadArchivedSession } from "@/lib/copilot/sessionArchive";
import {
  RESEARCH_SECTIONS,
  isResearchSectionId,
  useResearchWorkspacePrefsStore,
} from "@/lib/research-workspace";
import { useCollapsePanelsBelowLg } from "@/lib/a11y";
import { loadAuthenticatedAnalyseRequest } from "@/lib/research/buildAnalyseRequest";
import {
  mapResearchView,
  type ResearchView,
} from "@/lib/research/mapResearchView";
import {
  loadResearchSession,
  saveResearchSession,
} from "@/lib/research/sessionStore";
import { useNotifications } from "@/providers/NotificationProvider";
import { cn } from "@/lib/utils";
import { ResearchLeftNav } from "./LeftNav";
import { ResearchRightPanel } from "./RightPanel";
import {
  AiSection,
  ArchiveSection,
  ComplianceSection,
  DiffSection,
  ExportSection,
  LibrarySection,
  ViewerSection,
} from "./Sections";
import { SectionCard, WorkspaceEmpty, WorkspaceSkeleton } from "./Primitives";

/** RC3-004 — code-split heavy company-analysis overlays. */
const BuffettIndicatorSection = lazy(() =>
  import("@/components/company-analysis/BuffettIndicatorSection").then(
    (m) => ({ default: m.BuffettIndicatorSection }),
  ),
);
const InstitutionalRatingsSection = lazy(() =>
  import("@/components/company-analysis/InstitutionalRatingsSection").then(
    (m) => ({ default: m.InstitutionalRatingsSection }),
  ),
);
const ValuationTransparencySection = lazy(() =>
  import("@/components/company-analysis/ValuationTransparencySection").then(
    (m) => ({ default: m.ValuationTransparencySection }),
  ),
);

function LazySectionFallback() {
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <WorkspaceSkeleton />
      <Skeleton className="h-24 w-full" />
      <p className="text-xs text-[var(--muted)]">Loading section…</p>
    </div>
  );
}

function Toolbar({
  ticker,
  loading,
  onLoad,
  leftOpen,
  rightOpen,
  onToggleLeft,
  onToggleRight,
  onToggleFavourite,
  onTogglePinned,
  isFavourite,
  isPinned,
}: {
  ticker: string | null;
  loading: boolean;
  onLoad: () => void;
  leftOpen: boolean;
  rightOpen: boolean;
  onToggleLeft: () => void;
  onToggleRight: () => void;
  onToggleFavourite: () => void;
  onTogglePinned: () => void;
  isFavourite: boolean;
  isPinned: boolean;
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
          Shortcuts: 1–7 sections · [ / ] panels · Ctrl+Enter load
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {ticker ? (
          <>
            <Button size="sm" variant="ghost" onClick={onToggleFavourite}>
              {isFavourite ? "Unfavourite" : "Favourite"}
            </Button>
            <Button size="sm" variant="ghost" onClick={onTogglePinned}>
              {isPinned ? "Unpin" : "Pin"}
            </Button>
          </>
        ) : null}
        <Button className="min-h-11" onClick={onLoad} disabled={loading || !ticker}>
          {loading ? "Loading…" : "Load research"}
        </Button>
        <Link href="/research/institutional">
          <Button size="sm" variant="secondary">
            Institutional
          </Button>
        </Link>
      </div>
    </div>
  );
}

export function ResearchWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session } = useAuth();
  const token = session?.accessToken;
  const { success, error: notifyError } = useNotifications();

  const activeSection = useResearchWorkspacePrefsStore((s) => s.activeSection);
  const setActiveSection = useResearchWorkspacePrefsStore(
    (s) => s.setActiveSection,
  );
  const leftOpen = useResearchWorkspacePrefsStore((s) => s.leftOpen);
  const rightOpen = useResearchWorkspacePrefsStore((s) => s.rightOpen);
  const toggleLeft = useResearchWorkspacePrefsStore((s) => s.toggleLeft);
  const toggleRight = useResearchWorkspacePrefsStore((s) => s.toggleRight);
  const setLeftOpen = useResearchWorkspacePrefsStore((s) => s.setLeftOpen);
  const setRightOpen = useResearchWorkspacePrefsStore((s) => s.setRightOpen);
  const selectedTicker = useResearchWorkspacePrefsStore((s) => s.selectedTicker);
  const setSelectedTicker = useResearchWorkspacePrefsStore(
    (s) => s.setSelectedTicker,
  );
  const toggleFavourite = useResearchWorkspacePrefsStore(
    (s) => s.toggleFavourite,
  );
  const togglePinned = useResearchWorkspacePrefsStore((s) => s.togglePinned);
  const isFavourite = useResearchWorkspacePrefsStore((s) => s.isFavourite);
  const isPinned = useResearchWorkspacePrefsStore((s) => s.isPinned);
  const { runWithDisclaimer, gate: disclaimerGate } =
    useResearchDisclaimerGate();

  useCollapsePanelsBelowLg(setLeftOpen, setRightOpen);

  const [query, setQuery] = useState(selectedTicker || "");
  const [view, setView] = useState<ResearchView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ticker = searchParams.get("ticker");
    const section = searchParams.get("section");
    if (ticker) {
      setSelectedTicker(ticker);
      setQuery(ticker.toUpperCase());
    }
    if (section && isResearchSectionId(section)) {
      setActiveSection(section);
    }
  }, [searchParams, setActiveSection, setSelectedTicker]);

  const loadMutation = useMutation({
    mutationFn: async (ticker: string) => {
      const sym = ticker.trim().toUpperCase();
      const cached =
        loadResearchSession(sym) || loadArchivedSession(sym) || null;
      if (cached) {
        return {
          fromCache: true as const,
          body: cached.request,
          response: cached.response,
          analysedAt: cached.analysedAt,
        };
      }
      const match = COMPANY_CATALOGUE.find((c) => c.ticker === sym);
      // P0-01 — authenticated statements only; never clone demo ACM financials.
      const body = await loadAuthenticatedAnalyseRequest(sym, {
        exchange: match?.exchange,
        company: match?.name,
        loadStatements: () =>
          api.financialStatements(sym, {
            token,
            limit: 1,
            exchange: match?.exchange,
          }),
        loadQuote: () =>
          api.marketQuote(sym, { token, exchange: match?.exchange }),
      });
      const response = await api.analyse(body, { token });
      return {
        fromCache: false as const,
        body,
        response,
        analysedAt: new Date().toISOString(),
      };
    },
    onSuccess: ({ body, response, analysedAt, fromCache }) => {
      setError(null);
      const mapped = mapResearchView(response, body, analysedAt);
      setView(mapped);
      saveResearchSession({
        ticker: body.ticker,
        exchange: body.exchange ?? null,
        company: body.company ?? null,
        analysedAt,
        request: body,
        response,
      });
      pushRecentAnalysis({
        ticker: body.ticker.toUpperCase(),
        company: body.company || body.ticker,
        exchange: body.exchange || "—",
        recommendation: mapped.recommendation,
        analysedAt,
      });
      success(
        fromCache
          ? `Loaded cached research for ${body.ticker}`
          : `Loaded research for ${body.ticker}`,
        "Research",
      );
      setActiveSection("viewer");
    },
    onError: (err) => {
      const message =
        err instanceof ApiClientError ? err.message : "Research load failed";
      setError(message);
      notifyError(message, "Research failed");
    },
  });

  const openTicker = useCallback(
    (ticker: string) => {
      const sym = ticker.trim().toUpperCase();
      if (!sym) return;
      setSelectedTicker(sym);
      setQuery(sym);
      router.replace(`/research?ticker=${encodeURIComponent(sym)}&section=viewer`);
      runWithDisclaimer(() => {
        loadMutation.mutate(sym);
      });
    },
    [loadMutation, router, runWithDisclaimer, setSelectedTicker],
  );

  const runLoad = useCallback(() => {
    const sym = (query.trim() || selectedTicker || "").toUpperCase();
    if (!sym) return;
    openTicker(sym);
  }, [openTicker, query, selectedTicker]);

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
      } else if (/^[0-9]$/.test(event.key)) {
        const section = RESEARCH_SECTIONS.find((s) => s.shortcut === event.key);
        if (section) {
          event.preventDefault();
          setActiveSection(section.id);
          const params = new URLSearchParams();
          if (selectedTicker) params.set("ticker", selectedTicker);
          params.set("section", section.id);
          router.replace(`/research?${params.toString()}`);
        }
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [
    router,
    runLoad,
    selectedTicker,
    setActiveSection,
    toggleLeft,
    toggleRight,
  ]);

  // Auto-load when URL provides ticker on first paint — gated by disclaimer.
  useEffect(() => {
    const ticker = searchParams.get("ticker");
    if (ticker && !view && !loadMutation.isPending) {
      runWithDisclaimer(() => {
        loadMutation.mutate(ticker.toUpperCase());
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- one-shot URL hydrate
  }, []);

  const section = isResearchSectionId(activeSection)
    ? activeSection
    : "library";

  return (
    <div className="flex min-h-[70vh] flex-col rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--bg)]">
      {disclaimerGate}
      <Toolbar
        ticker={selectedTicker}
        loading={loadMutation.isPending}
        onLoad={runLoad}
        leftOpen={leftOpen}
        rightOpen={rightOpen}
        onToggleLeft={toggleLeft}
        onToggleRight={toggleRight}
        onToggleFavourite={() => {
          if (selectedTicker) {
            toggleFavourite(selectedTicker, view?.company);
          }
        }}
        onTogglePinned={() => {
          if (selectedTicker) togglePinned(selectedTicker);
        }}
        isFavourite={selectedTicker ? isFavourite(selectedTicker) : false}
        isPinned={selectedTicker ? isPinned(selectedTicker) : false}
      />

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <aside
          className={cn(
            "border-[var(--border)] bg-[var(--surface)] lg:w-72 lg:shrink-0 lg:border-r",
            leftOpen ? "block" : "hidden",
          )}
          aria-label="Research navigation"
        >
          <ResearchLeftNav
            query={query}
            onQueryChange={setQuery}
            onOpenTicker={openTicker}
            onAnalyze={runLoad}
          />
        </aside>

        <div
          role="region"
          className="min-w-0 flex-1 overflow-y-auto scroll-smooth p-4 motion-reduce:scroll-auto"
          id="research-workspace-main"
          tabIndex={-1}
          aria-label="Main research view"
        >
          <div className="mb-4">
            <SurfaceTrustChrome
              summary={researchWorkspaceSurfaceTrust({
                ticker: selectedTicker,
                analyseOk: view ? view.ok : loadMutation.isError ? false : null,
                stagesCount: view?.stages?.length ?? 0,
                recommendation: view?.recommendation ?? null,
                confidenceDisplay:
                  view?.recommendationConfidence != null
                    ? String(view.recommendationConfidence)
                    : null,
                opposingNotes: [
                  ...(view?.weaknesses ?? []),
                  ...(view?.risks ?? []),
                  ...(error ? [error] : []),
                ].slice(0, 6),
                analysedAt: view?.analysedAt ?? null,
              })}
              title="Trust Ladder"
            />
          </div>
          {section === "library" ? (
            <LibrarySection onOpenTicker={openTicker} />
          ) : null}
          {section === "viewer" ? (
            <ViewerSection
              view={view}
              loading={loadMutation.isPending}
              error={error}
              onRetry={runLoad}
            />
          ) : null}
          {section === "ratings" ? (
            view ? (
              <Suspense fallback={<LazySectionFallback />}>
                <InstitutionalRatingsSection
                  ratings={view.ratings}
                  transparency={view.transparency}
                  explainability={view.explainability}
                />
              </Suspense>
            ) : (
              <SectionCard title="Institutional Ratings">
                <WorkspaceEmpty description="Data unavailable. Load research in the Viewer first." />
              </SectionCard>
            )
          ) : null}
          {section === "valuationTransparency" ? (
            view ? (
              <Suspense fallback={<LazySectionFallback />}>
                <ValuationTransparencySection
                  transparency={view.valuationTransparency}
                />
              </Suspense>
            ) : (
              <SectionCard title="Valuation Transparency">
                <WorkspaceEmpty description="Data unavailable. Load research in the Viewer first." />
              </SectionCard>
            )
          ) : null}
          {section === "archive" ? <ArchiveSection /> : null}
          {section === "diff" ? <DiffSection /> : null}
          {section === "ai" ? <AiSection view={view} /> : null}
          {section === "buffett" ? (
            view ? (
              <Suspense fallback={<LazySectionFallback />}>
                <BuffettIndicatorSection report={view.buffett} />
              </Suspense>
            ) : (
              <SectionCard title="Buffett Indicator">
                <WorkspaceEmpty description="Data unavailable. Load research in the Viewer first." />
              </SectionCard>
            )
          ) : null}
          {section === "compliance" ? (
            <ComplianceSection view={view} />
          ) : null}
          {section === "export" ? <ExportSection view={view} /> : null}

          <p className="mt-4 text-[10px] text-[var(--muted)]">
            Research tools — not investment advice. No client-side research
            generation.
          </p>
        </div>

        <aside
          className={cn(
            "border-[var(--border)] bg-[var(--surface)] lg:w-72 lg:shrink-0 lg:border-l",
            rightOpen ? "block" : "hidden",
            "max-lg:border-t",
          )}
          aria-label="Research context panel"
        >
          <ResearchRightPanel view={view} ticker={selectedTicker} />
        </aside>
      </div>
    </div>
  );
}
