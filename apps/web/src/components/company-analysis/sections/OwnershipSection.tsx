"use client";

/**
 * Institutional Company Workspace — Ownership tab.
 *
 * Promoter holding, insider transactions, and institutional ownership are
 * backed by the Data Connector Framework (GET /api/v1/ownership and
 * GET /api/v1/insider-trading) — each tries every configured provider in
 * priority order (automatic failover). When no provider is configured or
 * reports data, this stays an honest, wired "Data unavailable." empty
 * state, never mocked data. Management-quality fields that *are* covered
 * (Capital Allocation, Governance) live under the Management tab and are
 * linked from here rather than duplicated.
 */

import { useQuery } from "@tanstack/react-query";

import { Button } from "@/components/ds";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useWorkspacePrefsStore } from "@/lib/company-analysis";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { FieldRow, SectionCard, WorkspaceEmpty } from "../WorkspacePrimitives";

const INSTITUTIONAL_HOLDER_TYPES = new Set([
  "institutional_domestic",
  "institutional_foreign",
  "mutual_fund",
]);

function formatPercent(value: number | null | undefined): string | null {
  if (value == null) return null;
  return `${value.toFixed(2)}%`;
}

export function OwnershipSection({ view }: { view: ResearchView }) {
  const setActiveSection = useWorkspacePrefsStore((s) => s.setActiveSection);
  const { session } = useAuth();
  const token = session?.accessToken ?? null;
  const symbol = view.ticker;

  const ownershipQuery = useQuery({
    queryKey: ["company-analysis", "ownership", symbol],
    queryFn: () => api.ownership(symbol, { token }),
    enabled: Boolean(token && symbol),
    retry: false,
    staleTime: 60_000,
  });

  const insiderQuery = useQuery({
    queryKey: ["company-analysis", "insider-trading", symbol],
    queryFn: () => api.insiderTrading(symbol, { token, limit: 20 }),
    enabled: Boolean(token && symbol),
    retry: false,
    staleTime: 60_000,
  });

  const ownership = ownershipQuery.data;
  const ownershipAvailable = Boolean(ownership?.available && ownership.authenticated);
  const stakes = ownershipAvailable ? ownership?.stakes ?? [] : [];
  const institutionalStakes = stakes.filter(
    (s) => s.holder_type && INSTITUTIONAL_HOLDER_TYPES.has(s.holder_type),
  );

  const insider = insiderQuery.data;
  const transactions =
    insider?.available && insider.authenticated ? insider.transactions ?? [] : [];

  return (
    <div className="space-y-4">
      <SectionCard
        title="Promoter Holding"
        description="Authenticated shareholding feed via GET /ownership — real holders only, never invented."
      >
        {ownershipQuery.isLoading ? (
          <p className="text-sm text-[var(--muted)]">Loading…</p>
        ) : null}
        {!ownershipQuery.isLoading && !ownershipAvailable ? (
          <WorkspaceEmpty description="Data unavailable — no data source connected." />
        ) : (
          <dl>
            <FieldRow
              label="Promoter holding"
              value={formatPercent(ownership?.promoter_holding_percent)}
            />
            <FieldRow label="As of" value={ownership?.as_of ?? null} />
            <FieldRow
              label="Source"
              value={ownership?.provenance?.provider_name ?? null}
            />
          </dl>
        )}
      </SectionCard>
      <SectionCard
        title="Insider Transactions"
        description="Authenticated insider trading feed via GET /insider-trading — real transactions only."
      >
        {insiderQuery.isLoading ? (
          <p className="text-sm text-[var(--muted)]">Loading…</p>
        ) : null}
        {!insiderQuery.isLoading && transactions.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable — no data source connected." />
        ) : (
          <ul className="space-y-2 text-sm">
            {transactions.map((t) => (
              <li
                key={t.transaction_id}
                className="border-b border-[var(--border)] pb-2 last:border-0"
              >
                <dl>
                  <FieldRow label="Insider" value={t.insider_name ?? null} />
                  <FieldRow label="Type" value={t.transaction_type ?? null} />
                  <FieldRow label="Date" value={t.transaction_date ?? null} />
                  <FieldRow
                    label="Shares"
                    value={t.shares != null ? String(t.shares) : null}
                  />
                  <FieldRow
                    label="Value"
                    value={t.value != null ? String(t.value) : null}
                  />
                </dl>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard
        title="Institutional Ownership"
        description="Authenticated shareholding feed via GET /ownership — real holders only."
      >
        {ownershipQuery.isLoading ? (
          <p className="text-sm text-[var(--muted)]">Loading…</p>
        ) : null}
        {!ownershipQuery.isLoading && institutionalStakes.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable — no data source connected." />
        ) : (
          <>
            <FieldRow
              label="Institutional holding"
              value={formatPercent(ownership?.institutional_holding_percent)}
            />
            <ul className="mt-2 space-y-1 text-sm">
              {institutionalStakes.map((s, i) => (
                <li
                  key={`${s.holder_type}-${s.holder_name ?? i}`}
                  className="flex justify-between gap-3"
                >
                  <span className="text-[var(--muted)]">
                    {s.holder_name ?? s.holder_type}
                  </span>
                  <span>{formatPercent(s.percent_held) ?? "Data unavailable."}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </SectionCard>
      <SectionCard
        title="Related — Management &amp; Governance"
        description={`Capital allocation and governance for ${view.company} are covered under Management — not duplicated here.`}
      >
        <Button size="sm" variant="secondary" onClick={() => setActiveSection("management")}>
          Open Management tab
        </Button>
      </SectionCard>
    </div>
  );
}
