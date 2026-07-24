"use client";

import { memo, useState, useSyncExternalStore, type ReactNode } from "react";

import { AdvisorShell } from "@/components/advisor/AdvisorWorkspace";
import { PresentationSidebar } from "@/components/advisor/PresentationSidebar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { WindowedList } from "@/lib/perf/WindowedList";
import { downloadText } from "@/lib/analysis/sprint7Reports";
import { listAdvisorResearchTimeline } from "@/lib/advisor/advisorResearchViewModel";
import {
  buildPortfolioReview,
  marketCapMix,
  sectorMix,
} from "@/lib/advisor/modelPortfolioManager";
import {
  PRESENTATION_TRUST,
  buildPresentationHtml,
  buildPresentationMarkdown,
  demoCommentaries,
  getEnvelopesForPresentation,
  getPortfolioForPresentation,
  presentationTemplates,
} from "@/lib/advisor/presentationModels";
import {
  archiveSessionPresentation,
  createSessionPresentation,
  duplicateSessionPresentation,
  getPresentationSnapshot,
  renameSessionPresentation,
  setActivePresentationId,
  subscribePresentations,
  updateSessionPresentation,
} from "@/lib/advisor/presentationSession";
import type {
  AdvisorPresentation,
  PreviewMode,
  PresentationSectionDef,
} from "@/lib/advisor/presentationTypes";

function usePresentationSession() {
  return useSyncExternalStore(
    subscribePresentations,
    getPresentationSnapshot,
    getPresentationSnapshot,
  );
}

function useActivePresentation(): AdvisorPresentation | null {
  const { presentations, activeId } = usePresentationSession();
  return presentations.find((p) => p.id === activeId) ?? null;
}

function PresShell({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <AdvisorShell title={title} description={description}>
      <p
        role="note"
        className="rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm"
      >
        {PRESENTATION_TRUST}
      </p>
      <div className="flex flex-col gap-4 lg:flex-row">
        <PresentationSidebar />
        <div className="min-w-0 flex-1 space-y-4">{children}</div>
      </div>
    </AdvisorShell>
  );
}

export function PresentationToolbar({ onPrint }: { onPrint?: () => void }) {
  const active = useActivePresentation();
  return (
    <div className="flex flex-wrap gap-2" role="toolbar" aria-label="Presentation toolbar">
      <Badge tone="accent">{active?.title ?? "No presentation"}</Badge>
      {onPrint ? (
        <Button type="button" variant="secondary" size="sm" onClick={onPrint}>
          Print layout
        </Button>
      ) : null}
    </div>
  );
}

export function PresentationOutline({ sections }: { sections: PresentationSectionDef[] }) {
  const visible = sections.filter((s) => s.visible);
  return (
    <nav aria-label="Presentation outline">
      <ol className="list-decimal space-y-1 pl-5 text-sm">
        {visible.map((s) => (
          <li key={s.id}>
            <a
              href={`#section-${s.id}`}
              className="text-[var(--accent)] underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              {s.label}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

export function PresentationSectionList({
  sections,
  onToggle,
  onMove,
}: {
  sections: PresentationSectionDef[];
  onToggle: (id: string) => void;
  onMove: (id: string, dir: -1 | 1) => void;
}) {
  return (
    <WindowedList
      items={sections}
      initial={12}
      className="space-y-2"
      empty={<EmptyState title="No sections" />}
      renderItem={(s, index) => (
        <div
          key={s.id}
          className="flex flex-wrap items-center gap-2 rounded-md border border-[var(--border)] px-3 py-2 text-sm"
        >
          <label className="flex min-h-11 flex-1 items-center gap-2">
            <input
              type="checkbox"
              checked={s.visible}
              onChange={() => onToggle(s.id)}
              aria-label={`Show ${s.label}`}
            />
            <span className={s.visible ? "font-medium" : "text-[var(--muted)]"}>{s.label}</span>
          </label>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            aria-label={`Move ${s.label} up`}
            disabled={index === 0}
            onClick={() => onMove(s.id, -1)}
          >
            Up
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            aria-label={`Move ${s.label} down`}
            disabled={index === sections.length - 1}
            onClick={() => onMove(s.id, 1)}
          >
            Down
          </Button>
        </div>
      )}
    />
  );
}

export function AdvisorCommentaryCard({
  title,
  kind,
  body,
}: {
  title: string;
  kind: string;
  body: string;
}) {
  return (
    <Card className="dsp-interactive">
      <CardHeader title={title} action={<Badge tone="neutral">{kind}</Badge>} />
      <CardBody className="text-sm text-[var(--muted)] whitespace-pre-wrap">{body}</CardBody>
    </Card>
  );
}

export function PresentationTemplateCard({
  name,
  blurb,
  onUse,
}: {
  name: string;
  blurb: string;
  onUse?: () => void;
}) {
  return (
    <Card className="dsp-interactive">
      <CardHeader title={name} description={blurb} action={<Badge tone="accent">Template</Badge>} />
      <CardBody>
        {onUse ? (
          <Button type="button" variant="secondary" onClick={onUse}>
            Create from template
          </Button>
        ) : null}
      </CardBody>
    </Card>
  );
}

export function PresentationSection({
  section,
  children,
}: {
  section: PresentationSectionDef;
  children: ReactNode;
}) {
  if (!section.visible) return null;
  return (
    <section
      id={`section-${section.id}`}
      aria-labelledby={`heading-${section.id}`}
      className="scroll-mt-4 space-y-2 border-b border-[var(--border)] pb-6"
    >
      <h2
        id={`heading-${section.id}`}
        className="font-[family-name:var(--font-display)] text-xl tracking-tight"
      >
        {section.label}
      </h2>
      <div className="text-sm">{children}</div>
    </section>
  );
}

export const PresentationSectionContent = memo(function PresentationSectionContent({
  presentation,
}: {
  presentation: AdvisorPresentation;
}) {
  const portfolio = getPortfolioForPresentation(presentation);
  const envelopes = getEnvelopesForPresentation(presentation);
  const review = buildPortfolioReview(portfolio);
  const sectors = sectorMix(portfolio.holdings);
  const caps = marketCapMix(portfolio.holdings);
  const timeline = listAdvisorResearchTimeline().slice(0, 5);

  return (
    <article className="space-y-6" aria-label="Presentation body">
      {presentation.sections.map((section) => (
        <PresentationSection key={section.id} section={section}>
          {section.id === "executive_summary" ? (
            <p>
              Pack for <strong>{presentation.clientAlias}</strong> using model{" "}
              <strong>{portfolio.name}</strong> ({portfolio.riskLevel}, {portfolio.targetHorizon}
              ). Envelopes: {envelopes.map((e) => e.companyLabel).join(", ")}.
            </p>
          ) : null}
          {section.id === "investment_objectives" ? <p>{portfolio.objective}</p> : null}
          {section.id === "client_profile" ? (
            <p>{presentation.clientAlias} — demo alias only. No personal information.</p>
          ) : null}
          {section.id === "research_summary" ? (
            <div className="space-y-4">
              {envelopes.map((e) => (
                <Card key={e.id}>
                  <CardHeader
                    title={e.companyLabel}
                    action={<Badge tone="accent">DSP envelope</Badge>}
                  />
                  <CardBody className="space-y-1 text-[var(--muted)]">
                    <p>
                      <span className="font-medium text-[var(--fg)]">Investment thesis — </span>
                      {e.thesis}
                    </p>
                    <p>Business quality: {e.businessQuality}</p>
                    <p>Financial strength: {e.financialStrength}</p>
                    <p>Valuation summary: {e.valuationSummary}</p>
                    <p>Risk summary: {e.risk}</p>
                    <p>Confidence: {e.confidence}</p>
                    <p>Evidence: {e.evidence.join("; ")}</p>
                    <p>Methodology: {e.methodology}</p>
                    <p>Limitations: {e.limitations.join("; ")}</p>
                  </CardBody>
                </Card>
              ))}
            </div>
          ) : null}
          {section.id === "model_portfolio" ? (
            <p>
              {portfolio.name} · {portfolio.category.replace(/_/g, " ")} · Risk {portfolio.riskLevel}
            </p>
          ) : null}
          {section.id === "portfolio_allocation" ? (
            <div className="space-y-2">
              <p>Cash allocation: {portfolio.cashAllocationPct}%</p>
              <ul className="list-disc pl-5 text-[var(--muted)]">
                {portfolio.holdings.map((h) => (
                  <li key={h.envelopeId}>
                    {h.companyLabel}: {h.allocationPct}%
                  </li>
                ))}
              </ul>
              <p>Sector mix: {sectors.map((s) => `${s.label} ${s.pct}%`).join("; ") || "None"}</p>
              <p>Market cap mix: {caps.map((c) => `${c.label} ${c.pct}%`).join("; ") || "None"}</p>
              <p>Diversification: {review.diversification}</p>
              <p className="font-medium text-[var(--fg)]">Holding summaries</p>
              <ul className="list-disc pl-5 text-[var(--muted)]">
                {envelopes.map((e) => (
                  <li key={e.id}>
                    {e.companyLabel}: {e.thesis}
                  </li>
                ))}
              </ul>
              <p>Portfolio review — {review.evidenceCompleteness}</p>
            </div>
          ) : null}
          {section.id === "top_opportunities" ? (
            <ul className="list-disc pl-5 text-[var(--muted)]">
              {envelopes.flatMap((e) =>
                e.keyOpportunities.map((o) => (
                  <li key={`${e.id}-${o}`}>
                    {e.companyLabel}: {o}
                  </li>
                )),
              )}
            </ul>
          ) : null}
          {section.id === "risk_review" ? (
            <ul className="list-disc pl-5 text-[var(--muted)]">
              {envelopes.flatMap((e) =>
                e.topRisks.map((r) => (
                  <li key={`${e.id}-${r}`}>
                    {e.companyLabel}: {r}
                  </li>
                )),
              )}
              <li>Concentration: {review.concentration}</li>
            </ul>
          ) : null}
          {section.id === "research_timeline" ? (
            <ol className="list-decimal pl-5 text-[var(--muted)]">
              {timeline.map((t) => (
                <li key={t.id}>{t.label}</li>
              ))}
            </ol>
          ) : null}
          {section.id === "advisor_notes" ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {demoCommentaries.map((c) => (
                <AdvisorCommentaryCard
                  key={c.id}
                  title={c.title}
                  kind={c.kind}
                  body={c.body}
                />
              ))}
            </div>
          ) : null}
          {section.id === "disclosures" ? (
            <ul className="list-disc pl-5 text-[var(--muted)]">
              <li>Not investment advice. Demo presentation only.</li>
              <li>Research Mode: no BUY/SELL/HOLD or Target Price UI.</li>
              <li>{PRESENTATION_TRUST}</li>
            </ul>
          ) : null}
        </PresentationSection>
      ))}
    </article>
  );
});

export function PresentationPreview({
  presentation,
  mode,
}: {
  presentation: AdvisorPresentation;
  mode: PreviewMode;
}) {
  const width =
    mode === "tablet"
      ? "max-w-2xl"
      : mode === "print" || mode === "present"
        ? "max-w-3xl"
        : "max-w-4xl";
  return (
    <div
      className={`mx-auto rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-6 ${width} ${
        mode === "present" ? "min-h-[60vh]" : ""
      }`}
      data-preview-mode={mode}
    >
      <header className="mb-4 border-b border-[var(--border)] pb-3">
        <h1 className="font-[family-name:var(--font-display)] text-2xl tracking-tight">
          {presentation.title}
        </h1>
        <p className="text-sm text-[var(--muted)]">
          {presentation.clientAlias} · Preview: {mode}
        </p>
        <div className="mt-2">
          <PresentationOutline sections={presentation.sections} />
        </div>
      </header>
      <PresentationSectionContent presentation={presentation} />
    </div>
  );
}

export function PresentationBuilder() {
  const { presentations, activeId } = usePresentationSession();
  const active = presentations.find((p) => p.id === activeId);
  if (!active) return <EmptyState title="No active presentation" />;

  const toggle = (id: string) => {
    updateSessionPresentation(active.id, (p) => ({
      ...p,
      sections: p.sections.map((s) => (s.id === id ? { ...s, visible: !s.visible } : s)),
    }));
  };

  const move = (id: string, dir: -1 | 1) => {
    updateSessionPresentation(active.id, (p) => {
      const idx = p.sections.findIndex((s) => s.id === id);
      const next = idx + dir;
      if (idx < 0 || next < 0 || next >= p.sections.length) return p;
      const sections = [...p.sections];
      const tmp = sections[idx];
      sections[idx] = sections[next];
      sections[next] = tmp;
      return { ...p, sections };
    });
  };

  return (
    <div className="space-y-4">
      <label className="block text-sm">
        Active presentation
        <select
          className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          value={active.id}
          onChange={(e) => setActivePresentationId(e.target.value)}
        >
          {presentations
            .filter((p) => p.lifecycle === "active")
            .map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
        </select>
      </label>
      <label className="block text-sm">
        Title
        <input
          className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          value={active.title}
          onChange={(e) =>
            updateSessionPresentation(active.id, (p) => ({ ...p, title: e.target.value }))
          }
        />
      </label>
      <PresentationSectionList sections={active.sections} onToggle={toggle} onMove={move} />
      <PresentationOutline sections={active.sections} />
    </div>
  );
}

export const PresentationWorkspace = memo(function PresentationWorkspace() {
  const { presentations } = usePresentationSession();
  const [newTitle, setNewTitle] = useState("");
  const activeList = presentations.filter((p) => p.lifecycle === "active");
  const archived = presentations.filter((p) => p.lifecycle === "archived");

  return (
    <PresShell
      title="Presentation Workspace"
      description="Assemble client packs from DSP research & model portfolios — session only."
    >
      <PresentationToolbar />
      <Card>
        <CardHeader title="Create presentation" description="Session only — not persisted" />
        <CardBody className="flex flex-wrap gap-2">
          <input
            className="min-h-11 min-w-[12rem] flex-1 rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            placeholder="Title"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            aria-label="New presentation title"
          />
          <Button
            type="button"
            onClick={() => {
              createSessionPresentation("tpl-custom", newTitle || undefined);
              setNewTitle("");
            }}
          >
            Create
          </Button>
        </CardBody>
      </Card>
      <WindowedList
        items={activeList}
        initial={8}
        empty={<EmptyState title="No presentations" />}
        className="grid gap-3 md:grid-cols-2"
        renderItem={(p) => (
          <Card key={p.id} className="dsp-interactive">
            <CardHeader
              title={p.title}
              description={`${p.clientAlias} · ${p.templateId}`}
              action={<Badge tone="success">Active</Badge>}
            />
            <CardBody className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => setActivePresentationId(p.id)}
              >
                Set active
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => duplicateSessionPresentation(p.id)}
              >
                Duplicate
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => {
                  const next = window.prompt("Rename presentation", p.title);
                  if (next) renameSessionPresentation(p.id, next);
                }}
              >
                Rename
              </Button>
              <Button
                type="button"
                size="sm"
                variant="danger"
                onClick={() => archiveSessionPresentation(p.id)}
              >
                Archive
              </Button>
            </CardBody>
          </Card>
        )}
      />
      {archived.length > 0 ? (
        <p className="text-sm text-[var(--muted)]">
          Archived: {archived.map((a) => a.title).join(" · ")}
        </p>
      ) : null}
    </PresShell>
  );
});

export const PresentationBuilderWorkspace = memo(function PresentationBuilderWorkspace() {
  return (
    <PresShell
      title="Presentation Builder"
      description="Reorder sections and toggle visibility — session only."
    >
      <PresentationBuilder />
    </PresShell>
  );
});

export const PresentationPreviewWorkspace = memo(function PresentationPreviewWorkspace() {
  const active = useActivePresentation();
  const [mode, setMode] = useState<PreviewMode>("desktop");
  if (!active) {
    return (
      <PresShell title="Presentation Preview">
        <EmptyState title="Select or create a presentation first" />
      </PresShell>
    );
  }
  return (
    <PresShell
      title="Presentation Preview"
      description="Desktop · Tablet · Print · Presentation mode"
    >
      <PresentationToolbar onPrint={() => window.print()} />
      <div className="flex flex-wrap gap-2" role="group" aria-label="Preview mode">
        {(["desktop", "tablet", "print", "present"] as PreviewMode[]).map((m) => (
          <Button
            key={m}
            type="button"
            size="sm"
            variant={mode === m ? "primary" : "secondary"}
            aria-pressed={mode === m}
            onClick={() => setMode(m)}
          >
            {m}
          </Button>
        ))}
      </div>
      <PresentationPreview presentation={active} mode={mode} />
    </PresShell>
  );
});

export const PresentationTemplatesWorkspace = memo(function PresentationTemplatesWorkspace() {
  return (
    <PresShell title="Presentation Templates" description="Initial Consultation → Custom">
      <div className="grid gap-3 md:grid-cols-2">
        {presentationTemplates.map((t) => (
          <PresentationTemplateCard
            key={t.id}
            name={t.name}
            blurb={t.blurb}
            onUse={() => createSessionPresentation(t.id)}
          />
        ))}
      </div>
    </PresShell>
  );
});

export const PresentationExportWorkspace = memo(function PresentationExportWorkspace() {
  const active = useActivePresentation();
  if (!active) {
    return (
      <PresShell title="Export Preparation">
        <EmptyState title="No active presentation" />
      </PresShell>
    );
  }
  const md = buildPresentationMarkdown(active);
  const html = buildPresentationHtml(active);

  return (
    <PresShell
      title="Export Preparation"
      description="Print · Markdown · HTML · PDF/DOCX placeholders — reuses client download helper."
    >
      <PresentationToolbar onPrint={() => window.print()} />
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          onClick={() =>
            downloadText(`${active.title}.md`, md, "text/markdown;charset=utf-8")
          }
        >
          Download Markdown
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={() => downloadText(`${active.title}.html`, html, "text/html;charset=utf-8")}
        >
          Download HTML preview
        </Button>
        <Button type="button" variant="ghost" disabled title="Backend deferred">
          PDF placeholder
        </Button>
        <Button type="button" variant="ghost" disabled title="Backend deferred">
          DOCX placeholder
        </Button>
      </div>
      <Card>
        <CardHeader title="Markdown preview" />
        <CardBody>
          <pre className="max-h-80 overflow-auto whitespace-pre-wrap text-xs text-[var(--muted)]">
            {md}
          </pre>
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="HTML preview (source)" />
        <CardBody>
          <pre className="max-h-48 overflow-auto whitespace-pre-wrap text-xs text-[var(--muted)]">
            {html.slice(0, 1200)}…
          </pre>
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Print / export layout" />
        <CardBody>
          <PresentationPreview presentation={active} mode="print" />
        </CardBody>
      </Card>
    </PresShell>
  );
});
