"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { ErrorState } from "@/components/ds";
import { api } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import { analysisPath } from "@/lib/securities/identity";

const TYPE_COLOR: Record<string, string> = {
  upgrade: "var(--c-profit)",
  downgrade: "var(--c-risk)",
  risk: "var(--c-risk)",
  valuation: "var(--c-valuation)",
};

export function FigmaSignalFeed() {
  const [sector, setSector] = useState("All");
  const query = useQuery({
    queryKey: ["coverage-signals", sector],
    queryFn: () =>
      api.coverageSignals({
        limit: 24,
        sector: sector === "All" ? null : sector,
      }),
  });

  const sectors = useMemo(() => {
    const fromApi = query.data?.sectors?.filter(Boolean) ?? [];
    if (fromApi.length > 0) return ["All", ...fromApi];
    const found = new Set<string>();
    for (const signal of query.data?.signals ?? []) {
      if (signal.sector) found.add(signal.sector);
    }
    return ["All", ...found];
  }, [query.data?.sectors, query.data?.signals]);

  const today = query.data?.today;

  return (
    <section aria-labelledby="ri-feed-title" className="space-y-4">
      <header>
        <h2
          id="ri-feed-title"
          className="font-[family-name:var(--font-heading)] text-2xl font-medium text-[var(--fg)]"
        >
          Research Intelligence
        </h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Signals returned by the coverage service.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Summary label="New signals" value={today?.new_signals} loading={query.isLoading} />
        <Summary label="Upgrades" value={today?.upgrades} loading={query.isLoading} />
        <Summary label="Downgrades" value={today?.downgrades} loading={query.isLoading} />
        <Summary label="Risk flags" value={today?.risk_flags} loading={query.isLoading} />
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {sectors.map((item) => (
          <button
            key={item}
            type="button"
            aria-pressed={sector === item}
            onClick={() => setSector(item)}
            className={`min-h-11 shrink-0 rounded-full border px-3 text-xs ${
              sector === item
                ? "border-[var(--fg)] bg-[var(--fg)] text-[var(--bg)]"
                : "border-[var(--border)] text-[var(--muted)]"
            }`}
          >
            {item}
          </button>
        ))}
      </div>

      {query.isLoading ? <p className="text-sm text-[var(--muted)]">Loading signals…</p> : null}
      {query.isError ? (
        <ErrorState
          title="Signals unavailable"
          description={
            query.error instanceof ApiClientError
              ? query.error.message
              : "The coverage service did not respond."
          }
        />
      ) : null}
      {!query.isLoading && !query.isError && (query.data?.signals.length ?? 0) === 0 ? (
        <p className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 text-sm text-[var(--muted)]">
          Data unavailable.
        </p>
      ) : null}
      <ul className="space-y-3">
        {(query.data?.signals ?? []).map((signal) => {
          const href = signal.symbol
            ? analysisPath({ ticker: signal.symbol })
            : null;
          return (
            <li
              key={signal.signal_id}
              className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ background: TYPE_COLOR[signal.type] ?? "var(--muted)" }}
                  aria-hidden
                />
                <span className="font-mono text-xs text-[var(--fg)]">{signal.symbol}</span>
                <span className="text-xs text-[var(--muted)]">{signal.label}</span>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-[var(--fg)]">{signal.text}</p>
              {href ? (
                <Link href={href} className="mt-3 inline-flex min-h-11 items-center text-sm text-[var(--accent)]">
                  Open analysis
                </Link>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function Summary({
  label,
  value,
  loading,
}: {
  label: string;
  value: number | undefined;
  loading: boolean;
}) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <p className="text-xs text-[var(--muted)]">{label}</p>
      <p className="mt-1 font-mono text-lg text-[var(--fg)]">
        {loading ? "…" : value == null ? "Data unavailable." : value}
      </p>
    </div>
  );
}
