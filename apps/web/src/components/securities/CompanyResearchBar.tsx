"use client";

/**
 * Canonical client-facing Company Research search.
 * Thin client: GET /api/v1/securities/search → select ISIN+MIC → /analysis.
 * Does not calculate WACC/DCF. Does not invent listings.
 */

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

import { Input } from "@/components/ds";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useDashboardPrefsStore } from "@/lib/dashboard";
import {
  analysisPath,
  type SecurityListingView,
} from "@/lib/securities/identity";
import { cn } from "@/lib/utils";

const DEBOUNCE_MS = 200;
const SEARCH_LIMIT = 8;

export function CompanyResearchBar({
  variant = "hero",
  query: controlledQuery,
  onQueryChange,
  onSelect,
  className,
}: {
  variant?: "hero" | "compact";
  query?: string;
  onQueryChange?: (value: string) => void;
  onSelect?: (listing: SecurityListingView) => void;
  className?: string;
}) {
  const router = useRouter();
  const { session } = useAuth();
  const token = session?.accessToken;
  const recordSearch = useDashboardPrefsStore((s) => s.recordSearch);
  const listId = useId();
  const inputId = useId();
  const [uncontrolled, setUncontrolled] = useState("");
  const query = controlledQuery ?? uncontrolled;
  const setQuery = onQueryChange ?? setUncontrolled;
  const [results, setResults] = useState<SecurityListingView[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const generation = useRef(0);
  const listRef = useRef<HTMLUListElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const q = query.trim();
    if (!q) {
      generation.current += 1;
      setResults([]);
      setStatus(null);
      setError(null);
      setSearching(false);
      setOpen(false);
      return;
    }
    if (!token) {
      setResults([]);
      setStatus("Sign in required for Security Master search.");
      setError(null);
      setSearching(false);
      setOpen(document.activeElement === inputRef.current);
      return;
    }
    const handle = window.setTimeout(() => {
      const gen = ++generation.current;
      setSearching(true);
      setError(null);
      void api
        .searchSecurities(q, { token, limit: SEARCH_LIMIT })
        .then((payload) => {
          if (gen !== generation.current) return;
          const rows = payload.results ?? [];
          setResults(rows);
          setStatus(payload.status === "MATCHES" ? null : payload.status || null);
          setOpen(document.activeElement === inputRef.current);
          setActiveIndex(0);
        })
        .catch(() => {
          if (gen !== generation.current) return;
          setResults([]);
          setStatus(null);
          setError("Search failed. Check the connection and retry.");
          setOpen(true);
        })
        .finally(() => {
          if (gen !== generation.current) return;
          setSearching(false);
        });
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(handle);
  }, [query, token]);

  const selectListing = useCallback(
    (listing: SecurityListingView) => {
      recordSearch(listing.ticker);
      setOpen(false);
      if (onSelect) {
        onSelect(listing);
        return;
      }
      router.push(analysisPath(listing));
    },
    [onSelect, recordSearch, router],
  );

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      return;
    }
    if (!open) {
      if (event.key === "ArrowDown" && (results.length || status || error)) {
        event.preventDefault();
        setOpen(true);
      }
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, Math.max(results.length - 1, 0)));
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      const chosen = results[activeIndex] ?? (results.length === 1 ? results[0] : null);
      if (chosen) selectListing(chosen);
    }
  }

  const hero = variant === "hero";
  const expanded = open && Boolean(query.trim());

  return (
    <section
      className={cn(
        hero
          ? "mx-auto w-full max-w-3xl rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-6"
          : "w-full",
        className,
      )}
      aria-label="Company Research"
    >
      {hero ? (
        <div className="mb-4 text-center">
          <h2 className="font-[family-name:var(--font-display)] text-xl font-medium tracking-tight sm:text-2xl">
            Company Research
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Search a company or ticker, then select the official listing.
          </p>
        </div>
      ) : (
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Company Research
        </p>
      )}
      <div className="relative z-20">
        <label htmlFor={inputId} className="sr-only">
          Company search
        </label>
        <div className="relative">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted)]"
            aria-hidden
          />
          <Input
            ref={inputRef}
            id={inputId}
            type="search"
            role="combobox"
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            onFocus={() => {
              if (query.trim() && (results.length || status || error || searching)) {
                setOpen(true);
              }
            }}
            placeholder="Search company / ticker…"
            aria-label="Company search"
            aria-autocomplete="list"
            aria-expanded={expanded}
            aria-controls={listId}
            aria-activedescendant={
              expanded && results[activeIndex]
                ? `${listId}-opt-${activeIndex}`
                : undefined
            }
            className="min-h-11 pl-9"
          />
        </div>
        {expanded ? (
          <div
            className="absolute left-0 right-0 mt-1 max-h-72 overflow-y-auto rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-md,0_8px_24px_rgba(0,0,0,0.12))]"
            role="status"
          >
            {searching ? (
              <p className="px-3 py-2 text-sm text-[var(--muted)]">Searching…</p>
            ) : null}
            {error ? (
              <p className="px-3 py-2 text-sm text-[var(--danger,var(--muted))]" role="alert">
                {error}
              </p>
            ) : null}
            {!searching && !error && status ? (
              <p className="px-3 py-2 text-sm text-[var(--muted)]">
                {statusLabel(status)}
              </p>
            ) : null}
            <ul
              id={listId}
              ref={listRef}
              role="listbox"
              aria-label="Security Master results"
            >
              {results.map((row, index) => (
                <li
                  key={row.listing_id || `${row.isin}.${row.mic}`}
                  id={`${listId}-opt-${index}`}
                  role="option"
                  aria-selected={index === activeIndex}
                >
                  <button
                    type="button"
                    className={cn(
                      "w-full px-3 py-2.5 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent)]",
                      index === activeIndex
                        ? "bg-[var(--accent-soft)]"
                        : "hover:bg-[var(--surface-2)]",
                    )}
                    onMouseDown={(event) => event.preventDefault()}
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => selectListing(row)}
                  >
                    <span className="font-medium">{row.ticker}</span>
                    <span className="ml-2 text-[var(--muted)]">
                      {row.company_name} · {row.exchange} · {row.isin} ·{" "}
                      {row.mic}
                      {row.security_type ? ` · ${row.security_type}` : ""}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function statusLabel(status: string): string {
  switch (status) {
    case "UNKNOWN":
      return "No matching company. The platform does not invent a security.";
    case "UNSUPPORTED":
      return "UNSUPPORTED — this instrument is outside ordinary-equity analysis.";
    case "REJECTED":
      return "REJECTED — the query is not a valid Security Master lookup.";
    case "AMBIGUOUS":
      return "Multiple listings matched. Select ISIN + exchange to continue.";
    default:
      return status;
  }
}
