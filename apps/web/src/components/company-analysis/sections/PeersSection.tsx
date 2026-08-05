"use client";

/**
 * Institutional Company Workspace — Peers tab.
 *
 * Orchestrates existing, already-mounted endpoints only:
 *   POST /analyze/company (as_decision_pack=true) → report_id per symbol
 *   POST /compare         → comparison.QualitativeComparisonEngine output
 *
 * No client-side peer scoring, eligibility, or valuation math — the server
 * is the sole source of the comparison conclusion.
 */

import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Badge, Button, Input } from "@/components/ds";
import { api } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { FieldRow, SectionCard, WorkspaceEmpty } from "../WorkspacePrimitives";

const MAX_PEERS = 6;

type ComparisonObservation = {
  code: string;
  text: string;
  dimension: string;
  subjects: string[];
};

type ComparisonReport = {
  status: string;
  scope_notes: string[];
  methodology_id: string | null;
  methodology_version: string | null;
  industry_id: string | null;
  included_symbols: string[];
  excluded_symbols: string[];
  exclusion_reasons: string[];
  eligibility_group_status: string | null;
  dimension_results: { dimension: string; observations: ComparisonObservation[] }[];
  shared_observations: ComparisonObservation[];
  pair_observations: ComparisonObservation[];
  limitations: { code: string; message: string; subjects: string[] }[];
  explanation: { summary: string; detail: string | null };
};

type ComparisonResultPayload = {
  status: string;
  refused: boolean;
  report: ComparisonReport;
};

function defaultRange() {
  const end = new Date();
  const start = new Date();
  start.setFullYear(end.getFullYear() - 1);
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { start: iso(start), end: iso(end) };
}

function dimensionLabel(dimension: string): string {
  return dimension
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function describeError(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 401) {
      return "Permission denied — sign in required for peer comparison.";
    }
    return error.message || `API error (${error.status})`;
  }
  if (error instanceof Error) return error.message;
  return "Data unavailable.";
}

export function PeersSection({ view }: { view: ResearchView }) {
  const { session } = useAuth();
  const token = session?.accessToken ?? null;
  const primary = view.ticker;
  const [draft, setDraft] = useState("");
  const [allowRelated, setAllowRelated] = useState(false);
  const [allowLimited, setAllowLimited] = useState(false);

  const peerSymbols = useMemo(() => {
    return Array.from(
      new Set(
        draft
          .split(/[,+\s]+/)
          .map((s) => s.trim().toUpperCase())
          .filter((s) => s && s !== primary.toUpperCase()),
      ),
    ).slice(0, MAX_PEERS);
  }, [draft, primary]);

  const compareMutation = useMutation({
    mutationFn: async () => {
      if (peerSymbols.length < 1) {
        throw new Error("Add at least one peer ticker to compare.");
      }
      const { start, end } = defaultRange();
      const symbols = [primary, ...peerSymbols];
      const analyzed = await Promise.all(
        symbols.map(async (symbol) => {
          try {
            const res = await api.analyzeCompany(
              { symbol, start, end, as_decision_pack: true },
              { token },
            );
            return { symbol, reportId: res.payload?.report_id ?? null, error: null };
          } catch (err) {
            return { symbol, reportId: null, error: describeError(err) };
          }
        }),
      );

      const reportIds = analyzed
        .map((a) => a.reportId)
        .filter((id): id is string => Boolean(id));
      const failed = analyzed.filter((a) => !a.reportId);

      if (reportIds.length < 2) {
        throw new Error(
          `At least two Decision Pack reports are required for comparison — only ${reportIds.length} succeeded.`,
        );
      }

      const compared = await api.compare(
        {
          report_ids: reportIds,
          allow_related: allowRelated,
          allow_limited: allowLimited,
        },
        { token },
      );

      return {
        failed,
        result: (compared.result as ComparisonResultPayload | undefined) ?? null,
        ok: compared.ok,
        message: compared.message ?? null,
      };
    },
  });

  const result = compareMutation.data?.result ?? null;
  const report = result?.report ?? null;

  return (
    <div className="space-y-4">
      <SectionCard
        title="Peer Comparison"
        description="Reuses comparison.QualitativeComparisonEngine + industry.PeerEligibilityEvaluator via POST /compare — no client-side scoring."
      >
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label className="mb-1 block text-xs text-[var(--muted)]" htmlFor="peer-symbols">
              Peer tickers (comma-separated, up to {MAX_PEERS}) — compared against {primary}
            </label>
            <Input
              id="peer-symbols"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="e.g. ICICIBANK, KOTAKBANK"
              aria-label="Peer tickers"
            />
          </div>
          <Button
            size="sm"
            onClick={() => compareMutation.mutate()}
            disabled={compareMutation.isPending || peerSymbols.length === 0}
          >
            {compareMutation.isPending ? "Comparing…" : "Compare"}
          </Button>
        </div>
        <div className="mt-3 flex flex-wrap gap-4 text-xs">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={allowRelated}
              onChange={(e) => setAllowRelated(e.target.checked)}
            />
            Allow related peers
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={allowLimited}
              onChange={(e) => setAllowLimited(e.target.checked)}
            />
            Allow limited comparisons
          </label>
        </div>
        {peerSymbols.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-1">
            {[primary, ...peerSymbols].map((s) => (
              <Badge key={s} variant={s === primary ? "accent" : "outline"}>
                {s}
              </Badge>
            ))}
          </div>
        ) : null}
      </SectionCard>

      {compareMutation.isError ? (
        <SectionCard title="Comparison failed">
          <p className="text-sm text-[var(--danger-fg)]">
            {describeError(compareMutation.error)}
          </p>
        </SectionCard>
      ) : null}

      {compareMutation.data?.failed.length ? (
        <SectionCard title="Symbols that could not be analyzed">
          <ul className="list-disc space-y-1 pl-4 text-sm text-[var(--muted)]">
            {compareMutation.data.failed.map((f) => (
              <li key={f.symbol}>
                {f.symbol}: {f.error}
              </li>
            ))}
          </ul>
        </SectionCard>
      ) : null}

      {!compareMutation.isPending && !report ? (
        <WorkspaceEmpty description="Add peer tickers and run Compare to load the qualitative comparison report." />
      ) : null}

      {report ? (
        <>
          <SectionCard
            title="Comparison Result"
            description={report.explanation.summary}
          >
            <dl>
              <FieldRow label="Status" value={result?.status} />
              <FieldRow label="Methodology" value={report.methodology_id} />
              <FieldRow label="Industry" value={report.industry_id} />
              <FieldRow
                label="Included"
                value={report.included_symbols.join(", ") || null}
              />
              <FieldRow
                label="Excluded"
                value={report.excluded_symbols.join(", ") || null}
              />
              <FieldRow
                label="Eligibility group"
                value={report.eligibility_group_status}
              />
            </dl>
            {report.explanation.detail ? (
              <p className="mt-3 text-xs text-[var(--muted)]">
                {report.explanation.detail}
              </p>
            ) : null}
            {report.exclusion_reasons.length ? (
              <ul className="mt-3 list-disc space-y-1 pl-4 text-xs text-[var(--muted)]">
                {report.exclusion_reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            ) : null}
          </SectionCard>

          {report.dimension_results.map((dim) => (
            <SectionCard
              key={dim.dimension}
              title={dimensionLabel(dim.dimension)}
              description="Unweighted observations from the comparison engine — no scores."
            >
              {dim.observations.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {dim.observations.map((o) => (
                    <li key={o.code} className="border-b border-[var(--border)] pb-2 last:border-0">
                      <p>{o.text}</p>
                      {o.subjects.length ? (
                        <p className="mt-1 text-xs text-[var(--muted)]">
                          {o.subjects.join(", ")}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </SectionCard>
          ))}

          {report.shared_observations.length || report.pair_observations.length ? (
            <SectionCard title="Shared &amp; pairwise observations">
              <ul className="space-y-2 text-sm">
                {[...report.shared_observations, ...report.pair_observations].map(
                  (o) => (
                    <li key={o.code}>{o.text}</li>
                  ),
                )}
              </ul>
            </SectionCard>
          ) : null}

          {report.limitations.length ? (
            <SectionCard title="Limitations">
              <ul className="list-disc space-y-1 pl-4 text-sm text-[var(--muted)]">
                {report.limitations.map((l) => (
                  <li key={l.code}>{l.message}</li>
                ))}
              </ul>
            </SectionCard>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
