"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";

import { AnalysisWorkspace } from "@/components/analysis/AnalysisWorkspace";
import { Alert } from "@/components/ui/Alert";
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
  // RC3-003 — no silent default company; require explicit symbol.
  const [symbol, setSymbol] = useState("");
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

  function onResearch() {
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
    <div className="mx-auto max-w-5xl">
      {restoredBanner ? (
        <div className="mb-4">
          <Alert tone="info" title="Local workspace">
            {restoredBanner}
          </Alert>
        </div>
      ) : null}

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
        symbol={symbol}
        onSymbolChange={setSymbol}
        onResearch={onResearch}
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
