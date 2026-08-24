"use client";

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Clock, Search } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  loadRecentAnalyses,
  type RecentAnalysisEntry,
} from "@/lib/analysis/recentAnalyses";
import { searchCatalogue, type CompanyEntry } from "@/lib/companies/catalogue";

const MAX_RESULTS = 7;
const MAX_RECENT = 5;

/** Formats an ISO timestamp after hydration only — avoids locale/TZ mismatch. */
function formatAnalysedAt(iso: string): string | null {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function SearchFirstDashboard() {
  const router = useRouter();
  const listboxId = useId();
  const optionIdPrefix = useId();

  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [recent, setRecent] = useState<RecentAnalysisEntry[]>([]);

  const inputRef = useRef<HTMLInputElement | null>(null);
  const activeOptionRef = useRef<HTMLLIElement | null>(null);

  // Hydration-safe: server renders the deterministic empty list, client fills in after mount.
  useEffect(() => {
    setRecent(loadRecentAnalyses());
  }, []);

  const trimmed = query.trim();
  const matched = useMemo<CompanyEntry[]>(
    () => (trimmed ? searchCatalogue(trimmed).slice(0, MAX_RESULTS) : []),
    [trimmed],
  );

  const showResults = open && trimmed.length > 0;
  const activeOption = showResults ? matched[activeIndex] : undefined;

  const submit = useCallback(
    (symbol: string) => {
      const next = symbol.trim().toUpperCase();
      if (!next) return;
      router.push(`/analysis?symbol=${encodeURIComponent(next)}`);
    },
    [router],
  );

  useEffect(() => {
    setActiveIndex(-1);
  }, [trimmed]);

  useEffect(() => {
    activeOptionRef.current?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    // Never intercept keys while an IME is composing (CJK input).
    if (event.nativeEvent.isComposing || event.keyCode === 229) return;

    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (!trimmed || matched.length === 0) return;
      event.preventDefault();
      setOpen(true);
      setActiveIndex((current) => {
        const delta = event.key === "ArrowDown" ? 1 : -1;
        const next = current + delta;
        if (next < 0) return matched.length - 1;
        if (next >= matched.length) return 0;
        return next;
      });
      return;
    }

    if (event.key === "Home" && showResults) {
      event.preventDefault();
      setActiveIndex(0);
      return;
    }

    if (event.key === "End" && showResults) {
      event.preventDefault();
      setActiveIndex(matched.length - 1);
      return;
    }

    if (event.key === "Escape") {
      if (open) {
        event.preventDefault();
        setOpen(false);
        setActiveIndex(-1);
      }
      return;
    }

    if (event.key === "Enter") {
      event.preventDefault();
      submit(activeOption ? activeOption.ticker : query);
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-16rem)] flex-col justify-center py-10 sm:py-14">
      <div className="mx-auto w-full max-w-xl">
        <h1 className="text-balance text-center font-[family-name:var(--font-display)] text-3xl font-semibold leading-tight tracking-tight sm:text-[2.75rem]">
          What would you like to research?
        </h1>
        <p className="mx-auto mt-4 max-w-md text-pretty text-center text-sm leading-relaxed text-[var(--muted)] sm:text-base">
          Search any covered company to open its full research workspace.
        </p>

        <div className="relative mt-8 sm:mt-10">
          <div
            className={cn(
              "group relative flex items-center rounded-[var(--radius-lg,0.75rem)]",
              "border border-[var(--border)] bg-[var(--surface)]",
              "shadow-[var(--shadow-sm,0_1px_2px_rgba(0,0,0,0.04))]",
              "transition-colors focus-within:border-[var(--accent)]",
            )}
          >
            <Search
              className="pointer-events-none absolute left-4 h-[18px] w-[18px] text-[var(--muted)]"
              aria-hidden
            />
            <input
              ref={inputRef}
              type="text"
              role="combobox"
              aria-expanded={showResults}
              aria-controls={listboxId}
              aria-autocomplete="list"
              aria-haspopup="listbox"
              aria-activedescendant={
                activeOption ? `${optionIdPrefix}-${activeIndex}` : undefined
              }
              aria-label="Search a company or stock"
              autoComplete="off"
              spellCheck={false}
              value={query}
              placeholder="Search a company or stock…"
              onChange={(event) => {
                setQuery(event.target.value);
                setOpen(true);
              }}
              onFocus={() => setOpen(true)}
              onBlur={() => {
                // Allow pointer selection to land before closing.
                window.setTimeout(() => setOpen(false), 120);
              }}
              onKeyDown={onKeyDown}
              className={cn(
                "h-14 w-full flex-1 bg-transparent pl-12 pr-14",
                "text-base text-[var(--fg)] placeholder:text-[var(--muted)]",
                "rounded-[var(--radius-lg,0.75rem)] outline-none",
              )}
            />
            <button
              type="button"
              onClick={() => submit(activeOption ? activeOption.ticker : query)}
              disabled={!trimmed}
              aria-label="Open research"
              className={cn(
                "absolute right-2 grid h-10 w-10 place-items-center rounded-[var(--radius-md,0.5rem)]",
                "text-[var(--muted)] transition-colors",
                "hover:bg-[var(--surface-2)] hover:text-[var(--fg)]",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
                "disabled:pointer-events-none disabled:opacity-0",
                trimmed && "bg-[var(--accent)] text-[var(--accent-fg)] hover:bg-[var(--accent)] hover:opacity-90 hover:text-[var(--accent-fg)]",
              )}
            >
              <ArrowRight className="h-[18px] w-[18px]" aria-hidden />
            </button>
          </div>

          {showResults ? (
            <div
              className={cn(
                "absolute left-0 right-0 top-[calc(100%+0.5rem)] z-20 overflow-hidden",
                "rounded-[var(--radius-lg,0.75rem)] border border-[var(--border)]",
                "bg-[var(--surface)] shadow-[var(--shadow-md,0_8px_24px_rgba(0,0,0,0.08))]",
              )}
            >
              {matched.length === 0 ? (
                <p className="px-4 py-3.5 text-sm text-[var(--muted)]">
                  No covered company matches{" "}
                  <span className="text-[var(--fg)]">{trimmed}</span>. Press
                  Enter to try it anyway.
                </p>
              ) : (
                <ul
                  id={listboxId}
                  role="listbox"
                  aria-label="Company results"
                  className="max-h-[19rem] overflow-y-auto py-1"
                >
                  {matched.map((company, index) => {
                    const isActive = index === activeIndex;
                    return (
                      <li
                        key={company.ticker}
                        id={`${optionIdPrefix}-${index}`}
                        ref={isActive ? activeOptionRef : undefined}
                        role="option"
                        aria-selected={isActive}
                        onMouseDown={(event) => {
                          event.preventDefault();
                          submit(company.ticker);
                        }}
                        onMouseEnter={() => setActiveIndex(index)}
                        className={cn(
                          "flex cursor-pointer items-center justify-between gap-3 px-4 py-2.5",
                          isActive && "bg-[var(--surface-2)]",
                        )}
                      >
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-medium text-[var(--fg)]">
                            {company.name}
                          </span>
                          <span className="mt-0.5 block truncate text-xs text-[var(--muted)]">
                            {company.exchange} · {company.sector}
                          </span>
                        </span>
                        <span className="shrink-0 font-mono text-xs text-[var(--muted)]">
                          {company.ticker}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          ) : null}
        </div>

        <div className="mt-10 sm:mt-12">
          <h2 className="text-[11px] font-medium uppercase tracking-[0.12em] text-[var(--muted)]">
            Recent research
          </h2>
          {recent.length === 0 ? (
            <p className="mt-3 text-sm text-[var(--muted)]">
              Nothing yet — your recent companies will appear here.
            </p>
          ) : (
            <ul className="mt-1 divide-y divide-[var(--border)]">
              {recent.slice(0, MAX_RECENT).map((entry) => {
                const when = formatAnalysedAt(entry.analysedAt);
                return (
                  <li key={`${entry.ticker}-${entry.analysedAt}`}>
                    <button
                      type="button"
                      onClick={() => submit(entry.ticker)}
                      className={cn(
                        "flex w-full items-center justify-between gap-3 py-3 text-left",
                        "rounded-[var(--radius-sm,0.375rem)] transition-colors",
                        "hover:text-[var(--accent)]",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
                      )}
                    >
                      <span className="flex min-w-0 items-baseline gap-2">
                        <span className="truncate text-sm text-[var(--fg)]">
                          {entry.company || entry.ticker}
                        </span>
                        <span className="shrink-0 font-mono text-xs text-[var(--muted)]">
                          {entry.ticker}
                        </span>
                      </span>
                      <span className="flex shrink-0 items-center gap-3">
                        {entry.recommendation ? (
                          <span className="hidden text-xs text-[var(--muted)] sm:inline">
                            {entry.recommendation}
                          </span>
                        ) : null}
                        {when ? (
                          <span className="flex items-center gap-1.5 text-xs text-[var(--muted)]">
                            <Clock className="h-3 w-3" aria-hidden />
                            {when}
                          </span>
                        ) : null}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
