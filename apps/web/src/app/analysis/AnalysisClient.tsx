"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";

import { AnalysisWorkspace } from "@/components/analysis/AnalysisWorkspace";
import { PageHeader } from "@/components/layout/PageHeader";
import { ResearchModeBanner } from "@/components/research/ResearchModeBanner";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import {
  emptyWorkspace,
  mapAnalyzeResponse,
} from "@/lib/analysis/mapEnvelope";
import type { AnalysisWorkspaceView } from "@/lib/analysis/types";
import { api } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { pushRecentReport } from "@/lib/recentReports";

function defaultRange() {
  const end = new Date();
  const start = new Date();
  start.setFullYear(end.getFullYear() - 1);
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { start: iso(start), end: iso(end) };
}

export default function AnalysisClient() {
  const { session } = useAuth();
  const searchParams = useSearchParams();
  const range = defaultRange();
  const [symbol, setSymbol] = useState("AAPL");
  const [start, setStart] = useState(range.start);
  const [end, setEnd] = useState(range.end);
  const [restoredView, setRestoredView] = useState<AnalysisWorkspaceView | null>(
    null,
  );
  const [restoredBanner, setRestoredBanner] = useState<string | null>(null);

  useEffect(() => {
    const fromQuery = searchParams.get("symbol");
    if (fromQuery) setSymbol(fromQuery.toUpperCase());
  }, [searchParams]);

  const mutation = useMutation({
    mutationFn: () =>
      api.analyzeCompany(
        {
          symbol: symbol.trim().toUpperCase(),
          start,
          end,
          as_decision_pack: false,
        },
        { token: session?.accessToken },
      ),
    onSuccess: (data) => {
      setRestoredView(null);
      setRestoredBanner(null);
      const reportId = data.payload?.report_id;
      if (reportId) {
        pushRecentReport({
          reportId,
          symbol: symbol.trim().toUpperCase(),
          savedAt: new Date().toISOString(),
        });
      }
    },
  });

  const view = useMemo(() => {
    if (restoredView) return restoredView;
    if (mutation.data) {
      return mapAnalyzeResponse(mutation.data, symbol.trim().toUpperCase());
    }
    return emptyWorkspace(symbol.trim().toUpperCase() || "—");
  }, [mutation.data, symbol, restoredView]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setRestoredView(null);
    setRestoredBanner(null);
    mutation.mutate();
  }

  function onShare() {
    const url = `${window.location.origin}/analysis?symbol=${encodeURIComponent(symbol.trim().toUpperCase())}`;
    void navigator.clipboard?.writeText(url);
  }

  function onReopenSaved(
    next: AnalysisWorkspaceView,
    meta: { ticker: string; name: string },
  ) {
    setRestoredView(next);
    setSymbol(meta.ticker);
    setRestoredBanner(
      `Reopened local save “${meta.name}” — not a live API refresh.`,
    );
    window.location.hash = "#company_snapshot";
  }

  return (
    <div>
      <PageHeader
        title="Company Analysis"
        description="Understand one company in under five minutes. Thin client over /api/v1 — Research Mode language, honest Unavailable labels, no fabricated numbers."
      />
      <div className="mb-4">
        <ResearchModeBanner />
      </div>

      {restoredBanner ? (
        <div className="mb-4">
          <Alert tone="info" title="Local workspace">
            {restoredBanner}
          </Alert>
        </div>
      ) : null}

      <Card className="mb-6">
        <CardBody>
          <form
            onSubmit={onSubmit}
            className="grid gap-4 md:grid-cols-4"
            aria-label="Analyze company"
          >
            <label className="text-sm md:col-span-2">
              <span className="text-[var(--muted)]">Symbol</span>
              <Input
                className="mt-1 min-h-11"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                required
                aria-required
                autoComplete="off"
              />
            </label>
            <label className="text-sm">
              <span className="text-[var(--muted)]">Start</span>
              <Input
                type="date"
                className="mt-1 min-h-11"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                required
              />
            </label>
            <label className="text-sm">
              <span className="text-[var(--muted)]">End</span>
              <Input
                type="date"
                className="mt-1 min-h-11"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                required
              />
            </label>
            <Button
              type="submit"
              disabled={mutation.isPending}
              className="min-h-11 md:col-span-4 md:w-fit"
            >
              {mutation.isPending ? "Requesting…" : "Analyze via API"}
            </Button>
          </form>
        </CardBody>
      </Card>

      {mutation.isError ? (
        <div className="mb-4">
          <Alert tone="danger" title="Request failed">
            {mutation.error instanceof ApiClientError
              ? mutation.error.message
              : (mutation.error as Error).message}
          </Alert>
        </div>
      ) : null}

      <AnalysisWorkspace
        view={view}
        loading={mutation.isPending}
        onRefresh={() => {
          setRestoredView(null);
          setRestoredBanner(null);
          mutation.mutate();
        }}
        onShare={onShare}
        onReopenSaved={onReopenSaved}
      />
    </div>
  );
}
