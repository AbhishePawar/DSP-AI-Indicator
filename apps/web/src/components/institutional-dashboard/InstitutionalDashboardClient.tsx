"use client";

import { FormEvent, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";

import { InstitutionalResearchDashboard } from "@/components/institutional-dashboard/InstitutionalResearchDashboard";
import { PageHeader } from "@/components/layout/PageHeader";
import { ResearchModeBanner } from "@/components/research/ResearchModeBanner";
import { CompactTrustLadder } from "@/components/trust/SurfaceTrustChrome";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Input,
  Skeleton,
  Spinner,
} from "@/components/ds";
import {
  mapInstitutionalDashboard,
  payloadsFromUnifiedBundle,
  type UnifiedDataBundlePayload,
} from "@/lib/institutional-dashboard/mapInstitutionalDashboard";
import { api } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { loadAuthenticatedAnalyseRequest } from "@/lib/research/buildAnalyseRequest";
import { irdSurfaceTrust } from "@/lib/trust/surfaceTrust";

export function InstitutionalDashboardClient({
  initialTicker = "",
}: {
  initialTicker?: string;
}) {
  const { session } = useAuth();
  // RC3-003 — supporting panels view; no silent ACM/AAPL default.
  const [ticker, setTicker] = useState(initialTicker.trim().toUpperCase());

  const mutation = useMutation({
    mutationFn: async () => {
      const symbol = ticker.trim().toUpperCase();
      if (!symbol) {
        throw new Error(
          "Ticker is required — no default company is invented in the thin client.",
        );
      }
      const opts = { token: session?.accessToken };
      // P0-01 — authenticated statements only; never clone demo ACM financials.
      const request = await loadAuthenticatedAnalyseRequest(symbol, {
        loadStatements: () =>
          api.financialStatements(symbol, { ...opts, limit: 1 }),
      });
      const [response, dataResp] = await Promise.all([
        api.analyse(request, opts),
        api
          .dataBundle(symbol, {
            ...opts,
            historical_series_kind: "ohlcv",
            historical_frequency: "daily",
            historical_limit: 30,
          })
          .catch((err: unknown) => {
            if (err instanceof ApiClientError) {
              const typed =
                err.status === 401 || err.status === 403
                  ? `Data gateway ${err.status}: permission denied.`
                  : err.status === 404
                    ? "Data gateway 404: no coverage for this symbol."
                    : err.status === 408 || err.status === 504
                      ? "Data gateway timeout."
                      : err.status >= 500
                        ? `Data gateway ${err.status}: server error.`
                        : `Data gateway error ${err.status}.`;
              return {
                ok: false as const,
                bundle: undefined as UnifiedDataBundlePayload | undefined,
                message: typed,
                gatewayStatus: err.status,
              };
            }
            return {
              ok: false as const,
              bundle: undefined as UnifiedDataBundlePayload | undefined,
              message: "Data gateway unreachable (network).",
              gatewayStatus: undefined as number | undefined,
            };
          }),
      ]);
      const sections = payloadsFromUnifiedBundle(dataResp.bundle ?? null);
      return {
        request,
        response,
        ...sections,
        analysedAt: new Date().toISOString(),
        dataGatewayNote:
          "ok" in dataResp && dataResp.ok === false
            ? dataResp.message
            : undefined,
      };
    },
  });

  const view = useMemo(() => {
    if (!mutation.data) return null;
    return mapInstitutionalDashboard(mutation.data);
  }, [mutation.data]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const symbol = ticker.trim().toUpperCase();
    if (!symbol) return;
    mutation.mutate();
  }

  function describeIrdError(error: unknown): string {
    if (error instanceof ApiClientError) {
      if (error.status === 401) {
        return "Permission denied — sign in required. No fabricated research is shown.";
      }
      if (error.status === 403) {
        return "Permission denied — this account cannot run research for the requested symbol.";
      }
      if (error.status === 404) {
        return "No coverage — analyse returned not found for this symbol. Data unavailable.";
      }
      if (error.status === 408 || error.status === 504) {
        return "Network timeout — the analyse request did not complete. Retry when the API is available.";
      }
      if (error.status >= 500) {
        return `API unavailable (${error.status}) — ${error.message}. Data unavailable.`;
      }
      return error.message || "Data unavailable.";
    }
    if (error instanceof Error) {
      const msg = error.message.toLowerCase();
      if (msg.includes("timeout") || msg.includes("network") || msg.includes("fetch")) {
        return "Network timeout or connectivity failure — Data unavailable. Retry when online.";
      }
      return error.message;
    }
    return "Analysis request failed. Data unavailable.";
  }

  const errorMessage = mutation.error
    ? describeIrdError(mutation.error)
    : null;

  const classicResearchHref = ticker.trim()
    ? `/research/${encodeURIComponent(ticker.trim().toUpperCase())}`
    : null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Institutional Research Dashboard"
        description="Production research surface implementing RS-001…RS-010 over frozen /api/v1 — thin client, no invented numbers."
      />
      <ResearchModeBanner />

      <CompactTrustLadder
        summary={irdSurfaceTrust({
          ticker: ticker.trim() || null,
          loaded: Boolean(view),
          priceDisplay: view?.executive.currentMarketPrice.display ?? null,
          mosDisplay: view?.executive.marginOfSafety.display ?? null,
          confidenceDisplay: view?.executive.confidence.display ?? null,
          recommendationDisplay: view?.executive.recommendation.display ?? null,
          unavailableFieldCount: view
            ? [
                view.executive.currentMarketPrice,
                view.executive.intrinsicValue,
                view.executive.marginOfSafety,
                view.executive.confidence,
                view.executive.recommendation,
              ].filter((f) => f.presence !== "available").length
            : 5,
          opposingNotes: mutation.data?.dataGatewayNote
            ? [mutation.data.dataGatewayNote]
            : errorMessage
              ? [errorMessage]
              : [],
          reportTimestamp: view?.executive.reportTimestamp.display ?? null,
        })}
        title="Trust Ladder"
      />

      <Card>
        <CardContent>
          <form
            onSubmit={onSubmit}
            className="flex flex-wrap items-end gap-3"
            aria-label="Load institutional research"
          >
            <div className="min-w-[10rem] flex-1">
              <label
                htmlFor="ird-ticker"
                className="mb-1 block text-xs font-medium uppercase tracking-wide text-[var(--muted)]"
              >
                Ticker
              </label>
              <Input
                id="ird-ticker"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                autoComplete="off"
                required
              />
            </div>
            <Button
              type="submit"
              disabled={mutation.isPending || !ticker.trim()}
            >
              {mutation.isPending ? "Loading…" : "Run research"}
            </Button>
            {classicResearchHref ? (
              <Link
                href={classicResearchHref}
                className="inline-flex min-h-11 items-center text-sm text-[var(--accent)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              >
                Open classic research
              </Link>
            ) : (
              <span className="text-sm text-[var(--muted)]">
                Enter a ticker to open classic research
              </span>
            )}
          </form>
        </CardContent>
      </Card>

      {mutation.isPending ? (
        <div
          className="space-y-3 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-4"
          role="status"
          aria-live="polite"
        >
          <div className="flex items-center gap-3 text-sm text-[var(--muted)]">
            <Spinner label="Loading composition pipeline" />
            Loading composition pipeline…
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
            <Skeleton className="h-32 sm:col-span-2 lg:col-span-3" />
          </div>
        </div>
      ) : null}

      {errorMessage ? <Alert variant="error">{errorMessage}</Alert> : null}

      {mutation.data?.dataGatewayNote ? (
        <Alert variant="warning">
          Partial coverage: analyse succeeded but the data gateway reported —{" "}
          {mutation.data.dataGatewayNote} Market/statement panels may show Data
          unavailable. Full trust ladder, contradictory evidence, and
          recommendation evidence live on{" "}
          <Link
            href="/research/institutional"
            className="underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            Institutional Reports
          </Link>
          .
        </Alert>
      ) : null}

      {view && !mutation.data?.dataGatewayNote ? (
        <Alert variant="info">
          This dashboard renders RS panels from the analyse composition. For the
          epistemic ladder (Facts → Analysis → Inference → Recommendation),
          opposing evidence, and report audit trail, open{" "}
          <Link
            href="/research/institutional"
            className="underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            Institutional Reports
          </Link>
          .
        </Alert>
      ) : null}

      {view ? <InstitutionalResearchDashboard view={view} /> : null}

      {!view && !mutation.isPending && !errorMessage ? (
        <Alert variant="info">
          Enter a ticker and run research. Authenticated data without a configured
          provider will show Data unavailable. — never placeholders.
        </Alert>
      ) : null}
    </div>
  );
}
