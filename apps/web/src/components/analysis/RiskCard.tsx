import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import type { RiskInsightView } from "@/lib/analysis/types";

export function RiskCard({ risk }: { risk: RiskInsightView }) {
  return (
    <div className="border-b border-[var(--border)] pb-5 last:border-0 last:pb-0">
      {/* Header row */}
      <div className="flex flex-wrap items-start justify-between gap-2 mb-3">
        <h4 className="font-[family-name:var(--font-display)] text-base font-semibold text-[var(--fg)] leading-snug">
          {risk.title}
        </h4>
        <span className="shrink-0 rounded border border-amber-500/30 bg-amber-500/8 px-2 py-0.5 font-mono text-xs font-semibold text-amber-700">
          {risk.severity}
        </span>
      </div>

      {/* Trust badges */}
      <div className="flex flex-wrap gap-2 mb-4">
        <ValueCategoryBadge category={risk.category} />
        <SourceBadge source={risk.source} />
      </div>

      {/* Severity / Probability / Impact — inline row, no boxes */}
      <div className="flex flex-wrap gap-x-6 gap-y-1 mb-4 text-xs">
        <Stat label="Severity" value={risk.severity} />
        <Stat label="Probability" value={risk.probability} />
        <Stat label="Impact" value={risk.impact} />
      </div>

      {/* Content blocks */}
      <div className="space-y-3 text-sm mb-4">
        <Block label="Reason">{risk.reason}</Block>
        <Block label="Mitigation">{risk.mitigation}</Block>
      </div>

      {/* Watchpoints */}
      <div className="mb-3">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] mb-1.5">
          Investor watchpoints
        </p>
        <ul className="space-y-1 text-sm text-[var(--fg)]">
          {risk.investorWatchpoints.map((w) => (
            <li key={w} className="flex gap-2">
              <span className="text-[var(--muted)] shrink-0 mt-0.5">–</span>
              <span>{w}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Supporting evidence */}
      {risk.supportingEvidence.length ? (
        <ul className="space-y-0.5 text-xs text-[var(--muted)]">
          {risk.supportingEvidence.map((e) => (
            <li key={e} className="flex gap-2">
              <span className="shrink-0">·</span>
              <span>{e}</span>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState
          title="Supporting evidence unavailable"
          description="Severity/probability/impact stay Unavailable until risk artifacts appear in the API envelope. DSP will not invent risk scores."
        />
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <span className="text-[var(--muted)]">
      <span className="font-medium uppercase tracking-wide">{label}: </span>
      <span className="font-mono text-[var(--fg)]">{value}</span>
    </span>
  );
}

function Block({ label, children }: { label: string; children: string }) {
  return (
    <div className="pl-3 border-l-2 border-[var(--border)]">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] mb-0.5">
        {label}
      </p>
      <p className="text-[var(--fg)] leading-relaxed">{children}</p>
    </div>
  );
}
