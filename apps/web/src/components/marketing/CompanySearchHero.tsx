"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { api, type SecuritySearchResult } from "@/lib/api/client";

function resultItems(
  response:
  | SecuritySearchResult[]
  | { results?: SecuritySearchResult[]; securities?: SecuritySearchResult[]; data?: SecuritySearchResult[]; payload?: SecuritySearchResult[] },
): SecuritySearchResult[] {
  if (Array.isArray(response)) return response;
  return response.results ?? response.securities ?? response.data ?? response.payload ?? [];
}

function resultSymbol(result: SecuritySearchResult) {
  return result.symbol ?? result.ticker ?? "";
}

export function CompanySearchHero() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SecuritySearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setResults([]);
      setError(false);
      return;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      setIsLoading(true);
      setError(false);
      try {
        const response = await api.searchSecurities(trimmedQuery, { signal: controller.signal });
        setResults(resultItems(response).filter((result) => resultSymbol(result)));
      } catch (searchError) {
        if (!(searchError instanceof DOMException && searchError.name === "AbortError")) {
          setResults([]);
          setError(true);
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    }, 300);

    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [query]);

  function selectResult(result: SecuritySearchResult) {
    const symbol = resultSymbol(result);
    if (!symbol) return;

    const params = new URLSearchParams({ symbol });
    const company = result.company_name ?? result.name;
    if (company) params.set("company", company);
    if (result.exchange) params.set("exchange", result.exchange);
    if (result.isin) params.set("isin", result.isin);
    router.push(`/analysis?${params.toString()}`);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (results[0]) selectResult(results[0]);
  }

  const hasQuery = query.trim().length > 0;

  return (
    <div className="max-w-2xl">
      <form onSubmit={submit} role="search" className="relative flex items-center">
        <label htmlFor="marketing-company-search" className="sr-only">Search for a company</label>
        <Search aria-hidden="true" className="pointer-events-none absolute left-4 text-[var(--muted)]" data-icon="inline-start" />
        <input
          id="marketing-company-search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by company name, ticker or ISIN"
          autoComplete="off"
          className="min-h-14 w-full rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] py-3 pl-12 pr-28 text-base text-[var(--fg)] shadow-[var(--shadow-md)] outline-none transition-[border-color,box-shadow] placeholder:text-[var(--muted)] focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)]"
          aria-expanded={hasQuery && !isLoading}
          aria-controls="company-search-results"
        />
        <button type="submit" className="absolute right-2 inline-flex min-h-10 items-center rounded-[var(--radius-sm)] bg-[var(--accent)] px-4 text-sm font-medium text-[var(--accent-fg)] transition-opacity hover:opacity-85 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50" disabled={!results[0] || isLoading}>
          Research
        </button>
      </form>

      {isLoading ? <p className="mt-3 text-sm text-[var(--muted)]" role="status">Searching securities…</p> : null}
      {error ? <p className="mt-3 text-sm text-[var(--muted)]" role="alert">Unable to search right now. Please try again.</p> : null}
      {!isLoading && !error && hasQuery && results.length === 0 ? <p className="mt-3 text-sm text-[var(--muted)]">No matching companies found.</p> : null}

      {!isLoading && results.length > 0 ? (
        <ul id="company-search-results" aria-label="Company search results" className="mt-2 grid gap-1 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-1 shadow-[var(--shadow-md)]">
          {results.slice(0, 6).map((result, index) => {
            const symbol = resultSymbol(result);
            const name = result.company_name ?? result.name;
            return (
              <li key={`${symbol}-${result.isin ?? index}`}>
                <button type="button" onClick={() => selectResult(result)} className="flex min-h-14 w-full items-center justify-between gap-4 rounded-[var(--radius-sm)] px-3 text-left text-sm text-[var(--fg)] transition-colors hover:bg-[var(--surface-2)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--accent)]">
                  <span className="min-w-0"><span className="block truncate font-medium">{name ?? symbol}</span><span className="block truncate text-xs text-[var(--muted)]">{[result.exchange, result.mic, result.isin].filter(Boolean).join(" · ")}</span></span>
                  <span className="shrink-0 font-mono text-xs text-[var(--muted)]">{symbol}</span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}

      <p className="mt-3 text-xs leading-relaxed text-[var(--muted)]">Search the live security universe by company name, ticker, or ISIN. Research Mode keeps evidence, calculation, and interpretation distinct.</p>
    </div>
  );
}
