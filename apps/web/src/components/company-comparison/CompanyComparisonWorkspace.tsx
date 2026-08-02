"use client";

/**
 * EPIC-012/013 — Institutional Company Comparison Workspace.
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
import {
  COMPARISON_SECTIONS,
  MAX_COMPANIES,
  MIN_COMPANIES,
  WORKSPACE_DISCLAIMER,
  isComparisonSectionId,
  mapComparisonWorkspace,
  mapIntelligenceOverlay,
  useComparisonPrefsStore,
  type ComparisonCompanySlot,
  type ComparisonSectionId,
  type ComparisonWorkspaceModel,
  type CompanyIntelligenceOverlay,
} from "@/lib/company-comparison";
import { featureFlags } from "@/lib/featureFlags";
import { buildAnalyseRequestForTicker } from "@/lib/research/buildAnalyseRequest";
import { mapResearchView } from "@/lib/research/mapResearchView";
import { useNotifications } from "@/providers/NotificationProvider";
import { cn } from "@/lib/utils";
import {
  ArchitectureSection,
  BuffettPreferenceSection,
  BusinessQualitySection,
  EvidenceSection,
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
  RiskSection,
  ScenarioSection,
  TradeOffSection,
  ValuationSection,
  WinnerMatrixSection,
} from "./Sections";
import { WorkspaceEmpty, WorkspaceSkeleton } from "./Primitives";

const LazyWinner = lazy(async () => ({ default: WinnerMatrixSection }));
const LazyTradeOff = lazy(async () => ({ default: TradeOffSection }));
const LazyBuffett = lazy(async () => ({ default: BuffettPreferenceSection }));
const LazyHeatmap = lazy(async () => ({ default: HeatmapSection }));

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
) {
  const map: Partial<Record<ComparisonSectionId, ModelSection>> = {
    summary: ExecutiveSummarySection,
    winnerMatrix: LazyWinner,
    tradeOffs: LazyTradeOff,
    valuation: ValuationSection,
    businessQuality: BusinessQualitySection,
    management: ManagementSection,
    moat: MoatSection,
    risk: RiskSection,
    financial: FinancialSection,
    evidence: EvidenceSection,
    explainability: ExplainabilitySection,
    intelligence: IntelligenceSection,
    buffett: LazyBuffett,
    heatmap: LazyHeatmap,
    scenarios: ScenarioSection,
    portfolioFit: PortfolioFitSection,
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
  } = useComparisonPrefsStore();

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
  const [history, setHistory] = useState<
    { at: string; symbols: string[] }[]
  >([]);

  useEffect(() => {
    const section = searchParams.get("section");
    if (section && isComparisonSectionId(section)) {
      setActiveSection(section);
    }
  }, [searchParams, setActiveSection]);

  const syncUrl = useCallback(
    (symbols: string[]) => {
      const params = new URLSearchParams();
      if (symbols.length) params.set("symbols", symbols.join(","));
      if (activeSection !== "summary") params.set("section", activeSection);
      const qs = params.toString();
      router.replace(qs ? `/analysis/compare?${qs}` : "/analysis/compare");
    },
    [router, activeSection],
  );

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
          const body = buildAnalyseRequestForTicker(symbol, {
            company: cat?.name,
            exchange: cat?.exchange,
          });
          try {
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

      // Optional Research Intelligence overlays (measurement only).
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
      const readySymbols = next
        .filter((s) => s.status === "ready")
        .map((s) => s.symbol);
      setSymbols(next.map((s) => s.symbol));
      syncUrl(next.map((s) => s.symbol));
      setHistory((h) =>
        [
          { at: new Date().toISOString(), symbols: next.map((s) => s.symbol) },
          ...h,
        ].slice(0, 12),
      );
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

  const model = useMemo(
    () => mapComparisonWorkspace(slots, intelligence),
    [slots, intelligence],
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

  return (
    <div
      className="overflow-hidden rounded-[var(--radius-lg,0.75rem)] border border-[var(--border)] bg-[var(--surface)]"
      data-testid="company-comparison-workspace"
    >
      {disclaimerGate}
      {/* Comparison Header */}
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
          <Button size="sm" variant="ghost" onClick={toggleLeft}>
            {leftOpen ? "Hide sections" : "Show sections"}
          </Button>
        </div>
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
        {history.length > 0 ? (
          <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
            <span>History:</span>
            {history.slice(0, 5).map((h) => (
              <button
                key={h.at}
                type="button"
                className="rounded border border-[var(--border)] px-2 py-0.5 hover:bg-[var(--surface-2)]"
                onClick={() => setDraftInput(h.symbols.join(", "))}
              >
                {h.symbols.join(" · ")}
              </button>
            ))}
          </div>
        ) : null}
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
                    onClick={() => {
                      setActiveSection(section.id);
                      const params = new URLSearchParams(searchParams.toString());
                      if (section.id === "summary") params.delete("section");
                      else params.set("section", section.id);
                      const qs = params.toString();
                      router.replace(
                        qs ? `/analysis/compare?${qs}` : "/analysis/compare",
                      );
                    }}
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
                renderModelSection(activeSection, model)
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
