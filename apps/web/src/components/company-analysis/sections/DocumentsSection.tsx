"use client";

/**
 * Institutional Company Workspace — Document Center tab.
 *
 * Corporate Actions is real (EPIC-D003, GET /corporate-actions, newly
 * mounted). Annual Reports / Quarterly Results / Investor Presentations /
 * Conference Calls have no connected filings/document data source anywhere
 * in the platform — honest "Data unavailable." empty states, not mocked data.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { FieldRow, SectionCard, WorkspaceEmpty } from "../WorkspacePrimitives";

function DocumentPlaceholder({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <SectionCard title={title}>
      <WorkspaceEmpty description={description} />
    </SectionCard>
  );
}

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

  const payload = corporateActionsQuery.data;
  const events = payload?.available && payload.authenticated ? payload.events ?? [] : [];

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

      <DocumentPlaceholder
        title="Annual Reports"
        description="Data unavailable — no filings/documents data source connected."
      />
      <DocumentPlaceholder
        title="Quarterly Results"
        description="Data unavailable — no filings/documents data source connected."
      />
      <DocumentPlaceholder
        title="Investor Presentations"
        description="Data unavailable — no filings/documents data source connected."
      />
      <DocumentPlaceholder
        title="Conference Calls"
        description="Data unavailable — no filings/documents data source connected."
      />
    </div>
  );
}
