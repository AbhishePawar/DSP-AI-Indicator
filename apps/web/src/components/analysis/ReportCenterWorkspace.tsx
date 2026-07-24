"use client";

import { memo, useMemo, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { AnalysisWorkspaceView } from "@/lib/analysis/types";
import {
  buildReport,
  defaultCustomization,
  downloadText,
  EXPORT_FORMATS,
  MANDATORY_SECTIONS,
  REPORT_SECTION_LABELS,
  REPORT_TEMPLATES,
  reportMetricsCsv,
  reportToHtml,
  reportToJson,
  reportToMarkdown,
  type BuiltReport,
  type DateFormatId,
  type ExportFormatId,
  type ReportCustomization,
  type ReportSectionId,
  type ReportTemplateDef,
  type ReportTemplateId,
} from "@/lib/analysis/sprint7Reports";

export const ReportCenterWorkspace = memo(function ReportCenterWorkspace({
  view,
}: {
  view: AnalysisWorkspaceView;
}) {
  const [templateId, setTemplateId] = useState<ReportTemplateId>("full_research");
  const template = useMemo(
    () => REPORT_TEMPLATES.find((t) => t.id === templateId) ?? REPORT_TEMPLATES[1],
    [templateId],
  );
  const [custom, setCustom] = useState<ReportCustomization>(() =>
    defaultCustomization(view, template),
  );

  // Keep title company-aware when symbol changes
  const company =
    view.snapshot.ticker.value ?? view.snapshot.companyName.value ?? "Company";

  const report = useMemo(
    () => buildReport(view, templateId, custom),
    [view, templateId, custom],
  );

  const onSelectTemplate = (t: ReportTemplateDef) => {
    setTemplateId(t.id);
    setCustom(defaultCustomization(view, t));
  };

  return (
    <div className="space-y-4">
      <p className="rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm">
        <span className="font-medium">What you should know — </span>
        Generate professional research reports from this workspace. Limitations,
        confidence, methodology, and evidence references are always included.
        PDF/DOCX generation awaits backend export services.
      </p>

      <ReportMetadataCard view={view} company={company} />

      <div>
        <h3 className="mb-2 font-[family-name:var(--font-display)] text-lg">
          Report templates
        </h3>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {REPORT_TEMPLATES.map((t) => (
            <ReportTemplateCard
              key={t.id}
              template={t}
              selected={t.id === templateId}
              onSelect={() => onSelectTemplate(t)}
            />
          ))}
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="space-y-4">
          <CustomizationPanel custom={custom} onChange={setCustom} />
          <SectionSelector custom={custom} onChange={setCustom} />
          <ExportActionCard
            report={report}
            view={view}
            templateId={templateId}
          />
          <ExportHistoryPlaceholder />
        </div>
        <ReportPreview report={report} />
      </div>

      <DisclosurePanel report={report} />
    </div>
  );
});

export function ReportTemplateCard({
  template,
  selected,
  onSelect,
}: {
  template: ReportTemplateDef;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={`min-h-11 rounded-md border p-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
        selected
          ? "border-[var(--accent)] bg-[var(--accent-soft)]"
          : "border-[var(--border)] bg-[var(--surface)]"
      }`}
    >
      <p className="font-medium">{template.title}</p>
      <p className="mt-1 text-xs text-[var(--muted)]">{template.description}</p>
    </button>
  );
}

function CustomizationPanel({
  custom,
  onChange,
}: {
  custom: ReportCustomization;
  onChange: (c: ReportCustomization) => void;
}) {
  return (
    <Card>
      <CardHeader title="Customization" description="Title, date format, and trust toggles" />
      <CardBody className="space-y-3 text-sm">
        <label className="block">
          <span className="text-xs font-medium uppercase text-[var(--muted)]">
            Report title
          </span>
          <input
            value={custom.title}
            onChange={(e) => onChange({ ...custom, title: e.target.value })}
            className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          />
        </label>
        <label className="block">
          <span className="text-xs font-medium uppercase text-[var(--muted)]">
            Date format
          </span>
          <select
            value={custom.dateFormat}
            onChange={(e) =>
              onChange({ ...custom, dateFormat: e.target.value as DateFormatId })
            }
            className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            <option value="locale_long">Long locale</option>
            <option value="locale_short">Short locale</option>
            <option value="iso">ISO (YYYY-MM-DD)</option>
          </select>
        </label>
        <Toggle
          label="Show detailed evidence list"
          checked={custom.showEvidence}
          locked={false}
          onChange={(v) => onChange({ ...custom, showEvidence: v })}
        />
        <Toggle
          label="Show assumptions"
          checked={custom.showAssumptions}
          locked={false}
          onChange={(v) => onChange({ ...custom, showAssumptions: v })}
        />
        <Toggle
          label="Include methodology (required)"
          checked
          locked
          onChange={() => undefined}
        />
        <Toggle
          label="Include confidence ratings (required)"
          checked
          locked
          onChange={() => undefined}
        />
        <p className="text-xs text-[var(--muted)]">
          Evidence summary, confidence, methodology, limitations, and disclosures
          cannot be removed from exports. Unchecking detailed evidence only
          condenses the list.
        </p>
      </CardBody>
    </Card>
  );
}

function Toggle({
  label,
  checked,
  locked,
  onChange,
}: {
  label: string;
  checked: boolean;
  locked?: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex min-h-11 items-center gap-2">
      <input
        type="checkbox"
        checked={checked}
        disabled={locked}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span>
        {label}
        {locked ? <Badge tone="neutral" className="ml-2">Locked</Badge> : null}
      </span>
    </label>
  );
}

export function SectionSelector({
  custom,
  onChange,
}: {
  custom: ReportCustomization;
  onChange: (c: ReportCustomization) => void;
}) {
  const sections = Object.keys(REPORT_SECTION_LABELS) as ReportSectionId[];
  const included = useMemo(
    () => new Set(custom.includedSections),
    [custom.includedSections],
  );

  const toggle = (id: ReportSectionId) => {
    if (MANDATORY_SECTIONS.includes(id)) return;
    const next = new Set(included);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    for (const m of MANDATORY_SECTIONS) next.add(m);
    onChange({ ...custom, includedSections: Array.from(next) });
  };

  return (
    <Card>
      <CardHeader
        title="Sections"
        description="Include or exclude optional sections — trust sections stay locked"
      />
      <CardBody>
        <ul className="grid max-h-64 gap-1 overflow-y-auto sm:grid-cols-2" aria-label="Report sections">
          {sections.map((id) => {
            const mandatory = MANDATORY_SECTIONS.includes(id);
            return (
              <li key={id}>
                <label className="flex min-h-10 items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={included.has(id)}
                    disabled={mandatory}
                    onChange={() => toggle(id)}
                  />
                  <span>
                    {REPORT_SECTION_LABELS[id]}
                    {mandatory ? (
                      <span className="ml-1 text-xs text-[var(--muted)]">(required)</span>
                    ) : null}
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
      </CardBody>
    </Card>
  );
}

export function CitationBlock({
  evidenceReference,
  confidence,
  methodology,
  timestamp,
}: {
  evidenceReference: string;
  confidence: string;
  methodology: string;
  timestamp: string | null;
}) {
  return (
    <aside
      className="mt-2 rounded-md border border-dashed border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-xs text-[var(--muted)]"
      aria-label="Citation"
    >
      <p>
        <span className="font-medium text-[var(--fg)]">Evidence — </span>
        {evidenceReference}
      </p>
      <p>
        <span className="font-medium text-[var(--fg)]">Confidence — </span>
        {confidence}
      </p>
      <p>
        <span className="font-medium text-[var(--fg)]">Methodology — </span>
        {methodology}
      </p>
      <p>
        <span className="font-medium text-[var(--fg)]">Timestamp — </span>
        {timestamp ?? "Unavailable"}
      </p>
    </aside>
  );
}

export const ReportPreview = memo(function ReportPreview({
  report,
}: {
  report: BuiltReport;
}) {
  // Virtualize long reports: show first N blocks + expand
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? report.blocks : report.blocks.slice(0, 6);
  const hidden = Math.max(report.blocks.length - visible.length, 0);

  return (
    <Card className="xl:sticky xl:top-20">
      <CardHeader
        title="Live preview"
        description="Desktop two-column layout · mobile scrollable preview"
        action={<Badge tone="accent">{report.blocks.length} sections</Badge>}
      />
      <CardBody>
        <article
          className="max-h-[70vh] space-y-4 overflow-y-auto rounded-md border border-[var(--border)] bg-[var(--surface)] p-4"
          aria-label="Report preview"
        >
          <header>
            <h2 className="font-[family-name:var(--font-display)] text-xl">
              {report.title}
            </h2>
            <p className="text-xs text-[var(--muted)]">
              {report.companyLabel} · Generated {report.generatedAt}
            </p>
          </header>
          {visible.map((block) => (
            <section key={block.id} className="border-t border-[var(--border)] pt-3">
              <h3 className="text-base font-medium">{block.heading}</h3>
              {block.paragraphs.map((p) => (
                <p key={p.slice(0, 40)} className="mt-2 text-sm text-[var(--muted)]">
                  {p}
                </p>
              ))}
              {block.bullets?.length ? (
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                  {block.bullets.slice(0, expanded ? 50 : 8).map((b) => (
                    <li key={b.slice(0, 48)}>{b}</li>
                  ))}
                </ul>
              ) : null}
              {block.citation ? (
                <CitationBlock
                  evidenceReference={block.citation.evidenceReference}
                  confidence={block.citation.confidence}
                  methodology={block.citation.methodology}
                  timestamp={block.citation.timestamp}
                />
              ) : null}
            </section>
          ))}
          {hidden > 0 ? (
            <Button variant="secondary" size="sm" onClick={() => setExpanded(true)}>
              Show remaining {hidden} section(s)
            </Button>
          ) : null}
          {expanded && report.blocks.length > 6 ? (
            <Button variant="ghost" size="sm" onClick={() => setExpanded(false)}>
              Collapse preview
            </Button>
          ) : null}
        </article>
      </CardBody>
    </Card>
  );
});

export function ExportActionCard({
  report,
  view,
  templateId,
}: {
  report: BuiltReport;
  view: AnalysisWorkspaceView;
  templateId: ReportTemplateId;
}) {
  const [status, setStatus] = useState<string | null>(null);
  const slug = `${templateId}-${report.companyLabel}`.replace(/\s+/g, "-").toLowerCase();

  const runExport = (format: ExportFormatId) => {
    const def = EXPORT_FORMATS.find((f) => f.id === format);
    if (!def?.ready) {
      setStatus(
        `${def?.label ?? format} export is prepared in UI — backend generation is deferred for this RC.`,
      );
      return;
    }
    try {
      if (format === "markdown") {
        downloadText(`${slug}.md`, reportToMarkdown(report), "text/markdown");
      } else if (format === "html") {
        downloadText(`${slug}.html`, reportToHtml(report), "text/html");
      } else if (format === "json") {
        downloadText(`${slug}.json`, reportToJson(report), "application/json");
      } else if (format === "csv") {
        downloadText(`${slug}-metrics.csv`, reportMetricsCsv(view), "text/csv");
      }
      setStatus(`Downloaded ${def.label} (client-side). Includes mandatory trust sections.`);
    } catch {
      setStatus("Export failed in browser — try again.");
    }
  };

  return (
    <Card>
      <CardHeader
        title="Export"
        description="Client-side formats available now · PDF/DOCX await backend"
      />
      <CardBody className="space-y-3">
        <div className="grid gap-2 sm:grid-cols-2">
          {EXPORT_FORMATS.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => runExport(f.id)}
              className="min-h-11 rounded-md border border-[var(--border)] px-3 text-left text-sm hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              <span className="font-medium">{f.label}</span>
              <span className="mt-0.5 block text-xs text-[var(--muted)]">
                {f.description}
                {!f.ready ? " · Placeholder" : ""}
              </span>
            </button>
          ))}
        </div>
        {status ? (
          <p className="text-xs text-[var(--muted)]" role="status" aria-live="polite">
            {status}
          </p>
        ) : null}
      </CardBody>
    </Card>
  );
}

export function ReportMetadataCard({
  view,
  company,
}: {
  view: AnalysisWorkspaceView;
  company: string;
}) {
  return (
    <Card>
      <CardHeader title="Report metadata" />
      <CardBody className="grid gap-2 text-sm sm:grid-cols-2">
        <Meta label="Company" value={company} />
        <Meta label="Research mode" value={view.freshness.researchMode} />
        <Meta label="Analysis version" value={view.freshness.analysisVersion} />
        <Meta label="Methodology" value={view.freshness.methodologyVersion} />
        <Meta label="Data currency" value={view.freshness.dataCurrency} />
        <Meta
          label="Coverage"
          value={`${view.coverage.coveragePercent}% (completeness meta)`}
        />
      </CardBody>
    </Card>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase text-[var(--muted)]">{label}</p>
      <p className="mt-0.5">{value}</p>
    </div>
  );
}

export function DisclosurePanel({ report }: { report: BuiltReport }) {
  return (
    <Card>
      <CardHeader
        title="Disclosures"
        description="Always included in exports — Research Mode, methodology, limitations, AI assistance"
      />
      <CardBody>
        <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
          {report.disclosures.map((d) => (
            <li key={d.slice(0, 60)}>{d}</li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}

export function ExportHistoryPlaceholder() {
  return (
    <Card>
      <CardHeader title="Export history" description="Placeholder — server history arrives later" />
      <CardBody className="text-sm text-[var(--muted)]">
        No persisted export history in this session. Client downloads are not stored by DSP.
      </CardBody>
    </Card>
  );
}
