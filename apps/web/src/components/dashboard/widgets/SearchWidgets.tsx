"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent, type KeyboardEvent } from "react";

import { Button, SearchBox } from "@/components/ds";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useDashboardPrefsStore } from "@/lib/dashboard";
import {
  analysisPath,
  type SecurityListingView,
} from "@/lib/securities/identity";
import { useUiStore } from "@/lib/shell";
import { DashboardWidgetShell } from "../DashboardWidgetShell";

export function CompanySearchWidget() {
  const router = useRouter();
  const { session } = useAuth();
  const token = session?.accessToken;
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SecurityListingView[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const recordSearch = useDashboardPrefsStore((s) => s.recordSearch);
  const pinCompany = useDashboardPrefsStore((s) => s.pinCompany);

  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setResults([]);
      setStatus(null);
      return;
    }
    if (!token) {
      setResults([]);
      setStatus("Sign in required for Security Master search.");
      return;
    }
    const handle = window.setTimeout(() => {
      setSearching(true);
      void api
        .searchSecurities(q, { token, limit: 8 })
        .then((payload) => {
          setStatus(payload.status === "MATCHES" ? null : payload.status);
          setResults(payload.results ?? []);
        })
        .catch(() => {
          setResults([]);
          setStatus("UNKNOWN");
        })
        .finally(() => setSearching(false));
    }, 200);
    return () => window.clearTimeout(handle);
  }, [query, token]);

  function openListing(listing: SecurityListingView) {
    recordSearch(listing.ticker);
    router.push(analysisPath(listing));
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      if (results.length === 1) {
        openListing(results[0]);
      }
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (results.length === 1) {
      openListing(results[0]);
    }
  }

  return (
    <DashboardWidgetShell
      title="Quick Company Search"
      description="Official Security Master — select ISIN + exchange, then analyse"
    >
      <form onSubmit={onSubmit} className="space-y-3">
        <SearchBox
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onKeyDown}
          aria-label="Company symbol or name"
          placeholder="INFY, Infosys, HDFC Bank…"
        />
        {searching ? (
          <p className="text-xs text-[var(--muted)]">Searching…</p>
        ) : null}
        {status && status !== "MATCHES" ? (
          <p className="text-xs text-[var(--muted)]" role="status">
            {status}
          </p>
        ) : null}
        {results.length > 0 ? (
          <ul className="space-y-1" aria-label="Security Master results">
            {results.map((row) => (
              <li key={row.listing_id || `${row.isin}.${row.mic}`}>
                <button
                  type="button"
                  className="w-full rounded-[var(--radius-md)] px-2 py-1.5 text-left text-sm hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                  onClick={() => openListing(row)}
                >
                  <span className="font-medium">{row.ticker}</span>
                  <span className="ml-2 text-[var(--muted)]">
                    {row.company_name} · {row.exchange} · {row.isin} · {row.mic}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <Button size="sm" type="submit" disabled={results.length !== 1}>
            Analyze
          </Button>
          <Button
            size="sm"
            type="button"
            variant="secondary"
            disabled={results.length !== 1}
            onClick={() => {
              if (results.length !== 1) return;
              pinCompany(results[0].ticker);
            }}
          >
            Pin symbol
          </Button>
        </div>
      </form>
    </DashboardWidgetShell>
  );
}

export function GlobalSearchEntryWidget() {
  const setOpen = useUiStore((s) => s.setCommandPaletteOpen);
  return (
    <DashboardWidgetShell
      title="Global Search"
      description="Route search via command palette (Ctrl+K)"
    >
      <Button
        className="w-full justify-start"
        variant="secondary"
        onClick={() => setOpen(true)}
        aria-label="Open global search and command palette"
      >
        Search pages… Ctrl+K
      </Button>
    </DashboardWidgetShell>
  );
}
