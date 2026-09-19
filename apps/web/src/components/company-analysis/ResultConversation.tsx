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

export function ResultConversation({ view, onShare, onRefresh }: { view: ResearchView; onShare: () => void; onRefresh: () => void }) {
  const [followUp, setFollowUp] = useState("");
  const company = unavailable(view.company);
  const ticker = unavailable(view.ticker);
  const roe = view.financial.metrics.find((metric) => metric.label.toLowerCase().includes("roe"))?.value ?? "Data unavailable";
  const roce = view.financial.metrics.find((metric) => metric.label.toLowerCase().includes("roce"))?.value ?? "Data unavailable";

  return (
    <div className="flex min-h-screen flex-col overflow-hidden bg-[var(--surface)]">
      <header className="flex items-center justify-between border-b border-[var(--border)] px-5 py-3">
        <div className="min-w-0"><div className="flex items-center gap-2"><h1 className="truncate text-base font-semibold text-[var(--ink)]">{company} ({ticker})</h1><Pencil className="size-4 text-[var(--muted)]" aria-hidden="true" /></div><p className="text-xs text-[var(--muted)]">DSP AI Research · Updated {view.analysedAt ? new Date(view.analysedAt).toLocaleString() : "Data unavailable"}</p></div>
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
                <section className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-4"><h3 className="mb-4 text-sm font-semibold">Key Takeaways</h3><div className="space-y-4"><Takeaway tone="bg-emerald-100 text-emerald-700" icon={TrendingUp} title="Business quality">{unavailable(view.businessQuality.label)} · {unavailable(view.businessQuality.decision)}</Takeaway><Takeaway tone="bg-red-100 text-red-600" icon={TrendingDown} title="Risk and uncertainty">{view.risks[0] ?? "Data unavailable"}</Takeaway><Takeaway tone="bg-blue-100 text-blue-700" icon={IndianRupee} title="Valuation">{unavailable(view.valuation.intrinsicValue)} intrinsic value · {unavailable(view.valuation.marginOfSafety)} margin of safety</Takeaway><Takeaway tone="bg-violet-100 text-violet-700" icon={Users} title="Research confidence">{unavailable(view.committee.confidence)} committee confidence</Takeaway></div></section>
                <section className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-4"><Metric value={unavailable(view.valuation.currentPrice)} label="Current Price" /><div className="my-4 border-t border-[var(--border)]" /><Metric value={unavailable(view.valuation.marginOfSafety)} label="Margin of Safety" /></section>
                <section className="grid grid-cols-2 gap-x-4 gap-y-4 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-4"><Metric value={unavailable(roe)} label="ROE" /><Metric value={unavailable(roce)} label="ROCE" /><Metric value={unavailable(view.businessQuality.score)} label="Business Quality" /><Metric value={unavailable(view.committee.confidence)} label="Confidence" /></section>
              </div>
              <div className="border-t border-[var(--border)] px-4 py-4"><p className="mb-3 text-sm font-semibold">Suggested follow-ups</p><div className="flex flex-wrap gap-2">{["Show detailed valuation analysis", "Why are margins under pressure?", `Compare ${ticker} with peers`, "Show revenue trend"].map((prompt) => <button key={prompt} type="button" onClick={() => setFollowUp(prompt)} className="rounded-full border border-[var(--border)] px-3 py-2 text-xs text-[var(--muted)] hover:border-[var(--accent)] hover:text-[var(--accent-strong)]">{prompt}</button>)}</div></div>
            </article>
          </div></div>
          {view.risks.length > 0 ? <div className="flex items-start gap-3"><div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[var(--accent)] text-sm font-semibold text-white">D</div><article className="flex-1 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4"><h2 className="text-base font-semibold">{ticker} — Risk &amp; What to Watch</h2><ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-[var(--muted)]">{view.risks.slice(0, 4).map((risk) => <li key={risk}>{risk}</li>)}</ul></article></div> : null}
        </div>
      </main>
      <form onSubmit={(event) => event.preventDefault()} className="mx-auto flex w-[calc(100%-2rem)] max-w-5xl items-center gap-3 rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 shadow-[var(--shadow-sm)]"><Paperclip className="size-4 shrink-0 text-[var(--muted)]" /><input value={followUp} onChange={(event) => setFollowUp(event.target.value)} placeholder={`Ask a follow-up about ${ticker}…`} className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--muted)]" aria-label="Ask a follow-up" /><button type="submit" aria-label="Send follow-up" className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[var(--accent)] text-white hover:opacity-90"><ArrowUp className="size-4" /></button></form>
      <p className="pb-2 pt-1 text-center text-[10px] text-[var(--muted)]">DSP AI can make mistakes. Please verify important information.</p>
    </div>
  );
}

export default ResultConversation;
