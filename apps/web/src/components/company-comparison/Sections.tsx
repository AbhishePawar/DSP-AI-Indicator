"use client";

import { useMemo, useState, type ReactNode } from "react";

import { Badge, Button, Input, Textarea } from "@/components/ds";
import {
  BUFFETT_FRAMEWORK_PREFIX,
  COMPARISON_SECTIONS,
  DECISION_WORKFLOW_STEPS,
  FUTURE_ARCHITECTURE_NOTES,
  INSTITUTIONAL_UX_QUESTIONS,
  PLANNED_SUBJECT_KINDS,
  REVIEW_MODES,
  SUPPORTED_SUBJECT_KINDS_V1,
  WEIGHTING_PROFILES,
  committeeMemoToHtml,
  committeeMemoToJson,
  comparisonToCsv,
  comparisonToHtml,
  comparisonToJson,
  describeFutureAdapter,
  downloadText,
  nextWorkflowStep,
  prevWorkflowStep,
  useComparisonHistoryStore,
  useComparisonPrefsStore,
  type ComparisonWorkspaceModel,
  type WeightingProfileId,
} from "@/lib/company-comparison";
import { cn } from "@/lib/utils";
import {
  AlignmentBadge,
  FieldRow,
  HeatCell,
  MedalBadge,
  SectionCard,
} from "./Primitives";

function emphasisClass(
  emphasis: "highlight" | "normal" | "deemphasize",
): string {
  if (emphasis === "highlight") {
    return "bg-[var(--accent-soft)]/40 ring-1 ring-[var(--accent)]/30";
  }
  if (emphasis === "deemphasize") {
    return "opacity-70";
  }
  return "";
}

function SymbolGrid({
  symbols,
  children,
}: {
  symbols: string[];
  children: (symbol: string) => ReactNode;
}) {
  return (
    <div
      className="grid gap-3"
      style={{
        gridTemplateColumns: `repeat(${Math.min(symbols.length, 5)}, minmax(0, 1fr))`,
      }}
    >
      {symbols.map((s) => (
        <div key={s}>{children(s)}</div>
      ))}
    </div>
  );
}

export function ExecutiveSummarySection({
  model,
}: {
  model: ComparisonWorkspaceModel;
}) {
  const e = model.executive;
  return (
    <SectionCard
      title="Executive Summary"
      description="Institutional overview — assists decisions, never makes them."
    >
      <dl className="space-y-1">
        <FieldRow label="Overall" value={e.overall} />
        <FieldRow label="Institutional summary" value={e.institutionalSummary} />
        <FieldRow label="Winner summary" value={e.winnerSummary} />
        <FieldRow label="Confidence" value={e.confidence} />
        <FieldRow label="Coverage" value={e.coverage} />
        <FieldRow label="Evidence quality" value={e.evidenceQuality} />
        <FieldRow
          label="Weighting profile"
          value={`${model.weightingProfileId} (presentation emphasis only)`}
        />
      </dl>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
        {e.tradeOffs.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>
      <div className="mt-4">
        <p className="mb-2 text-xs font-medium text-[var(--muted)]">
          Institutional review questions
        </p>
        <ul className="flex flex-wrap gap-2">
          {INSTITUTIONAL_UX_QUESTIONS.map((q) => (
            <li key={q}>
              <Badge variant="outline">{q}</Badge>
            </li>
          ))}
        </ul>
      </div>
    </SectionCard>
  );
}

export function ExecutiveScorecardSection({
  model,
}: {
  model: ComparisonWorkspaceModel;
}) {
  const symbols = model.symbols.filter((s) =>
    model.scorecard.some((r) => r.cells.some((c) => c.symbol === s)),
  );
  const cols = symbols.length ? symbols : model.symbols;

  return (
    <SectionCard
      title="Executive Comparison Scorecard"
      description="Institutional scorecard from existing research outputs. Highlighting reflects presentation weighting only — scores are never recalculated."
    >
      <p className="mb-3 text-xs text-[var(--muted)]">
        Active weighting: {model.weightingProfileId} · presentation emphasis only
      </p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[36rem] border-collapse text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left">
              <th className="py-2 pr-3 font-medium">Metric</th>
              {cols.map((s) => (
                <th key={s} className="px-2 py-2 font-medium">
                  {s}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {model.scorecard.map((row) => (
              <tr
                key={row.id}
                className={cn(
                  "border-b border-[var(--border)] align-top",
                  emphasisClass(row.emphasis),
                )}
              >
                <td className="py-2 pr-3 text-[var(--muted)]">{row.label}</td>
                {cols.map((sym) => {
                  const cell = row.cells.find((c) => c.symbol === sym);
                  return (
                    <td key={sym} className="px-2 py-2">
                      <span>{cell?.display ?? "Data unavailable."}</span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}

export function EvidenceStrengthSection({
  model,
}: {
  model: ComparisonWorkspaceModel;
}) {
  return (
    <SectionCard
      title="Evidence Strength Meter"
      description="Strong / Moderate / Limited / Data unavailable. — from coverage, freshness, completeness, source quality, and research confidence only."
    >
      <SymbolGrid symbols={model.evidenceStrength.map((e) => e.symbol)}>
        {(symbol) => {
          const e = model.evidenceStrength.find((x) => x.symbol === symbol)!;
          return (
            <div className="rounded-md border border-[var(--border)] p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="font-medium">{symbol}</p>
                <Badge
                  variant={
                    e.level === "Strong"
                      ? "accent"
                      : e.level === "Moderate"
                        ? "default"
                        : "outline"
                  }
                >
                  {e.level}
                </Badge>
              </div>
              <dl>
                <FieldRow label="Coverage" value={e.coverage} />
                <FieldRow label="Freshness" value={e.freshness} />
                <FieldRow label="Completeness" value={e.completeness} />
                <FieldRow label="Source quality" value={e.sourceQuality} />
                <FieldRow
                  label="Research confidence"
                  value={e.researchConfidence}
                />
              </dl>
              <p className="mt-2 text-xs text-[var(--muted)]">{e.rationale}</p>
            </div>
          );
        }}
      </SymbolGrid>
    </SectionCard>
  );
}

export function ContradictoryEvidenceSection({
  model,
}: {
  model: ComparisonWorkspaceModel;
}) {
  return (
    <SectionCard
      title="Contradictory Evidence Panel"
      description="Supporting and contradictory evidence side-by-side. Conflicts are never hidden."
    >
      <div className="space-y-4">
        {model.contradictoryEvidence.map((cell) => (
          <div
            key={cell.symbol}
            className="rounded-md border border-[var(--border)] p-3"
          >
            <p className="font-medium">{cell.symbol}</p>
            <dl className="mt-2">
              <FieldRow label="Coverage" value={cell.coverage} />
              <FieldRow label="Confidence" value={cell.confidence} />
              <FieldRow label="Source quality" value={cell.sourceQuality} />
            </dl>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <div>
                <p className="mb-1 text-xs font-semibold text-[var(--fg)]">
                  Supporting
                </p>
                <ul className="list-disc space-y-1 pl-5 text-sm">
                  {cell.supporting.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="mb-1 text-xs font-semibold text-[var(--fg)]">
                  Contradictory
                </p>
                <ul className="list-disc space-y-1 pl-5 text-sm">
                  {cell.contradictory.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </div>
            </div>
            <p className="mt-2 text-xs text-[var(--muted)]">{cell.honestyNote}</p>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

export function WhyNotSection({ model }: { model: ComparisonWorkspaceModel }) {
  return (
    <SectionCard
      title="Why Not Analysis"
      description="Evidence-backed reasons each company is not preferred. Never generic when differentials exist. Platform never decides."
    >
      <div className="space-y-4">
        {model.whyNot.map((item) => (
          <div
            key={item.symbol}
            className="rounded-md border border-[var(--border)] p-3"
          >
            <p className="font-medium">{item.symbol}</p>
            <ul className="mt-2 space-y-2">
              {item.reasons.map((r, i) => (
                <li
                  key={`${item.symbol}-${i}`}
                  className="rounded border border-[var(--border)] p-2 text-sm"
                >
                  <Badge variant="outline">{r.dimension}</Badge>
                  <p className="mt-1">{r.reason}</p>
                  <p className="mt-1 text-xs text-[var(--muted)]">
                    Evidence: {r.evidence}
                  </p>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-[var(--muted)]">{item.note}</p>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

export function CommitteeMemoSection({
  model,
}: {
  model: ComparisonWorkspaceModel;
}) {
  const memo = model.committeeMemo;
  const stamp = model.symbols.join("-") || "memo";

  return (
    <SectionCard
      title="Investment Committee Memo"
      description="Executive Committee Memo assembled from existing comparison outputs. Assists review — never produces the investment decision."
    >
      <dl className="mb-3 space-y-1">
        <FieldRow label="Title" value={memo.title} />
        <FieldRow label="Companies" value={memo.companies.join(", ")} />
        <FieldRow label="Summary" value={memo.executiveSummary} />
        <FieldRow label="Winner Matrix" value={memo.winnerMatrixSummary} />
        <FieldRow label="Confidence" value={memo.confidence} />
      </dl>
      <div className="space-y-3 text-sm">
        <div>
          <p className="font-medium">Trade-offs</p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {memo.tradeOffs.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <p className="font-medium">Supporting evidence</p>
            <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
              {memo.supportingEvidence.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="font-medium">Contradictory evidence</p>
            <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
              {memo.contradictoryEvidence.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </div>
        </div>
        <div>
          <p className="font-medium">Buffett-style summary</p>
          <p className="mt-1 text-[var(--muted)]">{memo.buffettSummary}</p>
        </div>
        <div>
          <p className="font-medium">Outstanding questions</p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {memo.outstandingQuestions.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="font-medium">Decision notes (user-authored)</p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {memo.decisionNotes.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          size="sm"
          onClick={() =>
            downloadText(
              `dsp-ic-memo-${stamp}.json`,
              committeeMemoToJson(model),
              "application/json",
            )
          }
        >
          Export memo JSON
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => {
            const html = committeeMemoToHtml(memo);
            const w = window.open("", "_blank");
            if (!w) return;
            w.document.write(html);
            w.document.close();
            w.focus();
            w.print();
          }}
        >
          Print / PDF memo
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled
          title="Native DOCX not available in current export patterns"
        >
          DOCX unavailable
        </Button>
      </div>
      <p className="mt-2 text-xs text-[var(--muted)]">{memo.exportNote}</p>
    </SectionCard>
  );
}

export function SectorContextSection({
  model,
}: {
  model: ComparisonWorkspaceModel;
}) {
  return (
    <SectionCard
      title="Sector Context"
      description="Sector/industry labels when available. Authenticated medians/relatives require API support — otherwise Data unavailable."
    >
      <SymbolGrid symbols={model.sectorContext.map((s) => s.symbol)}>
        {(symbol) => {
          const s = model.sectorContext.find((x) => x.symbol === symbol)!;
          return (
            <div className="rounded-md border border-[var(--border)] p-3">
              <p className="mb-2 font-medium">{symbol}</p>
              <dl>
                <FieldRow label="Sector" value={s.sector} />
                <FieldRow label="Industry" value={s.industry} />
                <FieldRow label="Sector median" value={s.sectorMedian} />
                <FieldRow label="Industry median" value={s.industryMedian} />
                <FieldRow label="Relative position" value={s.relativePosition} />
              </dl>
              <p className="mt-2 text-xs text-[var(--muted)]">{s.note}</p>
            </div>
          );
        }}
      </SymbolGrid>
    </SectionCard>
  );
}

export function SensitivitySection({
  model,
}: {
  model: ComparisonWorkspaceModel;
}) {
  return (
    <SectionCard
      title="Sensitivity Panel"
      description="Coverage / evidence / confidence sensitivity when certified — otherwise Analysis unavailable."
    >
      <SymbolGrid symbols={model.sensitivity.map((s) => s.symbol)}>
        {(symbol) => {
          const s = model.sensitivity.find((x) => x.symbol === symbol)!;
          return (
            <div className="rounded-md border border-[var(--border)] p-3">
              <p className="mb-2 font-medium">{symbol}</p>
              <dl>
                <FieldRow label="Coverage input" value={s.coverageInput} />
                <FieldRow label="Evidence input" value={s.evidenceInput} />
                <FieldRow label="Confidence input" value={s.confidenceInput} />
                <FieldRow
                  label="Coverage sensitivity"
                  value={s.coverageSensitivity}
                />
                <FieldRow
                  label="Evidence sensitivity"
                  value={s.evidenceSensitivity}
                />
                <FieldRow
                  label="Confidence sensitivity"
                  value={s.confidenceSensitivity}
                />
              </dl>
              <p className="mt-2 text-xs text-[var(--muted)]">{s.note}</p>
            </div>
          );
        }}
      </SymbolGrid>
    </SectionCard>
  );
}

export function WeightingProfilesSection({
  model,
}: {
  model: ComparisonWorkspaceModel;
}) {
  const { weightingProfileId, setWeightingProfileId } =
    useComparisonPrefsStore();
  const active = WEIGHTING_PROFILES.find((p) => p.id === weightingProfileId);

  return (
    <SectionCard
      title="Comparison Weighting Profiles"
      description="Equal / Quality / Value / Growth / Conservative / Buffett-style — presentation emphasis only. Analytical outputs never change."
    >
      <div className="flex flex-wrap gap-2">
        {WEIGHTING_PROFILES.map((p) => (
          <Button
            key={p.id}
            size="sm"
            variant={weightingProfileId === p.id ? "default" : "secondary"}
            aria-pressed={weightingProfileId === p.id}
            onClick={() => setWeightingProfileId(p.id as WeightingProfileId)}
          >
            {p.label}
          </Button>
        ))}
      </div>
      {active ? (
        <p className="mt-3 text-sm text-[var(--muted)]">{active.description}</p>
      ) : null}
      <p className="mt-2 text-xs text-[var(--muted)]">
        Model weighting id: {model.weightingProfileId}. Scorecard highlighting
        updates for emphasis; Winner Matrix numeric cells remain identical.
      </p>
    </SectionCard>
  );
}

export function ComparisonHistorySection() {
  const entries = useComparisonHistoryStore((s) => s.entries);
  const search = useComparisonHistoryStore((s) => s.search);
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => search(query), [search, query]);

  return (
    <SectionCard
      title="Comparison History"
      description="Immutable append-only timeline of comparisons. Past entries are never edited."
    >
      <Input
        aria-label="Search comparison history"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Filter by symbol, winner, version…"
      />
      {filtered.length === 0 ? (
        <p className="mt-3 text-sm text-[var(--muted)]">
          {entries.length === 0
            ? "No history yet — run a comparison to append an immutable snapshot."
            : "No history matches this filter."}
        </p>
      ) : (
        <ol className="mt-3 space-y-2">
          {filtered.map((e) => (
            <li
              key={e.id}
              className="rounded-md border border-[var(--border)] p-3 text-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium">{e.symbols.join(" · ")}</span>
                <Badge variant="outline">immutable</Badge>
              </div>
              <dl className="mt-2">
                <FieldRow label="Date" value={new Date(e.at).toLocaleString()} />
                <FieldRow label="Research version" value={e.researchVersion} />
                <FieldRow label="Confidence" value={e.confidence} />
                <FieldRow label="Winner" value={e.winnerSummary} />
                <FieldRow label="Changes" value={e.changes} />
              </dl>
            </li>
          ))}
        </ol>
      )}
    </SectionCard>
  );
}

export function DecisionWorkspaceSection({
  model,
  onNavigateSection,
}: {
  model: ComparisonWorkspaceModel;
  onNavigateSection?: (sectionId: string) => void;
}) {
  const { workflowStep, setWorkflowStep, setActiveSection } =
    useComparisonPrefsStore();
  const step =
    DECISION_WORKFLOW_STEPS.find((s) => s.id === workflowStep) ??
    DECISION_WORKFLOW_STEPS[0]!;
  const prev = prevWorkflowStep(step.id);
  const next = nextWorkflowStep(step.id);

  const go = (target: typeof step) => {
    setWorkflowStep(target.id);
    setActiveSection(target.sectionId);
    onNavigateSection?.(target.sectionId);
  };

  return (
    <SectionCard
      title="Decision Workspace"
      description="Guided workflow: Comparison → Winner → Trade-offs → Contradictory → Buffett → RI → Notes → Thesis → Decision Memo → Export. The platform never produces the investment decision."
    >
      <ol className="mb-4 flex flex-wrap gap-2">
        {DECISION_WORKFLOW_STEPS.map((s, i) => (
          <li key={s.id}>
            <Button
              size="sm"
              variant={s.id === step.id ? "default" : "ghost"}
              aria-current={s.id === step.id ? "step" : undefined}
              onClick={() => go(s)}
            >
              {i + 1}. {s.label}
            </Button>
          </li>
        ))}
      </ol>
      <p className="text-sm font-medium">{step.label}</p>
      <p className="mt-1 text-sm text-[var(--muted)]">{step.description}</p>
      {step.userOwned ? (
        <p className="mt-2 text-xs text-[var(--muted)]">
          User-owned step — your notes/thesis/decision memo. Platform assists
          only.
        </p>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="secondary"
          disabled={!prev}
          onClick={() => prev && go(prev)}
        >
          Previous
        </Button>
        <Button
          size="sm"
          disabled={!next}
          onClick={() => next && go(next)}
        >
          Next
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            setActiveSection(step.sectionId);
            onNavigateSection?.(step.sectionId);
          }}
        >
          Open section
        </Button>
      </div>
      <ul className="mt-4 flex flex-wrap gap-2">
        {model.institutionalQuestions.map((q) => (
          <li key={q}>
            <Badge variant="outline">{q}</Badge>
          </li>
        ))}
      </ul>
    </SectionCard>
  );
}

export function ReviewModeControls() {
  const { reviewMode, setReviewMode } = useComparisonPrefsStore();
  return (
    <div
      className="flex flex-wrap items-center gap-2"
      role="group"
      aria-label="Institutional review mode"
    >
      <span className="text-xs text-[var(--muted)]">Review mode:</span>
      {REVIEW_MODES.map((m) => (
        <Button
          key={m.id}
          size="sm"
          variant={reviewMode === m.id ? "default" : "ghost"}
          aria-pressed={reviewMode === m.id}
          title={m.description}
          onClick={() => setReviewMode(m.id)}
        >
          {m.label}
        </Button>
      ))}
    </div>
  );
}

export function WinnerMatrixSection({
  model,
}: {
  model: ComparisonWorkspaceModel;
}) {
  const symbols = model.symbols.filter((s) =>
    model.winnerMatrix.some((r) => r.cells.some((c) => c.symbol === s)),
  );
  const cols = symbols.length ? symbols : model.symbols;

  return (
    <SectionCard
      title="Winner Matrix"
      description="Medals only where server-provided scores exist. Missing fields stay Data unavailable."
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[36rem] border-collapse text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left">
              <th className="py-2 pr-3 font-medium">Dimension</th>
              {cols.map((s) => (
                <th key={s} className="px-2 py-2 font-medium">
                  {s}
                </th>
              ))}
              <th className="py-2 pl-2 font-medium">Leader</th>
            </tr>
          </thead>
          <tbody>
            {model.winnerMatrix.map((row) => (
              <tr
                key={row.id}
                className="border-b border-[var(--border)] align-top"
              >
                <td className="py-2 pr-3 text-[var(--muted)]">{row.label}</td>
                {cols.map((sym) => {
                  const cell = row.cells.find((c) => c.symbol === sym);
                  return (
                    <td key={sym} className="px-2 py-2">
                      <span>{cell?.display ?? "Data unavailable."}</span>
                      <MedalBadge medal={cell?.medal ?? null} />
                    </td>
                  );
                })}
                <td className="py-2 pl-2 font-medium">{row.leader}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}

export function TradeOffSection({ model }: { model: ComparisonWorkspaceModel }) {
  return (
    <SectionCard
      title="Trade-off Analysis"
      description="Every conclusion is grounded in existing research outputs only."
    >
      {model.tradeOffs.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
      ) : (
        <ul className="space-y-3">
          {model.tradeOffs.map((t, i) => (
            <li
              key={`${t.dimension}-${i}`}
              className="rounded-md border border-[var(--border)] p-3"
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="default">{t.dimension}</Badge>
                {t.stronger !== "Data unavailable." ? (
                  <span className="text-xs text-[var(--muted)]">
                    Stronger: {t.stronger}
                    {t.weaker !== "Data unavailable."
                      ? ` · Weaker: ${t.weaker}`
                      : ""}
                  </span>
                ) : null}
              </div>
              <p className="mt-2 text-sm">{t.summary}</p>
              <ul className="mt-2 list-disc pl-5 text-xs text-[var(--muted)]">
                {t.evidence.slice(0, 4).map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

export function ValuationSection({ model }: { model: ComparisonWorkspaceModel }) {
  return (
    <SectionCard
      title="Valuation Comparison"
      description="IV, Price, MoS, and method cards from existing valuation transparency — never recalculated."
    >
      <SymbolGrid symbols={model.valuation.map((v) => v.symbol)}>
        {(symbol) => {
          const v = model.valuation.find((x) => x.symbol === symbol)!;
          return (
            <div className="rounded-md border border-[var(--border)] p-3">
              <p className="mb-2 font-medium">{symbol}</p>
              <dl>
                <FieldRow label="Intrinsic value" value={v.intrinsicValue} />
                <FieldRow label="Price" value={v.price} />
                <FieldRow label="Margin of safety" value={v.marginOfSafety} />
                <FieldRow label="DCF" value={v.dcf} />
                <FieldRow label="Relative" value={v.relative} />
                <FieldRow label="Residual income" value={v.residualIncome} />
                <FieldRow label="EPV" value={v.epv} />
                <FieldRow label="Overall" value={v.overall} />
                <FieldRow label="Confidence" value={v.confidence} />
                <FieldRow label="Historical" value={v.historical} />
              </dl>
            </div>
          );
        }}
      </SymbolGrid>
    </SectionCard>
  );
}

function QualityModuleSection({
  title,
  description,
  rows,
}: {
  title: string;
  description: string;
  rows: { symbol: string; score: string; label: string; confidence: string }[];
}) {
  return (
    <SectionCard title={title} description={description}>
      <SymbolGrid symbols={rows.map((r) => r.symbol)}>
        {(symbol) => {
          const r = rows.find((x) => x.symbol === symbol)!;
          return (
            <div className="rounded-md border border-[var(--border)] p-3">
              <p className="mb-2 font-medium">{symbol}</p>
              <dl>
                <FieldRow label="Score" value={r.score} />
                <FieldRow label="Label" value={r.label} />
                <FieldRow label="Confidence" value={r.confidence} />
              </dl>
            </div>
          );
        }}
      </SymbolGrid>
    </SectionCard>
  );
}

export function BusinessQualitySection({
  model,
}: {
  model: ComparisonWorkspaceModel;
}) {
  return (
    <QualityModuleSection
      title="Business Quality"
      description="business_quality_aggregator stage only."
      rows={model.qualityModules.businessQuality}
    />
  );
}

export function ManagementSection({
  model,
}: {
  model: ComparisonWorkspaceModel;
}) {
  return (
    <QualityModuleSection
      title="Management"
      description="management_quality stage only."
      rows={model.qualityModules.management}
    />
  );
}

export function MoatSection({ model }: { model: ComparisonWorkspaceModel }) {
  return (
    <QualityModuleSection
      title="Economic Moat"
      description="economic_moat stage only."
      rows={model.qualityModules.moat}
    />
  );
}

export function RiskSection({ model }: { model: ComparisonWorkspaceModel }) {
  return (
    <QualityModuleSection
      title="Risk"
      description="Engine-supplied risk fields only — never aliased from unrelated stages."
      rows={model.qualityModules.risk}
    />
  );
}

export function FinancialSection({
  model,
}: {
  model: ComparisonWorkspaceModel;
}) {
  return (
    <QualityModuleSection
      title="Financial Strength"
      description="financial_strength stage only."
      rows={model.qualityModules.financial}
    />
  );
}

export function EvidenceSection({ model }: { model: ComparisonWorkspaceModel }) {
  return (
    <SectionCard
      title="Evidence Comparison"
      description="Evidence counts, confidence, sources, coverage, freshness from analyse metadata."
    >
      <SymbolGrid symbols={model.evidence.map((e) => e.symbol)}>
        {(symbol) => {
          const e = model.evidence.find((x) => x.symbol === symbol)!;
          return (
            <div className="rounded-md border border-[var(--border)] p-3">
              <p className="mb-2 font-medium">{symbol}</p>
              <dl>
                <FieldRow label="Evidence count" value={e.evidenceCount} />
                <FieldRow label="Confidence" value={e.confidence} />
                <FieldRow label="Coverage" value={e.coverage} />
                <FieldRow label="Freshness" value={e.freshness} />
                <FieldRow label="Status" value={e.status} />
              </dl>
              <ul className="mt-2 list-disc pl-5 text-xs text-[var(--muted)]">
                {e.sources.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </div>
          );
        }}
      </SymbolGrid>
    </SectionCard>
  );
}

export function ExplainabilitySection({
  model,
}: {
  model: ComparisonWorkspaceModel;
}) {
  return (
    <SectionCard
      title="Explainability Comparison"
      description="Side-by-side institutional explainability summaries — existing modules only."
    >
      <div className="space-y-4">
        {model.explainability.map((cell) => (
          <div
            key={cell.symbol}
            className="rounded-md border border-[var(--border)] p-3"
          >
            <p className="font-medium">{cell.symbol}</p>
            <p className="mt-1 text-sm text-[var(--muted)]">
              {cell.overallExplanation}
            </p>
            <ul className="mt-2 space-y-1 text-sm">
              {cell.moduleSummaries.map((m) => (
                <li key={m.title}>
                  <strong>{m.title}:</strong> {m.summary}{" "}
                  <span className="text-[var(--muted)]">({m.confidence})</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

export function IntelligenceSection({
  model,
}: {
  model: ComparisonWorkspaceModel;
}) {
  return (
    <SectionCard
      title="Research Intelligence Integration"
      description="EPIC-011B accuracy, calibration, and timeline — measurement only, never recalculated."
    >
      <SymbolGrid symbols={model.intelligence.map((i) => i.symbol)}>
        {(symbol) => {
          const i = model.intelligence.find((x) => x.symbol === symbol)!;
          return (
            <div className="rounded-md border border-[var(--border)] p-3">
              <p className="mb-2 font-medium">{symbol}</p>
              <dl>
                <FieldRow label="Overall accuracy" value={i.overallAccuracy} />
                <FieldRow
                  label="Recommendation accuracy"
                  value={i.recommendationAccuracy}
                />
                <FieldRow label="Calibration" value={i.calibrationStatus} />
                <FieldRow label="Timeline count" value={i.timelineCount} />
                <FieldRow label="Freshness" value={i.freshness} />
                <FieldRow label="Coverage" value={i.coverage} />
                <FieldRow label="Source" value={i.source} />
              </dl>
            </div>
          );
        }}
      </SymbolGrid>
    </SectionCard>
  );
}

export function BuffettPreferenceSection({
  model,
}: {
  model: ComparisonWorkspaceModel;
}) {
  return (
    <SectionCard
      title="Buffett-style Preference Analysis"
      description={`${BUFFETT_FRAMEWORK_PREFIX}… — never “Buffett would buy.”`}
    >
      <p className="mb-4 text-sm text-[var(--muted)]">{model.buffettDisclaimer}</p>
      <div className="space-y-4">
        {model.buffettPreference.map((row) => (
          <div
            key={row.id}
            className="rounded-md border border-[var(--border)] p-3"
          >
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-semibold">{row.label}</h3>
              <Badge variant="outline">{row.framing}</Badge>
            </div>
            <p className="mt-2 text-xs text-[var(--muted)]">{row.tradeOff}</p>
            <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
              {row.cells.map((cell) => (
                <div
                  key={cell.symbol}
                  className="rounded border border-[var(--border)] p-2 text-sm"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{cell.symbol}</span>
                    <AlignmentBadge alignment={cell.alignment} />
                  </div>
                  <p className="mt-2 text-xs">{cell.reason}</p>
                  <p className="mt-1 text-xs text-[var(--muted)]">
                    Evidence: {cell.evidence}
                  </p>
                  <p className="text-xs text-[var(--muted)]">
                    Confidence: {cell.confidence}
                  </p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

export function HeatmapSection({ model }: { model: ComparisonWorkspaceModel }) {
  const dims = Array.from(new Set(model.heatmap.map((h) => h.dimension)));
  const symbols = model.symbols;
  return (
    <SectionCard
      title="Decision Heatmap"
      description="Intensity bands from existing Winner Matrix scores — not a new decision engine."
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[36rem] border-collapse text-sm">
          <thead>
            <tr>
              <th className="py-2 pr-2 text-left">Dimension</th>
              {symbols.map((s) => (
                <th key={s} className="px-1 py-2 text-left">
                  {s}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dims.map((dim) => (
              <tr key={dim}>
                <td className="py-1 pr-2 text-[var(--muted)]">{dim}</td>
                {symbols.map((sym) => {
                  const cell = model.heatmap.find(
                    (h) => h.dimension === dim && h.symbol === sym,
                  );
                  return (
                    <td key={sym} className="p-1">
                      <HeatCell
                        intensity={cell?.intensity ?? "unavailable"}
                        display={cell?.display ?? "Data unavailable."}
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}

export function ScenarioSection({ model }: { model: ComparisonWorkspaceModel }) {
  return (
    <SectionCard
      title="Scenario Comparison"
      description="Bull / Base / Bear when present on research outputs."
    >
      <SymbolGrid symbols={model.scenarios.map((s) => s.symbol)}>
        {(symbol) => {
          const s = model.scenarios.find((x) => x.symbol === symbol)!;
          return (
            <div className="rounded-md border border-[var(--border)] p-3">
              <p className="mb-2 font-medium">{symbol}</p>
              <dl>
                <FieldRow label="Bull" value={s.bull} />
                <FieldRow label="Base" value={s.base} />
                <FieldRow label="Bear" value={s.bear} />
              </dl>
            </div>
          );
        }}
      </SymbolGrid>
    </SectionCard>
  );
}

export function PortfolioFitSection({
  model,
}: {
  model: ComparisonWorkspaceModel;
}) {
  return (
    <SectionCard
      title="Portfolio Fit"
      description="Style tags from existing research fields — never personalised advice."
    >
      <SymbolGrid symbols={model.portfolioFit.map((p) => p.symbol)}>
        {(symbol) => {
          const p = model.portfolioFit.find((x) => x.symbol === symbol)!;
          return (
            <div className="rounded-md border border-[var(--border)] p-3">
              <p className="mb-2 font-medium">{symbol}</p>
              <dl>
                <FieldRow label="Quality" value={p.quality} />
                <FieldRow label="Value" value={p.value} />
                <FieldRow label="Growth" value={p.growth} />
                <FieldRow label="Income" value={p.income} />
                <FieldRow
                  label="Buffett-framework alignment"
                  value={p.buffettFramework}
                />
              </dl>
              <p className="mt-2 text-xs text-[var(--muted)]">{p.note}</p>
            </div>
          );
        }}
      </SymbolGrid>
    </SectionCard>
  );
}

export function PersonalResearchSection({
  symbols,
}: {
  symbols: string[];
}) {
  const {
    notes,
    watch,
    saved,
    addNote,
    removeNote,
    addWatch,
    removeWatch,
    saveComparison,
    removeSaved,
  } = useComparisonPrefsStore();
  const [text, setText] = useState("");
  const [kind, setKind] = useState<"note" | "thesis" | "question" | "decision">(
    "note",
  );
  const [title, setTitle] = useState("");

  return (
    <SectionCard
      title="Personal Research Workspace"
      description="User-authored notes only — stored locally, never sent to /analyse."
    >
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="cmp-note-kind">
            Note kind
          </label>
          <select
            id="cmp-note-kind"
            className="w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 py-2 text-sm"
            value={kind}
            onChange={(e) =>
              setKind(e.target.value as typeof kind)
            }
          >
            <option value="note">Note</option>
            <option value="thesis">Thesis</option>
            <option value="question">Question</option>
            <option value="decision">Decision note</option>
          </select>
          <Textarea
            aria-label="Personal research note"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Your thesis, questions, or decision notes…"
            rows={4}
          />
          <Button
            size="sm"
            onClick={() => {
              addNote(kind, text, symbols);
              setText("");
            }}
          >
            Save note
          </Button>
          <ul className="mt-3 max-h-64 space-y-2 overflow-y-auto text-sm">
            {notes.map((n) => (
              <li
                key={n.id}
                className="rounded border border-[var(--border)] p-2"
              >
                <div className="flex justify-between gap-2">
                  <Badge variant="outline">{n.kind}</Badge>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => removeNote(n.id)}
                  >
                    Remove
                  </Button>
                </div>
                <p className="mt-1">{n.text}</p>
                <p className="text-xs text-[var(--muted)]">
                  {n.symbols.join(", ") || "—"} · {n.at}
                </p>
              </li>
            ))}
          </ul>
        </div>
        <div className="space-y-3">
          <div>
            <p className="mb-2 text-sm font-medium">Watch symbols</p>
            <div className="flex flex-wrap gap-2">
              {symbols.map((s) => (
                <Button key={s} size="sm" variant="secondary" onClick={() => addWatch(s)}>
                  Watch {s}
                </Button>
              ))}
            </div>
            <ul className="mt-2 space-y-1 text-sm">
              {watch.map((w) => (
                <li key={w.id} className="flex justify-between gap-2">
                  <span>{w.symbol}</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => removeWatch(w.id)}
                  >
                    Remove
                  </Button>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="mb-2 text-sm font-medium">Saved comparison</p>
            <Input
              aria-label="Saved comparison title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Title for this comparison set"
            />
            <Button
              className="mt-2"
              size="sm"
              onClick={() => {
                saveComparison(title, symbols);
                setTitle("");
              }}
            >
              Save comparison set
            </Button>
            <ul className="mt-2 space-y-1 text-sm">
              {saved.map((s) => (
                <li
                  key={s.id}
                  className="flex items-center justify-between gap-2 rounded border border-[var(--border)] p-2"
                >
                  <span>
                    {s.title} — {s.symbols.join(", ")}
                  </span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => removeSaved(s.id)}
                  >
                    Remove
                  </Button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </SectionCard>
  );
}

export function ExportSection({ model }: { model: ComparisonWorkspaceModel }) {
  const stamp = model.symbols.join("-") || "comparison";
  return (
    <SectionCard
      title="Institutional Export"
      description="Comparison / IC memo snapshot. Native DOCX not available — use print for PDF / HTML / JSON."
    >
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          onClick={() =>
            downloadText(
              `dsp-comparison-${stamp}.json`,
              comparisonToJson(model),
              "application/json",
            )
          }
        >
          Export JSON
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={() =>
            downloadText(
              `dsp-comparison-${stamp}.csv`,
              comparisonToCsv(model),
              "text/csv",
            )
          }
        >
          Export CSV
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => {
            const html = comparisonToHtml(model);
            const w = window.open("", "_blank");
            if (!w) return;
            w.document.write(html);
            w.document.close();
            w.focus();
            w.print();
          }}
        >
          Print / PDF
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={() =>
            downloadText(
              `dsp-ic-memo-${stamp}.json`,
              committeeMemoToJson(model),
              "application/json",
            )
          }
        >
          IC Memo JSON
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => {
            const html = committeeMemoToHtml(model.committeeMemo);
            const w = window.open("", "_blank");
            if (!w) return;
            w.document.write(html);
            w.document.close();
            w.focus();
            w.print();
          }}
        >
          IC Memo Print / PDF
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={async () => {
            const url = window.location.href;
            try {
              await navigator.clipboard.writeText(url);
            } catch {
              /* clipboard may be denied */
            }
          }}
        >
          Copy share link
        </Button>
        <Button size="sm" variant="outline" disabled title="DOCX not available in current export patterns">
          DOCX unavailable
        </Button>
      </div>
      <p className="mt-3 text-xs text-[var(--muted)]">
        Exports serialize mapped research comparison fields only. No client-side
        scoring is performed at export time. The platform never produces the
        investment decision.
      </p>
    </SectionCard>
  );
}

export function ArchitectureSection() {
  return (
    <SectionCard
      title="Future Comparison Architecture"
      description="Extensible subject adapters — company in v1; portfolio/ETF/MF/sector later without shell redesign."
    >
      <dl className="mb-3">
        <FieldRow
          label="Supported (v1)"
          value={SUPPORTED_SUBJECT_KINDS_V1.join(", ")}
        />
        <FieldRow
          label="Planned"
          value={PLANNED_SUBJECT_KINDS.join(", ")}
        />
      </dl>
      <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
        {FUTURE_ARCHITECTURE_NOTES.map((n) => (
          <li key={n}>{n}</li>
        ))}
      </ul>
      <div className="mt-3 space-y-1 text-xs text-[var(--muted)]">
        {(["company", ...PLANNED_SUBJECT_KINDS] as const).map((k) => (
          <p key={k}>
            <strong>{k}:</strong> {describeFutureAdapter(k)}
          </p>
        ))}
      </div>
      <p className="mt-3 text-xs">
        Sections registered:{" "}
        {COMPARISON_SECTIONS.map((s) => s.label).join(" · ")}
      </p>
    </SectionCard>
  );
}
