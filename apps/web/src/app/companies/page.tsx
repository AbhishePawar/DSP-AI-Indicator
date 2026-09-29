"use client";

/**
 * Figma Make `CompanyDirectory.tsx` — search, filters, card grid.
 * Results come from Security Master search. Price, rating, sector, and
 * market cap stay "Data unavailable." unless a later authenticated feed
 * supplies them. The Figma TCS/INFY demo catalogue is not used.
 */

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { FigmaPage } from "@/components/pages/PagePrimitives";
import { api } from "@/lib/api/client";
import {
  loadRecentAnalyses,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";
import { useAuth } from "@/lib/auth/AuthProvider";
import { analysisPath, type SecurityListingView } from "@/lib/securities/identity";

const UNAVAILABLE = "Data unavailable.";

export default function CompaniesPage() {
  const router = useRouter();
  const { session } = useAuth();
  const token = session?.accessToken;
  const [search, setSearch] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [recent, setRecent] = useState<RecentAnalysisEntry[]>([]);

  useEffect(() => {
    setRecent(loadRecentAnalyses());
  }, []);

  const searchQuery = useQuery({
    queryKey: ["companies", "search", submitted],
    queryFn: () => api.searchSecurities(submitted, { token, limit: 24 }),
    enabled: Boolean(token && submitted.trim().length >= 2),
    retry: false,
  });

  function onSearch(event: FormEvent) {
    event.preventDefault();
    setSubmitted(search.trim());
  }

  const results = searchQuery.data?.status === "MATCHES" ? searchQuery.data.results : [];

  return (
    <FigmaPage title="Company Directory" subtitle="Discover and search listed securities">
      <form onSubmit={onSearch} className="flex flex-wrap items-center gap-2.5">
        <label className="sr-only" htmlFor="company-directory-query">
          Search by name or ticker
        </label>
        <input
          id="company-directory-query"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search by name or ticker..."
          className="min-h-11 min-w-[240px] flex-1 rounded-[10px] border border-[var(--border)] bg-[var(--card)] px-3.5 text-sm text-[var(--fg)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--c-dsp)]"
        />
        <button
          type="submit"
          className="min-h-11 rounded-lg bg-[var(--c-dsp)] px-4 text-sm text-white"
        >
          Search
        </button>
        <span className="font-[family-name:var(--font-mono)] text-xs text-[var(--muted)]">
          {submitted ? `${results.length} results` : "Enter a name or ticker"}
        </span>
      </form>

      {!token ? (
        <p className="text-sm text-[var(--muted)]">
          Sign in to search the Security Master. No directory prices are shown until a listing is identified.
        </p>
      ) : null}

      {searchQuery.isError ? (
        <p className="text-sm text-[var(--muted)]">{UNAVAILABLE}</p>
      ) : null}

      {searchQuery.isFetching ? (
        <p className="text-sm text-[var(--muted)]" role="status">
          Searching…
        </p>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {results.map((listing) => (
          <DirectoryCard
            key={`${listing.isin}-${listing.mic}-${listing.ticker}`}
            listing={listing}
            onOpen={() => router.push(analysisPath(listing))}
          />
        ))}
      </div>

      {!submitted && recent.length > 0 ? (
        <section>
          <p className="section-label">Recent research</p>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {recent.slice(0, 6).map((entry) => (
              <button
                key={`${entry.ticker}-${entry.analysedAt}`}
                type="button"
                onClick={() =>
                  router.push(`/analysis?symbol=${encodeURIComponent(entry.ticker)}`)
                }
                className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-4 text-left hover:border-[color-mix(in_srgb,var(--c-dsp)_40%,transparent)]"
              >
                <div className="font-[family-name:var(--font-mono)] text-[15px] font-bold text-[var(--fg)]">
                  {entry.ticker}
                </div>
                <div className="mt-1 text-xs text-[var(--muted)]">
                  {entry.company || UNAVAILABLE}
                </div>
                <div className="mt-3 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-wide text-[var(--muted)]">
                  {entry.exchange || UNAVAILABLE}
                </div>
              </button>
            ))}
          </div>
        </section>
      ) : null}
    </FigmaPage>
  );
}

function DirectoryCard({
  listing,
  onOpen,
}: {
  listing: SecurityListingView;
  onOpen: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-[18px] py-4 text-left hover:border-[color-mix(in_srgb,var(--c-dsp)_40%,transparent)]"
    >
      <div className="mb-2.5 flex items-start justify-between gap-2">
        <div>
          <div className="font-[family-name:var(--font-mono)] text-[15px] font-bold text-[var(--fg)]">
            {listing.ticker}
          </div>
          <div className="mt-0.5 text-xs leading-snug text-[var(--muted)]">
            {listing.company_name || UNAVAILABLE}
          </div>
        </div>
        <span className="shrink-0 rounded-md bg-[color-mix(in_srgb,var(--c-dsp)_12%,transparent)] px-2 py-0.5 font-[family-name:var(--font-mono)] text-[11px] font-semibold text-[var(--muted)]">
          {UNAVAILABLE}
        </span>
      </div>
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="font-[family-name:var(--font-mono)] text-base text-[var(--muted)]">
            {UNAVAILABLE}
          </div>
          <div className="font-[family-name:var(--font-mono)] text-xs text-[var(--muted)]">
            {listing.exchange || UNAVAILABLE}
          </div>
        </div>
        <div className="text-right">
          <div className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-wide text-[var(--muted)]">
            {listing.mic || UNAVAILABLE}
          </div>
          <div className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)]">
            {listing.isin || UNAVAILABLE}
          </div>
        </div>
      </div>
    </button>
  );
}
