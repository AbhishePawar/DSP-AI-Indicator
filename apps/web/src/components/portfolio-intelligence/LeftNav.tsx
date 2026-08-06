"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Badge, Button, Input } from "@/components/ds";
import {
  PORTFOLIO_SECTIONS,
  usePortfolioIntelPrefsStore,
  type PortfolioSectionId,
} from "@/lib/portfolio-intelligence";
import { cn } from "@/lib/utils";

const PRIMARY_IDS: PortfolioSectionId[] = [
  "summary",
  "allocation",
  "performance",
  "quality",
  "valuation",
  "risk",
  "research",
  "watchlist",
  "opportunities",
  "rebalancing",
  "explainability",
  "export",
];

const DEEP_IDS: PortfolioSectionId[] = ["holdings", "compliance"];

const ANALYTICS_IDS: PortfolioSectionId[] = [
  "correlation",
  "efficient-frontier",
  "monte-carlo",
  "stress-testing",
  "scenario-impact",
  "tax-optimization",
  "position-limits",
  "factor-exposure",
];

export function PortfolioLeftNav({
  holdingsCount,
  onAddHoldingSymbol,
}: {
  holdingsCount: number;
  onAddHoldingSymbol: (symbol: string) => void;
}) {
  const router = useRouter();
  const activeSection = usePortfolioIntelPrefsStore((s) => s.activeSection);
  const setActiveSection = usePortfolioIntelPrefsStore((s) => s.setActiveSection);

  function selectSection(id: PortfolioSectionId) {
    setActiveSection(id);
    router.replace(`/portfolio?section=${id}`);
  }
  const portfolios = usePortfolioIntelPrefsStore((s) => s.portfolios);
  const activePortfolioId = usePortfolioIntelPrefsStore(
    (s) => s.activePortfolioId,
  );
  const setActivePortfolioId = usePortfolioIntelPrefsStore(
    (s) => s.setActivePortfolioId,
  );
  const toggleFavourite = usePortfolioIntelPrefsStore((s) => s.toggleFavourite);
  const watchlist = usePortfolioIntelPrefsStore((s) => s.watchlist);
  const addWatchlistSymbol = usePortfolioIntelPrefsStore(
    (s) => s.addWatchlistSymbol,
  );
  const removeWatchlistSymbol = usePortfolioIntelPrefsStore(
    (s) => s.removeWatchlistSymbol,
  );

  const recent = [...portfolios].sort((a, b) =>
    b.lastOpenedAt.localeCompare(a.lastOpenedAt),
  );
  const favourites = portfolios.filter((p) => p.favourite);

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-3">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Portfolio selector
        </p>
        <ul className="space-y-1" aria-label="Portfolio list">
          {portfolios.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                onClick={() => setActivePortfolioId(p.id)}
                aria-current={activePortfolioId === p.id ? "true" : undefined}
                className={cn(
                  "flex w-full items-center justify-between rounded-[var(--radius-md)] px-2 py-2 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
                  activePortfolioId === p.id
                    ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                    : "hover:bg-[var(--surface-2)]",
                )}
              >
                <span className="truncate">{p.name}</span>
                <Badge variant="outline" className="text-[10px]">
                  {holdingsCount}
                </Badge>
              </button>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-[10px] text-[var(--muted)]">
          Session portfolio only — no multi-portfolio API in frozen /api/v1.
        </p>
      </div>

      <nav aria-label="Portfolio sections">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Workspace
        </p>
        <ul className="space-y-0.5">
          {PORTFOLIO_SECTIONS.filter((s) => PRIMARY_IDS.includes(s.id)).map(
            (section) => (
              <li key={section.id}>
                <button
                  type="button"
                  onClick={() => selectSection(section.id)}
                  aria-current={activeSection === section.id ? "page" : undefined}
                  className={cn(
                    "flex w-full items-center justify-between rounded-[var(--radius-md)] px-2 py-2 text-left text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
                    activeSection === section.id
                      ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                      : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]",
                  )}
                >
                  <span>{section.label}</span>
                  <kbd className="font-mono text-[10px] opacity-70">
                    {section.shortcut}
                  </kbd>
                </button>
              </li>
            ),
          )}
        </ul>
        <p className="mb-2 mt-4 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Deep dive
        </p>
        <ul className="space-y-0.5">
          {PORTFOLIO_SECTIONS.filter((s) => DEEP_IDS.includes(s.id)).map(
            (section) => (
              <li key={section.id}>
                <button
                  type="button"
                  onClick={() => selectSection(section.id)}
                  aria-current={activeSection === section.id ? "page" : undefined}
                  className={cn(
                    "flex w-full items-center justify-between rounded-[var(--radius-md)] px-2 py-2 text-left text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
                    activeSection === section.id
                      ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                      : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]",
                  )}
                >
                  <span>{section.label}</span>
                  <kbd className="font-mono text-[10px] opacity-70">
                    {section.shortcut}
                  </kbd>
                </button>
              </li>
            ),
          )}
        </ul>
        <p className="mb-2 mt-4 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Analytics
        </p>
        <ul className="space-y-0.5">
          {PORTFOLIO_SECTIONS.filter((s) => ANALYTICS_IDS.includes(s.id)).map(
            (section) => (
              <li key={section.id}>
                <button
                  type="button"
                  onClick={() => selectSection(section.id)}
                  aria-current={activeSection === section.id ? "page" : undefined}
                  className={cn(
                    "flex w-full items-center justify-between rounded-[var(--radius-md)] px-2 py-2 text-left text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
                    activeSection === section.id
                      ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                      : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]",
                  )}
                >
                  <span>{section.label}</span>
                  <kbd className="font-mono text-[10px] opacity-70">
                    {section.shortcut}
                  </kbd>
                </button>
              </li>
            ),
          )}
        </ul>
      </nav>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Recent portfolios
        </p>
        <ul className="space-y-1 text-sm">
          {recent.map((p) => (
            <li key={`recent-${p.id}`}>
              <button
                type="button"
                className="text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                onClick={() => setActivePortfolioId(p.id)}
              >
                {p.name}
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Favourites
          </p>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => toggleFavourite(activePortfolioId)}
          >
            Toggle
          </Button>
        </div>
        {favourites.length === 0 ? (
          <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="flex flex-wrap gap-1">
            {favourites.map((p) => (
              <li key={`fav-${p.id}`}>
                <Badge variant="accent">{p.name}</Badge>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          Watchlists
        </p>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const fd = new FormData(e.currentTarget);
            const symbol = String(fd.get("symbol") || "");
            addWatchlistSymbol(symbol);
            e.currentTarget.reset();
          }}
        >
          <Input name="symbol" placeholder="Symbol" aria-label="Watchlist symbol" />
          <Button size="sm" type="submit" variant="secondary">
            Add
          </Button>
        </form>
        {watchlist.length === 0 ? (
          <p className="mt-2 text-xs text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="mt-2 space-y-1">
            {watchlist.map((w) => (
              <li
                key={w.symbol}
                className="flex items-center justify-between gap-2 text-sm"
              >
                <button
                  type="button"
                  className="text-[var(--accent)] hover:underline"
                  onClick={() => onAddHoldingSymbol(w.symbol)}
                >
                  {w.symbol}
                </button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => removeWatchlistSymbol(w.symbol)}
                >
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-2 text-[10px] text-[var(--muted)]">
          Local watchlist only — not a backend portfolio feed.
        </p>
      </div>

      <div className="mt-auto border-t border-[var(--border)] pt-3">
        <Link
          href="/analysis"
          className="text-xs text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          Open Company Analysis
        </Link>
      </div>
    </div>
  );
}
