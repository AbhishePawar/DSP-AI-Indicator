"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

const SEARCH_HINTS = ["TCS", "INFY", "HDFCBANK", "RELIANCE"] as const;

export function LandingResearchSearch() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [panelVisible, setPanelVisible] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setPanelVisible(query.trim().length > 0);
  }, [query]);

  useEffect(() => {
    function handler(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setPanelVisible(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function go(path: string) {
    router.push(path);
  }

  function symbol() {
    return query.trim().toUpperCase();
  }

  function handleSearch(event: React.FormEvent) {
    event.preventDefault();
    const next = symbol();
    if (!next) return;
    go(`/analysis?symbol=${encodeURIComponent(next)}`);
  }

  return (
    <div className="mx-auto mb-6 w-full max-w-[560px]">
      <div ref={panelRef} className="relative mb-3">
        <form onSubmit={handleSearch}>
          <div
            className="flex overflow-hidden border border-[var(--border)] bg-[var(--surface-2)]"
            style={{
              borderRadius: panelVisible ? "14px 14px 0 0" : 14,
            }}
          >
            <label className="sr-only" htmlFor="landing-research-query">
              Company or ticker
            </label>
            <input
              id="landing-research-query"
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onFocus={() => query.trim() && setPanelVisible(true)}
              placeholder="Enter company name or ticker"
              className="min-h-12 flex-1 bg-transparent px-5 py-4 text-[15px] text-[var(--fg)] outline-none"
            />
            <button
              type="submit"
              aria-label="Research"
              className="bg-[var(--accent)] px-6 text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 20 20"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.9"
                aria-hidden
              >
                <circle cx="8.5" cy="8.5" r="5.25" />
                <line x1="12.5" y1="12.5" x2="17" y2="17" />
              </svg>
            </button>
          </div>
        </form>
        {panelVisible ? (
          <div className="absolute inset-x-0 top-full z-20 overflow-hidden rounded-b-[14px] border border-[var(--border)] border-t-0 bg-[var(--surface)] shadow-[var(--shadow-lg)]">
            <p className="section-label px-4 pt-3">
              Choose analysis depth
              {symbol() ? (
                <span className="ml-1 text-[var(--fg)]">{symbol()}</span>
              ) : null}
            </p>
            <div className="grid grid-cols-1 border-t border-[var(--border)] sm:grid-cols-2">
              <button
                type="button"
                className="border-b border-[var(--border)] p-4 text-left sm:border-b-0 sm:border-r"
                onClick={() =>
                  go(
                    `/analysis?symbol=${encodeURIComponent(symbol())}&mode=simple`,
                  )
                }
                disabled={!symbol()}
              >
                <p className="text-sm font-medium text-[var(--fg)]">
                  Simple Research
                </p>
                <p className="mt-1 text-xs leading-relaxed text-[var(--muted)]">
                  Key certified metrics, risks, and valuation in one view.
                </p>
              </button>
              <button
                type="button"
                className="bg-[rgba(124,106,247,0.03)] p-4 text-left"
                onClick={() =>
                  go(`/analysis?symbol=${encodeURIComponent(symbol())}`)
                }
                disabled={!symbol()}
              >
                <p className="font-mono text-[10px] tracking-wider text-[var(--accent)]">
                  FLAGSHIP
                </p>
                <p className="mt-1 text-sm font-medium text-[var(--fg)]">
                  DSP Buffett Analysis
                </p>
                <p className="mt-1 text-xs leading-relaxed text-[var(--muted)]">
                  Official evidence through the deterministic DSP pipeline.
                </p>
              </button>
            </div>
          </div>
        ) : null}
      </div>
      <button
        type="button"
        onClick={() =>
          go(symbol() ? `/analysis?symbol=${encodeURIComponent(symbol())}` : "/analysis")
        }
        className="flex min-h-11 w-full items-center justify-center gap-2 rounded-[14px] bg-[linear-gradient(135deg,#7c6af7_0%,#2dd4bf_100%)] px-6 text-sm font-semibold text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
      >
        <span className="font-normal opacity-85">DSP</span>
        Buffett Indicator Analysis
      </button>
      <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
        <span className="font-mono text-xs text-[var(--muted)]">Search:</span>
        {SEARCH_HINTS.map((ticker) => (
          <button
            key={ticker}
            type="button"
            onClick={() => go(`/analysis?symbol=${ticker}`)}
            className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1 font-mono text-xs text-[var(--muted)] hover:border-[var(--accent)] hover:text-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            {ticker}
          </button>
        ))}
      </div>
    </div>
  );
}
