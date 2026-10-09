"use client";

import { BarChart3, GitCompareArrows, MessageSquare, Search, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { COMPANY_CATALOGUE } from "@/lib/companies/catalogue";
import { buildAnalysisUrl } from "@/lib/analysis/intents";
import { useDashboardPrefsStore } from "@/lib/dashboard";
import { useAuth } from "@/lib/auth/AuthProvider";

const researchExamples = ["TCS", "INFY", "HDFCBANK", "RELIANCE", "WIPRO"];
const features = [
  { icon: MessageSquare, title: "Conversational Research", description: "Ask questions in plain English. Explore financial evidence with clear explanations.", color: "var(--c-dsp)", href: "/copilot" },
  { icon: BarChart3, title: "Visual Evidence", description: "Explore available charts, ratios, and trends alongside the evidence behind them.", color: "var(--c-revenue)", href: "/analysis" },
  { icon: ShieldCheck, title: "DSP AI Indicator", description: "Deterministic DSP quality analysis grounded in verified financial data.", color: "var(--c-profit)", href: "/analysis" },
  { icon: GitCompareArrows, title: "Peer Comparison", description: "Compare companies side-by-side across available financial and valuation evidence.", color: "var(--c-valuation)", href: "/analysis/compare" },
];

export function MarketingLanding() {
  const recentSearches = useDashboardPrefsStore((s) => s.recentSearches);
  const recordSearch = useDashboardPrefsStore((s) => s.recordSearch);
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    const close = (event: MouseEvent) => {
      const target = event.target as Node | null;
      if (!target) return;
      if (panelRef.current?.contains(target)) return;
      if (target instanceof Element && target.closest("[data-testid^='landing-example-'], [data-testid^='landing-recent-'], [data-testid='landing-buffett-analysis']")) {
        return;
      }
      setSuggestionsOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  function openResearch(mode: "simple" | "full", raw = query) {
    const value = raw.trim();
    const company = COMPANY_CATALOGUE.find((entry) => entry.ticker.toLowerCase() === value.toLowerCase() || entry.name.toLowerCase() === value.toLowerCase());
    // Unknown names continue through the existing identity-search flow.
    if (value && !company && /\s/.test(value)) {
      router.push(`/search?q=${encodeURIComponent(value)}`);
      return;
    }
    const ticker = company?.ticker || value.toUpperCase();
    if (ticker) recordSearch(ticker);
    router.push(buildAnalysisUrl({ symbol: ticker || null, mode }));
  }

  function runDspIndicatorAnalysis() {
    setSuggestionsOpen(false);
    openResearch("full");
  }

  function submitResearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (query.trim()) {
      setSuggestionsOpen(false);
      openResearch("simple");
    }
  }

  return (
    <main data-testid="figma-landing" className="bg-[var(--bg)] text-[var(--fg)]">
      <section className="border-b border-[var(--border)] bg-[radial-gradient(ellipse_80%_60%_at_50%_0%,rgba(124,106,247,0.08)_0%,transparent_70%)] px-5 pb-16 pt-14 text-center sm:px-12 sm:pb-[100px] sm:pt-20">
        <div data-testid="landing-evidence-status" className="mb-8 inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3.5 py-[5px] font-mono text-xs text-[var(--muted)]"><span className="size-1.5 rounded-full bg-[var(--c-cashflow)]" />Research mode · Verified evidence only</div>
        <h1 data-testid="landing-title" className="mb-5 font-[family-name:var(--font-display)] text-[clamp(36px,6vw,68px)] font-medium leading-[1.1] tracking-[-0.02em]">Ask DSP anything<br />about any company.</h1>
        <p className="mx-auto mb-12 max-w-[520px] text-lg leading-[1.65] text-[var(--muted)]">Chat-first equity research. Financial evidence when you need it. No dashboards, no noise.</p>
        <div ref={panelRef} className="mx-auto mb-6 max-w-[560px]">
          <div className="mb-3" onKeyDown={(event) => { if (event.key === "Escape") setSuggestionsOpen(false); }}>
            <form onSubmit={submitResearch} data-testid="landing-search-form" className={`flex overflow-hidden border border-[var(--border)] bg-[var(--surface-2)] focus-within:border-[var(--accent)]/50 ${suggestionsOpen && query.trim() ? "rounded-t-[14px]" : "rounded-[14px]"}`}>
              <label className="sr-only" htmlFor="company-research">Company name or ticker</label>
              <input data-testid="landing-company-search" id="company-research" value={query} onFocus={() => setSuggestionsOpen(Boolean(query.trim()))} onChange={(event) => { setQuery(event.target.value); setSuggestionsOpen(Boolean(event.target.value.trim())); }} role="combobox" aria-expanded={Boolean(suggestionsOpen && query.trim())} aria-controls="landing-analysis-depth" placeholder="Enter company name or ticker — e.g. TCS, HDFC Bank" autoComplete="off" className="min-w-0 flex-1 bg-transparent px-5 py-4 text-[15px] outline-none placeholder:text-[var(--muted)]" />
              <button data-testid="landing-research-submit" type="submit" aria-label="Research" disabled={!query.trim()} className="flex shrink-0 items-center justify-center bg-[var(--accent)] px-6 text-white transition-colors hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed"><Search className="size-[18px]" /></button>
            </form>
            {suggestionsOpen && query.trim() && <div data-testid="landing-depth-panel" id="landing-analysis-depth" className="overflow-hidden rounded-b-[14px] border border-t-0 border-[var(--accent)]/30 bg-[var(--surface)] text-left shadow-[0_12px_40px_rgba(0,0,0,0.35)]">
              <p className="px-4 pb-2 pt-2.5 font-mono text-[10px] tracking-widest text-[var(--muted)]">CHOOSE ANALYSIS DEPTH FOR <span className="break-words text-[var(--fg)]">{query.toUpperCase()}</span></p>
              <div className="grid grid-cols-2 border-t border-[var(--border)]">
                <button data-testid="landing-simple-research" type="button" onClick={() => { setSuggestionsOpen(false); openResearch("simple", query); }} className="border-r border-[var(--border)] px-4 py-4 text-left transition-colors hover:bg-[var(--surface-2)] sm:px-[18px]"><span className="block text-[13px] font-medium">Simple Research</span><span className="mt-1 block text-[11px] leading-relaxed text-[var(--muted)]">Key metrics, strengths, risks, and valuation in one view.</span><span className="mt-2.5 flex flex-wrap gap-1.5">{["Metrics", "Risks", "Valuation"].map((label) => <span key={label} className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-2 py-0.5 font-mono text-[10px] text-[var(--muted)]">{label}</span>)}</span><span className="mt-2.5 block text-xs text-[var(--c-revenue)]">Quick research →</span></button>
                <button data-testid="landing-full-research" type="button" onClick={() => { setSuggestionsOpen(false); openResearch("full", query); }} className="bg-[var(--accent)]/5 px-4 py-4 text-left transition-colors hover:bg-[var(--accent)]/10 sm:px-[18px]"><span className="mb-1 block font-mono text-[10px] tracking-wider text-[var(--accent)]">FLAGSHIP</span><span className="block text-[13px] font-medium">DSP Buffett Analysis</span><span className="mt-1 block text-[11px] leading-relaxed text-[var(--muted)]">Complete evidence-driven analysis — moat, earnings, management, and intrinsic value.</span><span className="mt-2.5 flex flex-wrap gap-1.5">{["Moat", "Quality", "Valuation", "AI Chat"].map((label) => <span key={label} className="rounded-full border border-[var(--accent)]/25 bg-[var(--accent-soft)] px-2 py-0.5 font-mono text-[10px] text-[var(--accent)]">{label}</span>)}</span><span className="mt-2.5 block text-xs text-[var(--accent)]">Full analysis →</span></button>
              </div>
            </div>}
          </div>
          <button data-testid="landing-buffett-analysis" type="button" onClick={runDspIndicatorAnalysis} className="flex w-full items-center justify-center gap-2 rounded-[14px] bg-[linear-gradient(135deg,#7c6af7_0%,#2dd4bf_100%)] px-6 py-[13px] text-sm font-semibold tracking-tight text-white transition-opacity hover:opacity-85"><span className="text-[13px] font-normal opacity-85">DSP</span> Buffett Indicator Analysis</button>
        </div>
        {user && recentSearches.length > 0 && <div data-testid="landing-recent-searches" className="mb-3 flex flex-wrap items-center justify-center gap-2 font-mono text-xs text-[var(--accent)]"><span>Recent on this device:</span>{recentSearches.slice(0, 5).map(({ query: recent }) => <button data-testid={`landing-recent-${recent}`} key={recent} onClick={() => { setQuery(recent); setSuggestionsOpen(true); }} className="rounded-full border border-[var(--accent)]/30 bg-[var(--accent-soft)] px-3 py-1 transition-colors hover:border-[var(--accent)]">{recent}</button>)}</div>}
        <div className="flex flex-wrap items-center justify-center gap-2 font-mono text-xs text-[var(--muted)]"><span>Explore:</span>{researchExamples.map((ticker) => <button data-testid={`landing-example-${ticker}`} key={ticker} onClick={() => { setQuery(ticker); setSuggestionsOpen(true); }} className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1 transition-colors hover:border-[var(--accent)] hover:text-[var(--accent)]">{ticker}</button>)}</div>
      </section>
      <section data-testid="landing-capabilities" className="grid grid-cols-2 border-b border-[var(--border)] lg:grid-cols-4">{[{ value: String(COMPANY_CATALOGUE.length), label: "Directory entries" }, { value: "DSP", label: "Research framework" }, { value: "Verified", label: "Evidence sources" }, { value: "On request", label: "Company analysis" }].map((stat) => <div key={stat.label} className="border-r border-[var(--border)] px-5 py-8 text-center last:border-r-0 sm:px-10"><p className="mb-1.5 font-[family-name:var(--font-display)] text-[28px] font-semibold text-[var(--accent)]">{stat.value}</p><p className="font-mono text-xs uppercase tracking-wider text-[var(--muted)]">{stat.label}</p></div>)}</section>
      <section id="features" className="px-5 py-16 sm:px-12 sm:py-20"><div className="mb-14 text-center"><h2 className="mb-3 font-[family-name:var(--font-display)] text-3xl font-medium tracking-tight sm:text-4xl">Research the way you think.</h2><p className="mx-auto max-w-[480px] text-[15px] text-[var(--muted)]">No complex dashboards to learn. Just ask, and DSP builds the picture.</p></div><div className="mx-auto grid max-w-[840px] gap-5 sm:grid-cols-2">{features.map(({ title, description, href, color, icon: Icon }) => <Link data-testid={`landing-feature-${href.split("/").filter(Boolean).join("-")}-${title.split(" ")[0].toLowerCase()}`} key={title} href={href} className="rounded-[14px] border border-[var(--border)] border-t-2 bg-[var(--surface)] p-7 transition-colors hover:bg-[var(--surface-2)]" style={{ borderTopColor: color }}><Icon className="mb-3.5 size-6" style={{ color }} /><h3 className="mb-2 font-[family-name:var(--font-display)] text-lg font-medium">{title}</h3><p className="text-[13px] leading-relaxed text-[var(--muted)]">{description}</p></Link>)}</div></section>
      <section className="border-t border-[var(--border)] bg-[radial-gradient(ellipse_60%_80%_at_50%_100%,rgba(124,106,247,0.07)_0%,transparent_70%)] px-5 py-20 text-center sm:px-12"><h2 className="mb-4 font-[family-name:var(--font-display)] text-4xl font-medium tracking-tight">Start researching.</h2><p className="mb-8 text-[15px] text-[var(--muted)]">Create an account to explore evidence-backed company research.</p><div className="flex flex-wrap justify-center gap-3"><Link data-testid="landing-create-account" href="/register" className="rounded-[10px] bg-[var(--accent)] px-8 py-[13px] text-[15px] font-medium text-white transition-colors hover:bg-[var(--accent-hover)]">Create account</Link><Link data-testid="landing-learn-more" href="/about" className="rounded-[10px] border border-[var(--border)] bg-[var(--surface-2)] px-8 py-[13px] text-[15px] transition-colors hover:border-[var(--accent)]">Learn more</Link></div></section>
    </main>
  );
}
