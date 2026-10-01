"use client";

import { useState } from "react";
import Link from "next/link";
import { useQueries, useQuery } from "@tanstack/react-query";
import { ArrowRight, Plus, RefreshCw, Search, X } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useDashboardPrefsStore, type PinnedCompany } from "@/lib/dashboard";
import type { MarketQuotePayload } from "@/lib/institutional-dashboard/mapInstitutionalDashboard";

function WatchlistRow({ company, quote, loading, failed }: { company: PinnedCompany; quote?: MarketQuotePayload; loading: boolean; failed: boolean }) {
  const remove = useDashboardPrefsStore((s) => s.unpinCompany);
  const price = quote?.authenticated && quote.available ? quote.fields?.current_price : null;
  return <tr className="border-t border-[var(--border)]" data-testid={`watchlist-row-${company.symbol}`}>
    <td className="px-5 py-4"><span className="block font-mono text-[13px] font-semibold">{company.symbol}</span><span className="text-[11px] text-[var(--muted)]">{company.label || "Saved security"}</span></td>
    <td data-testid={`watchlist-price-${company.symbol}`} className="px-5 py-4 font-mono text-xs">{loading ? "Loading…" : price != null ? `${quote?.currency || ""} ${price.toLocaleString()}` : failed ? "Unavailable" : "—"}</td>
    <td className="px-5 py-4 text-xs text-[var(--muted)]">{quote?.provenance?.as_of ? new Date(quote.provenance.as_of).toLocaleDateString() : "Unavailable"}</td>
    <td className="px-5 py-4"><div className="flex items-center gap-3"><Link data-testid={`watchlist-research-${company.symbol}`} href={`/analysis?symbol=${encodeURIComponent(company.symbol)}`} className="whitespace-nowrap rounded-md border border-[var(--accent)]/30 px-2.5 py-1 text-[11px] text-[var(--accent)] hover:bg-[var(--accent-soft)]">Research →</Link><button data-testid={`watchlist-remove-${company.symbol}`} onClick={() => remove(company.symbol)} aria-label={`Remove ${company.symbol}`} className="p-2 text-[var(--muted)] hover:text-[var(--fg)]"><X className="size-3.5" /></button></div></td>
  </tr>;
}

export function ResearchOverview() {
  const { session } = useAuth();
  const token = session?.accessToken;
  const pinned = useDashboardPrefsStore((s) => s.pinnedCompanies);
  const recent = useDashboardPrefsStore((s) => s.recentSearches);
  const pin = useDashboardPrefsStore((s) => s.pinCompany);
  const [symbol, setSymbol] = useState("");
  const [adding, setAdding] = useState(false);
  const market = useQuery({ queryKey: ["dashboard", "market-readiness"], queryFn: () => api.marketHealth({ token }), retry: 1, staleTime: 60_000 });
  const quotes = useQueries({ queries: pinned.map((company) => ({ queryKey: ["dashboard", "quote", company.symbol, session?.subject], queryFn: () => api.marketQuote(company.symbol, { token }), retry: false, staleTime: 60_000 })) });
  const marketAvailable = market.data?.provider.authenticated === true && market.data?.provider.healthy === true;
  const status = market.isLoading ? "Checking market data…" : market.isError ? "Market service unavailable" : marketAvailable ? "Market source connected" : "Live market data unavailable";

  return <div data-testid="research-dashboard" className="space-y-5">
    <PageHeader title="Dashboard" description="Your research overview" actions={<Link data-testid="dashboard-new-research" href="/analysis" className="flex items-center gap-2 rounded-lg bg-[var(--accent)] px-3.5 py-2 text-xs font-medium text-white"><Plus className="size-4" /> New research</Link>} />
    <div data-testid="dashboard-market-status" role="status" className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-xs">
      <span className="flex items-center gap-2"><span className={`size-1.5 rounded-full ${marketAvailable ? "bg-[var(--c-profit)]" : "bg-[var(--c-risk)]"}`} />{status}</span>
      <button data-testid="dashboard-refresh" onClick={() => { void market.refetch(); quotes.forEach((quote) => void quote.refetch()); }} className="inline-flex items-center gap-1.5 text-[var(--muted)] hover:text-[var(--fg)]"><RefreshCw className="size-3.5" /> Refresh</button>
    </div>
    <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      {["NIFTY 50", "SENSEX", "NIFTY IT", "NIFTY BANK"].map((name) => <article key={name} data-testid={`market-index-${name.toLowerCase().replaceAll(" ", "-")}`} className="rounded-[10px] border border-[var(--border)] bg-[var(--surface)] px-4 py-3.5"><p className="font-mono text-[10px] tracking-wider text-[var(--muted)]">{name}</p><p className="mt-2 font-mono text-lg">—</p><p className="mt-1 text-[11px] text-[var(--muted)]">Index feed unavailable</p></article>)}
    </div>
    <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
      <section className="min-w-0 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)]">
        <header className="flex items-center justify-between px-5 py-4"><h2 className="text-[13px] font-medium">Watchlist</h2><button data-testid="watchlist-add-toggle" onClick={() => setAdding(!adding)} className="text-xs text-[var(--accent)]">{adding ? "Cancel" : "+ Add"}</button></header>
        {adding && <form data-testid="watchlist-add-form" className="flex gap-2 border-t border-[var(--border)] p-4" onSubmit={(event) => { event.preventDefault(); if (!symbol.trim()) return; pin(symbol); setSymbol(""); setAdding(false); }}><input data-testid="watchlist-symbol" aria-label="Watchlist ticker" value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} required maxLength={30} placeholder="Company ticker" className="min-w-0 flex-1 rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm outline-none focus:border-[var(--accent)]" /><button data-testid="watchlist-add-submit" className="rounded-lg bg-[var(--accent)] px-4 text-xs text-white">Add</button></form>}
        <div className="overflow-x-auto"><table className="w-full text-left"><thead className="border-t border-[var(--border)] font-mono text-[10px] uppercase tracking-wider text-[var(--muted)]"><tr>{["Symbol", "Price", "As of", ""].map((heading) => <th key={heading} className="px-5 py-3 font-normal">{heading}</th>)}</tr></thead><tbody>{pinned.map((company, index) => <WatchlistRow key={company.symbol} company={company} quote={quotes[index]?.data} loading={quotes[index]?.isLoading ?? false} failed={quotes[index]?.isError ?? false} />)}</tbody></table></div>
        {!pinned.length && <div data-testid="watchlist-empty" className="border-t border-[var(--border)] px-5 py-14 text-center"><Search className="mx-auto size-6 text-[var(--muted)]" /><p className="mt-4 text-sm">Your watchlist starts here</p><p className="mx-auto mt-2 max-w-sm text-xs leading-5 text-[var(--muted)]">Add securities you want to follow. Prices appear only when a verified market source is available.</p><button data-testid="watchlist-empty-add" onClick={() => setAdding(true)} className="mt-5 text-xs text-[var(--accent)]">Add a security <ArrowRight className="ml-1 inline size-3.5" /></button></div>}
        <p className="border-t border-[var(--border)] px-5 py-3 text-[10px] text-[var(--muted)]">Watchlist is saved on this device. Market values come from verified sources.</p>
      </section>
      <div className="space-y-4">
        <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)]"><h2 className="border-b border-[var(--border)] px-4 py-3.5 text-[13px] font-medium">Recent Research</h2>{recent.length ? recent.slice(0, 5).map(({ query, at }) => <Link key={query} data-testid={`dashboard-recent-${query}`} href={`/analysis?symbol=${encodeURIComponent(query)}`} className="block border-b border-[var(--border)] px-4 py-3 last:border-0 hover:bg-[var(--surface-2)]"><span className="flex items-center justify-between gap-2"><span className="font-mono text-[11px] text-[var(--accent)]">{query}</span><span className="text-[10px] text-[var(--muted)]">{new Date(at).toLocaleDateString()}</span></span><span className="mt-1 block text-xs">Continue company research</span></Link>) : <p data-testid="dashboard-research-empty" className="px-4 py-6 text-xs leading-5 text-[var(--muted)]">No research activity yet. Start with a company to build your research history.</p>}</section>
        <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)]"><h2 className="border-b border-[var(--border)] px-4 py-3.5 text-[13px] font-medium">DSP Signals</h2><p data-testid="dashboard-signals-empty" className="px-4 py-6 text-xs leading-5 text-[var(--muted)]">No verified signals available. Open company research to review evidence-backed DSP results.</p><Link data-testid="dashboard-signals-research" href="/research/intelligence" className="block border-t border-[var(--border)] px-4 py-3 text-xs text-[var(--accent)]">Research intelligence →</Link></section>
      </div>
    </div>
  </div>;
}
