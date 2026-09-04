"use client";

/**
 * EPIC-012/013/013A — Institutional Company Comparison Workspace.
 * Thin client: orchestrates N frozen /api/v1/analyse calls + optional RI overlays.
 * Assists decision-making — never makes investment decisions for users.
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
import { useMutation } from "@tanstack/react-query";

import { Button, ErrorState, Input } from "@/components/ds";
import { useResearchDisclaimerGate } from "@/components/legal/useResearchDisclaimerGate";
import { api } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { COMPANY_CATALOGUE } from "@/lib/companies/catalogue";
import { fetchSelectedExchange } from "@/lib/companies/listingSelection";
import {
  COMPARISON_SECTIONS,
  DATA_UNAVAILABLE,
  MAX_COMPANIES,
  MIN_COMPANIES,
  WORKSPACE_DISCLAIMER,
  describeHistoryChanges,
  isComparisonSectionId,
  mapComparisonWorkspace,
  mapIntelligenceOverlay,
  useComparisonHistoryStore,
  useComparisonPrefsStore,
  type ComparisonCompanySlot,
  type ComparisonSectionId,
  type ComparisonWorkspaceModel,
  type CompanyIntelligenceOverlay,
} from "@/lib/company-comparison";
import { featureFlags } from "@/lib/featureFlags";
import { loadAuthenticatedAnalyseRequest } from "@/lib/research/buildAnalyseRequest";
import { mapResearchView } from "@/lib/research/mapResearchView";
import { useNotifications } from "@/providers/NotificationProvider";
import { cn } from "@/lib/utils";
import {
  ArchitectureSection,
  BuffettPreferenceSection,
  BusinessQualitySection,
  CommitteeMemoSection,
  ComparisonHistorySection,
  ContradictoryEvidenceSection,
  DecisionWorkspaceSection,
  EvidenceSection,
  EvidenceStrengthSection,
  ExecutiveScorecardSection,
  ExecutiveSummarySection,
  ExplainabilitySection,
  ExportSection,
  FinancialSection,
  HeatmapSection,
  IntelligenceSection,
  ManagementSection,
  MoatSection,
  PersonalResearchSection,
  PortfolioFitSection,
  ReviewModeControls,
  RiskSection,
  ScenarioSection,
  SectorContextSection,
  SensitivitySection,
  TradeOffSection,
  ValuationSection,
  WeightingProfilesSection,
  WhyNotSection,
  WinnerMatrixSection,
} from "./Sections";
import { WorkspaceEmpty, WorkspaceSkeleton } from "./Primitives";

const LazyWinner = lazy(async () => ({ default: WinnerMatrixSection }));
const LazyTradeOff = lazy(async () => ({ default: TradeOffSection }));
const LazyBuffett = lazy(async () => ({ default: BuffettPreferenceSection }));
const LazyHeatmap = lazy(async () => ({ default: HeatmapSection }));
const LazyScorecard = lazy(async () => ({ default: ExecutiveScorecardSection }));
const LazyMemo = lazy(async () => ({ default: CommitteeMemoSection }));
const LazyContradictory = lazy(async () => ({
  default: ContradictoryEvidenceSection,
}));
const LazyWhyNot = lazy(async () => ({ default: WhyNotSection }));

function resolveCatalogue(ticker: string) {
  return COMPANY_CATALOGUE.find(
    (c) => c.ticker.toUpperCase() === ticker.trim().toUpperCase(),
  );
}

function describeError(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 401) {
      return "Permission denied — sign in required for /api/v1/analyse. No fabricated research is shown.";
    }
    return error.message || `API error (${error.status})`;
  }
  if (error instanceof Error) return error.message;
  return "Unable to load research pack.";
}

function parseSymbolsParam(raw: string | null): string[] {
  if (!raw) return [];
  return raw
    .split(/[,+\s]+/)
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean)
    .slice(0, MAX_COMPANIES);
}

type ModelSection = ComponentType<{ model: ComparisonWorkspaceModel }>;

function renderModelSection(
  id: ComparisonSectionId,
  model: ComparisonWorkspaceModel,
  onNavigateSection?: (sectionId: string) => void,
) {
  if (id === "decisionWorkspace") {
    return (
      <DecisionWorkspaceSection
        model={model}
        onNavigateSection={onNavigateSection}
      />
    );
  }
  if (id === "history") {
    return <ComparisonHistorySection />;
  }
  if (id === "weighting") {
    return <WeightingProfilesSection model={model} />;
  }

  const map: Partial<Record<ComparisonSectionId, ModelSection>> = {
    summary: ExecutiveSummarySection,
    scorecard: LazyScorecard,
    winnerMatrix: LazyWinner,
    tradeOffs: LazyTradeOff,
    valuation: ValuationSection,
    businessQuality: BusinessQualitySection,
    management: ManagementSection,
    moat: MoatSection,
    risk: RiskSection,
    financial: FinancialSection,
    evidence: EvidenceSection,
    evidenceStrength: EvidenceStrengthSection,
    contradictory: LazyContradictory,
    whyNot: LazyWhyNot,
    explainability: ExplainabilitySection,
    intelligence: IntelligenceSection,
    buffett: LazyBuffett,
    heatmap: LazyHeatmap,
    scenarios: ScenarioSection,
    portfolioFit: PortfolioFitSection,
    sectorContext: SectorContextSection,
    sensitivity: SensitivitySection,
    committeeMemo: LazyMemo,
    export: ExportSection,
  };
  const Comp = map[id];
  if (!Comp) return null;
  return <Comp model={model} />;
}

export function CompanyComparisonWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session } = useAuth();
  const token = session?.accessToken ?? null;
  const { success, error: notifyError } = useNotifications();
  const { runWithDisclaimer, gate: disclaimerGate } =
    useResearchDisclaimerGate();

  const {
    activeSection,
    setActiveSection,
    leftOpen,
    toggleLeft,
    symbols: storedSymbols,
    setSymbols,
    pinned,
    pinSymbol,
    unpinSymbol,
    weightingProfileId,
    reviewMode,
    notes,
  } = useComparisonPrefsStore();

  const appendHistory = useComparisonHistoryStore((s) => s.appendHistory);
  const historyEntries = useComparisonHistoryStore((s) => s.entries);

  const initialFromUrl = useMemo(() => {
    const multi = parseSymbolsParam(searchParams.get("symbols"));
    if (multi.length) return multi;
    const single = searchParams.get("symbol");
    if (single) return [single.trim().toUpperCase()];
    return storedSymbols;
  }, [searchParams, storedSymbols]);

  const [draftInput, setDraftInput] = useState(initialFromUrl.join(", "));
  const [slots, setSlots] = useState<ComparisonCompanySlot[]>([]);
  const [intelligence, setIntelligence] = useState<
    CompanyIntelligenceOverlay[]
  >([]);

  useEffect(() => {
    const section = searchParams.get("section");
    if (section && isComparisonSectionId(section)) {
      setActiveSection(section);
    }
  }, [searchParams, setActiveSection]);

  const syncUrl = useCallback(
    (symbols: string[], section: ComparisonSectionId = activeSection) => {
      const params = new URLSearchParams();
      if (symbols.length) params.set("symbols", symbols.join(","));
      if (section !== "summary") params.set("section", section);
      const qs = params.toString();
      router.replace(qs ? `/analysis/compare?${qs}` : "/analysis/compare");
    },
    [router, activeSection],
  );

  const navigateSection = useCallback(
    (sectionId: string) => {
      if (!isComparisonSectionId(sectionId)) return;
      setActiveSection(sectionId);
      syncUrl(
        slots.length ? slots.map((s) => s.symbol) : parseSymbolsParam(draftInput.replace(/\s+/g, ",")),
        sectionId,
      );
    },
    [setActiveSection, syncUrl, slots, draftInput],
  );

  // Keyboard navigation for institutional review modes.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      const idx = COMPARISON_SECTIONS.findIndex((s) => s.id === activeSection);
      if (e.key === "ArrowDown" || e.key === "j") {
        e.preventDefault();
        const next = COMPARISON_SECTIONS[Math.min(idx + 1, COMPARISON_SECTIONS.length - 1)];
        if (next) navigateSection(next.id);
      } else if (e.key === "ArrowUp" || e.key === "k") {
        e.preventDefault();
        const prev = COMPARISON_SECTIONS[Math.max(idx - 1, 0)];
        if (prev) navigateSection(prev.id);
      } else if (e.key === "Escape" && reviewMode === "fullscreen") {
        useComparisonPrefsStore.getState().setReviewMode("standard");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [activeSection, navigateSection, reviewMode]);

  const compareMutation = useMutation({
    mutationFn: async (symbols: string[]) => {
      const unique = Array.from(
        new Set(symbols.map((s) => s.trim().toUpperCase()).filter(Boolean)),
      ).slice(0, MAX_COMPANIES);

      if (unique.length < MIN_COMPANIES) {
        throw new Error(`Select at least ${MIN_COMPANIES} companies to compare.`);
      }

      const nextSlots: ComparisonCompanySlot[] = unique.map((symbol) => {
        const cat = resolveCatalogue(symbol);
        return {
          symbol,
          company: cat?.name ?? symbol,
          exchange: cat?.exchange ?? "—",
          pinned: pinned.includes(symbol),
          status: "loading",
          analysedAt: null,
          correlationId: null,
          error: null,
          view: null,
          intelligence: null,
        };
      });
      setSlots(nextSlots);

      const results = await Promise.all(
        unique.map(async (symbol) => {
          const cat = resolveCatalogue(symbol);
          try {
            // P0-01 — authenticated statements only; never clone demo ACM financials.
            const selected = await fetchSelectedExchange({
              symbol,
              token,
              catalogueExchange: cat?.exchange,
            });
            const body = await loadAuthenticatedAnalyseRequest(symbol, {
              company: cat?.name,
              exchange: selected,
              loadStatements: () =>
                api.financialStatements(symbol, {
                  token,
                  limit: 1,
                  exchange: selected,
                }),
            });
            const response = await api.analyse(body, { token });
            const at = new Date().toISOString();
            const view = mapResearchView(response, body, at);
            return {
              symbol,
              company: cat?.name ?? symbol,
              exchange: cat?.exchange ?? "—",
              pinned: pinned.includes(symbol),
              status: "ready" as const,
              analysedAt: at,
              correlationId: view.correlationId,
              error: null,
              view,
              intelligence: null,
            };
          } catch (err) {
            return {
              symbol,
              company: cat?.name ?? symbol,
              exchange: cat?.exchange ?? "—",
              pinned: pinned.includes(symbol),
              status: "error" as const,
              analysedAt: null,
              correlationId: null,
              error: describeError(err),
              view: null,
              intelligence: null,
            };
          }
        }),
      );

      let overlays: CompanyIntelligenceOverlay[] = [];
      if (featureFlags.researchIntelligence) {
        overlays = await Promise.all(
          unique.map(async (symbol) => {
            try {
              const [perf, cal, timeline] = await Promise.all([
                api
                  .researchIntelligencePerformance({}, { token })
                  .catch(() => null),
                api
                  .researchIntelligenceCalibration({}, { token })
                  .catch(() => null),
                api
                  .researchIntelligenceTimeline(
                    { symbol, limit: 5 },
                    { token },
                  )
                  .catch(() => null),
              ]);
              return mapIntelligenceOverlay(
                symbol,
                (perf as { dashboard?: Record<string, unknown> } | null) ??
                  null,
                (cal as { calibration?: Record<string, unknown> } | null) ??
                  null,
                timeline,
              );
            } catch {
              return mapIntelligenceOverlay(symbol, null, null, null);
            }
          }),
        );
      }

      return { slots: results, overlays };
    },
    onSuccess: ({ slots: next, overlays }) => {
      setSlots(next);
      setIntelligence(overlays);
      setSymbols(next.map((s) => s.symbol));
      syncUrl(next.map((s) => s.symbol));

      const readyViews = next
        .filter((s) => s.status === "ready" && s.view)
        .map((s) => s.view!);
      const preview = mapComparisonWorkspace(next, {
        intelligence: overlays,
        weightingProfileId,
      });
      const versions = Array.from(
        new Set(
          readyViews
            .map(
              (v) =>
                `pipeline=${v.pipelineVersion ?? "n/a"};platform=${v.platformVersion ?? "n/a"}`,
            )
            .filter(Boolean),
        ),
      );
      const previous =
        useComparisonHistoryStore.getState().entries[0] ?? null;
      appendHistory({
        at: new Date().toISOString(),
        symbols: next.map((s) => s.symbol),
        researchVersion:
          versions.length > 0 ? versions.join(" | ") : DATA_UNAVAILABLE,
        confidence: preview.executive.confidence,
        winnerSummary: preview.executive.winnerSummary,
        changes: describeHistoryChanges(
          previous,
          next.map((s) => s.symbol),
          preview.executive.winnerSummary,
        ),
      });

      const readySymbols = next
        .filter((s) => s.status === "ready")
        .map((s) => s.symbol);
      if (readySymbols.length >= MIN_COMPANIES) {
        success("Comparison research packs loaded.");
      } else {
        notifyError(
          "Fewer than two successful research packs — comparison coverage incomplete.",
        );
      }
    },
    onError: (err) => {
      notifyError(describeError(err));
    },
  });

  const catalogueLookups = useMemo(
    () =>
      COMPANY_CATALOGUE.map((c) => ({
        ticker: c.ticker,
        sector: c.sector,
        industry: c.industry,
      })),
    [],
  );

  const model = useMemo(
    () =>
      mapComparisonWorkspace(slots, {
        intelligence,
        weightingProfileId,
        catalogue: catalogueLookups,
        personalNotes: notes.map((n) => ({ kind: n.kind, text: n.text })),
      }),
    [slots, intelligence, weightingProfileId, catalogueLookups, notes],
  );

  const readyCount = slots.filter((s) => s.status === "ready").length;
  const isLoading = compareMutation.isPending;

  const runCompare = () => {
    const symbols = parseSymbolsParam(draftInput.replace(/\s+/g, ","));
    runWithDisclaimer(() => {
      compareMutation.mutate(symbols);
    });
  };

  const removeSymbol = (symbol: string) => {
    const next = draftInput
      .split(/[,+\s]+/)
      .map((s) => s.trim().toUpperCase())
      .filter((s) => s && s !== symbol);
    setDraftInput(next.join(", "));
    setSlots((prev) => prev.filter((s) => s.symbol !== symbol));
  };

  const swapSymbols = () => {
    const list = draftInput
      .split(/[,+\s]+/)
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);
    if (list.length < 2) return;
    const [a, b, ...rest] = list;
    setDraftInput([b!, a!, ...rest].join(", "));
  };

  const reviewClass =
    reviewMode === "presentation" || reviewMode === "fullscreen"
      ? "text-base md:text-lg"
      : reviewMode === "print"
        ? "print:bg-white"
        : reviewMode === "evidence_first" || reviewMode === "committee"
          ? ""
          : "";

  const preferredSection =
    reviewMode === "evidence_first" &&
    (activeSection === "summary" || activeSection === "scorecard")
      ? "contradictory"
      : reviewMode === "committee" && activeSection === "summary"
        ? "committeeMemo"
        : activeSection;

  useEffect(() => {
    if (preferredSection !== activeSection) {
      setActiveSection(preferredSection);
    }
    // Only re-sync when review mode changes preference — avoid loops.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reviewMode]);

  return (
    <div
      className={cn(
        "overflow-hidden rounded-[var(--radius-lg,0.75rem)] border border-[var(--border)] bg-[var(--surface)]",
        reviewMode === "fullscreen" && "fixed inset-0 z-50 rounded-none",
        reviewClass,
      )}
      data-testid="company-comparison-workspace"
      data-review-mode={reviewMode}
    >
      {disclaimerGate}
      <header className="sticky top-0 z-10 space-y-3 border-b border-[var(--border)] bg-[var(--surface)]/95 p-3 backdrop-blur supports-[backdrop-filter]:bg-[var(--surface)]/80 md:p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-[var(--fg)]">
              Institutional Company Comparison
            </h2>
            <p className="mt-1 max-w-3xl text-xs text-[var(--muted)]">
              {WORKSPACE_DISCLAIMER}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="ghost" onClick={toggleLeft}>
              {leftOpen ? "Hide sections" : "Show sections"}
            </Button>
            {reviewMode === "fullscreen" ? (
              <Button
                size="sm"
                variant="secondary"
                onClick={() =>
                  useComparisonPrefsStore.getState().setReviewMode("standard")
                }
              >
                Exit fullscreen
              </Button>
            ) : null}
          </div>
        </div>
        <ReviewModeControls />
        <div className="flex flex-col gap-2 lg:flex-row lg:items-end">
          <div className="flex-1">
            <label className="mb-1 block text-xs text-[var(--muted)]" htmlFor="cmp-symbols">
              Companies (2–{MAX_COMPANIES} tickers, comma-separated)
            </label>
            <Input
              id="cmp-symbols"
              value={draftInput}
              onChange={(e) => setDraftInput(e.target.value)}
              placeholder="AAPL, MSFT, GOOGL"
              aria-label="Comparison tickers"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={runCompare} disabled={isLoading}>
              {isLoading ? "Comparing…" : "Compare"}
            </Button>
            <Button size="sm" variant="secondary" onClick={swapSymbols}>
              Swap first two
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                const featured = COMPANY_CATALOGUE.filter((c) => c.featured)
                  .slice(0, 3)
                  .map((c) => c.ticker);
                setDraftInput(featured.join(", "));
              }}
            >
              Sample set
            </Button>
          </div>
        </div>
        {slots.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {slots.map((s) => (
              <div
                key={s.symbol}
                className="inline-flex items-center gap-1 rounded-md border border-[var(--border)] px-2 py-1 text-xs"
              >
                <span className="font-medium">{s.symbol}</span>
                <span className="text-[var(--muted)]">({s.status})</span>
                {s.analysedAt ? (
                  <span className="text-[var(--muted)]">
                    {new Date(s.analysedAt).toLocaleString()}
                  </span>
                ) : null}
                <Button
                  size="sm"
                  variant="ghost"
                  aria-pressed={pinned.includes(s.symbol)}
                  onClick={() =>
                    pinned.includes(s.symbol)
                      ? unpinSymbol(s.symbol)
                      : pinSymbol(s.symbol)
                  }
                >
                  {pinned.includes(s.symbol) ? "Pinned" : "Pin"}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => removeSymbol(s.symbol)}
                >
                  Remove
                </Button>
              </div>
            ))}
          </div>
        ) : null}
        {historyEntries.length > 0 ? (
          <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
            <span>History:</span>
            {historyEntries.slice(0, 5).map((h) => (
              <button
                key={h.id}
                type="button"
                className="rounded border border-[var(--border)] px-2 py-0.5 hover:bg-[var(--surface-2)]"
                onClick={() => setDraftInput(h.symbols.join(", "))}
              >
                {h.symbols.join(" · ")}
              </button>
            ))}
            <Button
              size="sm"
              variant="ghost"
              onClick={() => navigateSection("history")}
            >
              Open timeline
            </Button>
          </div>
        ) : null}
        <p className="text-[10px] text-[var(--muted)]">
          Keyboard: ↑/↓ or j/k to move sections · Esc exits fullscreen
        </p>
      </header>

      <div className="flex min-h-[70vh] flex-col lg:flex-row">
        {leftOpen ? (
          <nav
            aria-label="Comparison sections"
            className="w-full shrink-0 border-b border-[var(--border)] p-2 lg:w-56 lg:border-b-0 lg:border-r"
          >
            <ul className="flex gap-1 overflow-x-auto lg:flex-col lg:overflow-visible">
              {COMPARISON_SECTIONS.map((section) => (
                <li key={section.id}>
                  <button
                    type="button"
                    className={cn(
                      "w-full rounded-md px-2 py-2 text-left text-sm motion-safe:transition-colors",
                      activeSection === section.id
                        ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                        : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]",
                    )}
                    onClick={() => navigateSection(section.id)}
                  >
                    {section.label}
                    {section.star ? " ★" : ""}
                  </button>
                </li>
              ))}
            </ul>
          </nav>
        ) : null}

        <main className="min-w-0 flex-1 p-3 md:p-4" aria-live="polite">
          {isLoading ? <WorkspaceSkeleton /> : null}

          {!isLoading && slots.length === 0 ? (
            <WorkspaceEmpty
              action={
                <Button size="sm" onClick={runCompare}>
                  Start comparison
                </Button>
              }
            />
          ) : null}

          {!isLoading && slots.length > 0 && readyCount < MIN_COMPANIES ? (
            <ErrorState
              title="Coverage incomplete"
              description="At least two successful /analyse research packs are required. Failed symbols show honest errors — no fabricated scores."
            />
          ) : null}

          {!isLoading && readyCount >= MIN_COMPANIES ? (
            <Suspense fallback={<WorkspaceSkeleton />}>
              {activeSection === "personal" ? (
                <PersonalResearchSection symbols={model.symbols} />
              ) : activeSection === "architecture" ? (
                <ArchitectureSection />
              ) : (
                renderModelSection(activeSection, model, navigateSection)
              )}
            </Suspense>
          ) : null}

          {slots.some((s) => s.status === "error") ? (
            <div className="mt-4 space-y-2">
              {slots
                .filter((s) => s.status === "error")
                .map((s) => (
                  <ErrorState
                    key={s.symbol}
                    title={`${s.symbol} unavailable`}
                    description={s.error ?? "Data unavailable."}
                  />
                ))}
            </div>
          ) : null}
        </main>
      </div>
    </div>
  );
}
