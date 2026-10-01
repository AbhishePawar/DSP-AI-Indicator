"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, BookOpen, Search } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { loadRecentAnalyses } from "@/lib/analysis/recentAnalyses";
import { listArchivedSessions } from "@/lib/copilot/sessionArchive";
import { listRecentReports } from "@/lib/recentReports";
import { libraryFromArchive, libraryFromRecent, libraryFromReports, mergeLibraryItems, type ResearchLibraryItem } from "@/lib/research-workspace/library";
import { useDashboardPrefsStore } from "@/lib/dashboard";

const templates = [
  { section: "summary", title: "Full Financial Analysis", description: "Profitability, balance sheet, cash flow, and valuation" },
  { section: "quality", title: "Quick Quality Check", description: "Business quality, returns, margins, and debt" },
  { section: "valuation", title: "Valuation Assessment", description: "Intrinsic value and margin of safety" },
  { section: "risk", title: "Risk Profile", description: "Financial strength and evidence-backed risks" },
  { section: "compare", title: "Peer Comparison", description: "Compare companies using verified research" },
];

function ResearchCard({ item }: { item: ResearchLibraryItem }) {
  const href = item.reportId ? `/reports/${encodeURIComponent(item.reportId)}` : `/research?ticker=${encodeURIComponent(item.ticker)}&section=viewer`;
  return <Link data-testid={`research-card-${item.id}`} href={href} className="block rounded-xl border border-[var(--border)] bg-[var(--surface)] px-5 py-4 transition-colors hover:border-[var(--accent)]/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]">
    <div className="flex flex-wrap items-start justify-between gap-2"><div><span className="mr-2 font-mono text-[11px] text-[var(--accent)]">{item.ticker}</span><span className="text-sm">{item.company}</span></div><span className="font-mono text-[10px] text-[var(--muted)]">{item.analysedAt ? new Date(item.analysedAt).toLocaleDateString() : "Date unavailable"}</span></div>
    <div className="mt-3 flex flex-wrap gap-1.5"><span className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-2 py-0.5 font-mono text-[10px] text-[var(--muted)]">{item.source === "report" ? "Saved report" : "Company analysis"}</span>{item.exchange && <span className="rounded-full border border-[var(--border)] px-2 py-0.5 font-mono text-[10px] text-[var(--muted)]">{item.exchange}</span>}</div>
    <span className="mt-3 inline-flex items-center gap-1.5 text-[11px] text-[var(--accent)]">Open research <ArrowRight className="size-3" /></span>
  </Link>;
}

export function ResearchHub() {
  const router = useRouter();
  const recordSearch = useDashboardPrefsStore((s) => s.recordSearch);
  const [ticker, setTicker] = useState("");
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<ResearchLibraryItem[]>([]);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const all = mergeLibraryItems([...libraryFromRecent(loadRecentAnalyses()), ...libraryFromArchive(listArchivedSessions()), ...libraryFromReports(listRecentReports())]);
    const unique = new Map<string, ResearchLibraryItem>();
    all.forEach((item) => { const key = item.reportId || item.ticker; if (!unique.has(key)) unique.set(key, item); });
    setItems([...unique.values()].sort((a, b) => (b.analysedAt || "").localeCompare(a.analysedAt || "")));
    setReady(true);
  }, []);
  const filtered = items.filter((item) => `${item.company} ${item.ticker}`.toLowerCase().includes(search.trim().toLowerCase()));
  return <div data-testid="research-hub" className="space-y-6">
    <PageHeader title="Research Hub" description="Saved analyses · Research templates" actions={<Link data-testid="research-advanced-workspace" href="/research?view=workspace" className="rounded-lg border border-[var(--border)] px-3 py-2 text-xs text-[var(--muted)] hover:text-[var(--fg)]">Advanced workspace</Link>} />
    <section className="rounded-[14px] border border-[var(--accent)]/25 bg-[linear-gradient(135deg,rgba(124,106,247,0.1),rgba(45,212,191,0.05))] px-5 py-6 sm:px-7">
      <h2 className="font-[family-name:var(--font-display)] text-lg font-medium">Start new research</h2><p className="mt-2 text-[13px] text-[var(--muted)]">Enter a listed company ticker to begin a fresh research conversation.</p>
      <form data-testid="research-hub-search-form" className="mt-5 flex max-w-md gap-2.5" onSubmit={(event) => { event.preventDefault(); const value = ticker.trim().toUpperCase(); if (!value) return; recordSearch(value); router.push(`/analysis?symbol=${encodeURIComponent(value)}`); }}>
        <input data-testid="research-hub-ticker" aria-label="Company ticker" placeholder="Company ticker…" value={ticker} onChange={(event) => setTicker(event.target.value)} required maxLength={40} className="min-w-0 flex-1 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3.5 py-2.5 text-sm outline-none focus:border-[var(--accent)]" /><button data-testid="research-hub-start" type="submit" aria-label="Start research" className="rounded-lg bg-[var(--accent)] px-5 text-white transition-colors hover:bg-[var(--accent-hover)]"><Search className="size-4" /></button>
      </form>
    </section>
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
      <section className="min-w-0"><div className="mb-3.5 flex flex-wrap items-center justify-between gap-3"><h2 className="font-[family-name:var(--font-display)] text-base">Saved Research</h2><input data-testid="research-hub-filter" aria-label="Search saved research" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search…" className="w-40 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs outline-none focus:border-[var(--accent)]" /></div>
        <div className="space-y-2.5">{!ready ? <p data-testid="research-hub-loading" role="status" className="py-10 text-sm text-[var(--muted)]">Loading your research…</p> : filtered.length ? filtered.map((item) => <ResearchCard key={item.id} item={item} />) : <div data-testid="research-hub-empty" className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-6 py-12 text-center"><BookOpen className="mx-auto size-6 text-[var(--muted)]" /><p className="mt-4 text-sm">{search ? "No matching research" : "Your research library starts here"}</p><p className="mt-2 text-xs leading-5 text-[var(--muted)]">{search ? "Try another company name or ticker." : "Run a company analysis or save a report to revisit it here."}</p></div>}</div>
        <p className="mt-3 text-[10px] text-[var(--muted)]">History and cached analyses are stored on this device. Saved reports open their existing report viewer.</p>
      </section>
      <aside><h2 className="mb-3.5 font-[family-name:var(--font-display)] text-base">Research Templates</h2><div className="space-y-2.5">{templates.map((template) => <Link key={template.section} data-testid={`research-template-${template.section}`} href={template.section === "compare" ? "/compare" : `/analysis?section=${template.section}${ticker.trim() ? `&symbol=${encodeURIComponent(ticker.trim().toUpperCase())}` : ""}`} className="block rounded-[10px] border border-[var(--border)] bg-[var(--surface)] px-4 py-3.5 transition-colors hover:border-[var(--accent)]/40"><p className="text-[13px] font-medium">{template.title}</p><p className="mt-1 text-[11px] leading-relaxed text-[var(--muted)]">{template.description}</p></Link>)}</div></aside>
    </div>
  </div>;
}
