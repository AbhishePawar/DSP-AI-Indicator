"use client";

/**
 * Company Directory — search plus sector and DSP rating filters.
 * Analysed companies come from /coverage/directory. A ticker search also
 * asks Security Master. Missing price, change, sector, or rating stays
 * "Data unavailable." Demo catalogues are not used.
 */

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { FigmaPage } from "@/components/pages/PagePrimitives";
import { api } from "@/lib/api/client";
import type { DirectoryItem } from "@/lib/api/workspaceTypes";
import {
  loadRecentAnalyses,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";
import { useAuth } from "@/lib/auth/AuthProvider";
import { analysisPath, type SecurityListingView } from "@/lib/securities/identity";

const UNAVAILABLE = "Data unavailable.";
const NO_DIRECTORY_ITEMS: DirectoryItem[] = [];

function showNumber(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return UNAVAILABLE;
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function showChange(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return UNAVAILABLE;
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}%`;
}

export default function CompaniesPage() {
  const router = useRouter();
  const { session } = useAuth();
  const token = session?.accessToken;
  const [search, setSearch] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [sector, setSector] = useState("all");
  const [rating, setRating] = useState("all");
  const [recent, setRecent] = useState<RecentAnalysisEntry[]>([]);

  useEffect(() => {
    setRecent(loadRecentAnalyses());
  }, []);

  const directoryQuery = useQuery({
    queryKey: ["coverage", "directory", sector, rating, submitted],
    queryFn: () =>
      api.coverageDirectory({
        token,
        sector: sector === "all" ? null : sector,
        rating: rating === "all" ? null : rating,
        q: submitted || null,
        limit: 48,
      }),
    enabled: Boolean(token),
    retry: false,
  });

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

  function resetFilters() {
    setSearch("");
    setSubmitted("");
    setSector("all");
    setRating("all");
  }

  const directoryItems = directoryQuery.data?.items ?? NO_DIRECTORY_ITEMS;
  const sectors = directoryQuery.data?.sectors ?? [];
  const ratings = directoryQuery.data?.ratings ?? [];
  const covered = useMemo(
    () => new Set(directoryItems.map((item) => item.symbol.toUpperCase())),
    [directoryItems],
  );
  const listings =
    searchQuery.data?.status === "MATCHES"
      ? searchQuery.data.results.filter((listing) => !covered.has(listing.ticker.toUpperCase()))
      : [];
  const filtersActive = sector !== "all" || rating !== "all" || submitted.length > 0;

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
        <label className="sr-only" htmlFor="company-directory-sector">
          Sector
        </label>
        <select
          id="company-directory-sector"
          aria-label="Sector"
          value={sector}
          onChange={(event) => setSector(event.currentTarget.value)}
          disabled={!token}
          className="min-h-11 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 font-[family-name:var(--font-mono)] text-[13px] text-[var(--fg)] disabled:cursor-not-allowed disabled:text-[var(--muted)]"
        >
          <option value="all">All sectors</option>
          {sectors.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        <label className="sr-only" htmlFor="company-directory-rating">
          DSP rating
        </label>
        <select
          id="company-directory-rating"
          aria-label="DSP rating"
          value={rating}
          onChange={(event) => setRating(event.currentTarget.value)}
          disabled={!token}
          className="min-h-11 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 font-[family-name:var(--font-mono)] text-[13px] text-[var(--fg)] disabled:cursor-not-allowed disabled:text-[var(--muted)]"
        >
          <option value="all">All ratings</option>
          {ratings.map((grade) => (
            <option key={grade} value={grade}>
              {grade}
            </option>
          ))}
        </select>
        <button type="submit" className="min-h-11 rounded-lg bg-[var(--c-dsp)] px-4 text-sm text-white">
          Search
        </button>
        <button
          type="button"
          onClick={resetFilters}
          className="min-h-11 rounded-lg border border-[var(--border)] px-4 text-sm text-[var(--fg)]"
        >
          Reset
        </button>
        <span className="font-[family-name:var(--font-mono)] text-xs text-[var(--muted)]">
          {token
            ? `${directoryItems.length + listings.length} results`
            : "Sign in to search"}
        </span>
      </form>
      <p className="m-0 text-xs text-[var(--muted)]">
        Sector, rating, price, and market cap come from recorded analyses. A field that was not published shows Data unavailable.
      </p>

      {!token ? (
        <p className="text-sm text-[var(--muted)]">
          Sign in to search the Security Master and the analysed-company directory.
        </p>
      ) : null}

      {directoryQuery.isError || searchQuery.isError ? (
        <p className="text-sm text-[var(--muted)]" role="alert">
          {UNAVAILABLE}
        </p>
      ) : null}

      {directoryQuery.isFetching || searchQuery.isFetching ? (
        <p className="text-sm text-[var(--muted)]" role="status">
          Searching…
        </p>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {directoryItems.map((item) => (
          <CoverageCard
            key={`${item.symbol}-${item.exchange ?? "listing"}`}
            item={item}
            onOpen={() => {
              const params = new URLSearchParams({ symbol: item.symbol });
              if (item.exchange) params.set("exchange", item.exchange);
              router.push(`/analysis?${params.toString()}`);
            }}
          />
        ))}
        {listings.map((listing) => (
          <DirectoryCard
            key={`${listing.isin}-${listing.mic}-${listing.ticker}`}
            listing={listing}
            onOpen={() => router.push(analysisPath(listing))}
          />
        ))}
      </div>

      {token && !directoryQuery.isFetching && !searchQuery.isFetching && directoryItems.length === 0 && listings.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">
          {filtersActive
            ? "No listings matched this search and these filters."
            : "No analysed companies are on record yet."}
        </p>
      ) : null}

      {!submitted && recent.length > 0 ? (
        <section>
          <p className="section-label">Recent research</p>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {recent.slice(0, 6).map((entry) => (
              <button
                key={`${entry.ticker}-${entry.analysedAt}`}
                type="button"
                onClick={() => router.push(`/analysis?symbol=${encodeURIComponent(entry.ticker)}`)}
                className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-4 text-left hover:border-[color-mix(in_srgb,var(--c-dsp)_40%,transparent)]"
              >
                <div className="font-[family-name:var(--font-mono)] text-[15px] font-bold text-[var(--fg)]">
                  {entry.ticker}
                </div>
                <div className="mt-1 text-xs text-[var(--muted)]">{entry.company || UNAVAILABLE}</div>
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

function CoverageCard({ item, onOpen }: { item: DirectoryItem; onOpen: () => void }) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-[18px] py-4 text-left hover:border-[color-mix(in_srgb,var(--c-dsp)_40%,transparent)]"
    >
      <div className="mb-2.5 flex items-start justify-between gap-2">
        <div>
          <div className="font-[family-name:var(--font-mono)] text-[15px] font-bold text-[var(--fg)]">
            {item.symbol}
          </div>
          <div className="mt-0.5 text-xs leading-snug text-[var(--muted)]">
            {item.company_name || UNAVAILABLE}
          </div>
        </div>
        <span className="shrink-0 rounded-md bg-[color-mix(in_srgb,var(--c-dsp)_12%,transparent)] px-2 py-0.5 font-[family-name:var(--font-mono)] text-[11px] font-semibold text-[var(--fg)]">
          {item.rating || UNAVAILABLE}
        </span>
      </div>
      <div className="mb-2 text-xs text-[var(--muted)]">{item.sector || UNAVAILABLE}</div>
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="font-[family-name:var(--font-mono)] text-base text-[var(--fg)]">
            {showNumber(item.price)}
          </div>
          <div className="font-[family-name:var(--font-mono)] text-xs text-[var(--muted)]">
            {showChange(item.change_percent)}
          </div>
        </div>
        <div className="text-right">
          <div className="font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-wide text-[var(--muted)]">
            Market cap
          </div>
          <div className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)]">
            {showNumber(item.market_cap)}
          </div>
        </div>
      </div>
    </button>
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
      <div className="mb-2 text-xs text-[var(--muted)]">{UNAVAILABLE}</div>
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
