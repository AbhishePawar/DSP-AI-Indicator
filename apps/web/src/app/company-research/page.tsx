"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ResearchLoading } from "@/components/loading";
import { api } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";

import type { AnalyseRequest } from "@/lib/api/compositionTypes";
import { loadAuthenticatedAnalyseRequest } from "@/lib/research/buildAnalyseRequest";
import { mapResearchView } from "@/lib/research/mapResearchView";
import {
  clearResearchSession,
  loadResearchSession,
  saveResearchSession,
} from "@/lib/research/sessionStore";
import { CompanyResearchTabs } from "@/components/research/CompanyResearchTabs";
import { CompanyHeader } from "@/components/research/CompanyHeader";

const DEFAULT_TICKER = "AAPL";

type LoadResult = {
  request: AnalyseRequest;
  response: Awaited<ReturnType<typeof api.analyse>>;
  analysedAt: string;
  cached: boolean;
};

export default function CompanyResearchUnifiedPage() {
  const { session } = useAuth();
  const token = session?.accessToken;

  const [ticker, setTicker] = useState(DEFAULT_TICKER);
  const [inputValue, setInputValue] = useState(DEFAULT_TICKER);
  const [bootstrapped, setBootstrapped] = useState(false);

  const normalized = ticker.trim().toUpperCase();

  const load = useCallback(
    async (force = false): Promise<LoadResult> => {
      if (!force) {
        const cached = loadResearchSession(normalized);
        if (cached) {
          return {
            request: cached.request,
            response: cached.response,
            analysedAt: cached.analysedAt,
            cached: true,
          };
        }
      } else {
        clearResearchSession();
      }

      const request = await loadAuthenticatedAnalyseRequest(normalized, {
        loadStatements: () =>
          api.financialStatements(normalized, { token, limit: 1 }),
        loadQuote: () => api.marketQuote(normalized, { token }),
      });
      const response = await api.analyse(request, { token });
      const analysedAt = new Date().toISOString();
      saveResearchSession({
        ticker: request.ticker,
        exchange: request.exchange ?? null,
        company: request.company ?? null,
        analysedAt,
        request,
        response,
      });
      return { request, response, analysedAt, cached: false };
    },
    [normalized, token],
  );

  const analyseMutation = useMutation({
    mutationFn: (force: boolean) => load(force),
  });

  useEffect(() => {
    setBootstrapped(true);
    analyseMutation.mutate(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [normalized]);

  const view = useMemo(() => {
    if (!analyseMutation.data) return null;
    return mapResearchView(
      analyseMutation.data.response,
      analyseMutation.data.request,
      analyseMutation.data.analysedAt,
    );
  }, [analyseMutation.data]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const val = inputValue.trim().toUpperCase();
    if (val && val !== normalized) {
      setTicker(val);
    } else if (val === normalized) {
      analyseMutation.mutate(true);
    }
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold tracking-tight text-[var(--fg)]">
            Company Research
          </h1>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Unified research view — valuation, financials, moat, quality, risk,
            recommendation, and evidence
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/research">
            <Button variant="ghost" size="sm">
              ← Research Home
            </Button>
          </Link>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => analyseMutation.mutate(true)}
            disabled={analyseMutation.isPending}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Ticker search bar */}
      <form
        onSubmit={handleSearch}
        className="flex items-center gap-2"
        aria-label="Company ticker search"
      >
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value.toUpperCase())}
          placeholder="Enter ticker (e.g. AAPL)"
          aria-label="Ticker symbol"
          className="h-9 w-40 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-1)] px-3 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
        />
        <Button type="submit" size="sm" disabled={analyseMutation.isPending}>
          Analyse
        </Button>
      </form>

      {/* Loading state */}
      {(!bootstrapped || analyseMutation.isPending) && <ResearchLoading />}

      {/* Error state */}
      {!analyseMutation.isPending && analyseMutation.error && (
        <div className="space-y-4">
          <Alert tone="danger" title="Research unavailable">
            {analyseMutation.error instanceof ApiClientError
              ? analyseMutation.error.message
              : "Unable to load company research."}
          </Alert>
          <Button onClick={() => analyseMutation.mutate(true)}>Retry</Button>
        </div>
      )}

      {/* Research content */}
      {!analyseMutation.isPending && view && (
        <div className="space-y-6">
          {analyseMutation.data?.cached && (
            <Alert tone="info" title="Loaded from session">
              Showing the latest analyse result for {normalized}.
            </Alert>
          )}

          {/* Company header */}
          <CompanyHeader view={view} />

          {/* Tabbed research sections */}
          <CompanyResearchTabs view={view} />
        </div>
      )}
    </div>
  );
}
