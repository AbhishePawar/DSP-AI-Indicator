"use client";

/**
 * Institutional Company Workspace — Document Center tab.
 *
 * Corporate Actions (EPIC-D003, GET /corporate-actions), Filings (Data
 * Connector Framework, GET /filings), and Conference Call transcripts
 * (Data Connector Framework, GET /transcripts) are real authenticated
 * feeds — each tries every configured provider in priority order
 * (automatic failover). Honest "Data unavailable." empty states when no
 * provider is configured or reports data, never mocked documents.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { FieldRow, SectionCard, WorkspaceEmpty } from "../WorkspacePrimitives";

const REPORT_FILING_TYPES = new Set(["10-K", "annual_report"]);
const QUARTERLY_FILING_TYPES = new Set(["10-Q", "quarterly_report"]);
const PRESENTATION_FILING_TYPES = new Set(["investor_presentation"]);

export function DocumentsSection({ view }: { view: ResearchView }) {
  const { session } = useAuth();
  const token = session?.accessToken ?? null;
  const symbol = view.ticker;

  const corporateActionsQuery = useQuery({
    queryKey: ["company-analysis", "corporate-actions", symbol],
    queryFn: () => api.corporateActions(symbol, { token, limit: 20 }),
    enabled: Boolean(token && symbol),
    retry: false,
    staleTime: 60_000,
  });

  const filingsQuery = useQuery({
    queryKey: ["company-analysis", "filings", symbol],
    queryFn: () => api.filings(symbol, { token, limit: 50 }),
    enabled: Boolean(token && symbol),
    retry: false,
    staleTime: 60_000,
  });

  const transcriptsQuery = useQuery({
    queryKey: ["company-analysis", "transcripts", symbol],
    queryFn: () => api.transcripts(symbol, { token, limit: 8 }),
    enabled: Boolean(token && symbol),
    retry: false,
    staleTime: 60_000,
  });

  const corporateActionsPayload = corporateActionsQuery.data;
  const events =
    corporateActionsPayload?.available && corporateActionsPayload.authenticated
      ? corporateActionsPayload.events ?? []
      : [];

  const filingsPayload = filingsQuery.data;
  const filings =
    filingsPayload?.available && filingsPayload.authenticated
      ? filingsPayload.filings ?? []
      : [];
  const annualReports = filings.filter(
    (f) => f.filing_type && REPORT_FILING_TYPES.has(f.filing_type),
  );
  const quarterlyResults = filings.filter(
    (f) => f.filing_type && QUARTERLY_FILING_TYPES.has(f.filing_type),
  );
  const presentations = filings.filter(
    (f) => f.filing_type && PRESENTATION_FILING_TYPES.has(f.filing_type),
  );

  const transcriptsPayload = transcriptsQuery.data;
  const transcripts =
    transcriptsPayload?.available && transcriptsPayload.authenticated
      ? transcriptsPayload.transcripts ?? []
      : [];

  return (
    <div className="space-y-4">
      <SectionCard
        title="Corporate Actions"
        description="EPIC-D003 authenticated feed via GET /corporate-actions — real events only, never invented."
      >
        {corporateActionsQuery.isLoading ? (
          <p className="text-sm text-[var(--muted)]">Loading…</p>
        ) : null}
        {corporateActionsQuery.isError ? (
          <p className="text-sm text-[var(--danger-fg)]">Data unavailable.</p>
        ) : null}
        {!corporateActionsQuery.isLoading && events.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {events.map((e) => (
              <li
                key={e.action_id ?? `${e.action_type}-${e.effective_date}`}
                className="border-b border-[var(--border)] pb-2 last:border-0"
              >
                <dl>
                  <FieldRow label="Type" value={e.action_type} />
                  <FieldRow label="Description" value={e.description} />
                  <FieldRow label="Effective date" value={e.effective_date} />
                  <FieldRow label="Ex date" value={e.ex_date} />
                  <FieldRow
                    label="Amount"
                    value={e.amount != null ? `${e.amount} ${e.currency ?? ""}`.trim() : null}
                  />
                </dl>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <FilingListCard
        title="Annual Reports"
        description="Authenticated filings feed via GET /filings — real documents only."
        isLoading={filingsQuery.isLoading}
        filings={annualReports}
      />
      <FilingListCard
        title="Quarterly Results"
        description="Authenticated filings feed via GET /filings — real documents only."
        isLoading={filingsQuery.isLoading}
        filings={quarterlyResults}
      />
      <FilingListCard
        title="Investor Presentations"
        description="Authenticated filings feed via GET /filings — real documents only."
        isLoading={filingsQuery.isLoading}
        filings={presentations}
      />

      <SectionCard
        title="Conference Calls"
        description="Authenticated earnings call transcript feed via GET /transcripts — real content only."
      >
        {transcriptsQuery.isLoading ? (
          <p className="text-sm text-[var(--muted)]">Loading…</p>
        ) : null}
        {!transcriptsQuery.isLoading && transcripts.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable — no filings/documents data source connected." />
        ) : (
          <ul className="space-y-2 text-sm">
            {transcripts.map((t) => (
              <li
                key={t.transcript_id}
                className="border-b border-[var(--border)] pb-2 last:border-0"
              >
                {t.url ? (
                  <a
                    href={t.url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium text-[var(--fg)] hover:underline"
                  >
                    {t.title}
                  </a>
                ) : (
                  <span className="font-medium text-[var(--fg)]">{t.title}</span>
                )}
                <p className="mt-1 text-xs text-[var(--muted)]">{t.call_date ?? ""}</p>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}

function FilingListCard({
  title,
  description,
  isLoading,
  filings,
}: {
  title: string;
  description: string;
  isLoading: boolean;
  filings: NonNullable<
    import("@/lib/api/client").FilingsPayload["filings"]
  >;
}) {
  return (
    <SectionCard title={title} description={description}>
      {isLoading ? <p className="text-sm text-[var(--muted)]">Loading…</p> : null}
      {!isLoading && filings.length === 0 ? (
        <WorkspaceEmpty description="Data unavailable — no filings/documents data source connected." />
      ) : (
        <ul className="space-y-2 text-sm">
          {filings.map((f) => (
            <li key={f.filing_id} className="border-b border-[var(--border)] pb-2 last:border-0">
              <a
                href={f.url}
                target="_blank"
                rel="noreferrer"
                className="font-medium text-[var(--fg)] hover:underline"
              >
                {f.title}
              </a>
              <p className="mt-1 text-xs text-[var(--muted)]">{f.filed_at}</p>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
