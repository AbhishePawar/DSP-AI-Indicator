"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { searchCatalogue } from "@/lib/companies/catalogue";

export function CompanySearchHero() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const suggestions = query.trim() ? searchCatalogue(query).slice(0, 4) : [];

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const match = suggestions[0];
    if (match) {
      router.push(`/analysis?symbol=${encodeURIComponent(match.ticker)}`);
      return;
    }
    router.push(`/companies?query=${encodeURIComponent(query.trim())}`);
  }

  return (
    <div className="max-w-2xl">
      <form onSubmit={submit} role="search" className="relative flex items-center">
        <label htmlFor="marketing-company-search" className="sr-only">
          Search for a company
        </label>
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute left-4 text-[var(--muted)]"
          data-icon="inline-start"
        />
        <input
          id="marketing-company-search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search a company or ticker"
          autoComplete="off"
          className="min-h-14 w-full rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] py-3 pl-12 pr-28 text-base text-[var(--fg)] shadow-[var(--shadow-md)] outline-none transition-[border-color,box-shadow] placeholder:text-[var(--muted)] focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)]"
        />
        <button
          type="submit"
          className="absolute right-2 inline-flex min-h-10 items-center rounded-[var(--radius-sm)] bg-[var(--accent)] px-4 text-sm font-medium text-[var(--accent-fg)] transition-opacity hover:opacity-85 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!query.trim()}
        >
          Research
        </button>
      </form>

      {suggestions.length > 0 ? (
        <ul
          aria-label="Company suggestions"
          className="mt-2 grid gap-1 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-1 shadow-[var(--shadow-md)]"
        >
          {suggestions.map((company) => (
            <li key={company.ticker}>
              <button
                type="button"
                onClick={() => router.push(`/analysis?symbol=${encodeURIComponent(company.ticker)}`)}
                className="flex min-h-11 w-full items-center justify-between rounded-[var(--radius-sm)] px-3 text-left text-sm text-[var(--fg)] transition-colors hover:bg-[var(--surface-2)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--accent)]"
              >
                <span>{company.name}</span>
                <span className="font-mono text-xs text-[var(--muted)]">{company.ticker}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      <p className="mt-3 text-xs leading-relaxed text-[var(--muted)]">
        Start with a company name or ticker. Research Mode keeps evidence, calculation, and interpretation distinct.
      </p>
    </div>
  );
}
