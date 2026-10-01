"use client";

import { ANALYSIS_SECTIONS, type AnalysisSectionId } from "@/lib/company-analysis";
import type { StageSectionView } from "@/lib/research/mapResearchView";

const groups: { title: string; items: { id: AnalysisSectionId; label: string }[] }[] = [
  { title: "Analysis", items: [
    { id: "summary", label: "Summary" }, { id: "buffett", label: "Buffett Assessment" },
    { id: "financial", label: "Financials" }, { id: "valuation", label: "Valuation" },
    { id: "quality", label: "Business Quality" }, { id: "risk", label: "Key Risks" },
  ] },
  { title: "Deep Dive", items: [
    { id: "moat", label: "Economic Moat" }, { id: "management", label: "Management" },
    { id: "earnings", label: "Earnings Quality" }, { id: "growth", label: "Growth Quality" },
    { id: "valuationTransparency", label: "Margin of Safety" }, { id: "strengths", label: "Strengths & Weaknesses" },
    { id: "explainability", label: "Investment Context" }, { id: "evidence", label: "Evidence" },
  ] },
];
const toolIds: AnalysisSectionId[] = ["ratings", "ownership", "peers", "documents", "news", "compliance", "copilot", "settings", "export"];

export function AnalysisNavigation({ active, onSelect }: { active: AnalysisSectionId; onSelect: (section: AnalysisSectionId) => void }) {
  return <nav data-testid="analysis-toc" aria-label="Analysis sections" className="space-y-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3 lg:sticky lg:top-16">
    <div className="grid grid-cols-2 gap-3 lg:block lg:space-y-5">{groups.map((group) => <div key={group.title}><p className="mb-2 px-2 font-mono text-[10px] uppercase tracking-wider text-[var(--muted)]">{group.title}</p><div className="space-y-0.5">{group.items.map((item) => <button key={item.id} data-testid={`analysis-section-${item.id}`} aria-current={active === item.id ? "location" : undefined} onClick={() => onSelect(item.id)} className={`block min-h-8 w-full rounded-md px-2 py-1.5 text-left text-[11px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${active === item.id ? "bg-[var(--accent-soft)] text-[var(--accent)]" : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"}`}>{item.label}</button>)}</div></div>)}</div>
    <label className="block border-t border-[var(--border)] pt-3 font-mono text-[10px] text-[var(--muted)]">MORE TOOLS<select data-testid="analysis-more-tools" aria-label="More research tools" value={toolIds.includes(active) ? active : ""} onChange={(event) => { if (event.target.value) onSelect(event.target.value as AnalysisSectionId); }} className="mt-2 min-h-9 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 text-[11px] text-[var(--fg)] outline-none focus:border-[var(--accent)]"><option value="">Choose a tool</option>{ANALYSIS_SECTIONS.filter((item) => toolIds.includes(item.id)).map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
  </nav>;
}

export function AnalysisStageDetails({ title, stage }: { title: string; stage: StageSectionView }) {
  return <section data-testid={`analysis-stage-${stage.stage}`} className="rounded-[14px] border border-[var(--border)] bg-[var(--surface)] p-5">
    <h2 className="font-[family-name:var(--font-display)] text-lg">{title}</h2><p className="mt-2 text-sm text-[var(--muted)]">{stage.label || "Assessment unavailable"}</p>
    <dl className="mt-5 grid gap-3 sm:grid-cols-2">{[{ label: "Assessment", value: stage.decision }, { label: "Score", value: stage.score }, { label: "Confidence", value: stage.confidence }, ...stage.metrics].map((metric, index) => <div key={`${metric.label}-${index}`} className="rounded-lg bg-[var(--surface-2)] px-4 py-3"><dt className="font-mono text-[10px] text-[var(--muted)]">{metric.label}</dt><dd className="mt-1 font-mono text-sm">{metric.value || "Unavailable"}</dd></div>)}</dl>
    {stage.warnings.length > 0 && <ul className="mt-4 list-disc space-y-1 pl-4 text-xs text-[var(--muted)]">{stage.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>}
  </section>;
}
