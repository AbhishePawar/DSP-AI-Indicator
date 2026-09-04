"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ResearchLoading } from "@/components/loading";
import { api } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { logger } from "@/lib/observability/logger";
import type { AnalyseRequest } from "@/lib/api/compositionTypes";
import { COMPANY_CATALOGUE } from "@/lib/companies/catalogue";
import { fetchSelectedExchange } from "@/lib/companies/listingSelection";
import { loadAuthenticatedAnalyseRequest } from "@/lib/research/buildAnalyseRequest";
import { mapResearchView } from "@/lib/research/mapResearchView";
import {
  clearResearchSession,
  loadResearchSession,
  saveResearchSession,
} from "@/lib/research/sessionStore";
import { CompanyResearchLayout } from "./CompanyResearchLayout";

type LoadResult = {
  request: AnalyseRequest;
  response: Awaited<ReturnType<typeof api.analyse>>;
  analysedAt: string;
  cached: boolean;
};

export function CompanyResearchPage({ ticker }: { ticker: string }) {
  const { session } = useAuth();
  const token = session?.accessToken;
  const normalized = ticker.trim().toUpperCase();
  const [bootstrapped, setBootstrapped] = useState(false);

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

      // P0-01 — authenticated statements only; never clone demo ACM financials.
      // P0-02 — market price from authenticated quote (same as flagship workspace).
      const match = COMPANY_CATALOGUE.find(
        (c) => c.ticker.toUpperCase() === normalized,
      );
      const selected = await fetchSelectedExchange({
        symbol: normalized,
        token,
        catalogueExchange: match?.exchange,
      });
      const request = await loadAuthenticatedAnalyseRequest(normalized, {
        exchange: selected,
        company: match?.name,
        loadStatements: () =>
          api.financialStatements(normalized, {
            token,
            limit: 1,
            exchange: selected,
          }),
        loadQuote: () =>
          api.marketQuote(normalized, {
            token,
            exchange: selected,
          }),
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
    // eslint-disable-next-line react-hooks/exhaustive-deps -- bootstrap per ticker
  }, [normalized]);

  const view = useMemo(() => {
    if (!analyseMutation.data) return null;
    return mapResearchView(
      analyseMutation.data.response,
      analyseMutation.data.request,
      analyseMutation.data.analysedAt,
    );
  }, [analyseMutation.data]);

  if (!bootstrapped || analyseMutation.isPending) {
    return <ResearchLoading />;
  }

  if (analyseMutation.error || !view) {
    const message =
      analyseMutation.error instanceof ApiClientError
        ? analyseMutation.error.message
        : "Unable to load company research.";
    if (analyseMutation.error) {
      logger.recordClientError(
        analyseMutation.error instanceof Error
          ? analyseMutation.error
          : message,
        "research",
      );
    }
    return (
      <div className="space-y-4">
        <Alert tone="danger" title="Research unavailable">
          {message}
        </Alert>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => analyseMutation.mutate(true)}>Retry</Button>
          <Link href="/research">
            <Button variant="secondary">Back to Research</Button>
          </Link>
          <Link href="/intelligence">
            <Button variant="secondary">Open Intelligence Workspace</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {analyseMutation.data?.cached ? (
        <Alert tone="info" title="Loaded from session">
          Showing the latest analyse result for {normalized}.
        </Alert>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Link href="/research">
          <Button variant="ghost" size="sm">
            ← Research Home
          </Button>
        </Link>
        <Link href="/intelligence">
          <Button variant="ghost" size="sm">
            Intelligence Workspace
          </Button>
        </Link>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => analyseMutation.mutate(true)}
          disabled={analyseMutation.isPending}
        >
          Refresh Analysis
        </Button>
      </div>
      <CompanyResearchLayout view={view} />
    </div>
  );
}
