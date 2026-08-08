"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import {
  BusinessQualityCard,
  CommitteeConsensusCard,
  RecommendationCard,
} from "@/components/intelligence/DecisionCards";
import { PipelineTimeline } from "@/components/intelligence/PipelineTimeline";
import { ValidationBanner } from "@/components/intelligence/ValidationBanner";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { AnalysisActions } from "@/components/workspace/AnalysisActions";
import {
  AnalysisSummary,
  AnalysisSummaryEmpty,
} from "@/components/workspace/AnalysisSummary";
import { PipelineStatus } from "@/components/workspace/PipelineStatus";
import { RecentAnalyses } from "@/components/workspace/RecentAnalyses";
import { api } from "@/lib/api/client";
import type { AnalyseRequest } from "@/lib/api/compositionTypes";
import { ApiClientError } from "@/lib/api/types";
import {
  buildPipelineStages,
  PIPELINE_STAGE_DEFS,
} from "@/lib/analysis/pipelineStages";
import {
  loadRecentAnalyses,
  pushRecentAnalysis,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";
import { SavedAnalysesPanel } from "@/components/persistence/SavedAnalysesPanel";
import { useAuth } from "@/lib/auth/AuthProvider";
import { COMPANY_CATALOGUE } from "@/lib/companies/catalogue";
import {
  emptyIntelligenceView,
  formatPct,
  mapAnalyseResponse,
} from "@/lib/intelligence/mapResponse";
import {
  ANALYSE_DATA_UNAVAILABLE,
  loadAuthenticatedAnalyseRequest,
} from "@/lib/research/buildAnalyseRequest";
import { saveResearchSession } from "@/lib/research/sessionStore";
import { useNotifications } from "@/providers/NotificationProvider";
import { usePersistence } from "@/providers/PersistenceProvider";
import { usePerformanceTiming } from "@/hooks/usePerformanceTiming";
import { logger } from "@/lib/observability/logger";

function resolveCompany(ticker: string) {
  return COMPANY_CATALOGUE.find(
    (c) => c.ticker.toUpperCase() === ticker.trim().toUpperCase(),
  );
}

export function AnalysisWorkspace() {
  const { session, status: authStatus } = useAuth();
  const token = session?.accessToken;
  const { success, error: notifyError } = useNotifications();
  const analysisTiming = usePerformanceTiming("analysis.execution");
  const { saveAnalysis } = usePersistence();

  // RC3-003 — no silent default company; require explicit ticker.
  const [ticker, setTicker] = useState("");
  const [exchange, setExchange] = useState("");
  const [company, setCompany] = useState("");
  const [recent, setRecent] = useState<RecentAnalysisEntry[]>([]);
  const [tick, setTick] = useState(0);
  const [lastRequest, setLastRequest] = useState<AnalyseRequest | null>(null);

  useEffect(() => {
    setRecent(loadRecentAnalyses());
  }, []);

  useEffect(() => {
    const match = resolveCompany(ticker);
    if (match) {
      setExchange(match.exchange);
      setCompany(match.name);
    }
  }, [ticker]);

  const analyseMutation = useMutation({
    mutationFn: (body: AnalyseRequest) => api.analyse(body, { token }),
    onSuccess: (response, body) => {
      analysisTiming.end();
      const analysedAt = new Date().toISOString();
      saveResearchSession({
        ticker: body.ticker,
        exchange: body.exchange ?? null,
        company: body.company ?? null,
        analysedAt,
        request: body,
        response,
      });
      const mapped = mapAnalyseResponse(response);
      setRecent(
        pushRecentAnalysis({
          ticker: body.ticker.toUpperCase(),
          company: body.company || body.ticker,
          exchange: body.exchange || "—",
          recommendation: mapped.recommendation,
          analysedAt,
        }),
      );
      success(`Analysis complete for ${body.ticker.toUpperCase()}`, "Analyse");
    },
    onError: (err) => {
      analysisTiming.end();
      const message =
        err instanceof ApiClientError ? err.message : "Analyse failed";
      logger.recordClientError(
        err instanceof Error ? err : message,
        "api",
      );
      notifyError(message, "Analyse failed");
    },
  });

  useEffect(() => {
    if (!analyseMutation.isPending) return;
    const id = window.setInterval(() => setTick((t) => t + 1), 350);
    return () => window.clearInterval(id);
  }, [analyseMutation.isPending]);

  const view = useMemo(() => {
    if (analyseMutation.data) return mapAnalyseResponse(analyseMutation.data);
    return emptyIntelligenceView();
  }, [analyseMutation.data]);

  const hasResult = Boolean(analyseMutation.isSuccess && analyseMutation.data);

  const pipelineStages = useMemo(() => {
    if (analyseMutation.isPending) {
      const progressIndex = tick % PIPELINE_STAGE_DEFS.length;
      return PIPELINE_STAGE_DEFS.map((def, index) => ({
        id: def.id,
        label: def.label,
        apiStage: def.apiStage,
        status:
          index < progressIndex
            ? ("Completed" as const)
            : index === progressIndex
              ? ("Running" as const)
              : ("Pending" as const),
      }));
    }
    return buildPipelineStages(view.stages, {
      running: false,
      failed: Boolean(analyseMutation.isError),
    });
  }, [
    analyseMutation.isPending,
    analyseMutation.isError,
    tick,
    view.stages,
  ]);

  const intrinsicValue = useMemo(() => {
    const iv = lastRequest?.valuation_signals?.intrinsic_value_per_share;
    if (typeof iv === "number" && Number.isFinite(iv)) {
      return iv.toLocaleString(undefined, {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 2,
      });
    }
    return null;
  }, [lastRequest]);

  const apiError =
    analyseMutation.error instanceof ApiClientError
      ? analyseMutation.error.message
      : analyseMutation.error
        ? "Analyse failed"
        : null;

  const correlationId =
    (analyseMutation.error instanceof ApiClientError &&
      analyseMutation.error.body?.correlation_id) ||
    analyseMutation.data?.correlation_id ||
    null;

  async function runAnalysis(event?: FormEvent) {
    event?.preventDefault();
    const match = resolveCompany(ticker);
    try {
      // P0-01 — authenticated statements only; never clone demo ACM financials.
      const request = await loadAuthenticatedAnalyseRequest(ticker, {
        exchange: exchange || match?.exchange,
        company: company || match?.name,
        loadStatements: () =>
          api.financialStatements(ticker, { token, limit: 1 }),
      });
      setLastRequest(request);
      analysisTiming.start();
      analyseMutation.mutate(request);
    } catch (err) {
      notifyError(
        err instanceof Error ? err.message : ANALYSE_DATA_UNAVAILABLE,
        "Analyse",
      );
    }
  }

  function analyseAnother() {
    analyseMutation.reset();
    setLastRequest(null);
    setTicker("");
    setExchange("");
    setCompany("");
  }

  function selectCatalogue(nextTicker: string) {
    const match = resolveCompany(nextTicker);
    setTicker(nextTicker);
    if (match) {
      setExchange(match.exchange);
      setCompany(match.name);
    }
  }

  function saveCurrentAnalysis() {
    if (!analyseMutation.data || !lastRequest) return;
    if (authStatus !== "authenticated") {
      notifyError("Sign in to save analyses", "Authentication required");
      return;
    }
    const mapped = mapAnalyseResponse(analyseMutation.data);
    saveAnalysis({
      ticker: lastRequest.ticker.toUpperCase(),
      company: lastRequest.company || lastRequest.ticker,
      exchange: lastRequest.exchange || "—",
      recommendation: mapped.recommendation,
      analysedAt: new Date().toISOString(),
      label: `${lastRequest.company || lastRequest.ticker} analysis`,
      request: lastRequest,
      response: analyseMutation.data,
    });
    success(`Saved ${lastRequest.ticker.toUpperCase()}`, "Analysis saved");
  }

  const catalogue = COMPANY_CATALOGUE.slice(0, 8);
  const sector = resolveCompany(ticker)?.sector ?? "Unknown";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analysis Workspace"
        description="Run composition analysis in the Investment Terminal. Thin client over /api/v1/analyse — no local scoring."
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(18rem,22rem)_minmax(0,1fr)]">
        <aside className="space-y-4">
          <Card>
            <CardHeader
              title="Analysis Form"
              description="Select a company and run analysis"
            />
            <CardBody>
              <form className="space-y-3" onSubmit={runAnalysis}>
                <label className="block text-sm">
                  Company Selector
                  <select
                    className="mt-1 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                    value={
                      catalogue.some((c) => c.ticker === ticker.toUpperCase())
                        ? ticker.toUpperCase()
                        : ""
                    }
                    onChange={(e) => {
                      if (e.target.value) selectCatalogue(e.target.value);
                    }}
                    aria-label="Company selector"
                  >
                    <option value="">Custom ticker…</option>
                    {COMPANY_CATALOGUE.map((c) => (
                      <option key={c.ticker} value={c.ticker}>
                        {c.name} ({c.ticker})
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block text-sm">
                  Ticker
                  <Input
                    className="mt-1"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value.toUpperCase())}
                    placeholder="Enter ticker"
                    required
                    aria-label="Ticker"
                  />
                </label>

                <label className="block text-sm">
                  Exchange
                  <Input
                    className="mt-1"
                    value={exchange}
                    onChange={(e) => setExchange(e.target.value)}
                    placeholder="NASDAQ"
                    aria-label="Exchange"
                  />
                </label>

                <label className="block text-sm">
                  Company
                  <Input
                    className="mt-1"
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    placeholder="Company name"
                    aria-label="Company name"
                  />
                </label>

                <Button
                  type="submit"
                  className="w-full"
                  disabled={analyseMutation.isPending || !ticker.trim()}
                >
                  {analyseMutation.isPending ? "Running…" : "Run Analysis"}
                </Button>
              </form>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Recent Companies" description="From catalogue" />
            <CardBody>
              <ul className="space-y-2">
                {catalogue.map((c) => (
                  <li key={c.ticker}>
                    <button
                      type="button"
                      className="flex w-full items-center justify-between rounded-md border border-[var(--border)] px-3 py-2 text-left text-sm hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                      onClick={() => selectCatalogue(c.ticker)}
                    >
                      <span>{c.name}</span>
                      <span className="font-mono text-xs text-[var(--muted)]">
                        {c.ticker}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </CardBody>
          </Card>

          <RecentAnalyses
            items={recent}
            onSelect={(entry) => {
              setTicker(entry.ticker);
              setExchange(entry.exchange === "—" ? "" : entry.exchange);
              setCompany(entry.company);
            }}
          />
          <SavedAnalysesPanel />
        </aside>

        <div className="min-w-0 space-y-4">
          <PipelineStatus stages={pipelineStages} />

          <ValidationBanner
            valid={analyseMutation.isSuccess ? true : null}
            errors={
              analyseMutation.error instanceof ApiClientError
                ? analyseMutation.error.body?.validation_errors
                : undefined
            }
            apiError={apiError}
            correlationId={correlationId}
            onRetry={
              lastRequest
                ? () => analyseMutation.mutate(lastRequest)
                : undefined
            }
          />

          {view.warnings.length ? (
            <Alert tone="warning" title="Pipeline warnings">
              <ul className="list-inside list-disc">
                {view.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </Alert>
          ) : null}

          {analyseMutation.data ? (
            <>
              <AnalysisSummary
                view={view}
                intrinsicValue={intrinsicValue}
                ticker={lastRequest?.ticker || ticker}
              />
              <AnalysisActions
                ticker={lastRequest?.ticker || ticker}
                company={lastRequest?.company || company}
                sector={sector}
                recommendation={view.recommendation}
                hasResult={hasResult}
                onAnalyseAnother={analyseAnother}
                onSaveAnalysis={saveCurrentAnalysis}
                canSave={authStatus === "authenticated"}
              />
              <div className="grid gap-4 lg:grid-cols-2">
                <RecommendationCard
                  decision={view.recommendation}
                  confidence={view.recommendationConfidence}
                  marginOfSafety={view.marginOfSafety}
                />
                <BusinessQualityCard
                  label={view.businessQualityLabel}
                  score={view.businessQualityScore}
                  confidence={view.businessQualityConfidence}
                />
              </div>
              <CommitteeConsensusCard
                decision={view.committeeDecision}
                confidence={view.committeeConfidence}
                consensus={view.committeeConsensus}
                minorityNotes={view.minorityNotes}
              />
              <PipelineTimeline stages={view.stages} />
              <p className="text-xs text-[var(--muted)]">
                Confidence {formatPct(view.recommendationConfidence)} · Pipeline{" "}
                {view.pipelineVersion ?? "—"}
              </p>
            </>
          ) : (
            <AnalysisSummaryEmpty />
          )}
        </div>
      </div>
    </div>
  );
}
