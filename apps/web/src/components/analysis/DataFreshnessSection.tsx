"use client";

/**
 * DataFreshnessSection — compact research-terminal Data Freshness & Reliability block.
 *
 * Shows analysis freshness/reliability state using ONLY existing real data:
 *   • view.freshness   — researchDate, lastUpdated, dataCurrency, analysisVersion,
 *                        methodologyVersion, researchMode
 *   • view.coverage    — coveragePercent, evidenceStrength, availableMetrics, unavailableMetrics
 *   • view.conclusion  — researchConfidence, researchHealth
 *   • view.methodologyPanel — analysisVersion, calculationVersion, presentationVersion
 *   • view.transparencyPanel — estimatedFields, unavailableData, aiGeneratedSections, externalSources
 *   • view.reportId    — report provenance ID
 *   • view.apiOk       — API/cache status
 *
 * Rules:
 *   - Never invent or mock data.
 *   - Unavailable fields shown as "—" or "Unavailable".
 *   - No new backend endpoints.
 *   - No browser Date/time used to infer freshness.
 */

import type {
  AnalysisWorkspaceView,
  DisplayField,
} from "@/lib/analysis/types";

/* ─── Helpers ────────────────────────────────────────────────────── */

function fv(field: DisplayField<string | number> | undefined): string {
  if (!field || field.presence !== "available" || field.value == null) return "—";
  return String(field.value);
}

function str(v: string | null | undefined): string {
  if (!v || v.trim() === "") return "—";
  return v;
}

/* ─── Terminal row ───────────────────────────────────────────────── */

function TermRow({
  label,
  value,
  mono = true,
  valueClass,
}: {
  label: string;
  value: string;
  mono?: boolean;
  valueClass?: string;
}) {
  const isUnavail = value === "—" || value === "Unavailable";
  return (
    <div className="grid grid-cols-[auto_1fr] items-start gap-x-4 border-b border-[var(--border)] py-2 last:border-0">
      <span className="whitespace-nowrap text-[10px] font-bold uppercase tracking-widest text-[var(--muted)]">
        {label}
      </span>
      <span
        className={[
          "text-right text-sm leading-snug",
          mono ? "font-mono" : "font-normal",
          isUnavail
            ? "text-[var(--muted)] italic"
            : (valueClass ?? "text-[var(--fg)]"),
        ].join(" ")}
      >
        {value}
      </span>
    </div>
  );
}

/* ─── Section header ─────────────────────────────────────────────── */

function BlockHeader({ title }: { title: string }) {
  return (
    <div className="mb-2 flex items-center gap-2">
      <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--accent)]">
        {title}
      </span>
      <div className="h-px flex-1 bg-[var(--border)]" />
    </div>
  );
}

/* ─── Coverage bar ───────────────────────────────────────────────── */

function CoverageBar({ pct }: { pct: number }) {
  const clamped = Math.max(0, Math.min(100, pct));
  const colour =
    clamped >= 75
      ? "bg-emerald-500"
      : clamped >= 40
        ? "bg-amber-500" :"bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--surface-2)]">
        <div
          className={`h-full rounded-full transition-all ${colour}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <span className="w-8 text-right font-mono text-xs text-[var(--fg)]">
        {clamped}%
      </span>
    </div>
  );
}

/* ─── Confidence / reliability pill ─────────────────────────────── */

const CONFIDENCE_STYLE: Record<string, string> = {
  HIGH: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  MEDIUM: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  LOW: "bg-red-500/15 text-red-400 border-red-500/30",
};

function ConfidencePill({ level }: { level: string }) {
  if (!level || level === "—") {
    return (
      <span className="rounded border border-dashed border-[var(--border)] px-2 py-0.5 text-[10px] font-mono text-[var(--muted)] italic">
        Unavailable
      </span>
    );
  }
  const key = level.toUpperCase();
  const style =
    CONFIDENCE_STYLE[key] ??
    "bg-[var(--surface-2)] text-[var(--fg)] border-[var(--border)]";
  return (
    <span
      className={`rounded border px-2 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider ${style}`}
    >
      {level}
    </span>
  );
}

/* ─── API / cache status badge ───────────────────────────────────── */

function StatusBadge({ ok }: { ok: boolean }) {
  return ok ? (
    <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-mono font-semibold text-emerald-400">
      LIVE
    </span>
  ) : (
    <span className="rounded border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[10px] font-mono font-semibold text-red-400">
      STALE / ERROR
    </span>
  );
}

/* ─── Main component ─────────────────────────────────────────────── */

export function DataFreshnessSection({
  view,
}: {
  view: AnalysisWorkspaceView;
}) {
  const { freshness, coverage, conclusion, methodologyPanel, transparencyPanel, reportId, apiOk } = view;

  /* Confidence / health */
  const confidence = fv(conclusion.researchConfidence as DisplayField<string>);
  const health = fv(conclusion.researchHealth);

  /* Coverage */
  const coveragePct = coverage.coveragePercent ?? 0;
  const evidenceStrength = coverage.evidenceStrength ?? "—";
  const availMetrics = coverage.availableMetrics ?? 0;
  const unavailMetrics = coverage.unavailableMetrics ?? 0;

  /* Freshness */
  const researchDate = str(freshness.researchDate);
  const lastUpdated = str(freshness.lastUpdated);
  const dataCurrency = str(freshness.dataCurrency);
  const researchMode = str(freshness.researchMode);

  /* Provenance / methodology */
  const analysisVer = str(freshness.analysisVersion || methodologyPanel.analysisVersion);
  const methodologyVer = str(freshness.methodologyVersion || methodologyPanel.calculationVersion);
  const presentationVer = str(methodologyPanel.presentationVersion);
  const reportIdStr = str(reportId);

  /* Transparency */
  const estimatedCount = transparencyPanel.estimatedFields?.length ?? 0;
  const unavailDataCount = transparencyPanel.unavailableData?.length ?? 0;
  const aiSectionsCount = transparencyPanel.aiGeneratedSections?.length ?? 0;
  const externalSourcesCount = transparencyPanel.externalSources?.length ?? 0;

  return (
    <div className="space-y-5 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 font-mono text-sm">
      {/* ── Header bar ──────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-3">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--accent)]">
            Data Freshness &amp; Reliability
          </span>
          <StatusBadge ok={apiOk} />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[var(--muted)]">Confidence</span>
          <ConfidencePill level={confidence} />
        </div>
      </div>

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {/* ── Block 1: Freshness / As-Of ──────────────────────── */}
        <div>
          <BlockHeader title="Freshness / As-Of" />
          <div className="space-y-0">
            <TermRow label="Research Date" value={researchDate} />
            <TermRow label="Last Updated" value={lastUpdated} />
            <TermRow label="Data Currency" value={dataCurrency} mono={false} />
            <TermRow label="Research Mode" value={researchMode} mono={false} />
          </div>
        </div>

        {/* ── Block 2: Coverage & Evidence ────────────────────── */}
        <div>
          <BlockHeader title="Coverage &amp; Evidence" />
          <div className="mb-2">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)]">
                Coverage
              </span>
              <span className="text-[10px] text-[var(--muted)]">
                {availMetrics} available / {unavailMetrics} unavailable
              </span>
            </div>
            <CoverageBar pct={coveragePct} />
          </div>
          <div className="space-y-0">
            <TermRow
              label="Evidence Strength"
              value={evidenceStrength}
              mono={false}
            />
            <TermRow
              label="Research Health"
              value={health}
              mono={false}
            />
          </div>
        </div>

        {/* ── Block 3: Provenance / Source ────────────────────── */}
        <div>
          <BlockHeader title="Provenance / Source" />
          <div className="space-y-0">
            <TermRow label="Report ID" value={reportIdStr} />
            <TermRow label="Analysis Ver." value={analysisVer} />
            <TermRow label="Methodology Ver." value={methodologyVer} />
            <TermRow label="Presentation Ver." value={presentationVer} />
          </div>
        </div>
      </div>

      {/* ── Block 4: Transparency indicators ──────────────────── */}
      <div>
        <BlockHeader title="Transparency Indicators" />
        <div className="grid grid-cols-2 gap-x-6 gap-y-0 sm:grid-cols-4">
          <TermRow
            label="Estimated Fields"
            value={estimatedCount > 0 ? String(estimatedCount) : "—"}
          />
          <TermRow
            label="Unavailable Data"
            value={unavailDataCount > 0 ? String(unavailDataCount) : "—"}
          />
          <TermRow
            label="AI-Generated Sections"
            value={aiSectionsCount > 0 ? String(aiSectionsCount) : "—"}
          />
          <TermRow
            label="External Sources"
            value={externalSourcesCount > 0 ? String(externalSourcesCount) : "—"}
          />
        </div>
      </div>

      {/* ── Provenance footer ─────────────────────────────────── */}
      <p className="border-t border-[var(--border)] pt-2 text-[10px] leading-relaxed text-[var(--muted)]">
        Source: DSP AI Indicator — /api/v1/analyse display snapshot only. No
        client-side scoring. Freshness inferred solely from API response fields;
        browser time is not used.
      </p>
    </div>
  );
}
