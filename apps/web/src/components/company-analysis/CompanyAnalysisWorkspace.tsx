"use client";

/**
 * P9.4 / EPIC-005 — Flagship Company Analysis Workspace.
 * Consumes frozen /api/v1/analyse (+ optional market quote). Display only.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";

import { Button, ErrorState } from "@/components/ds";
import { useResearchDisclaimerGate } from "@/components/legal/useResearchDisclaimerGate";
import { api } from "@/lib/api/client";
import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";
import { ApiClientError } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { pushRecentAnalysis } from "@/lib/analysis/recentAnalyses";
import { useDashboardPrefsStore } from "@/lib/dashboard";
import {
  analysisPath,
  hasExactListingIdentity,
  identityFromSearchParams,
  type SecurityListingView,
} from "@/lib/securities/identity";
import { loadAuthenticatedAnalyseRequest } from "@/lib/research/buildAnalyseRequest";
import {
  mapResearchView,
  type ResearchView,
} from "@/lib/research/mapResearchView";
import { saveResearchSession } from "@/lib/research/sessionStore";
import { useNotifications } from "@/providers/NotificationProvider";
import { CompanyResearchBar } from "@/components/securities/CompanyResearchBar";
import {
  AnalysisEmpty,
  AnalysisModeChooser,
  AnalysisPending,
  FigmaAnalysisReport,
  SimpleResearchSummary,
} from "./FigmaAnalysisReport";

function listingFromIdentity(identity: {
  ticker: string;
  exchange: string;
  isin: string;
  mic: string;
}): SecurityListingView | null {
  if (!identity.ticker) return null;
  return {
    ticker: identity.ticker,
    company_name: identity.ticker,
    exchange: identity.exchange,
    isin: identity.isin,
    mic: identity.mic,
    security_type: "equity",
    eligibility: true,
  };
}

function describeAnalyseError(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 401) {
      return "Permission denied — sign in required for /api/v1/analyse. No fabricated research is shown.";
    }
    if (error.status === 403) {
      return "Permission denied — this account cannot run analyse for the requested symbol.";
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
    if (msg.includes("timeout") || msg.includes("network")) {
      return "Network timeout or connectivity failure — Data unavailable. Retry when online.";
    }
    if (error.message === "AMBIGUOUS") {
      return "IDENTITY_AMBIGUOUS — select ISIN + exchange/MIC. The platform never guesses a listing.";
    }
    if (error.message === "UNSUPPORTED") {
      return "UNSUPPORTED_SECURITY — this instrument is outside ordinary-equity analysis.";
    }
    if (error.message === "Data unavailable.") {
      return "Security identified successfully. Investment data is currently unavailable. No valuation was calculated.";
    }
    return error.message;
  }
  return "Data unavailable.";
}

export function CompanyAnalysisWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session } = useAuth();
  const token = session?.accessToken;
  const { success, error: notifyError } = useNotifications();

  // RC3-003 — no silent default company; require explicit Security Master identity.
  const urlIdentity = identityFromSearchParams(searchParams);
  const urlSymbol = urlIdentity.ticker;
  const urlExchange = urlIdentity.exchange;
  const urlIsin = urlIdentity.isin;
  const urlMic = urlIdentity.mic;
  const [symbol, setSymbol] = useState(urlSymbol);
  const [query, setQuery] = useState(urlSymbol);
  const [identityError, setIdentityError] = useState<string | null>(null);
  const [resolvingListing, setResolvingListing] = useState(false);
  const [listing, setListing] = useState<SecurityListingView | null>(() =>
    listingFromIdentity(urlIdentity),
  );
  const [view, setView] = useState<ResearchView | null>(null);
  const [analysedAt, setAnalysedAt] = useState<string | null>(null);
  const [lastAnalyseRequest, setLastAnalyseRequest] =
    useState<AnalyseRequest | null>(null);
  const [lastAnalyseResponse, setLastAnalyseResponse] =
    useState<AnalyseResponse | null>(null);
  /** Monotonic generation — drop stale analyse responses after symbol change. */
  const analyseGeneration = useRef(0);
  /** Skip a second /analyse when the user only changes presentation depth. */
  const analysedKeyRef = useRef<string | null>(null);

  const recordSearch = useDashboardPrefsStore((s) => s.recordSearch);
  const { runWithDisclaimer, gate: disclaimerGate } =
    useResearchDisclaimerGate();

  useEffect(() => {
    setSymbol((prev) => {
      if (prev === urlSymbol) return prev;
      analyseGeneration.current += 1;
      analysedKeyRef.current = null;
      setView(null);
      setLastAnalyseRequest(null);
      setLastAnalyseResponse(null);
      setAnalysedAt(null);
      setIdentityError(null);
      return urlSymbol;
    });
    setQuery(urlSymbol);
    setListing((prev) => {
      const next = listingFromIdentity({
        ticker: urlSymbol,
        exchange: urlExchange,
        isin: urlIsin,
        mic: urlMic,
      });
      if (
        prev?.ticker === next?.ticker &&
        prev?.exchange === next?.exchange &&
        prev?.isin === next?.isin &&
        prev?.mic === next?.mic
      ) {
        return prev;
      }
      return next;
    });
  }, [urlSymbol, urlExchange, urlIsin, urlMic]);

  const selectSymbol = useCallback(
    (next: SecurityListingView | string, depthOverride?: "simple" | "buffett") => {
      if (typeof next === "string") {
        const normalized = next.trim().toUpperCase();
        if (!normalized) return;
        setSymbol(normalized);
        setQuery(normalized);
        recordSearch(normalized);
        router.replace(`/analysis?symbol=${encodeURIComponent(normalized)}`);
        return;
      }
      if (!next.ticker) return;
      setSymbol(next.ticker);
      setQuery(next.ticker);
      setListing(next);
      setIdentityError(null);
      recordSearch(next.ticker);
      const params = new URLSearchParams(analysisPath(next).split("?")[1] || "");
      const depthNow = searchParams.get("depth");
      const modeNow = searchParams.get("mode");
      const keep =
        depthOverride ||
        (depthNow === "simple" || depthNow === "buffett"
          ? depthNow
          : modeNow === "simple"
            ? "simple"
            : modeNow === "buffett"
              ? "buffett"
              : null);
      if (keep) params.set("depth", keep);
      router.replace(`/analysis?${params.toString()}`);
    },
    [recordSearch, router, searchParams],
  );

  const explainResolveStatus = useCallback((status: string | null | undefined) => {
    if (status === "AMBIGUOUS") {
      return "Multiple listings matched. Select the ISIN and exchange to continue.";
    }
    if (status === "UNSUPPORTED" || status === "REJECTED") {
      return "This instrument is outside ordinary-equity analysis.";
    }
    return "No official listing matched. Data unavailable.";
  }, []);

  const resolveListing = useCallback(
    async (raw: string, depthOverride?: "simple" | "buffett") => {
      const normalized = raw.trim().toUpperCase();
      if (!normalized) return null;
      if (!token) {
        setIdentityError("Sign in required for Security Master search.");
        return null;
      }
      setResolvingListing(true);
      setIdentityError(null);
      try {
        const payload = await api.resolveSecurity(normalized, { token });
        if (payload.status === "RESOLVED" && payload.identity?.exchange) {
          selectSymbol(payload.identity, depthOverride);
          return payload.identity;
        }
        setIdentityError(explainResolveStatus(payload.status));
        return null;
      } catch {
        setIdentityError("Security Master search failed. Retry when the API is available.");
        return null;
      } finally {
        setResolvingListing(false);
      }
    },
    [explainResolveStatus, selectSymbol, token],
  );

  const analyseMutation = useMutation({
    mutationFn: async () => {
      const generation = ++analyseGeneration.current;
      const requestedSymbol = symbol;
      const exchange = listing?.exchange || urlExchange || null;
      const isin = listing?.isin || urlIsin || null;
      if (!exchange) {
        throw new Error("AMBIGUOUS");
      }
      const body = await loadAuthenticatedAnalyseRequest(requestedSymbol, {
        exchange,
        isin,
        mic: listing?.mic || urlMic || null,
        company: listing?.company_name,
        loadStatements: () =>
          api.financialStatements(requestedSymbol, {
            token,
            limit: 1,
            exchange,
          }),
        loadQuote: () => api.marketQuote(requestedSymbol, { token, exchange }),
      });
      const response = await api.analyse(body, { token });
      return {
        body,
        response,
        generation,
        requestedSymbol,
        identityKey: `${requestedSymbol.toUpperCase()}|${exchange || ""}|${isin || ""}|${listing?.mic || urlMic || ""}`,
      };
    },
    onSuccess: ({ body, response, generation, requestedSymbol, identityKey }) => {
      // Drop stale responses after navigation / newer analyse.
      if (generation !== analyseGeneration.current) return;
      if (body.ticker.toUpperCase() !== requestedSymbol.toUpperCase()) return;
      const at = new Date().toISOString();
      setAnalysedAt(at);
      setLastAnalyseRequest(body);
      setLastAnalyseResponse(response);
      const mapped = mapResearchView(response, body, at);
      setView(mapped);
      analysedKeyRef.current = identityKey;
      saveResearchSession({
        ticker: body.ticker,
        exchange: body.exchange ?? null,
        company: body.company ?? null,
        analysedAt: at,
        request: body,
        response,
      });
      pushRecentAnalysis({
        ticker: body.ticker.toUpperCase(),
        company: body.company || body.ticker,
        exchange: body.exchange || "—",
        recommendation: mapped.recommendation,
        analysedAt: at,
      });
      const serverIv = (
        response.payload as {
          server_valuation?: { intrinsic_value_per_share?: number | null };
        }
      )?.server_valuation?.intrinsic_value_per_share;
      const valuationOk =
        response.ok === true &&
        typeof serverIv === "number" &&
        Number.isFinite(serverIv);
      if (valuationOk) {
        success(`Analysis loaded for ${body.ticker.toUpperCase()}`, "Analyse");
      } else {
        notifyError(
          "Analysis completed with unavailable valuation or incomplete data",
          "Analyse",
        );
      }
    },
    onError: (err) => {
      const message =
        err instanceof ApiClientError ? err.message : "Analyse failed";
      notifyError(message, "Analyse failed");
    },
  });

  const runAnalyse = useCallback(() => {
    const normalized = (query.trim() || symbol).toUpperCase();
    if (!normalized) return;
    const exchange = listing?.exchange || urlExchange;
    if (!exchange) {
      void resolveListing(normalized);
      return;
    }
    if (normalized !== symbol) {
      selectSymbol({
        ticker: normalized,
        company_name: listing?.company_name || normalized,
        exchange,
        isin: listing?.isin || urlIsin,
        mic: listing?.mic || urlMic,
        security_type: "equity",
        eligibility: true,
      });
      return;
    }
    runWithDisclaimer(() => {
      analyseMutation.mutate();
    });
  }, [
    analyseMutation,
    listing,
    query,
    resolveListing,
    runWithDisclaimer,
    selectSymbol,
    symbol,
    urlExchange,
    urlIsin,
    urlMic,
  ]);

  const depthParam = searchParams.get("depth");
  const modeParam = searchParams.get("mode");
  const depth =
    depthParam === "simple" || depthParam === "buffett"
      ? depthParam
      : modeParam === "simple" || modeParam === "buffett"
        ? modeParam
        : null;
  const identityKey = `${symbol}|${listing?.exchange || urlExchange || ""}|${listing?.isin || urlIsin || ""}|${listing?.mic || urlMic || ""}`;
  const hasListing = Boolean(listing?.exchange || urlExchange);

  useEffect(() => {
    if (!symbol || !token || hasListing || resolvingListing || identityError) return;
    void resolveListing(symbol);
  }, [hasListing, identityError, resolveListing, resolvingListing, symbol, token]);

  function chooseDepth(next: "simple" | "buffett") {
    const target = (query.trim() || symbol).toUpperCase();
    if (!target) return;
    if (!hasListing) {
      void resolveListing(target, next);
      return;
    }
    const params = new URLSearchParams(searchParams.toString());
    params.set("depth", next);
    params.delete("mode");
    router.replace(`/analysis?${params.toString()}`);
  }

  function returnToDepthChoice() {
    const params = new URLSearchParams(searchParams.toString());
    params.delete("depth");
    params.delete("mode");
    const next = params.toString();
    router.replace(next ? `/analysis?${next}` : "/analysis");
  }

  // Auto-run only after the user picks a depth and the URL has an exact listing.
  useEffect(() => {
    if (!symbol || !token || !depth) return;
    if (!hasExactListingIdentity(urlIdentity) && !urlExchange) return;
    if (analysedKeyRef.current === identityKey) return;
    runWithDisclaimer(() => {
      analyseMutation.mutate();
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional identity-driven refresh
  }, [symbol, urlExchange, urlIsin, urlMic, token, depth, identityKey]);

  const marketQuery = useQuery({
    queryKey: ["company-analysis", "market", symbol, urlExchange],
    queryFn: () =>
      api.marketQuote(symbol, { token, exchange: urlExchange || listing?.exchange }),
    enabled: Boolean(token && symbol && (urlExchange || listing?.exchange)),
    retry: false,
    staleTime: 60_000,
  });

  const financialStatementsQuery = useQuery({
    // Five annual periods feed the Figma trend charts (Financials, Earnings
    // Quality, Growth Quality) as well as the summary's latest-period fields.
    queryKey: [
      "company-analysis",
      "financial-statements",
      symbol,
      urlExchange,
      "annual",
      5,
    ],
    queryFn: () =>
      api.financialStatements(symbol, {
        token,
        limit: 5,
        period_type: "annual",
        exchange: urlExchange || listing?.exchange,
      }),
    enabled: Boolean(token && symbol && (urlExchange || listing?.exchange)),
    retry: false,
    staleTime: 60_000,
  });

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typing =
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable);
      if (typing) return;
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        runAnalyse();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [runAnalyse]);

  return (
    <div className="flex min-h-[70vh] flex-col bg-[var(--bg)]">
      {disclaimerGate}
      <div className="border-b border-[var(--border)] px-4 py-3 sm:px-6">
        <CompanyResearchBar
          variant={symbol ? "compact" : "hero"}
          query={query}
          onQueryChange={setQuery}
          onSelect={selectSymbol}
        />
      </div>
      <div
        role="region"
        className="min-w-0 flex-1"
        id="company-analysis-main"
        tabIndex={-1}
        aria-label="Main analysis area"
      >
        {!depth ? (
          <AnalysisModeChooser
            companyLabel={
              listing?.company_name && listing.company_name !== symbol
                ? listing.company_name
                : symbol
            }
            blockedReason={
              !symbol && !query.trim()
                ? "Search for a company to begin."
                : identityError
                  ? identityError
                  : resolvingListing
                    ? "Resolving the official listing…"
                    : null
            }
            onSimple={() => chooseDepth("simple")}
            onBuffett={() => chooseDepth("buffett")}
          />
        ) : null}

        {depth && analyseMutation.isPending && !view ? <AnalysisPending /> : null}

        {depth && analyseMutation.isError && !view ? (
          <ErrorState
            title="Investment data is currently unavailable."
            description={describeAnalyseError(analyseMutation.error)}
            action={
              <Button size="sm" variant="secondary" onClick={runAnalyse}>
                Retry
              </Button>
            }
          />
        ) : null}

        {depth && !analyseMutation.isPending && !analyseMutation.isError && !view ? (
          <AnalysisEmpty
            symbol={symbol}
            description={
              identityError
                ? identityError
                : hasExactListingIdentity(urlIdentity)
                  ? "Security identified successfully. No valuation was calculated."
                  : symbol
                    ? "Select the official listing, then run analysis. No company is pre-selected."
                    : "Search for a company to begin. No company is pre-selected."
            }
            onAnalyze={symbol ? runAnalyse : undefined}
          />
        ) : null}

        {view && depth ? (
          <>
            <div className="px-4 pt-3 sm:px-6">
              <button
                type="button"
                onClick={returnToDepthChoice}
                className="text-[13px] text-[var(--muted)] hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              >
                ← Change research depth
              </button>
            </div>
            {analyseMutation.isPending ? (
              <p className="px-6 pt-3 text-xs text-[var(--muted)]" aria-live="polite">
                Refreshing analysis…
              </p>
            ) : null}
            {depth === "simple" ? (
              <SimpleResearchSummary
                view={view}
                marketQuote={marketQuery.data ?? null}
                financialStatements={financialStatementsQuery.data ?? null}
                onUpgrade={() => chooseDepth("buffett")}
              />
            ) : (
              <FigmaAnalysisReport
                view={view}
                marketQuote={marketQuery.data ?? null}
                financialStatements={financialStatementsQuery.data ?? null}
                analyseRequest={lastAnalyseRequest}
                analyseResponse={lastAnalyseResponse}
              />
            )}
            <p className="px-6 pb-6 text-[10px] text-[var(--muted)]">
              Last updated: {analysedAt ?? view.analysedAt ?? "Data unavailable."}{" "}
              · Research tools — not investment advice
            </p>
          </>
        ) : null}
      </div>
    </div>
  );
}
