"use client";

/**
 * EPIC-011B — Institutional Research Intelligence & Validation Workspace.
 * Thin client over /api/v1/research/intelligence/* — measurement only.
 */

import { lazy, Suspense, useCallback, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { Button, ErrorState } from "@/components/ds";
import { api } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import { useCollapsePanelsBelowLg } from "@/lib/a11y";
import { featureFlags } from "@/lib/featureFlags";
import {
  RI_SECTIONS,
  RI_WINDOWS,
  asRiSectionId,
  asRiWindow,
  type RiSectionId,
  type RiWindowMonths,
} from "@/lib/research-intelligence";
import { cn } from "@/lib/utils";

import { WorkspaceEmpty, WorkspaceSkeleton } from "./Primitives";

const LazyPerformance = lazy(() =>
  import("./Sections").then((m) => ({ default: m.PerformanceSection })),
);
const LazyTimeline = lazy(() =>
  import("./Sections").then((m) => ({ default: m.TimelineSection })),
);
const LazyCalibration = lazy(() =>
  import("./Sections").then((m) => ({ default: m.CalibrationSection })),
);
const LazyInsights = lazy(() =>
  import("./Sections").then((m) => ({ default: m.InsightsSection })),
);

function SectionFallback() {
  return <WorkspaceSkeleton />;
}

export function ResearchIntelligenceWorkspace() {
  const router = useRouter();
  const search = useSearchParams();
  const section = asRiSectionId(search.get("section"));
  const windowMonths = asRiWindow(search.get("window"));
  const [symbolFilter, setSymbolFilter] = useState(search.get("symbol") ?? "");
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  useCollapsePanelsBelowLg(setLeftOpen, setRightOpen);

  const setSection = useCallback(
    (id: RiSectionId) => {
      const params = new URLSearchParams(search.toString());
      params.set("section", id);
      router.replace(`/research/intelligence?${params.toString()}`);
    },
    [router, search],
  );

  const setWindow = useCallback(
    (w: RiWindowMonths) => {
      const params = new URLSearchParams(search.toString());
      params.set("window", String(w));
      router.replace(`/research/intelligence?${params.toString()}`);
    },
    [router, search],
  );

  const perfQuery = useQuery({
    queryKey: ["ri-performance", windowMonths],
    queryFn: async () => {
      const res = await api.researchIntelligencePerformance({
        window_months: windowMonths,
      });
      return res.dashboard ?? null;
    },
    enabled: featureFlags.researchIntelligence && section === "performance",
    retry: 1,
  });

  const timelineQuery = useQuery({
    queryKey: ["ri-timeline", symbolFilter],
    queryFn: async () => {
      const res = await api.researchIntelligenceTimeline({
        symbol: symbolFilter || undefined,
        limit: 100,
      });
      return res.timeline ?? [];
    },
    enabled: featureFlags.researchIntelligence && section === "timeline",
    retry: 1,
  });

  const calQuery = useQuery({
    queryKey: ["ri-calibration", windowMonths],
    queryFn: async () => {
      const res = await api.researchIntelligenceCalibration({
        window_months: windowMonths,
      });
      return res.calibration ?? null;
    },
    enabled: featureFlags.researchIntelligence && section === "calibration",
    retry: 1,
  });

  const insightsQuery = useQuery({
    queryKey: ["ri-insights", windowMonths],
    queryFn: async () => {
      const res = await api.researchIntelligenceInsights({
        window_months: windowMonths,
        top_n: 5,
      });
      return res.insights ?? null;
    },
    enabled: featureFlags.researchIntelligence && section === "insights",
    retry: 1,
  });

  const statusOf = useCallback(
    (q: {
      isLoading: boolean;
      isError: boolean;
      data: unknown;
    }): "loading" | "error" | "empty" | "ready" => {
      if (q.isLoading) return "loading";
      if (q.isError) return "error";
      if (
        q.data == null ||
        (Array.isArray(q.data) && q.data.length === 0) ||
        (typeof q.data === "object" &&
          q.data !== null &&
          "message" in q.data &&
          (q.data as { message?: string }).message === "Data unavailable.")
      ) {
        // Empty registry / unavailable metrics — still render section with honest empty
        if (Array.isArray(q.data) && q.data.length === 0) return "empty";
        if (q.data == null) return "empty";
      }
      return "ready";
    },
    [],
  );

  const errorMessage = useMemo(() => {
    const err =
      perfQuery.error ||
      timelineQuery.error ||
      calQuery.error ||
      insightsQuery.error;
    if (err instanceof ApiClientError) return err.message;
    if (err) return "API unavailable";
    return null;
  }, [
    perfQuery.error,
    timelineQuery.error,
    calQuery.error,
    insightsQuery.error,
  ]);

  if (!featureFlags.researchIntelligence) {
    return (
      <WorkspaceEmpty
        title="Research Intelligence is disabled"
        description="Enable NEXT_PUBLIC_RESEARCH_INTELLIGENCE to open this measurement workspace."
      />
    );
  }

  return (
    <div className="flex min-h-[70vh] flex-col rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--bg)]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border)] px-4 py-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-[var(--muted)]">
            Research · Measurement only
          </p>
          <h1 className="font-[family-name:var(--font-display)] text-lg text-[var(--fg)]">
            Research Intelligence
          </h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-sm text-[var(--muted)]">
            Horizon
            <select
              className="ml-2 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-[var(--fg)]"
              value={windowMonths}
              onChange={(e) => setWindow(Number(e.target.value) as RiWindowMonths)}
              aria-label="Holding horizon months"
            >
              {RI_WINDOWS.map((w) => (
                <option key={w} value={w}>
                  {w} months
                </option>
              ))}
            </select>
          </label>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setLeftOpen((v) => !v)}
            aria-expanded={leftOpen}
          >
            Nav
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setRightOpen((v) => !v)}
            aria-expanded={rightOpen}
          >
            Context
          </Button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <aside
          className={cn(
            "border-b border-[var(--border)] lg:border-b-0 lg:border-r",
            leftOpen ? "block lg:w-72" : "hidden",
          )}
          aria-label="Research intelligence sections"
        >
          <nav className="flex flex-row gap-1 overflow-x-auto p-3 lg:flex-col">
            {RI_SECTIONS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setSection(item.id)}
                className={cn(
                  "rounded-[var(--radius-sm)] px-3 py-2 text-left text-sm transition-colors motion-reduce:transition-none",
                  section === item.id
                    ? "bg-[var(--surface2)] text-[var(--fg)]"
                    : "text-[var(--muted)] hover:bg-[var(--surface)]",
                )}
                aria-current={section === item.id ? "page" : undefined}
              >
                <span className="block font-medium">{item.label}</span>
                <span className="hidden text-xs lg:block">{item.description}</span>
              </button>
            ))}
          </nav>
        </aside>

        <div
          role="region"
          aria-label="Research intelligence content"
          className="min-w-0 flex-1 overflow-y-auto p-4"
        >
          {errorMessage && section === "performance" && perfQuery.isError ? (
            <ErrorState title="Request failed" description={errorMessage} />
          ) : null}
          <Suspense fallback={<SectionFallback />}>
            {section === "performance" ? (
              <LazyPerformance
                dashboard={perfQuery.data ?? null}
                status={statusOf(perfQuery)}
                windowMonths={windowMonths}
                onRetry={() => void perfQuery.refetch()}
              />
            ) : null}
            {section === "timeline" ? (
              <LazyTimeline
                timeline={timelineQuery.data ?? []}
                status={statusOf(timelineQuery)}
                symbolFilter={symbolFilter}
                onSymbolChange={setSymbolFilter}
                onRetry={() => void timelineQuery.refetch()}
              />
            ) : null}
            {section === "calibration" ? (
              <LazyCalibration
                calibration={calQuery.data ?? null}
                status={statusOf(calQuery)}
                windowMonths={windowMonths}
                onRetry={() => void calQuery.refetch()}
              />
            ) : null}
            {section === "insights" ? (
              <LazyInsights
                insights={insightsQuery.data ?? null}
                status={statusOf(insightsQuery)}
                windowMonths={windowMonths}
                onRetry={() => void insightsQuery.refetch()}
              />
            ) : null}
          </Suspense>
        </div>

        <aside
          className={cn(
            "border-t border-[var(--border)] lg:border-l lg:border-t-0",
            rightOpen ? "block lg:w-72" : "hidden",
          )}
          aria-label="Research intelligence context"
        >
          <div className="space-y-3 p-4 text-sm">
            <h2 className="font-medium text-[var(--fg)]">Trust notes</h2>
            <p className="text-[var(--muted)]">
              This workspace measures research quality over time. It does not
              change valuation, recommendations, or analytical engines.
            </p>
            <p className="text-[var(--muted)]">
              Missing horizon market data is shown as Data unavailable. No
              outcomes are fabricated in the browser.
            </p>
            <p className="text-[var(--muted)]">
              Company Analysis remains the flagship research surface.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
