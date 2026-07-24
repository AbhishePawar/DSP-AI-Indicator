"use client";

import { memo, useCallback, useMemo, useState, type ReactNode } from "react";

import { AdvisorShell } from "@/components/advisor/AdvisorWorkspace";
import { PortfolioSidebar } from "@/components/advisor/PortfolioSidebar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { WindowedList } from "@/lib/perf/WindowedList";
import { getEnvelope } from "@/lib/advisor/advisorResearchViewModel";
import {
  MP_TRUST,
  buildPortfolioReview,
  cloneDraft,
  compareDrafts,
  computeAllocationTotals,
  emptyDraft,
  holdingMeta,
  listLibraryByCategory,
  marketCapMix,
  portfolioTemplates,
  sectorMix,
  seedModelPortfolioLibrary,
} from "@/lib/advisor/modelPortfolioManager";
import type {
  ModelPortfolioDraft,
  MpCategory,
  MpHolding,
  MpNote,
} from "@/lib/advisor/modelPortfolioTypes";

function MpShell({
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
        {MP_TRUST}
      </p>
      <div className="flex flex-col gap-4 lg:flex-row">
        <PortfolioSidebar />
        <div className="min-w-0 flex-1 space-y-4">{children}</div>
      </div>
    </AdvisorShell>
  );
}

export function AllocationSummary({
  draft,
}: {
  draft: ModelPortfolioDraft;
}) {
  const totals = useMemo(
    () => computeAllocationTotals(draft.holdings, draft.cashAllocationPct),
    [draft.holdings, draft.cashAllocationPct],
  );
  const sectors = useMemo(() => sectorMix(draft.holdings), [draft.holdings]);
  const caps = useMemo(() => marketCapMix(draft.holdings), [draft.holdings]);

  return (
    <Card>
      <CardHeader
        title="Allocation summary"
        action={
          <Badge tone={totals.isBalanced ? "success" : "warning"}>
            Total {totals.totalPct}%
          </Badge>
        }
      />
      <CardBody className="grid gap-3 sm:grid-cols-2 text-sm">
        <p>
          Holdings {totals.holdingsPct}% · Cash {totals.cashPct}%
        </p>
        {!totals.isBalanced ? (
          <p role="alert" className="text-[var(--danger-fg)]">
            Warning: total allocation is {totals.totalPct}% (off by {totals.deltaFrom100}% from
            100%).
          </p>
        ) : (
          <p className="text-[var(--muted)]">Balanced at 100% (demo check).</p>
        )}
        <div>
          <p className="font-medium">Sector mix</p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {sectors.length === 0 ? (
              <li>None</li>
            ) : (
              sectors.map((s) => (
                <li key={s.label}>
                  {s.label}: {s.pct}%
                </li>
              ))
            )}
          </ul>
        </div>
        <div>
          <p className="font-medium">Market cap mix</p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {caps.length === 0 ? (
              <li>None</li>
            ) : (
              caps.map((c) => (
                <li key={c.label}>
                  {c.label}: {c.pct}%
                </li>
              ))
            )}
          </ul>
        </div>
        <p className="sm:col-span-2 text-[var(--muted)]">
          Cash allocation: {draft.cashAllocationPct}%
        </p>
      </CardBody>
    </Card>
  );
}

export function PortfolioAllocationTable({ holdings }: { holdings: MpHolding[] }) {
  return (
    <div className="overflow-x-auto" role="region" aria-label="Holdings allocation table">
      <table className="w-full min-w-[28rem] border-collapse text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] text-left">
            <th className="p-2 font-medium">Company</th>
            <th className="p-2 font-medium">Allocation %</th>
            <th className="p-2 font-medium">Sector</th>
            <th className="p-2 font-medium">Market cap</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => (
            <tr key={h.envelopeId} className="border-b border-[var(--border)]">
              <td className="p-2">{h.companyLabel}</td>
              <td className="p-2 tabular-nums">{h.allocationPct}</td>
              <td className="p-2 text-[var(--muted)]">{h.sector}</td>
              <td className="p-2 text-[var(--muted)]">{h.marketCapBand}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export const HoldingCard = memo(function HoldingCard({ holding }: { holding: MpHolding }) {
  const env = getEnvelope(holding.envelopeId);
  return (
    <Card className="dsp-interactive">
      <CardHeader
        title={holding.companyLabel}
        description={`Allocation ${holding.allocationPct}%`}
        action={<Badge tone="accent">Demo envelope</Badge>}
      />
      <CardBody className="space-y-2 text-sm">
        {env ? (
          <>
            <p>
              <span className="font-medium">Investment thesis — </span>
              {env.thesis}
            </p>
            <p>
              <span className="font-medium">Business quality — </span>
              {env.businessQuality}
            </p>
            <p>
              <span className="font-medium">Financial strength — </span>
              {env.financialStrength}
            </p>
            <p>
              <span className="font-medium">Valuation summary — </span>
              {env.valuationSummary}
            </p>
            <p>
              <span className="font-medium">Risk summary — </span>
              {env.risk} · {env.topRisks.join("; ")}
            </p>
            <p>
              <span className="font-medium">Confidence — </span>
              {env.confidence}
            </p>
            <p>
              <span className="font-medium">Evidence coverage — </span>
              {env.evidenceCoverage}
            </p>
            <p className="text-xs text-[var(--muted)]">
              Methodology: {env.methodology} · Limitations preserved on envelope.
            </p>
          </>
        ) : (
          <p className="text-[var(--muted)]">Envelope unavailable</p>
        )}
      </CardBody>
    </Card>
  );
});

export function PortfolioReviewCard({ draft }: { draft: ModelPortfolioDraft }) {
  const review = useMemo(() => buildPortfolioReview(draft), [draft]);
  return (
    <Card>
      <CardHeader title="Portfolio review" description="Heuristic presentation — not engine output" />
      <CardBody className="grid gap-3 sm:grid-cols-2 text-sm">
        <div>
          <p className="font-medium">Strengths</p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {review.strengths.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="font-medium">Potential risks</p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {review.potentialRisks.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
        <p>
          <span className="font-medium">Diversification — </span>
          {review.diversification}
        </p>
        <p>
          <span className="font-medium">Concentration — </span>
          {review.concentration}
        </p>
        <p>
          <span className="font-medium">Research coverage — </span>
          {review.researchCoverage}
        </p>
        <p>
          <span className="font-medium">Evidence completeness — </span>
          {review.evidenceCompleteness}
        </p>
      </CardBody>
    </Card>
  );
}

export function PortfolioNotes({ notes }: { notes: MpNote[] }) {
  return (
    <Card>
      <CardHeader title="Portfolio notes" description="Advisor · Review · Suitability · Version" />
      <CardBody className="space-y-3">
        {notes.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No notes</p>
        ) : (
          notes.map((n) => (
            <article key={n.id} className="rounded-md border border-[var(--border)] px-3 py-2 text-sm">
              <div className="flex flex-wrap gap-2">
                <Badge tone="neutral">{n.kind}</Badge>
                <span className="font-medium">{n.title}</span>
              </div>
              <p className="mt-1 text-[var(--muted)] whitespace-pre-wrap">{n.body}</p>
            </article>
          ))
        )}
      </CardBody>
    </Card>
  );
}

export const PortfolioTemplateCard = memo(function PortfolioTemplateCard({
  name,
  blurb,
  category,
  onUse,
}: {
  name: string;
  blurb: string;
  category: string;
  onUse?: () => void;
}) {
  return (
    <Card className="dsp-interactive">
      <CardHeader
        title={name}
        description={blurb}
        action={<Badge tone="accent">{category.replace(/_/g, " ")}</Badge>}
      />
      <CardBody>
        {onUse ? (
          <Button type="button" variant="secondary" onClick={onUse}>
            Use in builder (session)
          </Button>
        ) : null}
      </CardBody>
    </Card>
  );
});

export const ModelPortfolioLibrary = memo(function ModelPortfolioLibrary() {
  const [category, setCategory] = useState<MpCategory | "all">("all");
  const items = useMemo(() => listLibraryByCategory(category), [category]);

  return (
    <div className="space-y-4">
      <label className="block text-sm">
        Category
        <select
          className="mt-1 min-h-11 rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          value={category}
          onChange={(e) => setCategory(e.target.value as MpCategory | "all")}
          aria-label="Filter model portfolio category"
        >
          <option value="all">All</option>
          <option value="growth">Growth</option>
          <option value="balanced">Balanced</option>
          <option value="income">Income</option>
          <option value="value">Value</option>
          <option value="quality">Quality</option>
          <option value="small_cap">Small Cap</option>
          <option value="large_cap">Large Cap</option>
          <option value="custom">Custom</option>
        </select>
      </label>
      <WindowedList
        items={items}
        initial={6}
        empty={<EmptyState title="No models in category" />}
        className="grid gap-3 md:grid-cols-2"
        renderItem={(p) => (
          <Card key={p.id} className="dsp-interactive">
            <CardHeader
              title={p.name}
              description={p.objective}
              action={<Badge tone="neutral">{p.category.replace(/_/g, " ")}</Badge>}
            />
            <CardBody className="space-y-2 text-sm">
              <p className="text-[var(--muted)]">
                Risk {p.riskLevel} · Horizon {p.targetHorizon}
              </p>
              <AllocationSummary draft={p} />
              <PortfolioAllocationTable holdings={p.holdings} />
            </CardBody>
          </Card>
        )}
      />
    </div>
  );
});

export const PortfolioBuilderWorkspace = memo(function PortfolioBuilderWorkspace() {
  const [draft, setDraft] = useState<ModelPortfolioDraft>(() => {
    return cloneDraft("mp-lib-balanced") ?? emptyDraft();
  });

  const totals = useMemo(
    () => computeAllocationTotals(draft.holdings, draft.cashAllocationPct),
    [draft],
  );

  const addCompany = useCallback((envelopeId: string) => {
    setDraft((d) => {
      if (d.holdings.some((h) => h.envelopeId === envelopeId)) return d;
      const meta = holdingMeta(envelopeId);
      return {
        ...d,
        holdings: [...d.holdings, { envelopeId, allocationPct: 10, ...meta }],
      };
    });
  }, []);

  const removeCompany = useCallback((envelopeId: string) => {
    setDraft((d) => ({
      ...d,
      holdings: d.holdings.filter((h) => h.envelopeId !== envelopeId),
    }));
  }, []);

  const setAllocation = useCallback((envelopeId: string, allocationPct: number) => {
    setDraft((d) => ({
      ...d,
      holdings: d.holdings.map((h) =>
        h.envelopeId === envelopeId
          ? { ...h, allocationPct: Math.max(0, Math.min(100, allocationPct)) }
          : h,
      ),
    }));
  }, []);

  const moveHolding = useCallback((envelopeId: string, dir: -1 | 1) => {
    setDraft((d) => {
      const idx = d.holdings.findIndex((h) => h.envelopeId === envelopeId);
      if (idx < 0) return d;
      const next = idx + dir;
      if (next < 0 || next >= d.holdings.length) return d;
      const holdings = [...d.holdings];
      const tmp = holdings[idx];
      holdings[idx] = holdings[next];
      holdings[next] = tmp;
      return { ...d, holdings };
    });
  }, []);

  const addOptions = useMemo(() => {
    const used = new Set(draft.holdings.map((h) => h.envelopeId));
    return ["re-aurora", "re-beacon", "re-cedar", "re-delta", "re-ember"].filter(
      (id) => !used.has(id),
    );
  }, [draft.holdings]);

  return (
    <MpShell
      title="Portfolio Builder"
      description="Session-only — add/remove/reorder holdings and assign allocation %."
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm">
          Name
          <input
            className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            value={draft.name}
            onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
          />
        </label>
        <label className="block text-sm">
          Cash allocation %
          <input
            type="number"
            min={0}
            max={100}
            className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            value={draft.cashAllocationPct}
            onChange={(e) =>
              setDraft((d) => ({
                ...d,
                cashAllocationPct: Number(e.target.value) || 0,
              }))
            }
          />
        </label>
        <label className="block text-sm sm:col-span-2">
          Investment objective
          <input
            className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            value={draft.objective}
            onChange={(e) => setDraft((d) => ({ ...d, objective: e.target.value }))}
          />
        </label>
      </div>

      <Card>
        <CardHeader
          title="Overview"
          description={`Risk ${draft.riskLevel} · Horizon ${draft.targetHorizon}`}
        />
        <CardBody className="space-y-3">
          <AllocationSummary draft={draft} />
          {!totals.isBalanced ? (
            <p role="status" className="text-sm text-[var(--danger-fg)]">
              Adjust holdings or cash so total equals 100%.
            </p>
          ) : null}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Add company" description="From demo DSP envelopes" />
        <CardBody className="flex flex-wrap gap-2">
          {addOptions.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">All demo companies added</p>
          ) : (
            addOptions.map((id) => (
              <Button key={id} type="button" variant="secondary" onClick={() => addCompany(id)}>
                Add {holdingMeta(id).companyLabel}
              </Button>
            ))
          )}
          <Button
            type="button"
            variant="ghost"
            onClick={() => setDraft(emptyDraft())}
          >
            Reset empty
          </Button>
        </CardBody>
      </Card>

      <section aria-labelledby="builder-holdings">
        <h2 id="builder-holdings" className="mb-2 font-[family-name:var(--font-display)] text-xl">
          Holdings
        </h2>
        {draft.holdings.length === 0 ? (
          <EmptyState title="No holdings" description="Add companies to begin." />
        ) : (
          <div className="space-y-3">
            {draft.holdings.map((h, index) => (
              <Card key={h.envelopeId}>
                <CardBody className="space-y-2 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-medium">{h.companyLabel}</p>
                    <div className="flex flex-wrap gap-1">
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        aria-label={`Move ${h.companyLabel} up`}
                        disabled={index === 0}
                        onClick={() => moveHolding(h.envelopeId, -1)}
                      >
                        Up
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        aria-label={`Move ${h.companyLabel} down`}
                        disabled={index === draft.holdings.length - 1}
                        onClick={() => moveHolding(h.envelopeId, 1)}
                      >
                        Down
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="danger"
                        onClick={() => removeCompany(h.envelopeId)}
                      >
                        Remove
                      </Button>
                    </div>
                  </div>
                  <label className="block">
                    Allocation %
                    <input
                      type="number"
                      min={0}
                      max={100}
                      className="mt-1 min-h-11 w-full max-w-xs rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                      value={h.allocationPct}
                      onChange={(e) =>
                        setAllocation(h.envelopeId, Number(e.target.value) || 0)
                      }
                    />
                  </label>
                  <HoldingCard holding={h} />
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </section>

      <PortfolioAllocationTable holdings={draft.holdings} />
      <PortfolioReviewCard draft={draft} />
      <PortfolioNotes notes={draft.notes} />
    </MpShell>
  );
});

export function ScenarioComparison() {
  const [idA, setIdA] = useState("mp-lib-growth");
  const [idB, setIdB] = useState("mp-lib-income");
  const a = seedModelPortfolioLibrary.find((p) => p.id === idA)!;
  const b = seedModelPortfolioLibrary.find((p) => p.id === idB)!;
  const cmp = useMemo(() => compareDrafts(a, b), [a, b]);

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm">
          Model A
          <select
            className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            value={idA}
            onChange={(e) => setIdA(e.target.value)}
          >
            {seedModelPortfolioLibrary.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          Model B
          <select
            className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            value={idB}
            onChange={(e) => setIdB(e.target.value)}
          >
            {seedModelPortfolioLibrary.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <Card>
        <CardHeader title="Risk & diversification" />
        <CardBody className="grid gap-2 sm:grid-cols-2 text-sm">
          <p>
            Risk: {cmp.riskA} vs {cmp.riskB}
          </p>
          <p>
            Sector buckets: {cmp.diversificationA} vs {cmp.diversificationB}
          </p>
          <ul className="sm:col-span-2 list-disc pl-5 text-[var(--muted)]">
            {cmp.characteristics.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </CardBody>
      </Card>
      <div className="overflow-x-auto" role="region" aria-label="Allocation differences">
        <table className="w-full min-w-[32rem] border-collapse text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left">
              <th className="p-2">Company</th>
              <th className="p-2">Model A %</th>
              <th className="p-2">Model B %</th>
              <th className="p-2">Δ</th>
            </tr>
          </thead>
          <tbody>
            {cmp.allocationDiffs.map((row) => (
              <tr key={row.companyLabel} className="border-b border-[var(--border)]">
                <td className="p-2">{row.companyLabel}</td>
                <td className="p-2 tabular-nums">{row.modelA}</td>
                <td className="p-2 tabular-nums">{row.modelB}</td>
                <td className="p-2 tabular-nums">{row.delta}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Card>
          <CardHeader title={`${a.name} sectors`} />
          <CardBody>
            <ul className="list-disc pl-5 text-sm text-[var(--muted)]">
              {cmp.sectorA.map((s) => (
                <li key={s.label}>
                  {s.label}: {s.pct}%
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title={`${b.name} sectors`} />
          <CardBody>
            <ul className="list-disc pl-5 text-sm text-[var(--muted)]">
              {cmp.sectorB.map((s) => (
                <li key={s.label}>
                  {s.label}: {s.pct}%
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

export const ModelPortfolioLibraryWorkspace = memo(function ModelPortfolioLibraryWorkspace() {
  return (
    <MpShell
      title="Model Portfolio Library"
      description="Growth · Balanced · Income · Value · Quality · Small Cap · Large Cap · Custom"
    >
      <ModelPortfolioLibrary />
    </MpShell>
  );
});

/** Default /advisor/portfolios entry */
export const ModelPortfolioWorkspace = ModelPortfolioLibraryWorkspace;

export const ScenarioComparisonWorkspace = memo(function ScenarioComparisonWorkspace() {
  return (
    <MpShell
      title="Scenario Comparison"
      description="Model A vs Model B — allocation, sectors, risk (presentation only)."
    >
      <ScenarioComparison />
    </MpShell>
  );
});

export const PortfolioTemplatesWorkspace = memo(function PortfolioTemplatesWorkspace() {
  return (
    <MpShell title="Portfolio Templates" description="Start from a demo template — open Builder to edit in session.">
      <div className="grid gap-3 md:grid-cols-2">
        {portfolioTemplates.map((t) => (
          <PortfolioTemplateCard
            key={t.id}
            name={t.name}
            blurb={t.blurb}
            category={t.category}
          />
        ))}
      </div>
      <p className="text-sm text-[var(--muted)]">
        Open the Builder to load and customize a session copy of a library model.
      </p>
    </MpShell>
  );
});

export const PortfolioNotesWorkspace = memo(function PortfolioNotesWorkspace() {
  const notes = useMemo(
    () => seedModelPortfolioLibrary.flatMap((p) => p.notes.map((n) => ({ ...n, portfolio: p.name }))),
    [],
  );
  return (
    <MpShell title="Portfolio Notes" description="Aggregated demo notes across library models — session display.">
      <div className="space-y-3">
        {notes.map((n) => (
          <Card key={`${n.id}-${n.portfolio}`}>
            <CardHeader
              title={n.title}
              description={n.portfolio}
              action={<Badge tone="neutral">{n.kind}</Badge>}
            />
            <CardBody className="text-sm text-[var(--muted)]">{n.body}</CardBody>
          </Card>
        ))}
      </div>
    </MpShell>
  );
});
