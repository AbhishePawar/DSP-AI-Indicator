"use client";

import { useState, type ReactNode } from "react";

import { Badge, Button, Input, Textarea } from "@/components/ds";
import {
  BUFFETT_FRAMEWORK_PREFIX,
  COMPARISON_SECTIONS,
  FUTURE_ARCHITECTURE_NOTES,
  PLANNED_SUBJECT_KINDS,
  SUPPORTED_SUBJECT_KINDS_V1,
  comparisonToCsv,
  comparisonToHtml,
  comparisonToJson,
  describeFutureAdapter,
  downloadText,
  useComparisonPrefsStore,
  type ComparisonWorkspaceModel,
} from "@/lib/company-comparison";
import {
  AlignmentBadge,
  FieldRow,
  HeatCell,
  MedalBadge,
  SectionCard,
} from "./Primitives";

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
      </dl>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
        {e.tradeOffs.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>
    </SectionCard>
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
      description="Comparison / IC-style executive snapshot. Native DOCX not available — use print for PDF."
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
        scoring is performed at export time.
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
