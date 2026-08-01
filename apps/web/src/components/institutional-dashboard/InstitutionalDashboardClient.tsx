"use client";

import { FormEvent, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";

import { InstitutionalResearchDashboard } from "@/components/institutional-dashboard/InstitutionalResearchDashboard";
import { PageHeader } from "@/components/layout/PageHeader";
import { ResearchModeBanner } from "@/components/research/ResearchModeBanner";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import {
  mapInstitutionalDashboard,
  payloadsFromUnifiedBundle,
  type UnifiedDataBundlePayload,
} from "@/lib/institutional-dashboard/mapInstitutionalDashboard";
import { api } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { buildAnalyseRequestForTicker } from "@/lib/research/buildAnalyseRequest";

export function InstitutionalDashboardClient({
  initialTicker = "ACM",
}: {
  initialTicker?: string;
}) {
  const { session } = useAuth();
  const [ticker, setTicker] = useState(initialTicker.toUpperCase());

  const mutation = useMutation({
    mutationFn: async () => {
      const symbol = ticker.trim().toUpperCase();
      const request = buildAnalyseRequestForTicker(symbol);
      const opts = { token: session?.accessToken };
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
    mutation.mutate();
  }

  const errorMessage =
    mutation.error instanceof ApiClientError
      ? mutation.error.message
      : mutation.error
        ? "Analysis request failed"
        : null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Institutional Research Dashboard"
        description="Production research surface implementing RS-001…RS-010 over frozen /api/v1 — thin client, no invented numbers."
      />
      <ResearchModeBanner />

      <Card>
        <CardBody>
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
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Loading…" : "Run research"}
            </Button>
            <Link
              href={`/research/${encodeURIComponent(ticker.trim().toUpperCase() || "ACM")}`}
              className="text-sm text-[var(--accent)] underline-offset-2 hover:underline"
            >
              Open classic research
            </Link>
          </form>
        </CardBody>
      </Card>

      {mutation.isPending ? (
        <div className="flex items-center gap-3 text-sm text-[var(--muted)]">
          <Spinner />
          Loading composition pipeline…
        </div>
      ) : null}

      {errorMessage ? <Alert tone="danger">{errorMessage}</Alert> : null}

      {mutation.data?.dataGatewayNote ? (
        <Alert tone="warning">
          Partial coverage: analyse succeeded but the data gateway reported —{" "}
          {mutation.data.dataGatewayNote} Market/statement panels may show Data
          unavailable. Full trust ladder, contradictory evidence, and
          recommendation evidence live on{" "}
          <Link
            href="/research/institutional"
            className="underline underline-offset-2"
          >
            Institutional Reports
          </Link>
          .
        </Alert>
      ) : null}

      {view && !mutation.data?.dataGatewayNote ? (
        <Alert tone="info">
          This dashboard renders RS panels from the analyse composition. For the
          epistemic ladder (Facts → Analysis → Inference → Recommendation),
          opposing evidence, and report audit trail, open{" "}
          <Link
            href="/research/institutional"
            className="underline underline-offset-2"
          >
            Institutional Reports
          </Link>
          .
        </Alert>
      ) : null}

      {view ? <InstitutionalResearchDashboard view={view} /> : null}

      {!view && !mutation.isPending && !errorMessage ? (
        <Alert tone="info">
          Enter a ticker and run research. Authenticated data without a configured
          provider will show Data unavailable. — never placeholders.
        </Alert>
      ) : null}
    </div>
  );
}
