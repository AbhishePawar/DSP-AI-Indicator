"use client";

/**
 * RisksOpportunitiesSection — compact research-terminal block for the Analysis Page.
 *
 * Data sources (all existing, no new endpoints):
 *   • view.risks[]                      — RiskInsightView[] (title, severity, reason, supportingEvidence)
 *   • view.thesis.keyStrengths          — DisplayField<string[]>  (opportunities)
 *   • view.thesis.keyConcerns           — DisplayField<string[]>  (risk signals)
 *   • view.thesis.thingsToMonitor       — DisplayField<string[]>  (watchpoints)
 *   • view.dashboard.riskScore          — overall risk score
 *
 * Unavailable fields are shown clearly as "—" (never invented).
 * Does NOT duplicate primaryOpportunity/primaryRisk already shown in AIResearchSection.
 */

import type {
  AnalysisWorkspaceView,
  DisplayField,
  RiskInsightView,
} from "@/lib/analysis/types";

/* ─── Helpers ────────────────────────────────────────────────────── */

function strVal(field: DisplayField<string | number>): string {
  if (field.presence === "unavailable" || field.value == null) return "—";
  return String(field.value);
}

function arrVal(field: DisplayField<string[]>): string[] {
  if (field.presence === "unavailable" || !Array.isArray(field.value)) return [];
  return field.value;
}

function isAvail(field: DisplayField<unknown>): boolean {
  return field.presence === "available" && field.value != null;
}

/* ─── Severity colour ────────────────────────────────────────────── */

const SEVERITY_COLOURS: Record<string, string> = {
  HIGH: "text-red-400 border-red-500/40 bg-red-500/10",
  MEDIUM: "text-amber-400 border-amber-500/40 bg-amber-500/10",
  LOW: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
};

function severityClass(severity: string): string {
  return (
    SEVERITY_COLOURS[severity.toUpperCase()] ??
    "text-[var(--muted)] border-[var(--border)] bg-[var(--surface-2)]"
  );
}

/* ─── Sub-components ─────────────────────────────────────────────── */

/** Compact risk row from view.risks[] */
function RiskRow({ risk }: { risk: RiskInsightView }) {
  const hasEvidence = risk.supportingEvidence.length > 0;
  return (
    <div className="border-b border-[var(--border)] py-3 last:border-0">
      <div className="flex flex-wrap items-start gap-2">
        {/* Severity badge */}
        <span
          className={[
            "inline-flex shrink-0 items-center rounded border px-2 py-0.5 font-mono text-[10px] font-bold uppercase",
            severityClass(risk.severity),
          ].join(" ")}
        >
          {risk.severity}
        </span>
        {/* Title */}
        <span className="flex-1 text-sm font-medium text-[var(--fg)]">
          {risk.title}
        </span>
      </div>
      {/* Reason */}
      {risk.reason && risk.reason !== "—" && (
        <p className="mt-1.5 pl-0 text-xs leading-snug text-[var(--muted)]">
          {risk.reason}
        </p>
      )}
      {/* Supporting evidence */}
      {hasEvidence && (
        <ul className="mt-1.5 space-y-0.5 pl-3">
          {risk.supportingEvidence.slice(0, 2).map((e, i) => (
            <li
              key={i}
              className="flex items-start gap-1.5 text-[11px] text-[var(--muted)]"
            >
              <span className="mt-0.5 shrink-0 text-[var(--accent)]">›</span>
              <span>{e}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Compact bullet list for opportunities / concerns / watchpoints */
function BulletList({
  items,
  icon,
  iconClass,
}: {
  items: string[];
  icon: string;
  iconClass: string;
}) {
  if (items.length === 0) return null;
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-sm text-[var(--fg)]">
          <span className={["mt-0.5 shrink-0 text-xs font-bold", iconClass].join(" ")}>
            {icon}
          </span>
          <span className="leading-snug">{item}</span>
        </li>
      ))}
    </ul>
  );
}

/** Panel header */
function PanelHeader({ label, count }: { label: string; count?: number }) {
  return (
    <div className="flex items-center gap-2 border-b border-[var(--border)] pb-2 mb-3">
      <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)]">
        {label}
      </span>
      {count != null && (
        <span className="rounded bg-[var(--surface-2)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--muted)]">
          {count}
        </span>
      )}
    </div>
  );
}

/* ─── Main component ─────────────────────────────────────────────── */

export function RisksOpportunitiesSection({
  view,
}: {
  view: AnalysisWorkspaceView;
}) {
  const { risks, thesis, dashboard } = view;

  /* ── Risks from view.risks[] ──────────────────────────────────── */
  const availableRisks = risks.filter((r) => r.available);
  const hasRisks = availableRisks.length > 0;

  /* ── Opportunities from thesis.keyStrengths ───────────────────── */
  const strengths = arrVal(thesis.keyStrengths);
  const hasStrengths = strengths.length > 0;

  /* ── Risk signals from thesis.keyConcerns ─────────────────────── */
  const concerns = arrVal(thesis.keyConcerns);
  const hasConcerns = concerns.length > 0;

  /* ── Watchpoints from thesis.thingsToMonitor ──────────────────── */
  const watchpoints = arrVal(thesis.thingsToMonitor);
  const hasWatchpoints = watchpoints.length > 0;

  /* ── Risk score from dashboard ────────────────────────────────── */
  const riskScoreRaw = strVal(dashboard.riskScore);
  const riskScoreAvail = isAvail(dashboard.riskScore);

  /* ── Nothing available at all ─────────────────────────────────── */
  const nothingAvailable =
    !hasRisks && !hasStrengths && !hasConcerns && !hasWatchpoints;

  return (
    <div className="space-y-3">
      {/* ── Terminal header ──────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)]">
          Risks &amp; Opportunities Terminal
        </span>
        <div className="flex items-center gap-3">
          {riskScoreAvail && (
            <span className="flex items-center gap-1.5">
              <span className="text-[10px] font-medium uppercase tracking-widest text-[var(--muted)]">
                Risk Score
              </span>
              <span className="font-mono text-sm font-bold text-[var(--fg)]">
                {riskScoreRaw}
              </span>
            </span>
          )}
          <span className="text-[10px] font-mono text-[var(--muted)]">
            DSP Research Engine · Deterministic
          </span>
        </div>
      </div>

      {nothingAvailable ? (
        /* ── Unavailable state ─────────────────────────────────── */
        <div className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-4 py-6 text-center">
          <p className="font-mono text-sm text-[var(--muted)]">
            Risks &amp; Opportunities data unavailable — run analysis to populate.
          </p>
        </div>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {/* ── LEFT: Opportunities ──────────────────────────────── */}
          <div className="rounded border border-emerald-500/20 bg-emerald-500/5 p-4">
            <PanelHeader
              label="Key Opportunities"
              count={hasStrengths ? strengths.length : undefined}
            />
            {hasStrengths ? (
              <BulletList
                items={strengths}
                icon="▲"
                iconClass="text-emerald-400"
              />
            ) : (
              <p className="font-mono text-xs text-[var(--muted)]">
                — Key opportunities unavailable
              </p>
            )}
          </div>

          {/* ── RIGHT: Key Risks (thesis concerns) ───────────────── */}
          <div className="rounded border border-red-500/20 bg-red-500/5 p-4">
            <PanelHeader
              label="Key Concerns"
              count={hasConcerns ? concerns.length : undefined}
            />
            {hasConcerns ? (
              <BulletList
                items={concerns}
                icon="▼"
                iconClass="text-red-400"
              />
            ) : (
              <p className="font-mono text-xs text-[var(--muted)]">
                — Key concerns unavailable
              </p>
            )}
          </div>
        </div>
      )}

      {/* ── Risk detail rows from view.risks[] ───────────────────── */}
      {hasRisks && (
        <div className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3">
          <PanelHeader
            label="Risk Detail"
            count={availableRisks.length}
          />
          <div className="divide-y divide-[var(--border)]">
            {availableRisks.map((risk) => (
              <RiskRow key={risk.id} risk={risk} />
            ))}
          </div>
        </div>
      )}

      {/* ── Watchpoints ──────────────────────────────────────────── */}
      {hasWatchpoints && (
        <div className="rounded border border-amber-500/20 bg-amber-500/5 px-4 py-3">
          <PanelHeader
            label="Things to Monitor"
            count={watchpoints.length}
          />
          <BulletList
            items={watchpoints}
            icon="◈"
            iconClass="text-amber-400"
          />
        </div>
      )}

      {/* ── Provenance footer ─────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-[10px] text-[var(--muted)]">
        <span>
          <span className="font-bold">Sources:</span> view.risks · view.thesis.keyStrengths · view.thesis.keyConcerns · view.thesis.thingsToMonitor · view.dashboard.riskScore
        </span>
        <span className="ml-auto font-mono">Real data only · No invented values</span>
      </div>
    </div>
  );
}
