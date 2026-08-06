"use client";

/**
 * Institutional Company Workspace — News tab.
 *
 * Authenticated company news via the Data Connector Framework
 * (GET /api/v1/news) — tries every configured provider in priority order
 * (automatic failover) and shows real articles only. When no provider is
 * configured or reports data, this remains an honest "Data unavailable."
 * empty state, never mocked headlines.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { SectionCard, WorkspaceEmpty } from "../WorkspacePrimitives";

export function NewsSection({ view }: { view: ResearchView }) {
  const { session } = useAuth();
  const token = session?.accessToken ?? null;
  const symbol = view.ticker;

  const newsQuery = useQuery({
    queryKey: ["company-analysis", "news", symbol],
    queryFn: () => api.news(symbol, { token, limit: 20 }),
    enabled: Boolean(token && symbol),
    retry: false,
    staleTime: 60_000,
  });

  const payload = newsQuery.data;
  const articles = payload?.available && payload.authenticated ? payload.articles ?? [] : [];

  return (
    <div className="space-y-4">
      <SectionCard
        title={`News — ${view.company}`}
        description="Authenticated feed via GET /news — real articles only, never invented."
      >
        {newsQuery.isLoading ? <p className="text-sm text-[var(--muted)]">Loading…</p> : null}
        {newsQuery.isError ? (
          <p className="text-sm text-[var(--danger-fg)]">Data unavailable.</p>
        ) : null}
        {!newsQuery.isLoading && articles.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable — no data source connected." />
        ) : (
          <ul className="space-y-3 text-sm">
            {articles.map((a) => (
              <li
                key={a.article_id ?? a.url}
                className="border-b border-[var(--border)] pb-3 last:border-0"
              >
                <a
                  href={a.url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-[var(--fg)] hover:underline"
                >
                  {a.headline}
                </a>
                <p className="mt-1 text-xs text-[var(--muted)]">
                  {a.source}
                  {a.published_at ? ` · ${new Date(a.published_at).toLocaleString()}` : ""}
                  {a.sentiment ? ` · ${a.sentiment}` : ""}
                </p>
                {a.summary ? (
                  <p className="mt-1 text-sm text-[var(--muted)]">{a.summary}</p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}
