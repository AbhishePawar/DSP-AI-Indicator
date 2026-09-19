"use client";

import { useState } from "react";
import { Copy, MoreHorizontal, Paperclip, Pencil, RefreshCw, Share2, ArrowUp, TrendingUp, TrendingDown, IndianRupee, Users } from "lucide-react";

import type { ResearchView } from "@/lib/research/mapResearchView";
import { formatPct } from "@/lib/intelligence/mapResponse";

function unavailable(value: string | null | undefined) {
  return value && value !== "Unavailable" ? value : "Data unavailable";
}

function Takeaway({ tone, icon: Icon, title, children }: { tone: string; icon: typeof TrendingUp; title: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <span className={`mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full ${tone}`}><Icon className="size-4" /></span>
      <div className="min-w-0"><p className="text-sm font-semibold text-[var(--ink)]">{title}</p><p className="text-xs leading-5 text-[var(--muted)]">{children}</p></div>
    </div>
  );
}

function Metric({ value, label }: { value: string; label: string }) {
  return <div className="min-w-0 border-b border-[var(--border)] pb-3 last:border-b-0 last:pb-0"><p className="text-lg font-semibold text-[var(--accent-strong)]">{value}</p><p className="text-[11px] text-[var(--muted)]">{label}</p></div>;
}

export function ResultConversation({ view, onShare, onRefresh }: { view: ResearchView | null; onShare: () => void; onRefresh: () => void }) {
  const [followUp, setFollowUp] = useState("");
  const demoView = {
    company: "Tata Consultancy Services",
    ticker: "TCS",
    analysedAt: new Date().toISOString(),
    financial: { metrics: [] },
    businessQuality: { label: "Strong", decision: "High quality", score: "8.4/10" },
    valuation: { currentPrice: "₹3,120", intrinsicValue: "₹3,580", marginOfSafety: "12.8%" },
    committee: { confidence: "High" },
    risks: [],
  } as unknown as ResearchView;
  const activeView = view ?? demoView;
  const liveUnavailable = !view || !activeView.company || activeView.company === "Unavailable" || activeView.company === "Data unavailable";
  const example = {
    company: "Tata Consultancy Services",
    ticker: "TCS",
    currentPrice: "₹3,120",
    change: "-0.8%",
    roe: "49%",
    roce: "66%",
    margin: "18.1%",
    dividend: "4.66%",
    pe: "22.4x",
    evEbitda: "18.2x",
  };
  const company = liveUnavailable ? example.company : unavailable(activeView.company);
  const ticker = liveUnavailable ? example.ticker : unavailable(activeView.ticker);
  const roe = liveUnavailable ? example.roe : activeView.financial.metrics.find((metric) => metric.label.toLowerCase().includes("roe"))?.value ?? "Data unavailable";
  const roce = liveUnavailable ? example.roce : activeView.financial.metrics.find((metric) => metric.label.toLowerCase().includes("roce"))?.value ?? "Data unavailable";
  const currentPrice = liveUnavailable ? example.currentPrice : unavailable(activeView.valuation.currentPrice);
  const margin = liveUnavailable ? example.margin : unavailable(activeView.valuation.marginOfSafety);

  return (
    <div className="flex min-h-screen flex-col overflow-hidden bg-[var(--surface)]">
      {liveUnavailable ? <div className="border-b border-amber-200 bg-amber-50 px-5 py-2 text-center text-xs font-medium text-amber-800">Example data shown for layout preactiveView. Live analysis data will replace this automatically.</div> : null}
      <header className="flex items-center justify-between border-b border-[var(--border)] px-5 py-3">
        <div className="min-w-0"><div className="flex items-center gap-2"><h1 className="truncate text-base font-semibold text-[var(--ink)]">{company} ({ticker})</h1><Pencil className="size-4 text-[var(--muted)]" aria-hidden="true" /></div><p className="text-xs text-[var(--muted)]">DSP AI Research · Updated {activeView.analysedAt ? new Date(activeView.analysedAt).toLocaleString() : "Data unavailable"}</p></div>
        <div className="flex items-center gap-1"><button type="button" onClick={onShare} className="inline-flex items-center gap-2 rounded-lg bg-[var(--surface-2)] px-3 py-2 text-sm font-medium text-[var(--ink)] hover:bg-[var(--accent-soft)]"><Share2 className="size-4" /> Share</button><button type="button" aria-label="More options" className="rounded-lg p-2 text-[var(--muted)] hover:bg-[var(--surface-2)]"><MoreHorizontal className="size-5" /></button></div>
      </header>

      <main className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-8 lg:px-12">
        <div className="mx-auto w-full max-w-6xl space-y-5">
          <div className="flex items-start gap-3"><div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[var(--accent-strong)] text-sm font-semibold text-white">AP</div><div><div className="rounded-xl bg-[var(--surface-2)] px-4 py-2 text-sm text-[var(--ink)]">Analyse {company} fundamentals and valuation.</div><p className="mt-1 text-[11px] text-[var(--muted)]">Research request</p></div></div>
          <div className="flex items-start gap-3"><div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[var(--accent)] text-sm font-semibold text-white">D</div><div className="min-w-0 flex-1"><div className="mb-2 flex items-center gap-3 text-xs"><span className="font-semibold text-[var(--accent-strong)]">DSP AI</span><span className="text-[var(--muted)]">Research Mode</span></div>
            <article className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-sm)]">
              <div className="flex items-start justify-between border-b border-[var(--border)] px-4 py-4"><div><h2 className="text-lg font-semibold text-[var(--ink)]">{ticker} — Fundamental Analysis &amp; Valuation</h2><p className="text-sm text-[var(--muted)]">An institutional analysis of {company}</p></div><div className="flex items-center gap-1"><button type="button" aria-label="Copy result" className="rounded p-2 text-[var(--muted)] hover:bg-[var(--surface-2)]"><Copy className="size-4" /></button><button type="button" onClick={onRefresh} aria-label="Regenerate result" className="rounded p-2 text-[var(--muted)] hover:bg-[var(--surface-2)]"><RefreshCw className="size-4" /></button><button type="button" aria-label="More result options" className="rounded p-2 text-[var(--muted)] hover:bg-[var(--surface-2)]"><MoreHorizontal className="size-4" /></button></div></div>
              <nav className="flex gap-5 overflow-x-auto border-b border-[var(--border)] px-4" aria-label="Analysis sections">{["Executive Summary", "Financials", "Profitability", "Cash Flow", "Valuation", "Ownership", "Risks", "What to Watch", "Sources"].map((tab, index) => <span key={tab} className={`whitespace-nowrap py-3 text-xs ${index === 0 ? "border-b-2 border-[var(--accent)] font-semibold text-[var(--accent-strong)]" : "text-[var(--muted)]"}`}>{tab}</span>)}</nav>
              <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(12rem,.6fr)_minmax(13rem,.8fr)]">
                <section className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-4"><h3 className="mb-4 text-sm font-semibold">Key Takeaways</h3><div className="space-y-4"><Takeaway tone="bg-emerald-100 text-emerald-700" icon={TrendingUp} title="Best-in-class returns">ROE ~{roe} and ROCE ~{roce} in FY26 — top-tier among global IT peers.</Takeaway><Takeaway tone="bg-red-100 text-red-600" icon={TrendingDown} title="Margin pressure">Net margin compressed ~1.9 percentage points from FY20 to FY26.</Takeaway><Takeaway tone="bg-blue-100 text-blue-700" icon={IndianRupee} title="Attractive valuation">Trading at a discount to its own history and industry.</Takeaway><Takeaway tone="bg-violet-100 text-violet-700" icon={Users} title="Healthy cash returns">Dividend yield of {example.dividend} — among the highest in large-cap IT.</Takeaway></div></section>
                <section className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-4"><Metric value={currentPrice} label="Current Price" /><div className="my-4 border-t border-[var(--border)]" /><Metric value={example.change} label="1D Change" /></section>
                <section className="grid grid-cols-2 gap-x-4 gap-y-4 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-4"><Metric value={unavailable(roe)} label="ROE" /><Metric value={unavailable(roce)} label="ROCE" /><Metric value={margin} label="Net Margin (FY26)" /><Metric value={example.dividend} label="Dividend Yield" /><Metric value={example.pe} label="P/E (TTM)" /><Metric value={example.evEbitda} label="EV/EBITDA (TTM)" /></section>
              </div>
              <div className="border-t border-[var(--border)] px-4 py-4"><p className="mb-3 text-sm font-semibold">Suggested follow-ups</p><div className="flex flex-wrap gap-2">{["Show detailed valuation analysis", "Why are margins under pressure?", `Compare ${ticker} with peers`, "Show revenue trend"].map((prompt) => <button key={prompt} type="button" onClick={() => setFollowUp(prompt)} className="rounded-full border border-[var(--border)] px-3 py-2 text-xs text-[var(--muted)] hover:border-[var(--accent)] hover:text-[var(--accent-strong)]">{prompt}</button>)}</div></div>
            </article>
          </div></div>
          {(liveUnavailable || activeView.risks.length > 0) ? <div className="flex items-start gap-3"><div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[var(--accent)] text-sm font-semibold text-white">D</div><article className="flex-1 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4"><h2 className="text-base font-semibold">{ticker} — Margin Compression Analysis</h2><p className="mt-1 text-sm text-[var(--muted)]">Analysis of key drivers behind the decline in margins from FY20 to FY26.</p><ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-[var(--muted)]">{(liveUnavailable ? ["Higher employee costs increased operating pressure.", "Revenue growth slowed relative to the broader IT sector.", "Margins remain resilient but should be monitored in the next two quarters."] : activeView.risks.slice(0, 4)).map((risk) => <li key={risk}>{risk}</li>)}</ul></article></div> : null}
        </div>
      </main>
      <form onSubmit={(event) => event.preventDefault()} className="mx-auto flex w-[calc(100%-2rem)] max-w-5xl items-center gap-3 rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 shadow-[var(--shadow-sm)]"><Paperclip className="size-4 shrink-0 text-[var(--muted)]" /><input value={followUp} onChange={(event) => setFollowUp(event.target.value)} placeholder={`Ask a follow-up about ${ticker}…`} className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--muted)]" aria-label="Ask a follow-up" /><button type="submit" aria-label="Send follow-up" className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[var(--accent)] text-white hover:opacity-90"><ArrowUp className="size-4" /></button></form>
      <p className="pb-2 pt-1 text-center text-[10px] text-[var(--muted)]">DSP AI can make mistakes. Please verify important information.</p>
    </div>
  );
}

export default ResultConversation;
